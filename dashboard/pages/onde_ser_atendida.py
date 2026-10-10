import html
import os
import sqlite3
import sys

import pandas as pd
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "algoritimos"))
sys.path.insert(0, os.path.join(AQUI, ".."))

import unidades_saude as us  # noqa: E402
from configuracao_geografica import BANCO, UF_REFERENCIA  # noqa: E402
from estilo import CSS  # noqa: E402

# ============================================================
# ONDE SER ATENDIDA -- unidades de saúde da cidade (CNES), 10/2026
#
# Pergunta nova: "onde, na minha cidade, uma mulher pode procurar
# atendimento?". Substitui a antiga página "Rede local", que só
# despejava o CNES cru. Aqui: tipo em palavras, endereço, telefone,
# mapa, público x privado, e (quando o banco tem) quantas internações
# por câncer feminino cada hospital registrou -- o cruzamento que liga
# o cadastro ao resto do Escudo.
#
# Só descreve: cadastro não é serviço aberto nem vaga, e a página diz
# isso. Não ranqueia unidades. Lê o CSV em banco\cnes\ (não vai para o
# GitHub) e o banco só para a contagem de internações (opcional).
# ============================================================

st.set_page_config(page_title="Escudo Feminino · Onde ser atendida", page_icon="E", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.un-grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 12px; margin: 10px 0; }
.un-cartao { background: #fff; border: 1px solid #ebe8f2; border-left: 6px solid #cdbfeb; border-radius: 14px;
             padding: 12px 16px; }
