import csv
import os
import re
import unicodedata
from urllib.parse import quote_plus

import pandas as pd

# ============================================================
# UNIDADES DE SAÚDE DA CIDADE (CNES) -- "Onde ser atendida" (10/2026)
#
# Pergunta que o Escudo ainda não respondia: "onde, na minha cidade,
# uma mulher pode procurar atendimento?". O resto do painel conta
# internações; aqui o cadastro do CNES (arquivo tbEstabelecimento*.csv,
# em banco\cnes\) vira uma lista de endereços de gente de verdade:
# nome legível, tipo em palavras (e não o código), endereço, telefone,
# mapa e a separação pública x privada.
#
# Substitui a antiga "Rede local" (rede_servicos_local.py), que só
# despejava 5 colunas cruas, filtrava pelo município do GESTOR (não o
# do endereço) e mostrava o tipo como número.
#
# Regras (as mesmas do resto do Escudo):
#   - cadastro NÃO é serviço ativo nem vaga: a página sempre diz
#     "confirme antes de ir";
#   - só descreve; nunca ranqueia unidades nem diz qual é melhor;
#   - este módulo só LÊ o CSV (não grava nada, não mexe no banco).
#
# Não depende do Streamlit; a página é dashboard/pages/onde_ser_atendida.py.
# Teste: algoritimos/teste_unidades_saude.py
# Ver o que o arquivo tem (colunas reconhecidas):
#   py algoritimos\unidades_saude.py
# ============================================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_CNES = os.environ.get("ESCUDO_CNES_PASTA") or os.path.join(RAIZ_PROJETO, "banco", "cnes")  # a variável é para testes
CODIGO_IBGE_PADRAO = "3543907"  # Rio Claro
TAMANHO_PEDACO = 100_000        # linhas lidas por vez (o arquivo nacional é grande)

# Quadro em volta de Rio Claro (com folga) só para o MAPA: coordenada
# fora dele é erro de cadastro e não vai para o mapa (a unidade continua
# na lista). Para outra cidade, o quadro não está cadastrado: vale só a faixa do Brasil.
CAIXA_RIO_CLARO = (-22.65, -22.15, -48.05, -47.15)  # lat_min, lat_max, lon_min, lon_max

# Nomes das colunas do CNES variam entre as versões do arquivo; cada
# campo aceita várias (sem acento, maiúsculas, _ no lugar de espaço).
ALIASES = {
    "municipio_local": ("CO_IBGE", "CO_MUNICIPIO", "CO_MUNICIPIO_IBGE", "COD_IBGE", "CO_MUNICIPIO_ESTABELECIMENTO"),
    "municipio_gestor": ("CO_MUNICIPIO_GESTOR",),
    "cnes": ("CO_CNES", "CNES", "COD_CNES"),
    "nome": ("NO_FANTASIA", "NOME_FANTASIA", "NO_RAZAO_SOCIAL", "NOME"),
    "razao": ("NO_RAZAO_SOCIAL",),
    "tipo_codigo": ("TP_UNIDADE", "CO_TIPO_UNIDADE", "TIPO_UNIDADE"),
    "tipo_texto": ("DS_TIPO_UNIDADE",),
    "natureza": ("CO_NATUREZA_JUR", "CO_NATUREZA_JURIDICA"),
    "logradouro": ("NO_LOGRADOURO", "LOGRADOURO"),
    "numero": ("NU_ENDERECO", "NUMERO"),
    "bairro": ("NO_BAIRRO", "BAIRRO"),
    "cep": ("CO_CEP", "CEP"),
    "telefone": ("NU_TELEFONE", "TELEFONE"),
    "lat": ("NU_LATITUDE", "LATITUDE"),
    "lon": ("NU_LONGITUDE", "LONGITUDE"),
    "desabilitado": ("CO_MOTIVO_DESAB",),
}
ROTULO_CAMPO = {
    "municipio_local": "município do endereço", "municipio_gestor": "município do gestor", "cnes": "número do CNES",
    "nome": "nome", "tipo_codigo": "tipo de unidade", "natureza": "natureza jurídica (público/privado)",
    "logradouro": "rua", "numero": "número", "bairro": "bairro", "cep": "CEP", "telefone": "telefone",
    "lat": "latitude", "lon": "longitude", "desabilitado": "motivo de desabilitação",
}

