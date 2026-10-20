import html
import os
import sqlite3
import sys

import pandas as pd
import pydeck as pdk
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "algoritimos"))
sys.path.insert(0, os.path.join(AQUI, ".."))

import hospitais_oncologia as h  # noqa: E402
from configuracao_geografica import BANCO  # noqa: E402
from estilo import CSS  # noqa: E402
from navegacao import barra_de_navegacao  # noqa: E402
from localizacao import carregar_localizacao  # noqa: E402

# ============================================================
# HOSPITAIS HABILITADOS EM ONCOLOGIA -- 18/10/2026
#
# "Onde ficam os hospitais habilitados em oncologia, e qual está mais perto de onde eu moro?" Lista oficial do
# Ministério da Saúde (habilitação 2023) + endereço, telefone e posição do cadastro do CNES. Duas visões com os mesmos
# dados: Estado de São Paulo (para quem procura onde ir) e Brasil (contexto para gestores e pesquisadores).
#
# Só descreve. "Habilitado" não é vaga nem porta de entrada: o acesso é pela regulação (UBS -> CROSS). A distância é em
# linha reta. Só vira ponto no mapa quem passou nas conferências de posição. Nunca ranqueia hospital. O mapa mostra ONDE
# ficam os hospitais; ele não explica por que as pessoas vão de um lugar a outro. A lógica está em
# algoritimos/hospitais_oncologia.py; a porta de entrada é a área "Hospitais no Estado" do Apoio à mulher.
# ============================================================

