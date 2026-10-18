"""Onde ser atendida: uma lista só, em palavras de quem procura, com Google Maps (10/2026).

Junta duas fontes que se completam:
  - CNES (unidades_saude.py): cadastro oficial e completo das unidades de saúde, mas sem horário
    e quase sempre sem telefone;
  - catálogo conferido (dados_geograficos/catalogo_servicos_rioclaro.json): menor, com telefone,
    horário, fonte e data de verificação em cada item, e o apoio à mulher (Secretaria da Mulher,
    DDM, Defensoria, CRAS...), que o CNES não tem.

Sem o arquivo do CNES a lista continua existindo (só com o catálogo): a página nunca fica vazia.
Só descreve; cadastro não é vaga nem serviço aberto, e a página diz isso. Não depende do Streamlit;
a página é dashboard/pages/onde_ser_atendida.py. Teste: algoritimos/teste_onde_atendida.py
"""
import difflib
import json
import os
import re
from urllib.parse import quote_plus

import pandas as pd

import unidades_saude as us

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_CATALOGO = os.environ.get("ESCUDO_CATALOGO") or os.path.join(
    RAIZ_PROJETO, "dados_geograficos", "catalogo_servicos_rioclaro.json")

# Caixa de Rio Claro: coordenada fora dela é erro de cadastro e não vai para o mapa.
CAIXA = us.CAIXA_RIO_CLARO

# O que a pessoa procura (poucas escolhas, em palavras): chave -> (rótulo, o que é)
ESCOLHAS = {
    "basica": ("Posto de saúde", "A porta de entrada: consulta, pedido de mamografia e de Papanicolau."),
    "especialidade": ("Exames e especialistas", "Ambulatório, laboratório e clínicas de especialidade."),
    "hospital": ("Hospital", "Internação, cirurgia e tratamento."),
    "urgencia": ("Urgência", "Pronto atendimento e pronto-socorro."),
    "mental": ("Saúde mental", "Apoio psicológico e psiquiátrico (CAPS)."),
    "apoio": ("Apoio à mulher", "Secretaria da Mulher, delegacia, defensoria, assistência social (CRAS e CREAS) e acolhimento."),
}
ORDEM = list(ESCOLHAS) + ["outros"]

# catálogo: subtipo -> (escolha, tipo em palavras). O que não está aqui não entra (creche, curso, farmácia...).
SUBTIPOS = {
    "ubs": ("basica", "Unidade básica de saúde"),
    "especialidades": ("especialidade", "Ambulatório de especialidades"),
    "laboratorio": ("especialidade", "Laboratório"),
    "hospital": ("hospital", "Hospital"),
    "urgencia": ("urgencia", "Pronto atendimento"),
    "caps": ("mental", "Saúde mental (CAPS)"),
}
APOIO = {  # (tipo, subtipo) -> tipo em palavras
    ("mulher", "secretaria"): "Secretaria da Mulher",
    ("mulher", "ddm"): "Delegacia de Defesa da Mulher",
    ("mulher", "patrulha"): "Patrulha Maria da Penha",
    ("mulher", "defensoria"): "Defensoria Pública",
    ("assistencia", "cras"): "CRAS (assistência social)",
    ("assistencia", "creas"): "CREAS (assistência social)",
    ("assistencia", "acolhimento"): "Acolhimento",
}

PRIMEIRO_NO_APOIO = {"Secretaria da Mulher", "Delegacia de Defesa da Mulher", "Patrulha Maria da Penha", "Defensoria Pública"}

COLUNAS = ["cnes", "nome", "tipo", "grupo", "natureza", "endereco", "bairro", "cep", "telefone", "horario", "servicos",
           "conferido_em", "aviso", "fonte_url", "origem", "lat", "lon", "mapa", "link_chegar", "link_ligar"]