# Para que serve cada grupo, em palavras de quem procura atendimento.
GRUPOS = {
    "basica": ("Posto ou UBS", "A porta de entrada: consulta, pedido de mamografia e de Papanicolau."),
    "especialidade": ("Exames e especialistas", "Policlínicas, clínicas de especialidade e unidades de exame."),
    "hospital": ("Hospitais", "Internação, cirurgia e tratamento."),
    "urgencia": ("Urgência", "Pronto atendimento e pronto-socorro."),
    "mental": ("Saúde mental (CAPS)", "Apoio psicológico e psiquiátrico."),
    "outros": ("Outros serviços", "Farmácia, vigilância, regulação e demais cadastros."),
}
ORDEM_GRUPOS = list(GRUPOS)

# Código TP_UNIDADE do CNES -> (descrição, grupo). Só os que são certos;
# código desconhecido vira "Tipo NN" no grupo "outros" (nunca inventado).
TIPOS = {
    "01": ("Posto de saúde", "basica"),
    "02": ("Centro de saúde / Unidade básica", "basica"),
    "71": ("Centro de apoio à saúde da família", "basica"),
    "04": ("Policlínica", "especialidade"),
    "22": ("Consultório isolado", "especialidade"),
    "36": ("Clínica / Centro de especialidade", "especialidade"),
    "39": ("Unidade de apoio a diagnose e terapia (exames)", "especialidade"),
    "05": ("Hospital geral", "hospital"),
    "07": ("Hospital especializado", "hospital"),
    "15": ("Unidade mista", "hospital"),
    "62": ("Hospital-dia", "hospital"),
    "20": ("Pronto-socorro geral", "urgencia"),
    "21": ("Pronto-socorro especializado", "urgencia"),
    "73": ("Pronto atendimento", "urgencia"),
    "42": ("Unidade móvel de urgência (SAMU)", "urgencia"),
    "70": ("Centro de atenção psicossocial (CAPS)", "mental"),
    "40": ("Unidade móvel terrestre", "outros"),
    "43": ("Farmácia", "outros"),
    "50": ("Unidade de vigilância em saúde", "outros"),
    "60": ("Cooperativa de profissionais de saúde", "outros"),
    "69": ("Centro de hemoterapia / hematologia", "outros"),
    "74": ("Polo academia da saúde", "outros"),
    "76": ("Central de regulação das urgências", "outros"),
    "77": ("Atenção domiciliar (home care)", "outros"),
    "78": ("Unidade de atenção em regime residencial", "outros"),
    "79": ("Oficina ortopédica", "outros"),
    "80": ("Laboratório de saúde pública", "outros"),
    "81": ("Central de regulação do acesso", "outros"),
}

# Primeiro dígito da natureza jurídica (tabela do IBGE/CNES):
# 1 administração pública, 2 empresarial, 3 sem fins lucrativos, 4 pessoa física.
NATUREZAS = {
    "publica": "Pública",
    "sem_fins": "Sem fins lucrativos (Santa Casa, associações: muitas atendem pelo SUS)",
    "privada": "Privada",
    "desconhecida": "Natureza não informada",
}
NATUREZA_CURTA = {"publica": "Pública", "sem_fins": "Sem fins lucrativos", "privada": "Privada",
                  "desconhecida": "Não informada"}

SIGLAS = {"UBS", "UPA", "CAPS", "AME", "USF", "PSF", "CEAD", "SAMU", "CRAS", "CREAS", "APAE", "UNESP", "FMS",
          "CTI", "UTI", "SUS", "ESF", "NASF", "CER", "SADT", "ONG", "SP", "RC", "II", "III", "IV", "VI", "VII",
          "VIII", "IX", "XI", "XII"}
LIGACOES = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para", "com"}


def _sem_acento(texto):
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()