st.set_page_config(page_title="MISM2 · Hospitais de câncer", page_icon="E", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.hc-grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 14px; margin: 10px 0; }
.hc-cartao { background: #fff; border: 1px solid #e6dceb; border-left: 6px solid #cdbfeb; border-radius: 4px 18px 4px 18px; padding: 14px 18px 16px; }
.hc-nome { font-family: Georgia, 'Times New Roman', serif; color: #2a1730; font-size: 1.16rem; line-height: 1.2; margin-top: 2px; }
.hc-onde { color: #7a6a80; font-size: .88rem; margin: 2px 0 8px; }
.hc-linha { color: #3d3852; font-size: .93rem; margin: 3px 0; }
.hc-aviso { color: #8a5a1e; font-size: .84rem; margin: 6px 0 0; }
.hc-selo { display: inline-block; font-size: .68rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
           border-radius: 999px; padding: 2px 9px; margin: 0 6px 4px 0; color: #fff; }
.hc-botoes { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
a.hc-chegar, a.hc-ligar { display: inline-block; text-align: center; border-radius: 999px; padding: 9px 18px; font-weight: 700; font-size: .92rem; text-decoration: none !important; }
a.hc-chegar { background: #5b2a55; color: #ffffff !important; flex: 1 1 160px; }
.hc-tipos { list-style: none; padding-left: 0; margin: .4rem 0 .6rem; }
.hc-tipos li { margin: .25rem 0; }
.hc-ponto { display: inline-block; width: .7rem; height: .7rem; border-radius: 50%; margin-right: .45rem; }
a.hc-chegar:hover { background: #3c1a38; }
a.hc-ligar { border: 1.5px solid #5b2a55; color: #5b2a55 !important; background: #ffffff; }
.hc-perto { background: #fff; border: 1px solid #e6dceb; border-left: 6px solid #5b2a55; border-radius: 4px 14px 4px 14px; padding: 10px 16px; margin: 6px 0; color: #3d3852; }
.hc-km { font-family: Georgia, serif; font-size: 1.25rem; color: #5b2a55; }
.hc-legenda span { display: inline-block; margin: 0 16px 4px 0; font-size: .88rem; color: #3d3852; }
.hc-legenda i { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
[class*="st-key-hc_pilulas"] label[data-testid="stRadioOption"], [class*="st-key-hc_pilulas"] label[data-baseweb="radio"] {
    border: 1px solid #cdbfeb; border-radius: 999px; padding: 6px 12px 6px 8px; background: #ffffff; margin: 0 6px 6px 0; cursor: pointer; }
[class*="st-key-hc_pilulas"] label[data-selected="true"], [class*="st-key-hc_pilulas"] label[data-baseweb="radio"]:has(input:checked) { background: #ece7f7; border-color: #5b2a55; }
</style>
""", unsafe_allow_html=True)

ROTULOS_ATE = 15  # acima disso os nomes escritos se sobrepõem (conferido na tela); ficam só no balão ao passar o mouse
PAGINA = 12


def _mtime(*nomes):
    return tuple(os.path.getmtime(os.path.join(h.DADOS, n)) if os.path.exists(os.path.join(h.DADOS, n)) else 0 for n in nomes)


@st.cache_data(show_spinner="Lendo a lista de hospitais…")
def hospitais(versao):
    return h.carregar()


@st.cache_data(show_spinner=False)
def centros(versao):
    """Centros das cidades de SP (do banco, ou de um CSV de teste). Vazio se não houver: a escolha de cidade some, sem quebrar."""
    csv_teste = os.environ.get("ESCUDO_CENTROS_CSV")
    if csv_teste and os.path.exists(csv_teste):
        df = pd.read_csv(csv_teste, dtype={"nome": str})
        df["chave"] = df["nome"].map(h.loc.ent.normalizar)
        return df[["nome", "chave", "latitude", "longitude"]]
    if not os.path.exists(BANCO):
        return pd.DataFrame(columns=["nome", "chave", "latitude", "longitude"])
    try:
        conexao = sqlite3.connect(f"file:{BANCO}?mode=ro", uri=True)
        try:
            return carregar_localizacao(conexao)
        finally:
            conexao.close()
    except Exception:
        return pd.DataFrame(columns=["nome", "chave", "latitude", "longitude"])


def inicio():
    st.markdown('<div style="background:#efe9f5;border-left:4px solid #5b2a55;border-radius:6px;padding:6px 12px;'
                'margin:4px 0 10px;font-size:.95rem;color:#2a1730">📍 Você está em: <b>Hospitais habilitados em oncologia</b></div>',
                unsafe_allow_html=True)
    barra_de_navegacao("hospitais", chave_inicio="hc_inicio")


def pergunta(texto, escopo):
    st.markdown(f'<div class="escudo-pergunta">{html.escape(texto)}</div>'
                f'<span class="escudo-escopo estado">🌎 {html.escape(escopo)}</span>', unsafe_allow_html=True)


def cartao(r):
    cor = h.TIPOS.get(str(r.tipo), h.TIPOS["Tipo não informado"])[0]
    selo = f'<span class="hc-selo" style="background:{cor}">{html.escape(str(r.tipo))}</span>'
    corpo = ""
    if r.habilitacao:
        corpo += f'<div class="hc-linha">{html.escape(r.habilitacao)}</div>'
    km = getattr(r, "km", None)
    if km is not None and km == km:  # km == km: NaN (sem posição confirmada) não mostra distância
        corpo += f'<div class="hc-linha"><span class="hc-km">{km:.0f} km</span> em linha reta da sua cidade</div>'
    if r.endereco:
        corpo += f'<div class="hc-linha">📍 {html.escape(r.endereco)}</div>'
    if r.telefone:
        corpo += f'<div class="hc-linha">📞 {html.escape(r.telefone)}</div>'
    if not r.no_mapa:
        corpo += f'<div class="hc-aviso">Sem ponto no mapa: {html.escape(r.motivo or "posição não confirmada")}.</div>'
    botoes = (f'<a class="hc-chegar" title="Abre a rota no Google Maps" href="{html.escape(h.link_chegar(r.nome, r.endereco, r.municipio, r.uf))}" '
              'target="_blank" rel="noopener noreferrer">📍 Como chegar</a>')
    ligar = h.link_ligar(r.telefone)
    if ligar:
        botoes += f'<a class="hc-ligar" href="{html.escape(ligar)}">📞 Ligar</a>'
    return (f'<div class="hc-cartao" style="border-left-color:{cor}">{selo}<div class="hc-nome">{html.escape(r.nome)}</div>'
            f'<div class="hc-onde">{html.escape(r.municipio)} · {html.escape(r.uf)}</div>{corpo}<div class="hc-botoes">{botoes}</div></div>')


# ---------------- topo ----------------
inicio()
try:  # quem chegou pela área "Hospitais no Estado" do Apoio volta para ela sem passar pelo Panorama
    st.page_link("pages/apoio.py", label="← Voltar ao Apoio à mulher")
except Exception:  # Streamlit antigo, ou fora do painel (teste isolado)
    pass
st.markdown('<div class="escudo-marca">MISM2</div>'
            '<div class="escudo-titulo">Hospitais habilitados em <em>oncologia</em></div>'
            '<div class="escudo-sub">Onde ficam os hospitais que o Ministério da Saúde habilitou para tratar câncer pelo SUS, '
            'e qual está mais perto da sua cidade. <b>Habilitado não é vaga:</b> o acesso é pela regulação.</div>',
            unsafe_allow_html=True)
st.markdown('<div class="escudo-alerta"><b>Risco imediato:</b> ligue <b>190</b> (Polícia Militar). Emergência médica: '
            '<b>192</b> (SAMU). Violência contra a mulher: <b>Ligue 180</b>. Em perigo, não espere resposta de um painel.</div>',
            unsafe_allow_html=True)

df = hospitais(_mtime(h.ARQ_GEO, h.ARQ_LISTA))
if df.empty:
    st.warning("Não encontrei a lista de hospitais habilitados (dados_geograficos). Rode "
               "py etl\\gerar_lista_hospitais_oncologia.py para criá-la a partir da planilha do Ministério.")
    st.stop()
if not df.attrs.get("tem_posicao"):
    st.info("O mapa ainda não tem as posições dos hospitais neste computador. A lista abaixo já está completa; para ver o mapa, "
            "rode py etl\\gerar_hospitais_oncologia_geo.py (só lê o CNES).")

# ---------------- 1. escopo, filtros ----------------
try:
    caixa = st.container(key="hc_pilulas_escopo")
except TypeError:  # Streamlit antigo, sem key em container
    caixa = st.container()
n_sp = int((df["uf"] == "SP").sum())
with caixa:
    escopo = st.radio("Mostrar", ["sp", "br"], horizontal=True, label_visibility="collapsed", key="hc_escopo",
                      format_func=lambda e: f"Estado de São Paulo ({n_sp})" if e == "sp" else f"Brasil ({len(df)})")
base = df[df["uf"] == "SP"] if escopo == "sp" else df
rotulo_escopo = "Todo o Estado de São Paulo" if escopo == "sp" else "Brasil"

pergunta("Onde ficam, e qual está mais perto de onde você mora?" if escopo == "sp" else "Onde ficam os hospitais habilitados no Brasil?", rotulo_escopo)

local = centros(_mtime(h.ARQ_GEO)) if escopo == "sp" else None
cidade = ""
if escopo == "sp" and local is not None and len(local):
    nomes = h.cidades_disponiveis(local)
    padrao = nomes.index("Rio Claro") + 1 if "Rio Claro" in nomes else 0
    cidade = st.selectbox("Em que cidade você mora? (digite para filtrar)", ["— escolher —"] + nomes, index=padrao, key="hc_cidade")
    cidade = "" if cidade.startswith("—") else cidade
    for km, r in h.mais_proximos(base, local, cidade, n=3) if cidade else []:
        st.markdown(f'<div class="hc-perto"><span class="hc-km">{km:.0f} km</span> em linha reta · <b>{html.escape(r.nome)}</b> · '
                    f'{html.escape(r.municipio)} · {html.escape(str(r.tipo))}</div>', unsafe_allow_html=True)
    if cidade:
        st.caption("Distância em linha reta entre o centro da sua cidade e o hospital, só para você se situar. Não é rota nem tempo de viagem, "
                   "e quem decide para onde você vai é a regulação, não a proximidade.")

if escopo == "br":
    c1, c2, c3 = st.columns([1.2, 1.6, 2])
    ufs = c1.multiselect("Estado", sorted(df["uf"].unique()), key="hc_ufs", placeholder="Todos")
else:
    c2, c3 = st.columns([1.6, 2])
    ufs = []
tipos = c2.multiselect("Tipo de habilitação", [t for t in h.ORDEM_TIPOS if t in set(base["tipo"].astype(str))], key="hc_tipos", placeholder="Todos")
busca = c3.text_input("Procure pelo nome do hospital ou da cidade", key="hc_busca", placeholder="ex.: Barretos, Santa Casa, Campinas")
mostrar = h.filtrar(base, ufs=ufs, tipos=tipos, busca=busca)

# ---------------- 2. mapa ----------------
def _rgb(hexa):
    hexa = hexa.lstrip("#")
    return [int(hexa[i:i + 2], 16) for i in (0, 2, 4)]


def _letras(rotulos):
    """Letras que os nomes usam, como texto JS entre aspas (o TextLayer só desenha o que está aqui; sem isso, acento some).
    O pydeck vira lista em expressão e quebra no navegador, por isso vai uma string literal."""
    letras = sorted(set("".join(rotulos) + " 0123456789") - {"'", "\\"})
    return "'" + "".join(letras) + "'"


def desenhar_mapa(pontos, origem, escopo):
    """Pontos coloridos pelo tipo, nome ao passar o mouse (ou tocar) e, com poucos hospitais na tela, o nome escrito ao lado.
    Com centenas de pontos os nomes se atropelariam; por isso o rótulo só aparece quando o filtro deixa até ROTULOS_ATE."""
    dados = pd.DataFrame({
        "lon": pontos["lon"].astype(float).to_numpy(), "lat": pontos["lat"].astype(float).to_numpy(),
        "nome": pontos["nome"].astype(str).to_numpy(),
        "rotulo": [n if len(n) <= 30 else n[:29].rstrip() + "…" for n in pontos["nome"].astype(str)],
        "detalhe": [f"{m} · {tp}" for m, tp in zip(pontos["municipio"].astype(str), pontos["tipo"].astype(str))],
        "cor": [_rgb(h.TIPOS[str(tp)][0]) for tp in pontos["tipo"]]})
    camadas = [pdk.Layer("ScatterplotLayer", dados, get_position="[lon, lat]", get_fill_color="cor", get_line_color=[255, 255, 255],
                         stroked=True, line_width_min_pixels=1, get_radius=3500 if escopo == "sp" else 22000,
                         radius_min_pixels=5, radius_max_pixels=13, pickable=True)]
    coordenadas = dados[["lon", "lat"]].values.tolist()
    if origem:
        casa = pd.DataFrame({"lon": [origem[1]], "lat": [origem[0]], "nome": ["Sua cidade"], "detalhe": ["centro da cidade escolhida"]})
        camadas.append(pdk.Layer("ScatterplotLayer", casa, get_position="[lon, lat]", get_fill_color=[31, 95, 181], get_line_color=[255, 255, 255],
                                 stroked=True, line_width_min_pixels=2, get_radius=2500, radius_min_pixels=7, radius_max_pixels=15, pickable=True))
        coordenadas.append([origem[1], origem[0]])
    if len(dados) <= ROTULOS_ATE:
        camadas.append(pdk.Layer("TextLayer", dados, get_position="[lon, lat]", get_text="rotulo", get_size=13, get_color=[40, 20, 40],
                                 get_pixel_offset=[0, -16], get_text_anchor="'middle'", get_alignment_baseline="'bottom'",
                                 background=True, get_background_color=[255, 255, 255, 215], background_padding=[3, 1],
                                 character_set=_letras(dados["rotulo"]), pickable=False))
    vista = pdk.ViewState(**h.vista_do_mapa(coordenadas))
    st.pydeck_chart(pdk.Deck(layers=camadas, initial_view_state=vista, map_style=pdk.map_styles.CARTO_LIGHT, height=460,
                             tooltip={"html": "<b>{nome}</b><br/>{detalhe}",
                                      "style": {"backgroundColor": "#3c1a38", "color": "white", "fontSize": "13px"}}))


pontos = mostrar[mostrar["no_mapa"]]
if len(pontos):
    origem = None
    if cidade and local is not None:
        origem = h.loc._ponto(local, h.loc.ent.normalizar(cidade))
    desenhar_mapa(pontos, origem, escopo)
    legenda = "".join(f'<span><i style="background:{h.TIPOS[t][0]}"></i>{html.escape(t)}</span>' for t in h.contar_por_tipo(pontos))
    if cidade and local is not None:
        legenda += '<span><i style="background:#1f5fb5"></i>sua cidade</span>'
    st.markdown(f'<div class="hc-legenda">{legenda}</div>', unsafe_allow_html=True)
    sem_ponto = len(mostrar) - len(pontos)
    st.caption(f"{len(pontos)} no mapa" + (f"; {sem_ponto} só na lista, porque a posição do cadastro não passou nas conferências." if sem_ponto else ".")
               + (" Os nomes aparecem escritos ao lado de cada ponto." if len(pontos) <= ROTULOS_ATE else
                  f" Passe o mouse (ou toque) em um ponto para ver o nome; com até {ROTULOS_ATE} hospitais na tela (use os filtros) os nomes aparecem escritos."))
elif df.attrs.get("tem_posicao"):
    st.info("Nenhum hospital com posição confirmada neste filtro.")

# ---------------- 2b. o que significam os tipos ----------------
if len(mostrar):
    itens = "".join(f'<li><span class="hc-ponto" style="background:{h.TIPOS[t][0]}"></span><b>{html.escape(t)}</b>: {html.escape(h.TIPOS[t][1])}</li>'
                    for t in h.ORDEM_TIPOS if t in set(mostrar["tipo"].astype(str)))
    st.markdown('<div class="escudo-leitura"><b>O que significam UNACON e CACON (e os outros tipos)</b>'
                f'<ul class="hc-tipos">{itens}</ul>'
                '<p>Em resumo: o <b>CACON</b> trata todos os tipos de câncer e o <b>UNACON</b> os mais frequentes, por isso um caso menos comum '
                'pode ser encaminhado de um UNACON para um CACON. Os dois são <b>habilitados pelo Ministério da Saúde</b>; '
                'o tipo não diz qual hospital é melhor, e o acesso continua sendo pela unidade de saúde e pela regulação.</p></div>',
                unsafe_allow_html=True)

# ---------------- 3. leitura ----------------
st.markdown('<div class="escudo-leitura"><b>Como ler</b><ul>'
            f'<li>{html.escape(h.leitura(mostrar))}</li>'
            '<li>A lista é a do Ministério da Saúde (habilitação 2023). Estar nela <b>não garante</b> vaga nem atendimento direto: '
            'o caminho é a unidade de saúde e a regulação.</li>'
            '<li>O mapa mostra <b>onde ficam</b> os hospitais; ele não explica por que as pessoas vão de um lugar a outro, e não diz qual é melhor.</li>'
            + ('<li>Os dados do Escudo enxergam só as internações em hospitais de São Paulo: dá para ver quem vem de outros estados para cá, '
               'mas não quem sai de São Paulo para se tratar fora.</li>' if escopo == "br" else '') +
            '</ul></div>', unsafe_allow_html=True)

# ---------------- 4. cartões ----------------
if mostrar.empty:
    st.info("Nenhum estabelecimento com esse filtro. Apague a busca ou escolha outro tipo.")
else:
    assinatura = (escopo, tuple(ufs), tuple(tipos), busca.strip().lower())
    if st.session_state.get("hc_assinatura") != assinatura:
        st.session_state["hc_assinatura"] = assinatura
        st.session_state["hc_limite"] = PAGINA
    limite = st.session_state.setdefault("hc_limite", PAGINA)
    # com a cidade escolhida, a lista segue o topo: do hospital mais perto ao mais longe (sem posição confirmada, no fim)
    lista = h.ordenar_por_distancia(mostrar, local, cidade) if (escopo == "sp" and cidade) else mostrar
    ordenada = "km" in lista.columns
    st.markdown(f'<div class="escudo-pergunta">{len(mostrar)} estabelecimento{"s" if len(mostrar) != 1 else ""}</div>', unsafe_allow_html=True)
    if ordenada:
        st.caption(f"Do mais perto ao mais longe de {cidade} (linha reta entre o centro da cidade e o hospital). "
                   "Quem não tem posição confirmada vem por último, sem distância.")
    st.markdown(f'<div class="hc-grade">{"".join(cartao(r) for r in lista.head(limite).itertuples())}</div>', unsafe_allow_html=True)
    if len(mostrar) > limite:
        if st.button(f"Mostrar mais ({len(mostrar) - limite} restantes)", key="hc_mais"):
            st.session_state["hc_limite"] = limite + PAGINA
            st.rerun()

if escopo == "br":
    with st.expander("Quantos hospitais habilitados há em cada estado"):
        st.dataframe(pd.DataFrame(h.contar_por_uf(df), columns=["Estado", "Estabelecimentos", "Com ponto no mapa"]), hide_index=True, width="stretch")
        st.caption("Conta estabelecimentos habilitados, não capacidade: um hospital grande e um serviço pequeno contam um cada. "
                   "Não compara estados nem diz onde falta atendimento.")

with st.expander("De onde vêm estes dados e quais são os limites"):
    st.markdown("""
- **Lista:** planilha "Hospitais habilitados em Oncologia" do Ministério da Saúde (habilitação 2023). Pode ter mudado desde então.
- **Endereço, telefone e posição:** cadastro do CNES (arquivo de 08/2026). Cadastro não é serviço aberto agora: **ligue antes de ir**.
- **Posição no mapa:** só entra o ponto que passou nas conferências (cadastro ativo, estado igual ao da planilha, coordenada dentro do estado e,
  em São Paulo, perto do município do hospital). Quem não passou fica na lista, sem ponto. Nunca se põe o ponto no centro da cidade.
- **Distância:** linha reta entre o centro da cidade e o hospital. Não é rota nem tempo de viagem.
- **Tipos:** UNACON e CACON são os hospitais de alta complexidade em oncologia; os outros são hospitais gerais habilitados para cirurgia de câncer e serviços de radioterapia.
- Esta página **descreve**; não ranqueia hospitais nem explica o motivo de nenhum deslocamento.
""")