# Tradução local de palavras que mulheres usam para descrições do cadastro CNES.
# Os rótulos-alvo foram conferidos nas classificações existentes na base do projeto.
SINONIMOS_SERVICOS = {
    "mamo": ("MAMOGRAFIA",), "mamografia": ("MAMOGRAFIA",), "mamografias": ("MAMOGRAFIA",),
    "ultrassom": ("ULTRASONOGRAFIA", "ULTRASSONOGRAFIA"), "ultra som": ("ULTRASONOGRAFIA", "ULTRASSONOGRAFIA"),
    "usg": ("ULTRASONOGRAFIA", "ULTRASSONOGRAFIA"), "ultrassonografia": ("ULTRASONOGRAFIA", "ULTRASSONOGRAFIA"),
    "ultrasonografia": ("ULTRASONOGRAFIA", "ULTRASSONOGRAFIA"),
    "preventivo": ("EXAMES CITOPATOLOGICOS",), "papanicolau": ("EXAMES CITOPATOLOGICOS",),
    "papanicolaou": ("EXAMES CITOPATOLOGICOS",),
    "ginecologista": ("DO APARELHO GINECOLOGICO", "GINECOLOGISTA"), "ginecologia": ("DO APARELHO GINECOLOGICO", "GINECOLOGISTA"),
    # especialidades médicas: vêm do cadastro de profissionais do CNES (ocupação "MEDICO ...")
    "dermatologia": ("DERMATOLOG",), "pele": ("DERMATOLOG",),
    "cardiologia": ("CARDIOLOG",), "ortopedia": ("ORTOPED",), "ortopedista": ("ORTOPED",),
    "oftalmologia": ("OFTALMOLOG",), "oculista": ("OFTALMOLOG",), "mastologia": ("MASTOLOG",),
    "endocrinologia": ("ENDOCRINOLOG",), "psiquiatria": ("PSIQUIATR",), "neurologia": ("NEUROLOG",),
    "raio x": ("RADIOLOGIA",), "raiox": ("RADIOLOGIA",), "radiografia": ("RADIOLOGIA",), "rx": ("RADIOLOGIA",),
    "laboratorio": ("SERVICO DE DIAGNOSTICO DE LABORATORIO CLINICO",),
    "exame de sangue": ("SERVICO DE DIAGNOSTICO DE LABORATORIO CLINICO",),
    "exames de sangue": ("SERVICO DE DIAGNOSTICO DE LABORATORIO CLINICO",),
    "oncologista": ("ONCOLOGIA CLINICA", "ONCOLOGISTA"),
    "coracao": ("CARDIOLOG",), "olho": ("OFTALMOLOG",), "olhos": ("OFTALMOLOG",), "vista": ("OFTALMOLOG",),
    "osso": ("ORTOPED",), "ossos": ("ORTOPED",), "ouvido": ("OTORRINO",), "garganta": ("OTORRINO",), "nariz": ("OTORRINO",),
    "diabetes": ("ENDOCRINOLOG",), "tireoide": ("ENDOCRINOLOG",), "mama": ("MASTOLOG", "MAMOGRAFIA"), "seio": ("MASTOLOG", "MAMOGRAFIA"),
    "gestante": ("PRE NATAL", "GINECOLOGISTA"), "gravida": ("PRE NATAL", "GINECOLOGISTA"), "gravidez": ("PRE NATAL", "GINECOLOGISTA"),
    "crianca": ("PEDIATRA",), "bebe": ("PEDIATRA",), "idoso": ("GERIATRA",), "dentista": ("DENTISTA",), "dente": ("DENTISTA",),
    "psiquiatria": ("PSIQUIATR",), "estomago": ("GASTRO",), "intestino": ("GASTRO", "COLOPROCT"), "rim": ("NEFRO",),
    "coluna": ("ORTOPED", "NEUROLOG"), "alergia": ("ALERGIST", "IMUNOLOG"), "sangue": ("HEMATOLOG", "LABORATORIO CLINICO"),
}
# Rótulos que dizem que a UNIDADE FAZ o exame. Só valem no texto de serviços: um médico "em radiologia" cadastrado
# numa unidade não significa que ela tenha o aparelho de raio X (visto no CNES real, 18/10/2026).
SO_NOS_SERVICOS = {"MAMOGRAFIA", "ULTRASONOGRAFIA", "ULTRASSONOGRAFIA", "EXAMES CITOPATOLOGICOS", "RADIOLOGIA",
                   "SERVICO DE DIAGNOSTICO DE LABORATORIO CLINICO"}
