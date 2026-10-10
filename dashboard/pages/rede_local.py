"""Rede local de saúde e proteção à mulher — Rio Claro/SP.

Página adicional e independente. Não altera o dashboard epidemiológico nem o banco.
Lê os CSVs locais em modo somente leitura e não presume que cadastro equivale a
serviço ativo ou vaga disponível. Endereços/telefones públicos vêm acompanhados
de links oficiais para conferência.
"""
from pathlib import Path
import csv
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
PASTA_BANCO = ROOT / "banco"
PASTA_CNES = PASTA_BANCO / "cnes"
PASTA_CEP = PASTA_BANCO / "cep_Rio_Claro"
# O CNES pode armazenar o código municipal sem o dígito verificador (6 dígitos).
CODIGO_MUNICIPIO = "3543907"
CODIGOS_MUNICIPIO = {"3543907", "354390"}

st.set_page_config(
    page_title="Escudo Feminino · Rede local",
    page_icon="E",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; max-width: 1440px;}
.rede-hero {background: linear-gradient(120deg,#f3effa,#fbf8fc); border:1px solid #e4dcef;
border-radius:18px;padding:22px 24px;margin-bottom:18px;}
.rede-hero h1 {color:#41365f;font-size:1.8rem;margin:0 0 8px 0;}
.rede-hero p {color:#514b60;margin:0;max-width:850px;}
.rede-note {background:#fff8ed;border-left:4px solid #d79a52;padding:12px 15px;border-radius:8px;margin:10px 0;}
.rede-card {background:#fff;border:1px solid #e6e1ee;border-radius:14px;padding:16px;height:100%;}
.rede-card h3 {color:#493d70;font-size:1.05rem;margin-top:0;}
.rede-muted {color:#6c6678;font-size:.88rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="rede-hero">
<h1>Rede de cuidado e proteção em Rio Claro</h1>
<p>Um caminho prático para encontrar atendimento de saúde, assistência social e proteção.
A rede local complementa os indicadores epidemiológicos: não substitui avaliação profissional,
regulação do SUS nem confirmação direta do funcionamento do serviço.</p>
</div>
""", unsafe_allow_html=True)

def normalizar(valor):
    valor = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", valor.upper()).strip("_")

def detectar_separador(path):
    with path.open("r", encoding="latin-1", newline="") as f:
        amostra = f.read(10000)
    try:
        return csv.Sniffer().sniff(amostra, delimiters=";|,\t").delimiter
    except csv.Error:
        return ";"

def ler_cabecalho(path):
    try:
        return list(pd.read_csv(path, sep=detectar_separador(path), encoding="latin-1",
                                dtype=str, nrows=0, engine="c").columns)
    except Exception:
        return []

def achar(colunas, candidatos):
    mapa = {normalizar(c): c for c in colunas}
    for candidato in candidatos:
        if normalizar(candidato) in mapa:
            return mapa[normalizar(candidato)]
    return None

def carregar_cnes_local():
    arquivos = sorted(PASTA_CNES.glob("tbEstabelecimento*.csv"), key=lambda p: p.stat().st_mtime)
    if not arquivos:
        return pd.DataFrame(), "Não encontrei tbEstabelecimento*.csv na pasta banco/cnes."
    path = arquivos[-1]
    sep = detectar_separador(path)
    colunas = ler_cabecalho(path)
    col_mun = achar(colunas, ["CO_MUNICIPIO_GESTOR", "CO_MUNICIPIO", "COD_MUNICIPIO"])
    if not col_mun:
        return pd.DataFrame(), (
            f"O arquivo {path.name} não tem uma coluna municipal reconhecida. "
            "Não vou mostrar registros sem conseguir confirmar que são de Rio Claro."
        )
    aliases = {
        "CNES": ["CO_CNES", "CNES", "COD_CNES"],
        "Nome": ["NO_FANTASIA", "NO_RAZAO_SOCIAL", "NOME_FANTASIA", "NOME"],
        "Tipo de unidade": ["TP_UNIDADE", "DS_TIPO_UNIDADE", "TIPO_UNIDADE"],
        "CEP": ["CO_CEP", "CEP"],
        "Situação": ["CO_MOTIVO_DESAB", "ST_STATUS", "SITUACAO"],
    }
    usecols = [col_mun]
    renomear = {col_mun: "Código do município"}
    for saida, candidatos in aliases.items():
        col = achar(colunas, candidatos)
        if col and col not in usecols:
            usecols.append(col)
            renomear[col] = saida
    try:
        df = pd.read_csv(path, sep=sep, encoding="latin-1", dtype=str,
                         usecols=usecols, low_memory=False, engine="c")
        codigos = df[col_mun].fillna("").str.replace(r"\D", "", regex=True)
        df = df.loc[codigos.str.lstrip("0").isin(CODIGOS_MUNICIPIO)].copy().rename(columns=renomear)
        if "CNES" in df:
            df = df.drop_duplicates(subset=["CNES"])
        else:
            df = df.drop_duplicates()
        df.attrs["arquivo"] = path.name
        return df.reset_index(drop=True), None
    except Exception as exc:
        return pd.DataFrame(), f"Não consegui ler {path.name}: {exc}"

def carregar_coordenadas():
    arquivos = sorted(PASTA_CEP.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not arquivos:
        return pd.DataFrame(), "Arquivo local de coordenadas por CEP não encontrado."
    path = arquivos[0]
    try:
        df = pd.read_csv(path, sep=detectar_separador(path), encoding="utf-8-sig",
                         dtype=str, low_memory=False, engine="c")
        df.columns = [str(c).strip() for c in df.columns]
        lat = achar(df.columns, ["latitude", "lat", "LATITUDE_GOOGLE", "LAT"])
        lon = achar(df.columns, ["longitude", "lon", "lng", "LONGITUDE_GOOGLE", "LONG"])
        cep = achar(df.columns, ["CEP", "CO_CEP", "COD_CEP", "CEP_NORMALIZADO"])
        if not lat or not lon:
            return pd.DataFrame(), (
                f"O arquivo {path.name} foi localizado, mas não reconheci as colunas de latitude/longitude."
            )
        if not cep:
            return pd.DataFrame(), (
                f"O arquivo {path.name} não tem uma coluna CEP reconhecida. "
                "Para evitar um mapa enganoso, não vou desenhar esses pontos como se fossem unidades de saúde."
            )
        df["_lat"] = pd.to_numeric(df[lat].str.replace(",", ".", regex=False), errors="coerce")
        df["_lon"] = pd.to_numeric(df[lon].str.replace(",", ".", regex=False), errors="coerce")
        df["_cep"] = df[cep].fillna("").str.replace(r"\D", "", regex=True)
        df = df[
            df["_cep"].str.len().eq(8)
            & df["_lat"].between(-90, 90)
            & df["_lon"].between(-180, 180)
        ].copy()
        df = df.drop_duplicates(subset=["_cep"], keep="first")
        df.attrs["arquivo"] = path.name
        return df[["_cep", "_lat", "_lon"]], None
    except Exception as exc:
        return pd.DataFrame(), f"Não consegui ler o arquivo de coordenadas: {exc}"

st.markdown("""
<div class="rede-note"><b>Risco imediato:</b> ligue 190 (Polícia Militar). Em emergência médica, 192 (SAMU).
Para orientação e denúncia de violência contra a mulher, Ligue 180. Em situação de perigo, não espere uma resposta do painel.</div>
""", unsafe_allow_html=True)

cnes, aviso_cnes = carregar_cnes_local()
st.subheader("Estabelecimentos do CNES em Rio Claro")
if aviso_cnes:
    pass
elif cnes.empty:
    st.info("O arquivo foi lido, mas não retornou estabelecimentos para o código municipal configurado.")
else:
    st.caption(
        f"{len(cnes)} registros únicos no arquivo {cnes.attrs.get('arquivo', 'CNES')}. "
        "É uma contagem cadastral, não uma medida de capacidade, qualidade, agenda ou vaga disponível."
    )
    if "Tipo de unidade" in cnes:
        tipos = ["Todos"] + sorted(cnes["Tipo de unidade"].fillna("Não informado").unique().tolist())
        tipo = st.selectbox("Filtrar por tipo de unidade", tipos)
        if tipo != "Todos":
            cnes = cnes[cnes["Tipo de unidade"].fillna("Não informado") == tipo]
    busca = st.text_input("Buscar estabelecimento pelo nome ou CNES", key="rede_busca_cnes").strip().casefold()
    if busca:
        mascara = pd.Series(False, index=cnes.index)
        for col in ("Nome", "CNES", "CEP"):
            if col in cnes:
                mascara |= cnes[col].fillna("").str.casefold().str.contains(busca, na=False)
        cnes = cnes[mascara]
    st.dataframe(cnes.drop(columns=["_cep_mapa"], errors="ignore"), use_container_width=True, hide_index=True)
    st.download_button("Baixar recorte exibido (CSV)", cnes.drop(columns=["_cep_mapa"], errors="ignore").to_csv(index=False).encode("utf-8-sig"),
                       file_name="cnes_rio_claro_filtrado.csv", mime="text/csv")

st.subheader("Documentos locais de referência")
docs = PASTA_BANCO / "documetacao"
documentos = [
    ("CRAS", "cras.pdf"), ("CREAS", "creas.pdf"), ("Conselho Tutelar", "ctutelar.pdf"),
    ("Disque 100", "disque100.pdf"), ("Endereços", "enderecos.pdf"),
    ("CNES", "cnes.pdf"), ("Unidades de saúde de Rio Claro", "usrc.pdf"),
    ("Unidades de saúde — complemento 2", "usrc2.pdf"),
    ("Unidades de saúde — complemento 3", "usrc3.pdf"),
]
for rotulo, nome in documentos:
    path = docs / nome
    if path.exists():
        st.caption(f"Documento disponível localmente: **{rotulo}** — {nome}")
st.caption("Os documentos locais são referências de trabalho. Confira sempre os canais oficiais para confirmar endereço, telefone, horário e elegibilidade antes do encaminhamento.")

with st.expander("Fontes e limites desta página"):
    st.markdown("""
- [Prefeitura de Rio Claro — Unidades Básicas de Saúde](https://rioclaro.sp.gov.br/unidades-basicas-de-saude/)
- [Prefeitura de Rio Claro — Postos de Saúde e urgência](https://rioclaro.sp.gov.br/postos-de-saude/)
- [Prefeitura de Rio Claro — CRAS](https://rioclaro.sp.gov.br/centro-ref-assistencia-social/)
- [Prefeitura de Rio Claro — CREAS](https://rioclaro.sp.gov.br/desenvolvimento-social/creas-tem-novo-local-de-funcionamento/)
- [Ministério das Mulheres — Ligue 180](https://www.gov.br/mulheres/pt-br/ligue180)

O CNES pode ter dados nacionais; esta página só mostra registros quando consegue filtrar pelo código municipal.
A localização no mapa vem do CSV local, não de geocodificação automática. Horários, situação ativa e disponibilidade
de atendimento não são inferidos pelo cadastro.
""")