def _chave(nome):
    """Nome de coluna comparável: sem acento, maiúsculo, sem BOM, _ no lugar de não-alfanumérico."""
    return re.sub(r"[^A-Z0-9]+", "_", _sem_acento(str(nome).lstrip("﻿")).upper()).strip("_")


def so_digitos(valor):
    return re.sub(r"\D", "", str(valor if valor is not None else ""))


def nome_legivel(nome):
    """'UBS JARDIM  NOVO DE SAO JOAO' -> 'UBS Jardim Novo de São João' (siglas ficam em maiúsculas).
    O CNES grava tudo em caixa alta e sem acento; o acento não dá para recuperar, só a caixa."""
    palavras = str(nome or "").split()
    saida = []
    for i, p in enumerate(palavras):
        parte = re.split(r"([-/()])", p)
        novas = []
        for q in parte:
            if not q or q in "-/()":
                novas.append(q)
            elif q.upper() in SIGLAS:
                novas.append(q.upper())
            elif q.lower() in LIGACOES and i > 0:
                novas.append(q.lower())
            else:
                novas.append(q[:1].upper() + q[1:].lower())
        saida.append("".join(novas))
    return " ".join(saida)


def telefone_legivel(valor):
    d = so_digitos(valor)
    if d.startswith("0") and len(d) > 8:
        d = d.lstrip("0")
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 8:
        return f"{d[:4]}-{d[4:]}"
    return d if len(d) >= 8 else ""


def cep_legivel(valor):
    d = so_digitos(valor)
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else ""


def endereco_legivel(logradouro, numero, bairro):
    rua = nome_legivel(logradouro)
    num = str(numero or "").strip()
    if num in ("0", "00", "S/N", "SN", "S N"):
        num = "s/n"
    partes = []
    if rua:
        partes.append(f"{rua}, {num}" if num else rua)
    if str(bairro or "").strip():
        partes.append(nome_legivel(bairro))
    return " – ".join(partes)


def link_mapa(nome, endereco, cidade):
    """Link de busca no Google Maps (a pessoa confere o ponto lá); não é geocodificação nossa."""
    consulta = ", ".join(p for p in (nome, endereco, cidade) if p)
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(consulta)


def classificar_tipo(codigo, descricao=""):
    """(descrição, grupo) do tipo de unidade, pelo código do CNES; se o arquivo trouxer o texto, usa o texto."""
    cod = so_digitos(codigo)
    cod = cod.zfill(2) if cod else ""
    texto = _sem_acento(str(descricao or "")).upper().strip()
    if cod in TIPOS and not texto:
        return TIPOS[cod]
    if texto:
        grupo = TIPOS[cod][1] if cod in TIPOS else _grupo_do_texto(texto)
        return nome_legivel(texto).replace("Ubs", "UBS"), grupo
    if cod:
        return f"Tipo {cod} (sem descrição)", "outros"
    return "Tipo não informado", "outros"


def _grupo_do_texto(texto):
    if "PSICOSSOCIAL" in texto:
        return "mental"
    if "HOSPITAL" in texto:
        return "hospital"
    if "PRONTO" in texto or "URGENCIA" in texto:
        return "urgencia"
    if "POSTO" in texto or "CENTRO DE SAUDE" in texto or "BASICA" in texto or "FAMILIA" in texto:
        return "basica"
    if "POLICLINICA" in texto or "CLINICA" in texto or "ESPECIALIDADE" in texto or "DIAGNOSE" in texto:
        return "especialidade"
    return "outros"


def classificar_natureza(codigo):
    """'publica' / 'sem_fins' / 'privada' / 'desconhecida', pelo 1º dígito da natureza jurídica (4 dígitos)."""
    d = so_digitos(codigo)
    if len(d) != 4:
        return "desconhecida"
    return {"1": "publica", "2": "privada", "3": "sem_fins", "4": "privada"}.get(d[0], "desconhecida")


# ---------- leitura do arquivo ----------

def achar_arquivo(pasta=PASTA_CNES):
    """tbEstabelecimento*.csv mais recente (o nome traz o ano e mês), ou None."""
    try:
        nomes = [n for n in os.listdir(pasta) if n.lower().startswith("tbestabelecimento") and n.lower().endswith(".csv")]
    except OSError:
        return None
    return os.path.join(pasta, sorted(nomes)[-1]) if nomes else None


