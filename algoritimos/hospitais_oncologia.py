import csv
import math
import os
import re
import unicodedata
from urllib.parse import quote_plus

import pandas as pd

import localizacao as loc

# ============================================================
# HOSPITAIS HABILITADOS EM ONCOLOGIA (Brasil) -- "Onde ficam, e qual está mais perto?" (18/10/2026)
#
# Lista oficial do Ministério da Saúde (habilitação 2023, `etl/gerar_lista_hospitais_oncologia.py`) + endereço, telefone
# e posição do cadastro do CNES (`etl/gerar_hospitais_oncologia_geo.py`). Só descreve:
#   - "habilitado" NÃO é vaga nem porta de entrada: o acesso é pela regulação (UBS -> CROSS);
#   - a distância é em LINHA RETA entre o centro da cidade e o hospital; não é rota nem tempo;
#   - só vira ponto no mapa quem passou nas conferências de posição; o resto fica na lista, sem ponto;
#   - nunca ranqueia hospital nem diz qual é melhor.
# Sem o arquivo de posições a página continua útil (lista e contagens, sem mapa).
# Teste: algoritimos/teste_hospitais_oncologia.py
# ============================================================

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.environ.get("ESCUDO_HOSPITAIS_PASTA") or os.path.join(RAIZ, "dados_geograficos")  # a variável é para testes
ARQ_GEO = "hospitais_oncologia_br_geo.csv"
ARQ_LISTA = "hospitais_oncologia_br.csv"

# tipo -> (cor no mapa, o que quer dizer, em palavras de quem procura)
TIPOS = {
    "UNACON": ("#5b2a55", "Unidade de Assistência de Alta Complexidade em Oncologia: faz o diagnóstico e o tratamento dos cânceres mais frequentes (como mama, colo do útero e intestino)."),
    "CACON": ("#b0306a", "Centro de Assistência de Alta Complexidade em Oncologia: o nível mais completo; atende todos os tipos de câncer, inclusive os raros, e costuma ter ensino e pesquisa."),
    "Hospital geral com cirurgia oncológica": ("#2f7f86", "Hospital geral habilitado para cirurgia de câncer; não trata sozinho todos os tipos."),
    "Serviço isolado de radioterapia": ("#c78a1c", "Serviço de radioterapia: faz só esse tratamento, em complemento a outro hospital."),
    "Tipo não informado": ("#8a8a99", "A planilha do Ministério não informa o tipo de habilitação deste estabelecimento."),
}
ORDEM_TIPOS = list(TIPOS)
COLUNAS = ["cnes", "uf", "municipio", "nome", "tipo", "habilitacao", "endereco", "cep", "telefone", "lat", "lon", "no_mapa", "motivo"]


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn")


