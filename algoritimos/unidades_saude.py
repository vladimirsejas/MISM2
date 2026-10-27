import csv
import os
import re
import unicodedata
from urllib.parse import quote_plus

import pandas as pd

try:
    import fonte_parquet as _pq  # tabelas do CNES em dados_parquet/cnes, quando o CSV não está no computador
except ImportError:
    _pq = None

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
    "unidade": ("CO_UNIDADE",),
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

def _so_parquet(caminho):
    """True quando o CSV não existe aqui mas a tabela existe em Parquet."""
    return _pq is not None and not os.path.isfile(caminho) and _pq.parquet_do_csv(caminho) is not None


def _existe(caminho):
    return os.path.isfile(caminho) or (_pq is not None and _pq.parquet_do_csv(caminho) is not None)


def _ler_csv(caminho, **opcoes):
    """pandas.read_csv; se só houver o Parquet da tabela, lê dele (mesmas opções usadas aqui)."""
    if _so_parquet(caminho):
        return _pq.ler(caminho, **opcoes)
    return pd.read_csv(caminho, **opcoes)


def achar_arquivo(pasta=PASTA_CNES):
    """tbEstabelecimento*.csv mais recente (o nome traz o ano e mês), ou None. Procura na pasta e,
    se não achar ali, nas subpastas (o pacote do CNES costuma abrir numa pasta como
    BASE_DE_DADOS_CNES_AAAAMM)."""
    achados = []
    if os.path.isdir(pasta):
        for raiz, subpastas, nomes in os.walk(pasta):
            achados += [(n.lower(), os.path.join(raiz, n)) for n in nomes
                        if n.lower().startswith("tbestabelecimento") and n.lower().endswith(".csv")]
            if achados:  # o que está na própria pasta vale mais que o de subpastas
                break
    if achados:
        return sorted(achados)[-1][1]
    if _pq is not None and _pq.competencia_cnes():  # sem o CSV: o Parquet, com o nome que o CSV teria
        virtual = os.path.join(pasta, f"tbEstabelecimento{_pq.competencia_cnes()}.csv")
        if _pq.parquet_do_csv(virtual):
            return virtual
    return None


def _codificacao(caminho):
    """utf-8 se a amostra for válida, senão latin-1 (o CNES costuma vir em latin-1)."""
    if _so_parquet(caminho):
        return "utf-8-sig"
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
    if _so_parquet(caminho):
        return ";"
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


def _colunas_por_nome(caminho):
    """Lê apenas o cabeçalho e devolve nomes de coluna comparáveis do arquivo CNES."""
    cod = _codificacao(caminho)
    sep = _separador(caminho, cod)
    colunas = list(_ler_csv(caminho, sep=sep, encoding=cod, dtype=str, nrows=0).columns)
    return sep, cod, {_chave(c): c for c in colunas}


# O CNES registra, em cada serviço da unidade, se ele é PRÓPRIO (TP_CARACTERISTICA = 1) ou feito por TERCEIRO (2: outro
# estabelecimento, identificado em CO_CNPJCPF). Uma UBS "tem" radiologia, ultrassom e mamografia por terceiro, mas não faz
# esses exames no local (visto no CNES real de Rio Claro, 18/10/2026; o autor, que trabalha na FMSRC, confirmou a rede).
# O texto de serviços marca o que é por terceiro com esta etiqueta; a busca só conta o que é próprio.
TAG_TERCEIRO = " [POR TERCEIRO]"