PARADA_BUSCA = {"A", "AO", "AOS", "AS", "COM", "DA", "DAS", "DE", "DO", "DOS", "E", "EM", "NA", "NAS", "NO", "NOS",
                "O", "OS", "PARA", "PELO", "PELA", "POR", "QUERO", "PRECISO", "PROCURO", "PROCURE", "BUSCAR", "CONSIGO",
                "ONDE", "FAZER", "FAZ", "TEM", "UM", "UMA", "SUS", "CONSULTA", "CONSULTAR", "AGENDAR", "AGENDAMENTO",
                "MARCAR", "MARCACAO", "ATENDIMENTO", "ATENDER", "EXAME", "EXAMES", "PROBLEMA", "PROBLEMAS",
                "MEDICO", "MEDICA", "DOUTOR", "DOUTORA", "ESPECIALISTA", "TRATAMENTO", "PROFISSIONAL", "UNIDADE", "LUGAR", "CLINICA",
                "FACO", "FACA", "FAZEMOS", "POSSO", "PODE", "PODEM", "QUERIA", "GOSTARIA", "NECESSITO", "TENHO", "ESTOU",
                "PROCURANDO", "ACHAR", "ENCONTRAR", "ALGUM", "ALGUMA", "QUAL", "QUAIS", "COMO", "AQUI", "PERTO", "MINHA", "MEU",
                "PRA", "PARA", "SE", "QUE", "SEM", "GRATIS", "GRATUITO", "GRATUITA", "DE", "DO", "DA"}


def link_como_chegar(nome, endereco, cidade="Rio Claro"):
    """Rota no Google Maps até o lugar. Sem origem, o Maps parte da localização de quem abre o link."""
    consulta = ", ".join(p for p in (nome, endereco, cidade, "SP") if p)
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(consulta)


def link_ligar(telefone, ddd="19"):
    """tel: do primeiro número do texto, ou '' (sem telefone legível). Aceita '(19) 3535-4558 / (19) 3532-6991',
    '(19) 9 9956-3042 (WhatsApp)', '3534-1234' e '0800 ...'."""
    texto = str(telefone or "")
    achou = re.search(r"0800[\s\d-]{7,}", texto)
    if achou:
        return "tel:" + re.sub(r"\D", "", achou.group(0))
    achou = re.search(r"(?:\(?(\d{2})\)?\s*)?(9\s?\d{4}|\d{4})[-\s]?(\d{4})", texto)
    if not achou:
        return ""
    return "tel:+55" + (achou.group(1) or ddd) + re.sub(r"\D", "", achou.group(2)) + achou.group(3)


def _coordenada_ok(lat, lon):
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return CAIXA[0] <= la <= CAIXA[1] and CAIXA[2] <= lo <= CAIXA[3]


def carregar_catalogo(arquivo=None):
    """Lista de serviços do catálogo conferido, ou [] se o arquivo não existe ou está ilegível."""
    arquivo = arquivo or ARQUIVO_CATALOGO
    try:
        with open(arquivo, encoding="utf-8") as f:
            return list(json.load(f).get("servicos", []))
    except (OSError, ValueError):
        return []


def _data_br(texto):
    achou = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(texto or "").strip())
    return f"{achou.group(3)}/{achou.group(2)}/{achou.group(1)}" if achou else ""