.un-cartao.publica { border-left-color: #4aa27c; }
.un-cartao.sem_fins { border-left-color: #6b9bd8; }
.un-cartao.privada { border-left-color: #c9c4d6; }
.un-nome { font-family: 'Manrope', sans-serif; font-weight: 700; color: #292541; font-size: 1.02rem; }
.un-tipo { color: #625d72; font-size: .88rem; margin: 1px 0 6px; }
.un-linha { color: #3d3852; font-size: .92rem; margin: 2px 0; }
.un-selo { display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
           border-radius: 999px; padding: 2px 9px; margin: 0 6px 6px 0; }
.un-selo.publica { background: #dcf3e8; color: #11734f; }
.un-selo.sem_fins { background: #e3eefc; color: #1f5fae; }
.un-selo.privada { background: #efeef3; color: #625d72; }
.un-selo.desconhecida { background: #efeef3; color: #625d72; }
.un-selo.cancer { background: #f6e8f3; color: #8a2f73; }
.un-selo.grupo { background: #ece7f7; color: #4d3f7a; }
a.un-mapa { font-size: .88rem; color: #1f5fae; font-weight: 600; text-decoration: none; }
a.un-mapa:hover { text-decoration: underline; }
[class*="st-key-un_pilulas"] label[data-testid="stRadioOption"],
[class*="st-key-un_pilulas"] label[data-baseweb="radio"] {
    border: 1px solid #cdbfeb; border-radius: 999px; padding: 7px 16px 7px 12px; background: #ffffff;
    margin: 0 6px 6px 0; cursor: pointer; }
[class*="st-key-un_pilulas"] label[data-selected="true"],
[class*="st-key-un_pilulas"] label[data-baseweb="radio"]:has(input:checked) { background: #ece7f7; border-color: #7565a8; }
</style>
""", unsafe_allow_html=True)

LIMITE_CARTOES = 60
NOME_CIDADE = "Rio Claro"


@st.cache_data(show_spinner="Lendo o cadastro do CNES…")
def unidades(arquivo, modificado):
    # `arquivo` e `modificado` só entram na chave do cache: ao trocar o CSV, a lista é lida de novo.
    return us.carregar_unidades(nome_cidade=NOME_CIDADE)


@st.cache_data
def internacoes_por_cnes(modificado):
    """CNES (7 dígitos) -> internações por câncer feminino registradas no hospital (2013-2025, 7 cânceres), ou {}
    se o banco não existe ou é antigo (sem CNES). Não é qualidade nem preferência: é só o que o SIH registrou."""
    try:
        import inteligencia as ti
        if not os.path.exists(BANCO):
            return {}
        conn = sqlite3.connect(BANCO)
        try:
            dados = ti.carregar_hospitais(conn, UF_REFERENCIA)
        finally:
            conn.close()
        if not dados:
            return {}
        lista = ti.lista_hospitais(dados)
        return dict(zip(lista["cnes"], lista["internacoes"]))
    except Exception:
        return {}


def inicio():
    if st.button("🏠 Início", key="un_inicio"):
        try:
            st.switch_page("app.py")
        except Exception:  # fora do painel (teste isolado): sem destino
            pass


def pergunta(texto, detalhe):
    st.markdown(f'<div class="escudo-pergunta">{html.escape(texto)}</div>'
                f'<span class="escudo-escopo cidade">📍 {html.escape(NOME_CIDADE)} <small>· {html.escape(detalhe)}</small></span>',
                unsafe_allow_html=True)


def cartao(u, n_internacoes):
    selos = (f'<span class="un-selo {u.natureza}">{html.escape(us.NATUREZA_CURTA[u.natureza])}</span>'
             f'<span class="un-selo grupo">{html.escape(us.GRUPOS[str(u.grupo)][0])}</span>')
    if n_internacoes:
        quantas = f"{int(n_internacoes):,}".replace(",", ".")
        selos += (f'<span class="un-selo cancer" title="Internações dos 7 cânceres femininos acompanhados, 2013–2025, '
                  f'registradas no SIH/SUS (não mede qualidade)">{quantas} internações por câncer</span>')
    linhas = []
    if u.endereco:
        linhas.append(f"📍 {html.escape(u.endereco)}" + (f" · CEP {html.escape(u.cep).replace('-', '&#8209;')}" if u.cep else ""))
    if u.telefone:
        linhas.append(f"📞 {html.escape(u.telefone)}")
    corpo = "".join(f'<div class="un-linha">{l}</div>' for l in linhas)
    return (f'<div class="un-cartao {u.natureza}">{selos}<div class="un-nome">{html.escape(u.nome)}</div>'
            f'<div class="un-tipo">{html.escape(u.tipo)} · CNES {html.escape(u.cnes)}</div>{corpo}'
            f'<div style="margin-top:6px"><a class="un-mapa" href="{html.escape(u.link_mapa)}" target="_blank" '
            f'rel="noopener noreferrer">Ver no mapa ↗</a></div></div>')


# ---------------- topo ----------------
inicio()
st.markdown('<div class="escudo-marca">Escudo Feminino</div>'
            f'<div class="escudo-titulo">Onde ser atendida em {html.escape(NOME_CIDADE)}</div>'
            '<div class="escudo-sub">As unidades de saúde da cidade em um só lugar: posto, exames, hospital e urgência, '
            'com endereço, telefone e mapa. A lista vem do cadastro oficial do Ministério da Saúde (CNES).</div>',
            unsafe_allow_html=True)
st.markdown('<div class="escudo-alerta"><b>Risco imediato:</b> ligue <b>190</b> (Polícia Militar). Emergência médica: '
            '<b>192</b> (SAMU). Violência contra a mulher: <b>Ligue 180</b>. Em perigo, não espere resposta de um painel.</div>',
            unsafe_allow_html=True)

arquivo = us.achar_arquivo()
df = unidades(arquivo or "", os.path.getmtime(arquivo) if arquivo else 0)

if df.empty:
    st.warning(df.attrs.get("aviso") or "Não encontrei estabelecimentos para mostrar.")
    st.caption("A lista depende do arquivo do CNES em banco\\cnes (ele não vai para o GitHub). Para conferir o que o "
               "arquivo tem, rode no terminal:  py algoritimos\\unidades_saude.py")
    st.stop()

internacoes = internacoes_por_cnes(os.path.getmtime(BANCO) if os.path.exists(BANCO) else 0)

# ---------------- 1. o que você procura ----------------
pergunta("O que você está procurando?", "cadastro ativo do CNES na cidade")
contagem = us.contar_por_grupo(df)
opcoes = ["Tudo"] + [g for g in us.ORDEM_GRUPOS if contagem[g] > 0]
rotulos = {"Tudo": f"Tudo ({len(df)})"} | {g: f"{us.GRUPOS[g][0]} ({contagem[g]})" for g in us.ORDEM_GRUPOS}
try:
    caixa = st.container(key="un_pilulas_grupo")
except TypeError:  # Streamlit antigo, sem key em container
    caixa = st.container()
with caixa:
    escolha = st.radio("Tipo de serviço", opcoes, horizontal=True, label_visibility="collapsed",
                       format_func=lambda g: rotulos[g], key="un_grupo")
if escolha != "Tudo":
    st.caption(us.GRUPOS[escolha][1])

c1, c2, c3 = st.columns([2, 1.4, 1.6])
busca = c1.text_input("Procurar pelo nome, rua ou bairro", key="un_busca", placeholder="ex.: Jardim, Santa Casa, Av. 1")
bairros = sorted(b for b in df["bairro"].unique() if b)
bairro = c2.selectbox("Bairro", ["Todos"] + bairros, key="un_bairro")
so_publicos = c3.checkbox("Só públicas e sem fins lucrativos", value=df.attrs.get("tem_natureza", False),
                          disabled=not df.attrs.get("tem_natureza", False), key="un_publicos",
                          help="Onde é mais provável haver atendimento pelo SUS. Desmarque para ver também clínicas privadas.")

grupos = None if escolha == "Tudo" else [escolha]
if escolha == "Tudo" and not busca.strip():
    grupos = [g for g in us.ORDEM_GRUPOS if g != "outros"]  # "Tudo" esconde farmácia, vigilância e afins
naturezas = ["publica", "sem_fins", "desconhecida"] if so_publicos else None
mostrar = us.filtrar(df, grupos=grupos, naturezas=naturezas, busca=busca, bairro=None if bairro == "Todos" else bairro)

if mostrar.empty:
    st.info("Nenhuma unidade com esses filtros. Tente tirar o bairro ou a busca, ou desmarcar “Só públicas e sem fins lucrativos”.")
else:
    pergunta(f"{len(mostrar)} unidade(s) encontrada(s)", "ordenadas por tipo e nome, não por qualidade")
    pontos = mostrar[mostrar["mapa"]]
    if not pontos.empty:
        st.map(pontos.rename(columns={"lat": "latitude", "lon": "longitude"})[["latitude", "longitude"]], size=18, zoom=12, height=340)
        sem_ponto = len(mostrar) - len(pontos)
        st.caption(f"{len(pontos)} unidade(s) no mapa" + (f"; {sem_ponto} sem coordenada confiável no cadastro (use o link “Ver no mapa” do cartão)." if sem_ponto else "."))
    cartoes = "".join(cartao(u, internacoes.get(u.cnes)) for u in mostrar.head(LIMITE_CARTOES).itertuples())
    st.markdown(f'<div class="un-grade">{cartoes}</div>', unsafe_allow_html=True)
    if len(mostrar) > LIMITE_CARTOES:
        st.caption(f"Mostrando as primeiras {LIMITE_CARTOES}. Use a busca ou o bairro para chegar nas outras, ou baixe a lista inteira abaixo.")

    st.markdown('<div class="escudo-leitura"><b>O que esta lista mostra (e o que não mostra)</b><ul>'
                + "".join(f"<li>{html.escape(f)}</li>" for f in us.leitura_lista(df, mostrar, grupos, so_publicos))
                + "</ul></div>", unsafe_allow_html=True)
    exportar = mostrar.drop(columns=["mapa", "link_mapa"]).assign(grupo=lambda d: d["grupo"].astype(str))
    st.download_button("Baixar esta lista (CSV)", exportar.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="unidades_de_saude_rio_claro.csv", mime="text/csv")

if internacoes:
    st.caption("O selo roxo “internações por câncer” liga o cadastro ao restante do Escudo: é quantas internações dos 7 cânceres "
               "femininos o SIH/SUS registrou naquele hospital em 2013–2025, de pacientes de qualquer cidade. Descreve o que "
               "aconteceu; não diz qual hospital é melhor.")

with st.expander("De onde vêm estes dados e quais são os limites"):
    st.markdown(f"""
- **Fonte:** CNES (Cadastro Nacional de Estabelecimentos de Saúde), arquivo `{html.escape(df.attrs.get('arquivo', ''))}`. Entram só os
  cadastros **ativos** do município; {df.attrs.get('desabilitados', 0)} cadastro(s) desabilitado(s) ficaram de fora.
- **Município:** pelo {'endereço da unidade' if df.attrs.get('criterio_municipio') == 'endereço' else 'município do gestor (o arquivo não traz o do endereço, então pode haver diferenças)'}.
- **Público x privado:** pela natureza jurídica do cadastro. {'' if df.attrs.get('tem_natureza') else 'Este arquivo não traz a natureza jurídica, então o filtro está desligado. '}Estar no CNES **não** prova que a unidade atende pelo SUS.
- **Mapa:** usa a latitude e longitude do próprio cadastro; ponto fora da cidade é ignorado. O link “Ver no mapa” abre uma busca no Google Maps.
- **Nomes:** o CNES grava em caixa alta e sem acento; a página só ajusta as maiúsculas.
- **Telefone, horário, vaga e fila** não são inferidos pelo cadastro. Confirme com a unidade ou com a Fundação Municipal de Saúde antes de ir.
- **Onde pedir mamografia e Papanicolau, direitos e outros caminhos:** veja o [Apoio à mulher](/apoio).
""")
    if df.attrs.get("ausentes"):
        st.caption("Informações que este arquivo não traz: " + ", ".join(df.attrs["ausentes"]) + ".")