def _servicos_cnes(caminho_estabelecimento, unidades, tamanho_pedaco=TAMANHO_PEDACO):
    """Agrupa serviços e classificações pelas unidades selecionadas (próprios e por terceiro, estes com TAG_TERCEIRO), sem ler dados profissionais."""
    unidades = {so_digitos(u) for u in unidades if so_digitos(u)}
    if not unidades:
        return {}, ""
    mes = re.search(r"(\d{6})\.csv$", os.path.basename(caminho_estabelecimento), re.IGNORECASE)
    if not mes:
        return {}, "O mês do arquivo de estabelecimentos não foi reconhecido; serviços CNES não carregados."
    pasta = os.path.dirname(caminho_estabelecimento)
    relacao = os.path.join(pasta, f"rlEstabServClass{mes.group(1)}.csv")
    classificacoes = os.path.join(pasta, f"tbClassificacaoServico{mes.group(1)}.csv")
    servicos = os.path.join(pasta, f"tbServicoEspecializado{mes.group(1)}.csv")
    if not all(_existe(p) for p in (relacao, classificacoes, servicos)):
        return {}, "Os arquivos de serviços do CNES do mesmo mês não estão disponíveis."

    try:
        sep_c, cod_c, cols_c = _colunas_por_nome(classificacoes)
        sep_s, cod_s, cols_s = _colunas_por_nome(servicos)
        _, _, cols_r = _colunas_por_nome(relacao)
        # A relação só traz códigos nas colunas consumidas e pode conter bytes de usuário CNES
        # que não seguem UTF-8. Latin-1 preserva esses códigos sem interromper o processamento.
        sep_r, cod_r = _separador(relacao, "latin-1"), "latin-1"
        class_cols = [cols_c[_chave(k)] for k in ("CO_SERVICO_ESPECIALIZADO", "CO_CLASSIFICACAO_SERVICO", "DS_CLASSIFICACAO_SERVICO")]
        service_cols = [cols_s[_chave(k)] for k in ("CO_SERVICO_ESPECIALIZADO", "DS_SERVICO_ESPECIALIZADO")]
        relation_cols = [cols_r[_chave(k)] for k in ("CO_UNIDADE", "CO_SERVICO", "CO_CLASSIFICACAO")]
        col_caracteristica = cols_r.get(_chave("TP_CARACTERISTICA"))  # arquivos antigos podem não ter: tudo conta como próprio
        usar_relacao = relation_cols + ([col_caracteristica] if col_caracteristica else [])
        classes = _ler_csv(classificacoes, sep=sep_c, encoding=cod_c, dtype=str, usecols=class_cols,
                              keep_default_na=False, low_memory=False)
        nomes_classes = {
            (so_digitos(r[class_cols[0]]), so_digitos(r[class_cols[1]])): str(r[class_cols[2]]).strip()
            for _, r in classes.iterrows() if str(r[class_cols[2]]).strip()
        }
        tabela_servicos = _ler_csv(servicos, sep=sep_s, encoding=cod_s, dtype=str, usecols=service_cols,
                                      keep_default_na=False, low_memory=False)
        nomes_servicos = {
            so_digitos(r[service_cols[0]]): str(r[service_cols[1]]).strip()
            for _, r in tabela_servicos.iterrows() if str(r[service_cols[1]]).strip()
        }
        proprios, terceiros = {}, {}
        for pedaco in _ler_csv(relacao, sep=sep_r, encoding=cod_r, dtype=str, usecols=usar_relacao,
                                  chunksize=tamanho_pedaco, keep_default_na=False, low_memory=False):
            ids = pedaco[relation_cols[0]].map(so_digitos)
            pedaco = pedaco.loc[ids.isin(unidades)]
            for _, r in pedaco.iterrows():
                unidade = so_digitos(r[relation_cols[0]])
                servico = so_digitos(r[relation_cols[1]])
                classificacao = so_digitos(r[relation_cols[2]])
                por_terceiro = bool(col_caracteristica) and so_digitos(r[col_caracteristica]) == "2"
                destino = terceiros if por_terceiro else proprios
                for rotulo in (nomes_classes.get((servico, classificacao), ""), nomes_servicos.get(servico, "")):
                    if rotulo:
                        destino.setdefault(unidade, set()).add(rotulo)
        por_unidade = {}
        for u in set(proprios) | set(terceiros):
            meus = proprios.get(u, set())
            so_terceiro = terceiros.get(u, set()) - meus  # o que a unidade também faz por conta própria não é "só por terceiro"
            por_unidade[u] = sorted(meus) + sorted(f"{x}{TAG_TERCEIRO}" for x in so_terceiro)
        return {u: " | ".join(itens) for u, itens in por_unidade.items()}, ""
    except (OSError, ValueError, KeyError, pd.errors.ParserError, pd.errors.EmptyDataError) as erro:
        return {}, f"Não foi possível ler as relações de serviços do CNES: {erro}"


