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

COLUNAS = ["cnes", "nome", "tipo", "grupo", "natureza", "endereco", "bairro", "cep", "telefone", "horario",
           "conferido_em", "aviso", "fonte_url", "origem", "lat", "lon", "mapa", "link_chegar", "link_ligar"]


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
    for c in ("cnes", "bairro", "cep", "telefone", "horario", "conferido_em", "aviso", "fonte_url", "endereco", "tipo"):
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


def filtrar(df, escolha=None, busca="", so_publicos=False):
    """Lista da escolha (ou de todas as escolhas, se houver busca). Texto da busca: nome, tipo, endereço, bairro."""
    saida = df
    texto = us._chave(busca).replace("_", "")
    if texto:
        alvo = (df["nome"] + " " + df["tipo"] + " " + df["endereco"] + " " + df["bairro"]).map(lambda t: us._chave(t).replace("_", ""))
        saida = df[alvo.str.contains(texto, regex=False)]
    elif escolha:
        saida = df[df["grupo"].astype(str) == escolha]
    if so_publicos and "natureza" in saida:
        saida = saida[saida["natureza"].isin(["publica", "sem_fins", "desconhecida"])]
    return saida.reset_index(drop=True)