def _linha_do_catalogo(s, cidade):
    tipo, subtipo = s.get("tipo"), s.get("subtipo")
    if tipo == "saude" and subtipo in SUBTIPOS:
        grupo, tipo_txt = SUBTIPOS[subtipo]
    elif (tipo, subtipo) in APOIO:
        grupo, tipo_txt = "apoio", APOIO[(tipo, subtipo)]
    else:
        return None
    nome = us.nome_legivel(s.get("nome") or "") if str(s.get("nome") or "").isupper() else str(s.get("nome") or "").strip()
    if not nome:
        return None
    endereco = str(s.get("endereco") or "").strip()
    aviso = str(s.get("aviso") or "").strip()
    if s.get("conferido") is False and not aviso:
        aviso = "Ainda não conferido: confirme antes de ir."
    elif s.get("conferido") is False:
        aviso = "Ainda não conferido. " + aviso
    com_ponto = s.get("geo") == "coordenada_fonte" and _coordenada_ok(s.get("lat"), s.get("lon"))
    return {
        "cnes": re.sub(r"\D", "", str(s.get("cnes") or "")).zfill(7) if s.get("cnes") else "",
        "nome": nome, "tipo": tipo_txt, "grupo": grupo, "natureza": "publica",
        "endereco": endereco, "bairro": "", "cep": us.cep_legivel(s.get("cep") or ""),
        "telefone": str(s.get("telefone") or "").strip(), "horario": str(s.get("horario") or "").strip(),
        "servicos": "",
        "conferido_em": _data_br(s.get("verificado_em")), "aviso": aviso, "fonte_url": str(s.get("fonte_url") or ""),
        "origem": "catalogo", "lat": s.get("lat") if com_ponto else None, "lon": s.get("lon") if com_ponto else None,
        "mapa": bool(com_ponto),
    }


def unificar(df_cnes, servicos, cidade="Rio Claro"):
    """Uma lista só: unidades do CNES (se houver) enriquecidas com telefone, horário e data do catálogo,
    mais o que só o catálogo tem (apoio à mulher e unidades sem correspondente no CNES).
    df_cnes pode ser None ou vazio: aí a lista é só o catálogo conferido."""
    base = df_cnes if df_cnes is not None and not df_cnes.empty else pd.DataFrame(columns=us_colunas())
    linhas = []
    for _, r in base.iterrows():
        d = r.to_dict()
        d.setdefault("servicos", "")
        d.update({"horario": "", "conferido_em": "", "aviso": "", "fonte_url": "", "origem": "cnes"})
        linhas.append(d)
    por_cnes = {d["cnes"]: d for d in linhas if str(d.get("cnes") or "").strip("0")}
    por_nome = {us._chave(d["nome"]): d for d in linhas}
    for s in servicos:
        novo = _linha_do_catalogo(s, cidade)
        if novo is None:
            continue
        alvo = (por_cnes.get(novo["cnes"]) if novo["cnes"].strip("0") else None) or por_nome.get(us._chave(novo["nome"]))
        if alvo is not None and novo["grupo"] != "apoio":
            for campo in ("telefone", "horario"):
                if novo[campo] and not str(alvo.get(campo) or "").strip():
                    alvo[campo] = novo[campo]
            alvo["conferido_em"], alvo["fonte_url"], alvo["aviso"] = novo["conferido_em"], novo["fonte_url"], novo["aviso"]
            if not str(alvo.get("endereco") or "").strip():
                alvo["endereco"] = novo["endereco"]
            continue
        linhas.append(novo)
    df = pd.DataFrame(linhas)
    if df.empty:
        df = pd.DataFrame(columns=COLUNAS)
    df["grupo"] = [g if g in ESCOLHAS else "outros" for g in df["grupo"].astype(str)]
    df["grupo"] = pd.Categorical(df["grupo"], categories=ORDEM, ordered=True)
    df["link_chegar"] = [link_como_chegar(n, e, cidade) for n, e in zip(df["nome"], df["endereco"])]
    df["link_ligar"] = [link_ligar(t) for t in df["telefone"]]
    for c in ("cnes", "bairro", "cep", "telefone", "horario", "servicos", "conferido_em", "aviso", "fonte_url", "endereco", "tipo"):
        df[c] = df[c].fillna("").astype(str)
    df["mapa"] = df["mapa"].fillna(False).astype(bool)
    # no apoio, primeiro o que é da mulher (Secretaria, delegacia, patrulha, defensoria), depois a assistência social
    df["_ordem"] = [0 if (g == "apoio" and t in PRIMEIRO_NO_APOIO) or g != "apoio" else 1 for g, t in zip(df["grupo"].astype(str), df["tipo"])]
    df = df.sort_values(["grupo", "_ordem", "nome"]).reset_index(drop=True)
    df = df[COLUNAS]
    if df_cnes is not None:
        df.attrs.update(df_cnes.attrs)
    df.attrs["tem_cnes"] = df_cnes is not None and not df_cnes.empty
    return df