# Ocupações (CBO) de quem atende a pessoa e que a busca "Onde ser atendida" reconhece. Técnicos e agentes ficam de fora;
# "médico veterinário" também (aparece no cadastro e não é saúde humana).
PROFISSOES_BUSCAVEIS = ("MEDICO", "PSICOLOGO", "NUTRICIONISTA", "FISIOTERAPEUTA", "CIRURGIAO DENTISTA", "ASSISTENTE SOCIAL",
                        "ENFERMEIRO", "FONOAUDIOLOGO", "TERAPEUTA OCUPACIONAL", "FARMACEUTICO")


def _profissao_buscavel(nome):
    n = _sem_acento(str(nome)).upper().strip()
    return n.startswith(PROFISSOES_BUSCAVEIS) and not n.startswith("MEDICO VETERINARIO")


def _medicos_cnes(caminho_estabelecimento, unidades, tamanho_pedaco=TAMANHO_PEDACO):
    """Médicos e outros profissionais de saúde cadastrados por unidade ("MEDICO DERMATOLOGISTA (2 no ambulatório, 3 cadastrados)").

    Só CONTA: o código do profissional é usado na memória para não contar a mesma pessoa duas vezes e
    não é guardado; nenhum nome, registro de conselho ou carga horária sai desta função. Conta quem tem
    carga horária ambulatorial no cadastro. É cadastro, não agenda: não diz que há consulta marcada.
    """
    unidades = {so_digitos(u) for u in unidades if so_digitos(u)}
    if not unidades:
        return {}, ""
    mes = re.search(r"(\d{6})\.csv$", os.path.basename(caminho_estabelecimento), re.IGNORECASE)
    if not mes:
        return {}, "O mês do arquivo de estabelecimentos não foi reconhecido; especialidades médicas não carregadas."
    pasta = os.path.dirname(caminho_estabelecimento)
    carga = os.path.join(pasta, f"tbCargaHorariaSus{mes.group(1)}.csv")
    ocupacoes = os.path.join(pasta, f"tbAtividadeProfissional{mes.group(1)}.csv")
    if not all(_existe(p) for p in (carga, ocupacoes)):
        return {}, "Os arquivos de profissionais do CNES do mesmo mês não estão disponíveis; só serviços e exames são buscados."
    try:
        sep_o, cod_o, cols_o = _colunas_por_nome(ocupacoes)
        col_cbo, col_nome = cols_o[_chave("CO_CBO")], cols_o[_chave("DS_ATIVIDADE_PROFISSIONAL")]
        tabela = _ler_csv(ocupacoes, sep=sep_o, encoding=cod_o, dtype=str, usecols=[col_cbo, col_nome],
                             keep_default_na=False)
        medicas = {str(r[col_cbo]).strip(): str(r[col_nome]).strip() for _, r in tabela.iterrows()
                   if _profissao_buscavel(r[col_nome])}
        # tbCargaHorariaSus tem ~1 GB e traz bytes fora de UTF-8 (nomes de usuário do cadastro) bem depois do começo:
        # a amostra de _codificacao (200 KB) não os vê. Só lemos códigos, então latin-1 (nunca falha) é seguro.
        cod_c = "latin-1"
        sep_c = _separador(carga, cod_c)
        cols_c = {_chave(c): c for c in _ler_csv(carga, sep=sep_c, encoding=cod_c, dtype=str, nrows=0).columns}
        c_unidade, c_pessoa, c_cbo, c_horas = (cols_c[_chave(k)] for k in (
            "CO_UNIDADE", "CO_PROFISSIONAL_SUS", "CO_CBO", "QT_CARGA_HORARIA_AMBULATORIAL"))
        pessoas = {}      # (unidade, cbo) -> profissionais cadastrados; só na memória
        ambulatorio = {}  # (unidade, cbo) -> os que têm carga horária ambulatorial
        for pedaco in _ler_csv(carga, sep=sep_c, encoding=cod_c, dtype=str, usecols=[c_unidade, c_pessoa, c_cbo, c_horas],
                                  chunksize=tamanho_pedaco, keep_default_na=False, low_memory=False):
            pedaco = pedaco.loc[pedaco[c_unidade].map(so_digitos).isin(unidades) & pedaco[c_cbo].str.strip().isin(medicas)]
            horas = pd.to_numeric(pedaco[c_horas].str.replace(",", ".", regex=False), errors="coerce").fillna(0)
            for u, p, c, h in zip(pedaco[c_unidade], pedaco[c_pessoa], pedaco[c_cbo], horas):
                chave = (so_digitos(u), c.strip())
                pessoas.setdefault(chave, set()).add(p)
                if h > 0:
                    ambulatorio.setdefault(chave, set()).add(p)
        por_unidade = {}
        for (u, cbo), quem in pessoas.items():
            n, a = len(quem), len(ambulatorio.get((u, cbo), ()))
            por_unidade.setdefault(u, []).append(
                f"{medicas[cbo]} ({a} no ambulatório, {n} cadastrado{'s' if n != 1 else ''})")
        return {u: " | ".join(sorted(v)) for u, v in por_unidade.items()}, ""
    except (OSError, ValueError, KeyError, pd.errors.ParserError, pd.errors.EmptyDataError) as erro:
        return {}, f"Não foi possível ler os profissionais do CNES: {erro}"


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
    colunas = list(_ler_csv(caminho, sep=_separador(caminho, cod), encoding=cod, dtype=str, nrows=0).columns)
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
        colunas = list(_ler_csv(caminho, sep=sep, encoding=cod, dtype=str, nrows=0).columns)
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
        for pedaco in _ler_csv(caminho, sep=sep, encoding=cod, dtype=str, usecols=usar,
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
    ids_unidade = (coluna("unidade") if "unidade" in achados else pd.Series("", index=bruto.index))
    servicos_por_unidade, aviso_servicos = _servicos_cnes(caminho, ids_unidade[ativo], tamanho_pedaco)
    medicos_por_unidade, aviso_medicos = _medicos_cnes(caminho, ids_unidade[ativo], tamanho_pedaco)
    for u, texto in medicos_por_unidade.items():
        servicos_por_unidade[u] = " | ".join(x for x in (servicos_por_unidade.get(u, ""), texto) if x)

    df = pd.DataFrame({
        "cnes": coluna("cnes").map(so_digitos).str.zfill(7),
        "servicos": [servicos_por_unidade.get(so_digitos(u), "") for u in ids_unidade],
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
             "lat", "lon", "mapa", "link_mapa", "servicos"]]

    df.attrs.update({
        "arquivo": os.path.basename(caminho), "criterio_municipio": criterio, "desabilitados": desabilitados,
        "ausentes": [ROTULO_CAMPO[c] for c in ROTULO_CAMPO if c not in achados],
        "tem_natureza": "natureza" in achados,
        "aviso": ("" if len(df) else
                  f"O arquivo {os.path.basename(caminho)} foi lido, mas nenhum estabelecimento tem o código "
                  f"{so_digitos(codigo_ibge)} na coluna de município ({achados[campo_municipio]})."),
        "aviso_servicos": aviso_servicos, "aviso_medicos": aviso_medicos,
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
        servicos = saida["servicos"] if "servicos" in saida else pd.Series("", index=saida.index)
        alvo = (saida["nome"] + " " + saida["endereco"] + " " + saida["cnes"] + " " + servicos).map(
            lambda t: _sem_acento(t).casefold())
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