def _codificacao(caminho):
    """utf-8 se a amostra for válida, senão latin-1 (o CNES costuma vir em latin-1)."""
    with open(caminho, "rb") as f:
        amostra = f.read(200_000)
    for corte in range(0, 4):  # a amostra pode cortar um caractere no meio
        try:
            (amostra[:-corte] if corte else amostra).decode("utf-8")
            return "utf-8-sig"
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _separador(caminho, codificacao):
    with open(caminho, "r", encoding=codificacao, errors="replace", newline="") as f:
        amostra = f.read(20_000)
    primeira = amostra.splitlines()[0] if amostra else ""
    contagem = {s: primeira.count(s) for s in (";", ",", "|", "\t")}
    melhor = max(contagem, key=contagem.get)
    if contagem[melhor] > 0:
        return melhor
    try:
        return csv.Sniffer().sniff(amostra, delimiters=";|,\t").delimiter
    except csv.Error:
        return ";"


def _mapear_colunas(colunas):
    """campo -> nome real da coluna no arquivo (só os que existem)."""
    por_chave = {}
    for c in colunas:
        por_chave.setdefault(_chave(c), c)
    achados = {}
    for campo, candidatos in ALIASES.items():
        for cand in candidatos:
            if cand in por_chave:
                achados[campo] = por_chave[cand]
                break
    return achados


def _vazio(aviso):
    df = pd.DataFrame()
    df.attrs["aviso"] = aviso
    return df


def diagnosticar(pasta=PASTA_CNES):
    """O que o arquivo tem: nome, colunas reconhecidas e as que faltam (para conferir sem abrir o CSV)."""
    caminho = achar_arquivo(pasta)
    if caminho is None:
        return {"arquivo": None, "reconhecidas": {}, "ausentes": [], "colunas": []}
    cod = _codificacao(caminho)
    colunas = list(pd.read_csv(caminho, sep=_separador(caminho, cod), encoding=cod, dtype=str, nrows=0).columns)
    achados = _mapear_colunas(colunas)
    return {"arquivo": os.path.basename(caminho), "reconhecidas": achados,
            "ausentes": [ROTULO_CAMPO[c] for c in ROTULO_CAMPO if c not in achados], "colunas": colunas}