def us_colunas():
    return ["cnes", "nome", "tipo", "grupo", "natureza", "endereco", "bairro", "cep", "telefone", "lat", "lon", "mapa"]


def contar(df):
    """{escolha: quantos} só das escolhas oferecidas (o grupo 'outros' do CNES não aparece como botão)."""
    return {g: int((df["grupo"].astype(str) == g).sum()) for g in ESCOLHAS}


_ESPECIALISTA = re.compile(r"^(.*?)\s*\((\d+) no ambulatório, (\d+) cadastrad")


_ACENTOS = {"clinico": "clínico", "clinica": "clínica", "ginecologico": "ginecológico", "laboratorio": "laboratório",
            "ambulatorio": "ambulatório", "urgencia": "urgência", "emergencia": "emergência", "citopatologicos": "citopatológicos",
            "assistencia": "assistência", "acoes": "ações", "orgaos": "órgãos", "doenca": "doença", "pre-natal": "pré-natal",
            "medico": "médico", "psicologo": "psicólogo", "cirurgiao": "cirurgião", "farmaceutico": "farmacêutico",
            "fonoaudiologo": "fonoaudiólogo", "estrategia": "estratégia", "saude": "saúde", "familia": "família",
            "ocupacional": "ocupacional", "diagnostico": "diagnóstico", "servico": "serviço", "atencao": "atenção"}


def _legivel(texto):
    palavras = texto.strip().lower().split()
    return " ".join(_ACENTOS.get(p, p) for p in palavras)


def rotulo_legivel(t):
    """O CNES escreve em MAIÚSCULAS e sem acento; na tela vai em letra normal, e o profissional em 'N no ambulatório, M cadastrados'."""
    m = _ESPECIALISTA.match(t)
    if m:
        n = int(m.group(3))
        return f"{_legivel(m.group(1)).capitalize()}: {m.group(2)} no ambulatório, {n} cadastrado{'s' if n != 1 else ''}"
    return _legivel(t).capitalize()


def separar_registros(texto):
    """Do texto de uma unidade devolve (profissionais, servicos PRÓPRIOS). O que o CNES marca como serviço
    por terceiro (outro estabelecimento faz) fica de fora: a unidade não faz aquilo no local."""
    itens = [t.strip() for t in str(texto or "").split("|") if t.strip()]
    prof = [t for t in itens if "cadastrad" in t]
    proprios = [t for t in itens if "cadastrad" not in t and not t.endswith(us.TAG_TERCEIRO)]
    return prof, proprios


def servicos_de_terceiros(texto):
    """Serviços que o CNES registra para a unidade, mas feitos por outro estabelecimento (sem a etiqueta)."""
    itens = [t.strip() for t in str(texto or "").split("|") if t.strip()]
    return [t[:-len(us.TAG_TERCEIRO)].strip() for t in itens if t.endswith(us.TAG_TERCEIRO)]


def opcoes_de_busca(df):
    """O que existe de verdade nas unidades da cidade, para a pessoa ESCOLHER em vez de adivinhar a palavra.
    Devolve (profissionais, servicos): listas de (rótulo, termo_de_busca, quantas_unidades), da mais comum à menos."""
    if df is None or "servicos" not in df:
        return [], []
    prof, serv = {}, {}
    for texto in df["servicos"].fillna("").astype(str):
        esp, svc = separar_registros(texto)
        for t in set(esp):
            m = _ESPECIALISTA.match(t)
            nome = (m.group(1) if m else t).strip()
            prof[nome] = prof.get(nome, 0) + 1
        for t in set(svc):
            serv[t] = serv.get(t, 0) + 1

    profissionais = []
    for n, q in prof.items():
        if n.startswith("MEDICO "):
            resto = n.replace("MEDICO ", "", 1)
            profissionais.append((f"Médico: {_legivel(resto).capitalize()}", resto, q))
        else:
            profissionais.append((f"Profissional: {_legivel(n).capitalize()}", n, q))
    servicos = [(_legivel(n).capitalize(), n, q) for n, q in serv.items()]
    ordem = lambda x: (-x[2], x[0])  # noqa: E731
    return sorted(profissionais, key=ordem), sorted(servicos, key=ordem)