def carregar(pasta=DADOS):
    """DataFrame com um estabelecimento por linha. Usa o arquivo com posições se existir; senão a lista oficial (sem mapa).
    attrs['tem_posicao'] diz se há posições; attrs['fonte'] diz de onde veio."""
    geo, lista = os.path.join(pasta, ARQ_GEO), os.path.join(pasta, ARQ_LISTA)
    if os.path.isfile(geo):
        df = pd.read_csv(geo, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        fonte = "geo"
    elif os.path.isfile(lista):
        df = pd.read_csv(lista, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        df = df.rename(columns={"nome_ministerio": "nome"})
        for c in ("endereco", "cep", "telefone", "lat", "lon", "motivo"):
            df[c] = ""
        df["no_mapa"] = "não"
        df["motivo"] = "as posições ainda não foram geradas (py etl\\gerar_hospitais_oncologia_geo.py)"
        fonte = "lista"
    else:
        vazio = pd.DataFrame(columns=COLUNAS)
        vazio.attrs.update({"tem_posicao": False, "fonte": "nenhuma"})
        return vazio
    for c in COLUNAS:
        if c not in df:
            df[c] = ""
    df["lat"] = pd.to_numeric(df["lat"].str.replace(",", "."), errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"].str.replace(",", "."), errors="coerce")
    df["no_mapa"] = (df["no_mapa"].str.lower().isin(["sim", "true", "1"])) & df["lat"].notna() & df["lon"].notna()
    df["tipo"] = df["tipo"].where(df["tipo"].isin(TIPOS), "Tipo não informado")
    df["tipo"] = pd.Categorical(df["tipo"], categories=ORDEM_TIPOS, ordered=True)
    df = df.sort_values(["uf", "municipio", "nome"]).reset_index(drop=True)
    df = df[COLUNAS]
    df.attrs.update({"tem_posicao": bool(df["no_mapa"].any()), "fonte": fonte})
    return df


def contar_por_uf(df):
    """[(uf, total, com_ponto)] do estado com mais estabelecimentos para o com menos."""
    if df.empty:
        return []
    g = df.groupby("uf").agg(total=("cnes", "count"), com_ponto=("no_mapa", "sum"))
    return [(uf, int(r["total"]), int(r["com_ponto"])) for uf, r in g.sort_values(["total"], ascending=False).iterrows()]


def contar_por_tipo(df):
    return {t: int((df["tipo"].astype(str) == t).sum()) for t in ORDEM_TIPOS if (df["tipo"].astype(str) == t).any()}


def filtrar(df, ufs=None, tipos=None, busca=""):
    """Filtra por estado, tipo e texto (nome, município). O texto casa começo de palavra, sem acento."""
    saida = df
    if ufs:
        saida = saida[saida["uf"].isin(ufs)]
    if tipos:
        saida = saida[saida["tipo"].astype(str).isin(tipos)]
    texto = _sem_acento(busca).lower().strip()
    if texto:
        def casa(linha):
            palavras = re.split(r"\W+", _sem_acento(f"{linha['nome']} {linha['municipio']}").lower())
            return all(any(p.startswith(t) for p in palavras) for t in texto.split())
        saida = saida[saida.apply(casa, axis=1)] if len(saida) else saida
    return saida.reset_index(drop=True)


def mais_proximos(df, localizacao, cidade, n=3):
    """Os `n` estabelecimentos COM posição confirmada mais perto do centro da cidade (SP): [(km, linha)] do mais perto ao mais longe.
    Vazio se a cidade não está na tabela de centros (nunca chuta a posição). Linha reta, não rota."""
    if localizacao is None or len(localizacao) == 0:
        return []
    origem = loc._ponto(localizacao, loc.ent.normalizar(cidade))
    if origem is None:
        return []
    candidatos = df[df["no_mapa"]]
    achados = [(loc.distancia_km(origem[0], origem[1], float(r.lat), float(r.lon)), r) for r in candidatos.itertuples()]
    achados.sort(key=lambda x: x[0])
    return achados[:n]


def ordenar_por_distancia(df, localizacao, cidade):
    """Cópia de `df` com a coluna `km` (linha reta do centro da cidade até o hospital) e ordenada do mais perto ao mais longe.
    Quem não tem posição confirmada fica sem km e vai para o fim (nunca ganha distância inventada). Se a cidade não está
    na tabela de centros, devolve `df` como veio, sem a coluna: a página não finge uma ordem que não calculou."""
    if localizacao is None or len(localizacao) == 0 or not cidade:
        return df
    origem = loc._ponto(localizacao, loc.ent.normalizar(cidade))
    if origem is None:
        return df
    km = [loc.distancia_km(origem[0], origem[1], float(r.lat), float(r.lon)) if r.no_mapa else float("nan") for r in df.itertuples()]
    return df.assign(km=km).sort_values("km", kind="mergesort", na_position="last").reset_index(drop=True)


def cidades_disponiveis(localizacao):
    """Nomes das cidades de SP que têm centro cadastrado (para a pessoa escolher onde mora)."""
    if localizacao is None or len(localizacao) == 0:
        return []
    return sorted(localizacao["nome"].astype(str).tolist(), key=_sem_acento)


def link_chegar(nome, endereco, municipio, uf):
    """Rota no Google Maps até o hospital; sem origem, o Maps parte de onde a pessoa está."""
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(", ".join(p for p in (nome, endereco, municipio, uf) if p))


def link_ligar(telefone):
    """tel: do telefone '(DD) NNNN-NNNN' do CNES; vazio se não tiver DDD (nunca chuta o DDD de outro estado)."""
    achou = re.search(r"\((\d{2})\)\s*(9?\d{4})-?(\d{4})", str(telefone or ""))
    return f"tel:+55{achou.group(1)}{achou.group(2)}{achou.group(3)}" if achou else ""


def vista_do_mapa(coordenadas, largura=1000, altura=460, margem=0.35):
    """Centro e zoom (projeção web do mapa, blocos de 512 px) para que TODOS os pontos [lon, lat] caibam na tela, com uma folga.
    O ajuste automático do pydeck deixava de fora o ponto mais ao norte (Barretos sumia). Um ponto só: zoom de cidade."""
    lons = [c[0] for c in coordenadas]
    lats = [c[1] for c in coordenadas]
    if not lons:
        return {"longitude": -47.0, "latitude": -22.0, "zoom": 6}

    def merc(lat):
        return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

    dx = max(lons) - min(lons)
    dy = merc(max(lats)) - merc(min(lats))
    if dx < 1e-6 and dy < 1e-9:
        return {"longitude": lons[0], "latitude": lats[0], "zoom": 10}
    zooms = []
    if dx > 1e-6:
        zooms.append(math.log2(largura * 360 / (512 * dx)))
    if dy > 1e-9:
        zooms.append(math.log2(altura * 2 * math.pi / (512 * dy)))
    zoom = max(2.0, min(11.0, min(zooms) - margem))
    meio_y = (merc(max(lats)) + merc(min(lats))) / 2
    return {"longitude": (max(lons) + min(lons)) / 2, "latitude": math.degrees(2 * math.atan(math.exp(meio_y)) - math.pi / 2), "zoom": zoom}


def leitura(df, total_no_pais=None):
    """Frase descritiva do que está na tela (nunca causa, nunca ranking)."""
    if df.empty:
        return "Nenhum estabelecimento com esse filtro."
    ufs = df["uf"].nunique()
    com = int(df["no_mapa"].sum())
    tipos = contar_por_tipo(df)
    partes = ", ".join(f"{q} {t}" for t, q in tipos.items())
    frase = (f"{len(df)} estabelecimento{'s' if len(df) != 1 else ''} habilitado{'s' if len(df) != 1 else ''} em oncologia "
             f"em {ufs} estado{'s' if ufs != 1 else ''} ({partes}). ")
    if com < len(df):
        sem = len(df) - com
        frase += (f"{com} {'aparecem' if com != 1 else 'aparece'} no mapa; {sem} {'estão' if sem != 1 else 'está'} só na lista "
                  "porque a posição do cadastro não passou nas conferências ou ainda não foi gerada. ")
    return frase + "Habilitado não quer dizer vaga: o acesso é pela regulação."