def carregar_unidades(pasta=PASTA_CNES, codigo_ibge=CODIGO_IBGE_PADRAO, nome_cidade="Rio Claro",
                      tamanho_pedaco=TAMANHO_PEDACO):
    """Unidades ativas da cidade, uma linha por CNES. Colunas: cnes, nome, tipo, grupo, natureza,
    endereco, bairro, cep, telefone, lat, lon, mapa (lat/lon só quando o ponto cai dentro da cidade).
    Se não der para confirmar o município, devolve vazio com o motivo em attrs['aviso'] (nunca chuta)."""
    caminho = achar_arquivo(pasta)
    if caminho is None:
        return _vazio("O arquivo de estabelecimentos do CNES (tbEstabelecimento*.csv) não está em banco\\cnes. "
                      "Baixe a base do CNES em cnes.datasus.gov.br (Download de dados) e coloque o arquivo nessa pasta.")
    cod = _codificacao(caminho)
    sep = _separador(caminho, cod)
    try:
        colunas = list(pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, nrows=0).columns)
    except Exception as erro:
        return _vazio(f"Não consegui ler o cabeçalho de {os.path.basename(caminho)}: {erro}")
    achados = _mapear_colunas(colunas)

    if "municipio_local" in achados:
        campo_municipio, criterio = "municipio_local", "endereço"
    elif "municipio_gestor" in achados:
        campo_municipio, criterio = "municipio_gestor", "gestor"
    else:
        return _vazio(f"O arquivo {os.path.basename(caminho)} não tem coluna de município reconhecida, e sem ela "
                      "não dá para saber quais unidades são da cidade. Colunas encontradas: "
                      + ", ".join(map(str, colunas[:30])))
    if "nome" not in achados:
        return _vazio(f"O arquivo {os.path.basename(caminho)} não tem coluna de nome (NO_FANTASIA). "
                      "Colunas encontradas: " + ", ".join(map(str, colunas[:30])))

    alvo = so_digitos(codigo_ibge)[:6]
    usar = list(dict.fromkeys(achados.values()))
    pedacos = []
    try:
        for pedaco in pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, usecols=usar,
                                  chunksize=tamanho_pedaco, keep_default_na=False, low_memory=False):
            codigos = pedaco[achados[campo_municipio]].map(so_digitos).str[:6]
            pedacos.append(pedaco.loc[codigos == alvo])
    except Exception as erro:
        return _vazio(f"Falha ao ler {os.path.basename(caminho)}: {erro}")
    bruto = pd.concat(pedacos, ignore_index=True) if pedacos else pd.DataFrame(columns=usar)

    def coluna(campo):
        return bruto[achados[campo]].astype(str).str.strip() if campo in achados else pd.Series("", index=bruto.index)

    ativo = pd.Series(True, index=bruto.index)
    if "desabilitado" in achados:
        motivo = coluna("desabilitado").map(so_digitos).str.lstrip("0")
        ativo = motivo == ""
    desabilitados = int((~ativo).sum())

    df = pd.DataFrame({
        "cnes": coluna("cnes").map(so_digitos).str.zfill(7),
        "nome": [nome_legivel(n) or nome_legivel(r) for n, r in
                 zip(coluna("nome"), coluna("razao") if "razao" in achados else coluna("nome"))],
        "tipo_codigo": coluna("tipo_codigo"),
        "tipo_texto": coluna("tipo_texto"),
        "natureza": coluna("natureza").map(classificar_natureza) if "natureza" in achados
        else pd.Series("desconhecida", index=bruto.index),
        "logradouro": coluna("logradouro"), "numero": coluna("numero"), "bairro_cru": coluna("bairro"),
        "cep": coluna("cep").map(cep_legivel), "telefone": coluna("telefone").map(telefone_legivel),
        "lat": pd.to_numeric(coluna("lat").str.replace(",", ".", regex=False), errors="coerce"),
        "lon": pd.to_numeric(coluna("lon").str.replace(",", ".", regex=False), errors="coerce"),
    })[ativo.values].reset_index(drop=True)

    tipos = [classificar_tipo(c, t) for c, t in zip(df["tipo_codigo"], df["tipo_texto"])]
    df["tipo"] = [t[0] for t in tipos]
    df["grupo"] = [t[1] for t in tipos]
    df["bairro"] = df["bairro_cru"].map(nome_legivel)
    df["endereco"] = [endereco_legivel(r, n, b) for r, n, b in zip(df["logradouro"], df["numero"], df["bairro_cru"])]
    df["mapa"] = _pontos_validos(df["lat"], df["lon"], alvo)
    df["link_mapa"] = [link_mapa(n, e, nome_cidade) for n, e in zip(df["nome"], df["endereco"])]

    com_cnes = df["cnes"].str.strip("0") != ""
    df = pd.concat([df[com_cnes].drop_duplicates("cnes", keep="first"), df[~com_cnes]], ignore_index=True)
    df = df[df["nome"] != ""].reset_index(drop=True)
    df["grupo"] = pd.Categorical(df["grupo"], categories=ORDEM_GRUPOS, ordered=True)
    df = df.sort_values(["grupo", "nome"]).reset_index(drop=True)
    df = df[["cnes", "nome", "tipo", "grupo", "natureza", "endereco", "bairro", "cep", "telefone",
             "lat", "lon", "mapa", "link_mapa"]]

    df.attrs.update({
        "arquivo": os.path.basename(caminho), "criterio_municipio": criterio, "desabilitados": desabilitados,
        "ausentes": [ROTULO_CAMPO[c] for c in ROTULO_CAMPO if c not in achados],
        "tem_natureza": "natureza" in achados,
        "aviso": ("" if len(df) else
                  f"O arquivo {os.path.basename(caminho)} foi lido, mas nenhum estabelecimento tem o código "
                  f"{so_digitos(codigo_ibge)} na coluna de município ({achados[campo_municipio]})."),
    })
    return df