def sugestoes(df, busca, n=5):
    """Quando nada casa: o que existe no cadastro e se parece com o que foi digitado (rótulo, termo de busca)."""
    tokens = [t for t in _tokens(busca) if t not in PARADA_BUSCA and len(t) > 1]
    if not tokens:
        return []
    profissionais, servicos = opcoes_de_busca(df)
    pontuadas = []
    for rotulo, termo, q in profissionais + servicos:
        palavras = us._chave(termo).split("_")
        melhor = 0.0
        for t in tokens:
            for p in palavras:
                r = difflib.SequenceMatcher(None, t, p).ratio()
                if len(t) >= 4 and len(p) >= 4 and (p.startswith(t[:5]) or t.startswith(p[:5])):
                    r = max(r, 0.8)
                melhor = max(melhor, r)
        if melhor >= 0.75:
            pontuadas.append((melhor, q, rotulo, termo))
    pontuadas.sort(key=lambda x: (-x[0], -x[1]))
    return [(rotulo, termo) for _, _, rotulo, termo in pontuadas[:n]]


def separar_por_natureza(df):
    """(rede pública e sem fins lucrativos, particulares): na busca os dois aparecem, nunca um escondido."""
    if df.empty or "natureza" not in df:
        return df, df.iloc[0:0]
    particular = df["natureza"].astype(str) == "privada"
    return df[~particular].reset_index(drop=True), df[particular].reset_index(drop=True)


def _tokens(texto):
    return [t for t in us._chave(texto).split("_") if t]


def _variantes(t):
    """Formas de uma palavra digitada que também valem: plural, feminino e radical (fisioterapia ~ fisioterapeuta)."""
    v = [t]
    if len(t) > 4 and t.endswith("S"):
        v.append(t[:-1])
    if len(t) > 5 and t.endswith("A"):
        v.append(t[:-1] + "O")
    if len(t) >= 9 and t.endswith(("IA", "ICA")):
        v.append(t[:-2])
    return list(dict.fromkeys(v))


def _casa(palavras, compacto, t):
    """A palavra digitada começa alguma palavra do texto (não vale trecho no meio: 'ame' não acha 'Gamela')."""
    for v in _variantes(t):
        if any(p.startswith(v) for p in palavras):
            return True
        if len(v) >= 7 and v in compacto:  # 'prenatal' x 'PRE-NATAL'
            return True
    return False


def _interpretar_grupos(tokens):
    """(grupos, residuais): cada grupo é um apelido reconhecido (rótulos alternativos do CNES); os demais viram residuais."""
    grupos, consumidos = [], set()
    for apelido, rotulos in SINONIMOS_SERVICOS.items():
        partes = us._chave(apelido).split("_")
        for inicio in range(len(tokens) - len(partes) + 1):
            if tokens[inicio:inicio + len(partes)] == partes:
                grupos.append(tuple(rotulos))
                consumidos.update(range(inicio, inicio + len(partes)))
    residuais = [t for i, t in enumerate(tokens) if i not in consumidos and t not in PARADA_BUSCA and len(t) > 1]
    if not residuais and not grupos:
        residuais = [t for t in tokens if len(t) > 1]
    return list(dict.fromkeys(grupos)), residuais


def _interpretar_busca(busca):
    """(rótulos do CNES que os apelidos pedem, palavras que sobraram): usado para destacar o que casou."""
    grupos, residuais = _interpretar_grupos(_tokens(busca))
    return tuple(dict.fromkeys(r for g in grupos for r in g)), residuais


def termos_servico_buscados(busca):
    """Classificações CNES correspondentes ao termo popular informado, para explicar o resultado na tela."""
    return _interpretar_busca(busca)[0]


def _partes_da_unidade(linha):
    """(palavras do nome/endereço, palavras dos serviços, palavras dos profissionais) de uma unidade."""
    esp, svc = separar_registros(linha.get("servicos", ""))
    nome = " ".join(str(linha.get(c, "") or "") for c in ("nome", "tipo", "endereco", "bairro"))
    return [us._chave(x).replace("_", " ").split() for x in (nome, " ".join(svc), " ".join(esp))]