def _pontos_validos(lat, lon, alvo):
    """True onde a coordenada existe e cai dentro da cidade. Rio Claro: quadro fixo. Outra cidade: só
    exige faixa do Brasil (o quadro dela não está cadastrado)."""
    if alvo == CODIGO_IBGE_PADRAO[:6]:
        la0, la1, lo0, lo1 = CAIXA_RIO_CLARO
    else:
        la0, la1, lo0, lo1 = -34.0, 6.0, -74.0, -34.0
    return lat.between(la0, la1) & lon.between(lo0, lo1)


# ---------- o que a página mostra ----------

def contar_por_grupo(df):
    """Quantas unidades em cada grupo (todas as naturezas), na ordem de ORDEM_GRUPOS."""
    if df.empty:
        return {g: 0 for g in ORDEM_GRUPOS}
    cont = df["grupo"].astype(str).value_counts()
    return {g: int(cont.get(g, 0)) for g in ORDEM_GRUPOS}


def filtrar(df, grupos=None, naturezas=None, busca="", bairro=None):
    """Recorte da lista. `grupos`/`naturezas`: listas de chaves (None = todas). `busca` procura no nome,
    no endereço e no CNES, sem acento nem caixa."""
    if df.empty:
        return df
    saida = df
    if grupos is not None:
        saida = saida[saida["grupo"].astype(str).isin(grupos)]
    if naturezas is not None:
        saida = saida[saida["natureza"].isin(naturezas)]
    if bairro:
        saida = saida[saida["bairro"] == bairro]
    termo = _sem_acento(str(busca or "")).casefold().strip()
    if termo:
        alvo = (saida["nome"] + " " + saida["endereco"] + " " + saida["cnes"]).map(lambda t: _sem_acento(t).casefold())
        saida = saida[alvo.str.contains(re.escape(termo), na=False)]
    return saida.reset_index(drop=True)


def leitura_lista(df, mostrados, grupos_escolhidos, so_sus_provavel):
    """Frases (sem causa, sem ranking) que explicam o que a lista mostra e o que ela NÃO garante."""
    if df.empty:
        return []
    frases = [f"{len(mostrados)} unidade(s) na lista, de {len(df)} cadastros ativos do CNES na cidade."]
    if so_sus_provavel:
        frases.append("A lista mostra unidades públicas e sem fins lucrativos, onde é mais provável haver atendimento "
                      "pelo SUS. O cadastro do CNES, porém, não diz quais convênios cada unidade mantém.")
    frases.append("Estar no CNES não garante que a unidade esteja aberta hoje, que tenha vaga, nem que atenda o seu caso: "
                  "ligue ou procure a unidade de saúde do seu bairro antes de ir.")
    if "basica" in (grupos_escolhidos or []):
        frases.append("Mamografia e Papanicolau costumam começar na unidade básica, com a solicitação de um profissional de saúde.")
    return frases


def resumo_diagnostico(pasta=PASTA_CNES):
    """Texto de uma linha por coluna reconhecida (para a página e para o terminal)."""
    d = diagnosticar(pasta)
    if d["arquivo"] is None:
        return ["Nenhum tbEstabelecimento*.csv em " + pasta]
    linhas = [f"Arquivo: {d['arquivo']} ({len(d['colunas'])} colunas)"]
    for campo, real in d["reconhecidas"].items():
        linhas.append(f"  reconhecida  {ROTULO_CAMPO.get(campo, campo):<38} <- {real}")
    for rotulo in d["ausentes"]:
        linhas.append(f"  FALTA        {rotulo}")
    return linhas


if __name__ == "__main__":
    print("\n".join(resumo_diagnostico()))
    dados = carregar_unidades()
    if dados.attrs.get("aviso"):
        print("\nAviso:", dados.attrs["aviso"])
    print(f"\n{len(dados)} unidades ativas em Rio Claro (município pelo {dados.attrs.get('criterio_municipio', '?')}).")
    if len(dados):
        print(dados.groupby(["grupo", "natureza"], observed=True).size().to_string())