def _vocabulario(df):
    vocab = set()
    for _, linha in df.iterrows():
        for palavras in _partes_da_unidade(linha):
            vocab.update(p for p in palavras if len(p) >= 4)
    for apelido in SINONIMOS_SERVICOS:
        vocab.update(p for p in us._chave(apelido).split("_") if len(p) >= 4)
    return vocab


def corrigir_busca(df, busca):
    """Conserta erro de digitação com as palavras que EXISTEM no cadastro ('ultrasom' -> 'ultrassom').
    Só mexe em palavra que não casa com nada; palavra certa nunca é trocada."""
    tokens = _tokens(busca)
    if not tokens or df is None or df.empty:
        return busca
    conhecidas = {p for a in SINONIMOS_SERVICOS for p in us._chave(a).split("_")} | PARADA_BUSCA
    vocab = None
    saida = []
    for t in tokens:
        if t in conhecidas or len(t) < 4:
            saida.append(t); continue
        if vocab is None:
            vocab = _vocabulario(df)
        if any(any(w.startswith(v) for w in vocab) for v in _variantes(t)):
            saida.append(t); continue
        perto = difflib.get_close_matches(t, sorted(vocab), n=1, cutoff=0.8)
        saida.append(perto[0] if perto else t)
    return " ".join(saida).lower() if saida != tokens else busca


def _rotulo_casa(rotulo, serv, prof, compacto_serv, compacto_prof):
    alvo = us._chave(rotulo).split("_")
    ok = _frase_em(alvo, serv)
    if rotulo not in SO_NOS_SERVICOS:
        ok = ok or _frase_em(alvo, prof)
    return ok


def _frase_em(alvo, palavras):
    n = len(alvo)
    return any(palavras[i:i + n] == alvo or all(p.startswith(a) for p, a in zip(palavras[i:i + n], alvo))
               for i in range(len(palavras) - n + 1))


def casa_item(item, busca):
    """Este item de serviço/profissional casa com o que foi digitado? (usado para destacar em negrito no cartão)"""
    grupos, residuais = _interpretar_grupos(_tokens(busca))
    palavras = us._chave(item).replace("_", " ").split()
    compacto = "".join(palavras)
    eh_profissional = "cadastrad" in item
    for g in grupos:
        for r in g:
            if r in SO_NOS_SERVICOS and eh_profissional:
                continue
            if _frase_em(us._chave(r).split("_"), palavras):
                return True
    return any(_casa(palavras, compacto, t) for t in residuais)


def filtrar(df, escolha=None, busca="", so_publicos=False):
    """Busca por unidade/local, serviço ou profissional do CNES, com as palavras que as pessoas usam.

    Regras: a palavra digitada tem de começar uma palavra do cadastro; plural, feminino e erro de digitação
    são aceitos; TODAS as partes da frase precisam casar; exame só conta em serviço (nunca em médico);
    lugares cujo NOME bate com a busca vêm primeiro."""
    saida = df
    if us._chave(busca):
        busca = corrigir_busca(df, busca)
        grupos, residuais = _interpretar_grupos(_tokens(busca))
        marcas, pontos = [], []
        for _, linha in df.iterrows():
            nome, serv, prof = _partes_da_unidade(linha)
            todas = nome + serv + prof
            compacto = "".join(todas)
            ok = all(any(_rotulo_casa(r, serv, prof, "".join(serv), "".join(prof)) for r in g) for g in grupos)
            ok = ok and all(_casa(todas, compacto, t) for t in residuais)
            marcas.append(ok)
            pontos.append(sum(1 for t in residuais if _casa(nome, "".join(nome), t)) if ok else 0)
        saida = df[pd.Series(marcas, index=df.index)]
        if residuais:
            saida = saida.assign(_pontos=pd.Series(pontos, index=df.index)[saida.index])
            saida = saida.sort_values("_pontos", ascending=False, kind="mergesort").drop(columns="_pontos")
    elif escolha:
        saida = df[df["grupo"].astype(str) == escolha]
    if so_publicos and "natureza" in saida:
        saida = saida[saida["natureza"].isin(["publica", "sem_fins", "desconhecida"])]
    return saida.reset_index(drop=True)
