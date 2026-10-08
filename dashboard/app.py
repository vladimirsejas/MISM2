import html
import os
import sqlite3
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "algoritimos"))

from configuracao_geografica import BANCO, listar_municipios_disponiveis, obter_municipio, UF_REFERENCIA
from lia import INICIO, Contexto, responder as lia_responder
from passeio import PARADAS, parada as passeio_parada
from lia_rosto import img as rosto_lia
from estilo import CSS
from inteligencia import (
    ano_atipico_no_estado,
    anos_fora_do_padrao,
    anos_incompletos,
    anos_fora_todos,
    cancer_de,
    canceres_com_duplicidade,
    carregar_faixas,
    carregar_fluxo,
    carregar_serie,
    cidades_parecidas,
    comparar_faixas,
    confiabilidade,
    destaques_cancer,
    ficha_cancer,
    fluxo_da_cidade,
    formatar_numero,
    evolucao_fluxo,
    leitura_cidade,
    leitura_evolucao,
    leitura_evolucao_fluxo,
    leitura_faixas,
    leitura_fluxo,
    pontos_mapa_fluxo,
    hospitais_fluxo,
    leitura_hospitais,
    nome_uf,
    CENTROS_UF,
    leitura_ponta_projecao,
    ligacoes_fluxo,
    mix_comparacao,
    nome_doenca,
    projetar,
    perfil_cidade,
    por_cancer_fluxo,
    porte_das_cidades,
    leitura_aparece,
    leitura_comparacao,
    quando_aparece,
    radar_futuro,
    resumo_doencas,
    resumo_fluxo,
    tabela_aparece_para_tela,
    tabela_comparacao,
    ritmo_estadual_na_escala,
    serie_doenca,
    tendencia_no_periodo,
    testar_projecao,
)

# ============================================================
# ESCUDO FEMININO — painel
#
# Reescrito do zero (09/2026). O painel anterior tinha 7 abas que
# repetiam os mesmos números em vários lugares. Regras deste:
#   - cada informação tem uma casa só;
#   - todo gráfico = pergunta (título) + gráfico + leitura em texto;
#   - a tela não calcula nada: tudo vem de algoritimos/inteligencia.py.
# Portas (abas): Panorama (o que está acontecendo), Evolução (como
# mudou e para onde vai), Investigar (o que merece ser pesquisado),
# Planejamento (que evidências entram na discussão), Método. A Lia
# (lateral; algoritimos/lia.py, docs/LIA.md) atravessa todas: conduz
# por botões e leva o painel até o gráfico. Sem caixa de texto livre
# (saiu em 09/2026). Dinheiro aparece sempre como "valor hospitalar
# registrado no SIH/SUS", nunca como orçamento.
# O painel antigo continua no histórico do git (commit 273fbe5).
# ============================================================


st.set_page_config(
    page_title="Escudo Feminino",
    page_icon="E",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta validada para daltonismo (ver skill de visualização):
# azul = a cidade, cinza = referência, laranja = fora do padrão.
AZUL = "#2a78d6"
AZUL_FAIXA = "rgba(42,120,214,0.13)"
CINZA = "#b9b7c4"
LARANJA = "#eb6834"
TINTA = "#292541"
TINTA_SUAVE = "#706b82"
GRADE = "#ebe8f2"
CONFIG_GRAFICO = {"displayModeBar": False}

st.markdown(CSS, unsafe_allow_html=True)

# Banco refeito (nova carga) com o painel aberto: o cache (st.cache_data)
# ainda seria o do banco antigo -- foi o que aconteceu em 24/09/2026 (o
# banco já tinha 6 cânceres e o painel mostrava 1). Quando a data de
# modificação do arquivo muda, o cache é limpo e os dados são lidos de
# novo; se o banco não mudou, o cache continua valendo.
_versao_banco = os.path.getmtime(BANCO) if os.path.exists(BANCO) else None
if st.session_state.get("versao_banco") != _versao_banco:
    st.cache_data.clear()
    st.session_state["versao_banco"] = _versao_banco


# ============================================================
# DADOS (uma consulta só, via inteligencia.py)
# ============================================================

@st.cache_data
def municipios():
    return listar_municipios_disponiveis()


@st.cache_data
def serie_municipio(origem):
    conn = sqlite3.connect(BANCO)
    try:
        return carregar_serie(conn, origem, UF_REFERENCIA)
    finally:
        conn.close()


@st.cache_data
def duplicados_municipio(origem):
    conn = sqlite3.connect(BANCO)
    try:
        return canceres_com_duplicidade(conn, origem)
    finally:
        conn.close()


@st.cache_data
def faixas_municipio(origem):
    conn = sqlite3.connect(BANCO)
    try:
        return carregar_faixas(conn, origem, UF_REFERENCIA)
    finally:
        conn.close()


@st.cache_data
def porte_cidades():
    conn = sqlite3.connect(BANCO)
    try:
        return porte_das_cidades(conn, UF_REFERENCIA)
    finally:
        conn.close()


@st.cache_data
def fluxo_geral():
    conn = sqlite3.connect(BANCO)
    try:
        return carregar_fluxo(conn, UF_REFERENCIA)
    finally:
        conn.close()


@st.cache_data
def fluxo_cidade(origem, codigo_ibge):
    conn = sqlite3.connect(BANCO)
    try:
        return fluxo_da_cidade(conn, origem, codigo_ibge, UF_REFERENCIA)
    finally:
        conn.close()


@st.cache_data
def radar(origem):
    return radar_futuro(serie_municipio(origem))


def reais(valor, compacto=False):
    """R$ no formato brasileiro; compacto para rótulos de gráfico."""
    if compacto and valor >= 1e6:
        return f"R$ {formatar_numero(valor / 1e6, 2)} mi"
    if compacto and valor >= 1e3:
        return f"R$ {formatar_numero(valor / 1e3)} mil"
    return f"R$ {formatar_numero(valor)}"


def selo_escopo(tipo, detalhe=""):
    """Diz de quem são os números do bloco: "estado" (todas as cidades de SP, não muda
    quando se troca de município) ou "cidade" (a escolhida no topo)."""
    if tipo == "estado":
        rotulo, padrao = "🌎 Todo o Estado de São Paulo", "não muda quando você troca de cidade"
    else:
        rotulo, padrao = f"📍 {html.escape(nome_cidade)}", "muda quando você troca de cidade"
    st.markdown(f'<div class="escudo-escopo {tipo}">{rotulo} <small>· {detalhe or padrao}</small></div>',
                unsafe_allow_html=True)


def pergunta(texto, escopo=None, detalhe=""):
    st.markdown(f'<div class="escudo-pergunta">{texto}</div>', unsafe_allow_html=True)
    if escopo:
        selo_escopo(escopo, detalhe)


def leitura(titulo, frases):
    st.markdown(
        f'<div class="escudo-leitura"><b>{titulo}</b><ul>'
        + "".join(f"<li>{f}</li>" for f in frases) + "</ul></div>",
        unsafe_allow_html=True,
    )


def estilizar(fig, altura):
    fig.update_layout(
        height=altura,
        font={"family": "DM Sans, sans-serif", "size": 13, "color": TINTA},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin={"l": 10, "r": 30, "t": 16, "b": 10},
        legend={"orientation": "h", "yanchor": "top", "y": -0.12, "x": 0, "title": None},
        hoverlabel={"bgcolor": "#ffffff", "font_color": TINTA, "bordercolor": GRADE},
        separators=",.",
        showlegend=True,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRADE, automargin=True, tickfont={"color": TINTA_SUAVE})
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, automargin=True, tickfont={"color": TINTA_SUAVE})
    return fig


lista_municipios = municipios()
if not lista_municipios:
    st.error("Nenhum município disponível no banco.")
    st.stop()


# ============================================================
# TOPO
# ============================================================

nomes = [m["nome"] for m in lista_municipios]
padrao = obter_municipio()
indice_padrao = next((i for i, m in enumerate(lista_municipios) if m["origem"] == padrao), 0)

col_titulo, col_cidade = st.columns([2.2, 1])
with col_cidade:
    nome_cidade = st.selectbox("Município", nomes, index=indice_padrao,
                               help="Digite para procurar entre os municípios de SP.")
    # Apoio à mulher (dashboard/pages/apoio.py): lâminas de apoio, separadas
    # deste estudo da doença. A única ligação é este botão vermelho (pedido
    # do autor); o estilo está em estilo.py ("botao_apoio").
    try:
        caixa_apoio = st.container(key="botao_apoio")
    except TypeError:  # Streamlit antigo: sem key em container
        caixa_apoio = st.container()
    with caixa_apoio:
        try:
            st.page_link("pages/apoio.py", label="Apoio à mulher")
        except Exception:  # Streamlit antigo, sem page_link
            st.markdown('<a href="/apoio" target="_self">Apoio à mulher</a>', unsafe_allow_html=True)
cidade = next(m for m in lista_municipios if m["nome"] == nome_cidade)
ORIGEM = cidade["origem"]

serie = serie_municipio(ORIGEM)
resumo = resumo_doencas(serie) if not serie.empty else pd.DataFrame()

with col_titulo:
    st.markdown('<div class="escudo-marca">Escudo Feminino</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="escudo-titulo">Câncer em mulheres de {nome_cidade}</div>',
                unsafe_allow_html=True)
    if not resumo.empty:
        ano_ini, ano_fim = int(serie["ano"].min()), int(serie["ano"].max())
        st.markdown(
            f'<div class="escudo-sub">De {ano_ini} a {ano_fim}, mulheres que moram em {nome_cidade} '
            f'tiveram <b>{formatar_numero(resumo["internacoes"].sum())} internações</b> no SUS pelos '
            f'{len(resumo)} tipos de câncer acompanhados, com <b>{formatar_numero(resumo["obitos"].sum())} '
            f'óbitos</b> durante a internação e <b>{reais(resumo["valor_total"].sum())}</b> em valores '
            f'hospitalares registrados no SIH/SUS.</div>',
            unsafe_allow_html=True,
        )

if resumo.empty:
    st.info(f"Ainda não há internações registradas para {nome_cidade}.")
    st.stop()

# ------------------------------------------------------------
# ESTADO DA TELA
#
# Aba, câncer em foco, medida e camadas ficam em chaves próprias do
# session_state, e cada widget tem uma chave que inclui o valor atual
# (ex.: "w_doenca_PULMAO"). Motivo: o Streamlit apaga o estado de um
# widget que sai da tela, e quando ele volta o navegador pode devolver
# o valor ANTIGO, desfazendo o que a Lia escolheu (foi o que aconteceu
# nos testes: pulmão virava mama ao trocar de aba). Com a chave
# atrelada ao valor, todo valor mudado por fora cria um widget novo,
# sem lembrança velha. definir() é como a Lia "leva" o painel.
# ------------------------------------------------------------

ABAS = ["Panorama", "Evolução", "Investigar", "Planejamento", "Método"]
PADROES = {"aba": "Panorama", "medida": "Internações",
           "ver_estado": True, "ver_fora": True, "ver_projecao": False}
for chave, valor in PADROES.items():
    st.session_state.setdefault(chave, valor)


def definir(chave, valor):
    st.session_state[chave] = valor


def chave_widget(chave):
    return f"w_{chave}_{st.session_state[chave]}"


def sincronizar(chave, chave_do_widget):
    st.session_state[chave] = st.session_state[chave_do_widget]


def seletor(onde, rotulo, chave, opcoes, **kwargs):
    """st.radio preso à chave persistente (ver ESTADO DA TELA)."""
    k = chave_widget(chave)
    return onde.radio(rotulo, opcoes, index=opcoes.index(st.session_state[chave]), key=k,
                      on_change=sincronizar, args=(chave, k), **kwargs)


def chave_liga(onde, rotulo, chave, **kwargs):
    """st.toggle preso à chave persistente (ver ESTADO DA TELA)."""
    k = chave_widget(chave)
    return onde.toggle(rotulo, value=st.session_state[chave], key=k,
                       on_change=sincronizar, args=(chave, k), **kwargs)


# Câncer em foco: começa pelo maior; se trocar de cidade e ele não
# existir lá, volta para o maior. Vale para todas as abas.
codigos = resumo["tipo_cancer"].tolist()
if st.session_state.get("doenca") not in codigos:
    definir("doenca", codigos[0])
    st.session_state.pop("ultimo_clique", None)
doenca = st.session_state["doenca"]
nome = nome_doenca(doenca)

ctx_lia = Contexto(serie=serie, cidade=nome_cidade, faixas=faixas_municipio(ORIGEM),
                   duplicados=tuple(duplicados_municipio(ORIGEM)),
                   fluxo=fluxo_geral(), fluxo_cidade=fluxo_cidade(ORIGEM, cidade["codigo_ibge"]))
st.session_state.setdefault("lia", {"cidade": None, "atual": None, "pilha": []})
lia_estado = st.session_state["lia"]
if lia_estado["cidade"] != ORIGEM:  # trocou de cidade: a Lia recomeça
    lia_estado.update({"cidade": ORIGEM, "atual": lia_responder(ctx_lia, INICIO), "pilha": []})


def lia_mostrar(resposta):
    """Guarda a resposta e leva o painel até o gráfico dela."""
    if lia_estado["atual"] is not None:
        lia_estado["pilha"].append(lia_estado["atual"])
    lia_estado["atual"] = resposta
    lia_estado["falas"] = lia_estado.get("falas", 0) + 1  # balão novo -> animação
    st.session_state["lia_fechada"] = True
    aplicar_destino(resposta.destino)


def aplicar_destino(destino):
    """Leva o painel até o gráfico de uma resposta (aba, câncer,
    medida, camadas). Usado pela Lia e pelo Passeio."""
    destino = destino or {}
    if destino.get("aba") in ABAS:
        definir("aba", destino["aba"])
    if destino.get("cancer") in codigos:
        definir("doenca", destino["cancer"])
        st.session_state["ultimo_clique"] = destino["cancer"]
    if destino.get("medida"):
        definir("medida", destino["medida"])
    for camada, valor in (destino.get("camadas") or {}).items():
        definir(camada, valor)


def lia_clicar(acao):
    lia_mostrar(lia_responder(ctx_lia, acao))


def recarregar():
    """st.rerun nas versões novas do Streamlit; experimental_rerun nas antigas."""
    (getattr(st, "rerun", None) or st.experimental_rerun)()


def lia_voltar():
    if lia_estado["pilha"]:
        lia_estado["atual"] = lia_estado["pilha"].pop()
        lia_estado["falas"] = lia_estado.get("falas", 0) + 1


def passeio_ir(indice):
    """Vai para a parada `indice` do Passeio (None = sair)."""
    st.session_state["passeio"] = indice
    if indice is not None:
        st.session_state["lia_fechada"] = True  # o passeio substitui as boas-vindas do centro
        aplicar_destino(passeio_parada(ctx_lia, indice)["destino"])


def balao(nome):
    """Container do balão da Lia (ver CSS). A key muda a cada fala, para
    o balão "nascer" de novo com a animação. Streamlit antigo, sem key
    em container: cai num container com borda, sem a pontinha."""
    chave = f"lia_balao_{nome}_{lia_estado.get('falas', 0)}"
    try:
        return st.container(key=chave)
    except TypeError:
        return st.container(border=True)


def rosto(expressao, tamanho):
    """O rosto da Lia, "respirando" devagar (ver CSS)."""
    return f'<div class="lia-rosto">{rosto_lia(expressao, tamanho)}</div>'


# ------------------------------------------------------------
# BOAS-VINDAS DA LIA (primeiro acesso)
# ------------------------------------------------------------

if not st.session_state.get("lia_fechada"):
    boas_vindas = lia_responder(ctx_lia, INICIO)
    c_rosto, c_fala = st.columns([1, 4.6])
    with c_rosto:
        st.markdown(rosto("acolhedora", 150), unsafe_allow_html=True)
    with c_fala, balao("centro"):
        st.markdown(f'<div class="lia-nome">Lia <span>· pesquisadora do Escudo Feminino</span></div>'
                    f'<div class="lia-fala-grande">{boas_vindas.fala.replace("**", "")}</div>',
                    unsafe_allow_html=True)
        # 4 portas de entrada (docs/LIA.md); os 8 caminhos ficam na lateral
        principais = {"mais_aparece", "aumentando", "atencao", "futuro"}
        colunas = st.columns(2)  # 2 x 2: os rótulos cabem inteiros
        for i, (rotulo, acao) in enumerate(a for a in boas_vindas.botoes if a[1].get("id") in principais):
            colunas[i % 2].button(rotulo, key=f"bv_{i}", on_click=lia_clicar, args=(acao,),
                              use_container_width=True)
        st.button("Prefiro explorar sozinha", key="bv_fechar",
                  on_click=lambda: st.session_state.update(lia_fechada=True))

# Abas + botão "Início" (pedido do autor, 09/2026): de qualquer aba, um
# clique volta ao Panorama, a página inicial do Escudo.
col_abas, col_inicio = st.columns([5, 1])
with col_abas:
    aba = seletor(st, "Navegação", "aba", ABAS, horizontal=True, label_visibility="collapsed")
with col_inicio:
    try:
        caixa_inicio = st.container(key="botao_inicio_painel")
    except TypeError:  # Streamlit antigo: sem key em container
        caixa_inicio = st.container()
    caixa_inicio.button("🏠 Início", key="inicio_painel", on_click=definir, args=("aba", "Panorama"),
                        use_container_width=True, disabled=aba == "Panorama",
                        help="Volta à página inicial do Escudo.")


# ============================================================
# PANORAMA — o que está acontecendo?
# ============================================================

MEDIDAS = {
    "Internações": ("internacoes", "Quais cânceres mais levam as mulheres de {c} ao hospital?", formatar_numero),
    "Valor hospitalar registrado": ("valor_total", "Em quais cânceres se concentram os valores hospitalares registrados em {c}?",
                                    lambda v: reais(v, compacto=True)),
    "Óbitos na internação": ("obitos", "Em quais cânceres mais mulheres de {c} morrem durante a internação?", formatar_numero),
    "Dias de internação": ("dias_permanencia", "Quais cânceres ocupam mais dias de internação em {c}?", formatar_numero),
}

if aba == "Panorama":
    medida = seletor(st, "Medir por", "medida", list(MEDIDAS), horizontal=True)
    coluna, titulo, formato = MEDIDAS[medida]
    pergunta(titulo.format(c=nome_cidade), "cidade", f"só moradoras de {html.escape(nome_cidade)}")
    st.markdown('<div class="escudo-dica">Total no período. Clique numa barra para pôr aquele câncer em foco.'
                + (' Valor hospitalar registrado = o que as AIHs registraram no SIH/SUS; não é o orçamento '
                   'do município nem o custo total do tratamento.' if coluna == "valor_total" else "")
                + '</div>', unsafe_allow_html=True)

    barras = resumo.sort_values(coluna)  # o maior fica em cima
    fig = go.Figure(go.Bar(
        x=barras[coluna], y=barras["doenca"], orientation="h",
        text=[formato(v) for v in barras[coluna]],
        textposition="outside", cliponaxis=False,
        marker={"color": [AZUL if c == doenca else CINZA for c in barras["tipo_cancer"]],
                "line": {"width": 0}},
        customdata=barras[["tipo_cancer"]].values,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        showlegend=False,
    ))
    fig.update_xaxes(visible=False, range=[0, max(barras[coluna].max(), 1) * 1.15])
    fig.update_yaxes(showgrid=False)
    estilizar(fig, altura=70 + 42 * len(barras))
    fig.update_layout(bargap=0.3, showlegend=False)

    try:
        evento = st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO,
                                 on_select="rerun", selection_mode="points", key="barras")
    except TypeError:  # Streamlit antigo, sem clique em gráfico
        st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
        evento = None

    # O clique só vale quando é novo: a seleção do gráfico continua
    # "ligada" nas próximas execuções, e sem isso ela desfaria uma
    # troca feita depois pelo seletor.
    pontos = (evento or {}).get("selection", {}).get("points", []) if evento else []
    if pontos:
        clicado = (pontos[0].get("customdata", [None])[0]
                   or dict(zip(resumo["doenca"], resumo["tipo_cancer"])).get(pontos[0].get("y")))
        if clicado and clicado != st.session_state.get("ultimo_clique"):
            st.session_state["ultimo_clique"] = clicado
            definir("doenca", clicado)
            recarregar()

    seletor(st, "Câncer em foco", "doenca", codigos, format_func=nome_doenca, horizontal=True)
    ficha = ficha_cancer(serie, doenca)

    pergunta(f"O que chama atenção no {cancer_de(doenca)}?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}; o Estado entra só como comparação")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Internações", formatar_numero(ficha["internacoes"]),
              help=f"{formatar_numero(ficha['pct_internacoes'], 1)}% das internações por câncer acompanhadas")
    k2.metric("Óbitos na internação", formatar_numero(ficha["obitos"]),
              help=f"Letalidade hospitalar {formatar_numero(ficha['letalidade'], 1)}% "
                   f"(Estado: {formatar_numero(ficha['letalidade_estado'], 1)}%)")
    k3.metric("Valor hospitalar registrado", reais(ficha["valor"], compacto=True),
              help=f"{reais(ficha['valor'])} no SIH/SUS; média de {reais(ficha['valor_medio'])} por internação "
                   f"(Estado: {reais(ficha['valor_medio_estado'])})")
    k4.metric("Dias de internação", formatar_numero(ficha["dias"]),
              help=f"Média de {formatar_numero(ficha['permanencia'], 1)} dias por internação "
                   f"(Estado: {formatar_numero(ficha['permanencia_estado'], 1)})")
    leitura("O que chama atenção", destaques_cancer(serie, doenca))
    st.caption(f"Para a história ano a ano e a projeção, veja a aba Evolução. Período: {ano_ini}–{ano_fim}.")


# ============================================================
# EVOLUÇÃO — como mudou e para onde vai?
# ============================================================

mun = serie_doenca(serie, doenca)

if aba == "Evolução":
    pergunta(f"Como as internações por {cancer_de(doenca)} mudaram de {ano_ini} a {ano_fim}?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}; a linha cinza é o Estado de SP, só para comparar o ritmo")
    st.markdown(f'<div class="escudo-dica">Câncer em foco: {nome}. Troque na aba Panorama.</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    ver_estado = chave_liga(c1, "Comparar com o Estado de SP", "ver_estado",
                           help="Linha cinza: o ritmo do Estado redimensionado para o tamanho da cidade.")
    ver_fora = chave_liga(c2, "Destacar anos fora do padrão", "ver_fora",
                         help="Anos que ficaram longe do esperado pela tendência dos outros anos.")
    ver_projecao = chave_liga(c3, "Projeção de tendência até " + str(ano_fim + 3), "ver_projecao",
                             help="Continuação da tendência histórica, com faixa de incerteza. "
                                  "Não é previsão clínica nem IA preditiva.")

    fig = go.Figure()
    if ver_projecao:
        proj = projetar(mun)
        # A projeção sai da RETA da tendência (desenhada fraquinha
        # sobre o histórico), não do último ponto: se o último ano
        # ficou acima da reta, sair dele desenhava uma "queda" falsa.
        reta = tendencia_no_periodo(mun)
        fig.add_trace(go.Scatter(
            x=reta["ano"], y=reta["internacoes"], mode="lines",
            line={"color": AZUL, "width": 1.5, "dash": "dot"}, opacity=0.55,
            name="Tendência (reta dos anos observados)",
            hovertemplate="%{x}: tendência ~%{y:.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=list(proj["ano"]) + list(proj["ano"])[::-1],
            y=list(proj["maximo"]) + list(proj["minimo"])[::-1],
            mode="lines", fill="toself", fillcolor=AZUL_FAIXA, line={"width": 0},
            hoverinfo="skip", name="Faixa provável da projeção (90%)",
        ))
        fig.add_trace(go.Scatter(
            x=[ano_fim] + list(proj["ano"]),
            y=[float(reta["internacoes"].iloc[-1])] + list(proj["internacoes"]),
            mode="lines+markers", line={"color": AZUL, "width": 2, "dash": "dot"},
            marker={"size": 8, "symbol": "circle-open"}, name="Projeção de tendência",
            hovertemplate="%{x}: cerca de %{y:.0f} (projeção)<extra></extra>",
        ))
    if ver_estado:
        estado = ritmo_estadual_na_escala(serie, doenca)
        if not estado.empty:
            fig.add_trace(go.Scatter(
                x=estado["ano"], y=estado["internacoes"], mode="lines",
                line={"color": CINZA, "width": 2},
                name=f"Ritmo do Estado de SP (na escala de {nome_cidade})",
                hovertemplate="%{x}: Estado no ritmo equivalente a %{y:.0f}<extra></extra>",
            ))
    # Anos com meses que o DATASUS não oferece: o ponto é a média mensal
    # x 12 (comparável), com marcador vazado e o registrado no hover.
    incompletos = anos_incompletos(serie)
    registradas = mun["internacoes_reg"] if "internacoes_reg" in mun else mun["internacoes"]
    fig.add_trace(go.Scatter(
        x=mun["ano"], y=mun["internacoes"], mode="lines+markers",
        line={"color": AZUL, "width": 2.5},
        marker={"size": 8, "color": [("#ffffff" if a in incompletos else AZUL) for a in mun["ano"]],
                "line": {"color": AZUL, "width": 2}},
        name=f"{nome_cidade}: internações por ano",
        customdata=[[f"estimado: {incompletos[a]} de 12 meses na fonte; registradas: {r:.0f}"
                     if a in incompletos else "registradas"] for a, r in zip(mun["ano"], registradas)],
        hovertemplate="%{x}: %{y:.0f} internações (%{customdata[0]})<extra></extra>",
    ))
    fora = anos_fora_do_padrao(mun)
    if ver_fora and not fora.empty:
        fig.add_trace(go.Scatter(
            x=fora["ano"], y=fora["observado"], mode="markers",
            marker={"size": 17, "color": "rgba(0,0,0,0)", "line": {"color": LARANJA, "width": 2.5}},
            name="Fora do padrão",
            customdata=fora[["esperado", "direcao"]].values,
            hovertemplate="%{x}: %{y:.0f} internações, %{customdata[1]} do esperado (~%{customdata[0]:.0f})<extra></extra>",
        ))
        for _, linha in fora.iterrows():
            fig.add_annotation(x=linha["ano"], y=linha["observado"], text=f"{linha['direcao']} do esperado",
                               showarrow=False, yshift=20 if linha["direcao"] == "acima" else -20,
                               font={"size": 11, "color": LARANJA})
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(rangemode="tozero")
    estilizar(fig, altura=430)
    st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)

    if incompletos:
        st.caption("Marcador vazado: ano com meses que o DATASUS não oferece ("
                   + ", ".join(f"{a}: {m} de 12" for a, m in sorted(incompletos.items()))
                   + "). O valor é a média dos meses disponíveis × 12, para os anos serem comparáveis.")
    leitura("O que o gráfico mostra", leitura_evolucao(serie, doenca))

    if ver_projecao:
        teste = testar_projecao(mun)
        if teste:
            melhor = teste["erro_tendencia"] <= teste["erro_media"]
            st.caption(
                f"Projeção de tendência: continua a reta de {ano_ini}–{ano_fim}, se nada mudar. "
                f"Teste de acerto: calculada só até {ano_fim - 3} e comparada com {ano_fim - 2}–{ano_fim}, errou em média "
                f"{formatar_numero(teste['erro_tendencia'], 1)} internações por ano, "
                f"{'menos' if melhor else 'mais'} do que repetir a média dos anos anteriores "
                f"({formatar_numero(teste['erro_media'], 1)}). Não é previsão clínica nem indica causa. "
                f"A pressão projetada em dias e valores está na aba Planejamento."
            )
        ponta = leitura_ponta_projecao(mun)
        if ponta:
            st.markdown(f'<div class="escudo-dica">{ponta}</div>', unsafe_allow_html=True)

    # Confiabilidade: a casa dos avisos é aqui, junto da tendência.
    avisos = confiabilidade(serie, doenca, duplicados_municipio(ORIGEM))
    st.markdown(
        '<div class="escudo-info"><b>Confiabilidade desta informação</b><ul>'
        + "".join(f"<li>{'⚠️ ' if nivel == 'atencao' else ''}{texto}</li>" for nivel, texto in avisos)
        + "</ul></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# INVESTIGAR — o que merece ser pesquisado?
# ============================================================

if aba == "Investigar":
    # ---- fluxo: mulheres de outros estados atendidas em SP (pedido do autor, 10/2026) ----
    pergunta("De onde vêm as mulheres de outros estados atendidas em São Paulo?", "estado",
             "todas as cidades de SP, 7 cânceres somados, 2013–2025 · não muda quando você troca de cidade")
    st.markdown('<div class="escudo-dica">Internações de mulheres que moram em outros estados, registradas em '
                'hospitais de SP. Conta internações (uma mulher pode ter várias) e só enxerga hospitais de SP.'
                '</div>', unsafe_allow_html=True)
    fluxo = fluxo_geral()
    if fluxo is None:
        st.info("O banco ainda não guarda onde cada mulher foi atendida. Rode a carga de novo "
                "(py etl\\carga_todas_bases.py) para ver o fluxo.")
    else:
        r_fluxo = resumo_fluxo(fluxo)
        e_fluxo = evolucao_fluxo(fluxo)
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Internações de fora de SP", formatar_numero(r_fluxo["internacoes_fora"]),
                  help=f"{formatar_numero(r_fluxo['pct_fora'], 1)}% das "
                       f"{formatar_numero(r_fluxo['internacoes_total'])} internações registradas em hospitais de SP")
        f2.metric("Parcela do total", f"{formatar_numero(r_fluxo['pct_fora'], 1)}%")
        f3.metric("Dias de leito", formatar_numero(r_fluxo["dias_fora"]),
                  help=f"{formatar_numero(r_fluxo['pct_dias_fora'], 1)}% de todos os dias de internação")
        f4.metric("Estados de origem", formatar_numero(r_fluxo["n_ufs"]))

        pergunta("Em quais estados elas moram?", "estado",
                 "todas as cidades de SP, 7 cânceres somados · cada bolha é um estado de origem")
        st.markdown('<div class="escudo-dica">Como ler: quanto maior a bolha, mais internações de mulheres '
                    'daquele estado. Os estados estão na posição aproximada (centro de cada um), sem fronteiras; '
                    'cinza é estado sem internação de fora. Mostra de onde elas vêm, não o caminho que fizeram.</div>', unsafe_allow_html=True)
        pontos, sem_posicao = pontos_mapa_fluxo(r_fluxo)
        if pontos.empty:
            st.info("Não há estados de origem para mostrar no mapa.")
        else:
            maior = float(pontos["internacoes"].max())
            sem_fluxo = [u for u in CENTROS_UF if u not in set(pontos["uf"]) and u != "SP"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(  # estados sem internação de fora: só a sigla, para desenhar o mapa
                x=[CENTROS_UF[u][1] for u in sem_fluxo], y=[CENTROS_UF[u][0] for u in sem_fluxo],
                mode="markers+text", text=sem_fluxo, textposition="middle center",
                textfont={"size": 9, "color": "#8a93a3"},
                marker={"size": 22, "color": "#eef0f4", "line": {"width": 1, "color": "#d5d9e0"}},
                hovertext=[f"{nome_uf(u)}: nenhuma internação de fora registrada" for u in sem_fluxo],
                hoverinfo="text", showlegend=False))
            fig.add_trace(go.Scatter(
                x=pontos["lon"], y=pontos["lat"], mode="markers+text",
                text=pontos["uf"], textposition="middle center", textfont={"size": 10, "color": "#ffffff"},
                marker={"size": 20 + 56 * (pontos["internacoes"] / maior) ** 0.5, "color": AZUL,
                        "opacity": 0.85, "line": {"width": 1, "color": "#ffffff"}},
                hovertext=[f"{e}: {formatar_numero(n)} internações ({formatar_numero(q, 1)}% das de fora)"
                           for e, n, q in zip(pontos["estado"], pontos["internacoes"], pontos["pct"])],
                hoverinfo="text", showlegend=False))
            fig.add_trace(go.Scatter(
                x=[CENTROS_UF["SP"][1]], y=[CENTROS_UF["SP"][0]], mode="markers+text", text=["SP"],
                textposition="bottom center", textfont={"size": 10, "color": "#c0392b"},
                marker={"size": 14, "color": "#c0392b", "symbol": "diamond", "line": {"width": 1, "color": "#ffffff"}},
                hovertext=["Estado de São Paulo (onde estão os hospitais)"], hoverinfo="text", showlegend=False))
            fig.update_xaxes(visible=False, range=[-76, -32])
            fig.update_yaxes(visible=False, range=[-35, 6], scaleanchor="x", scaleratio=1)
            estilizar(fig, altura=560)
            fig.update_layout(showlegend=False, margin={"l": 0, "r": 0, "t": 10, "b": 0})
            st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
            topo = pontos.iloc[0]
            frases = [f"{topo['estado']} é o estado com mais internações de mulheres de fora "
                      f"({formatar_numero(topo['internacoes'])}, {formatar_numero(topo['pct'], 1)}% das de fora); "
                      f"ao todo são {formatar_numero(len(pontos))} estados de origem.",
                      "O losango vermelho marca o Estado de São Paulo, onde ficam os hospitais."]
            if sem_posicao:
                frases.append(f"{formatar_numero(sem_posicao)} internações vêm de residência sem posição no mapa "
                              "e não aparecem nas bolhas.")
            leitura("O que o mapa mostra", frases)

        st.markdown('<div class="escudo-dica">Como ler: cada faixa liga o estado onde a mulher mora (à esquerda) '
                    'ao município do hospital de SP onde foi internada (à direita). A largura é o número de '
                    'internações.</div>', unsafe_allow_html=True)
        lig = ligacoes_fluxo(fluxo)
        origens = list(dict.fromkeys(lig["origem"]))
        destinos_s = list(dict.fromkeys(lig["destino"]))
        tot_o = lig.groupby("origem")["valor"].sum()
        tot_d = lig.groupby("destino")["valor"].sum()
        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node={"label": [f"{o} ({formatar_numero(tot_o[o])})" for o in origens]
                           + [f"{d} ({formatar_numero(tot_d[d])})" for d in destinos_s],
                  "color": [CINZA] * len(origens) + [AZUL] * len(destinos_s),
                  "pad": 22, "thickness": 18, "line": {"width": 0}},
            link={"source": [origens.index(o) for o in lig["origem"]],
                  "target": [len(origens) + destinos_s.index(d) for d in lig["destino"]],
                  "value": list(lig["valor"]),
                  "color": "rgba(42,120,214,0.22)",
                  "hovertemplate": "%{source.label} → %{target.label}<br>%{value} internações<extra></extra>"},
        ))
        estilizar(fig, altura=max(460, 120 + 44 * max(len(origens), len(destinos_s))))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
        leitura("O que o gráfico mostra", leitura_fluxo(r_fluxo, None))

        pergunta("Quais hospitais de SP mais atendem mulheres de outros estados?", "estado",
                 "os 10 hospitais com mais internações de mulheres de fora, 7 cânceres somados")
        hosp = hospitais_fluxo(fluxo, n=10)
        if not hosp.empty:
            tabela_h = pd.DataFrame({
                "Hospital": hosp["hospital"],
                "Município": hosp["municipio"],
                "Internações de fora": [formatar_numero(v) for v in hosp["internacoes"]],
                "Parcela das de fora": [f"{formatar_numero(v, 1)}%" for v in hosp["pct"]],
            })
            if tabela_h["Município"].nunique() == 1:  # coluna igual em todas as linhas não informa
                tabela_h = tabela_h.drop(columns="Município")
            st.dataframe(tabela_h, use_container_width=True, hide_index=True)
        leitura("O que a tabela mostra", leitura_hospitais(fluxo, hosp))

        pergunta("A parcela de mulheres de fora está crescendo?", "estado", "todas as cidades de SP, 7 cânceres somados")
        st.markdown('<div class="escudo-dica">Parcela = internações de mulheres de outros estados ÷ todas as '
                    'internações registradas em hospitais de SP naquele ano.</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(
            x=e_fluxo["ano"], y=e_fluxo["pct_fora"], mode="lines+markers",
            line={"color": AZUL, "width": 3}, marker={"size": 8, "color": AZUL},
            customdata=e_fluxo[["fora", "total"]].values,
            hovertemplate="%{x}: %{y:.1f}% (%{customdata[0]} de %{customdata[1]} internações)<extra></extra>",
            showlegend=False,
        ))
        fig.update_yaxes(ticksuffix="%", rangemode="tozero")
        fig.update_xaxes(dtick=1)
        estilizar(fig, altura=300)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
        leitura("O que o gráfico mostra", leitura_evolucao_fluxo(e_fluxo))

        pergunta("Em quais cânceres a parcela de fora é maior?", "estado", "uma linha por câncer, no Estado inteiro")
        pc = por_cancer_fluxo(fluxo)
        st.dataframe(pc.assign(
            pct_fora=[f"{formatar_numero(v, 1)}%" for v in pc["pct_fora"]],
            internacoes_fora=[formatar_numero(v) for v in pc["internacoes_fora"]],
            internacoes_total=[formatar_numero(v) for v in pc["internacoes_total"]],
        ).drop(columns="tipo_cancer").rename(columns={
            "doenca": "Câncer", "internacoes_fora": "Internações de fora", "internacoes_total": "Total de internações",
            "pct_fora": "Parcela de fora", "estado_principal": "Estado que mais envia",
            "destino_principal": "Município que mais atende"}), use_container_width=True, hide_index=True)

        pergunta(f"Quem é atendida nos hospitais de {nome_cidade}, e para onde vão as moradoras?", "cidade",
                 f"só hospitais de {html.escape(nome_cidade)} e só moradoras de {html.escape(nome_cidade)}, "
                 "7 cânceres somados")
        info_cidade = fluxo_cidade(ORIGEM, cidade["codigo_ibge"])
        if info_cidade is None:
            st.info("Sem o município do hospital no banco não dá para ver o fluxo da cidade.")
        else:
            g1, g2, g3 = st.columns(3)
            g1.metric(f"Internações em hospitais de {nome_cidade}", formatar_numero(info_cidade["atendimentos"]))
            g2.metric("De outros estados", formatar_numero(info_cidade["outros_estados"]))
            g3.metric("Moradoras atendidas fora da cidade", formatar_numero(info_cidade["moradoras_fora"]),
                      help=f"de {formatar_numero(info_cidade['moradoras'])} internações de moradoras de {nome_cidade}")
            leitura("O que mostra", leitura_cidade(info_cidade, nome_cidade))
        st.markdown("---")

    pergunta(f"Em que anos algum câncer saiu do padrão em {nome_cidade}?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}")
    st.markdown('<div class="escudo-dica">Todos os cânceres de uma vez. "Esperado" = tendência calculada com os '
                'outros anos. Detectar não explica a causa.</div>', unsafe_allow_html=True)
    fora_todos = anos_fora_todos(serie)
    f1, f2 = st.columns([1, 1])
    direcao = f1.radio("Direção", ["Todos", "Acima do esperado", "Abaixo do esperado"], horizontal=True, key="direcao")
    incluir_pequenos = f2.toggle("Incluir números pequenos", value=True,
                                 help="Cânceres com média abaixo de 10 internações por ano, onde o acaso pesa mais.")
    tabela = fora_todos
    if direcao != "Todos":
        tabela = tabela[tabela["direcao"] == ("acima" if direcao.startswith("Acima") else "abaixo")]
    if not incluir_pequenos:
        tabela = tabela[~tabela["numeros_pequenos"]]
    if tabela.empty:
        st.info("Nenhum ano fora do padrão com esses filtros.")
    else:
        st.dataframe(
            tabela.assign(
                observado=tabela["observado"].round(0).astype(int),
                esperado=[formatar_numero(v, 1) for v in tabela["esperado"]],
                diferenca_pct=[f"{'+' if v > 0 else ''}{formatar_numero(v)}%" for v in tabela["diferenca_pct"]],
                numeros_pequenos=tabela["numeros_pequenos"].map({True: "sim", False: "não"}),
            ).rename(columns={"doenca": "Câncer", "ano": "Ano", "observado": "Internações",
                              "esperado": "Esperado", "direcao": "Direção",
                              "numeros_pequenos": "Números pequenos", "diferenca_pct": "Diferença"}),
            use_container_width=True, hide_index=True,
        )
        contagem = tabela["ano"].value_counts()
        if contagem.iloc[0] >= 2:
            st.caption(f"{contagem.index[0]} aparece para {contagem.iloc[0]} cânceres ao mesmo tempo — quando "
                       f"vários mudam juntos, vale checar o registro antes de concluir.")

    pergunta("Qual câncer cresce mais rápido, e quando foi o ponto mais alto?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}, {ano_ini}–{ano_fim}")
    st.markdown('<div class="escudo-dica">Do que mais cresce para o que menos cresce. Uma linha por câncer.</div>',
                unsafe_allow_html=True)
    aparece = quando_aparece(serie)
    st.dataframe(tabela_aparece_para_tela(aparece, ano_ini), use_container_width=True, hide_index=True)
    leitura("O que a tabela mostra", leitura_aparece(aparece, anos_incompletos(serie), ano_fim, ano_ini))

    pergunta(f"A idade das mulheres internadas por {cancer_de(doenca)} mudou?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}")
    faixas = faixas_municipio(ORIGEM)
    tabela_faixas, periodos = comparar_faixas(faixas, doenca)
    if periodos is None:
        st.info("Não há idade registrada para esta seleção.")
    else:
        fig = go.Figure()
        for periodo, cor in zip(periodos, [CINZA, AZUL]):
            parte = tabela_faixas[tabela_faixas["periodo"] == periodo]
            fig.add_trace(go.Bar(
                x=parte["faixa"], y=parte["pct"], name=periodo, marker={"color": cor, "line": {"width": 0}},
                text=[f"{formatar_numero(v)}%" for v in parte["pct"]], textposition="outside", cliponaxis=False,
                customdata=parte[["internacoes"]].values,
                hovertemplate="%{x}: %{y:.1f}% (%{customdata[0]} internações)<extra>" + periodo + "</extra>",
            ))
        fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
        fig.update_yaxes(ticksuffix="%", rangemode="tozero")
        estilizar(fig, altura=340)
        st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
        leitura("O que o gráfico mostra", leitura_faixas(tabela_faixas, periodos)
                + ["A faixa de 50 a 69 anos é a do rastreamento de câncer de mama recomendado pelo INCA."
                   if doenca == "MAMA" else "Percentual de cada faixa dentro de cada período."])

    pergunta(f"Como {nome_cidade} se compara com outra cidade?", "cidade",
             f"moradoras de {html.escape(nome_cidade)} e da cidade escolhida abaixo")
    st.markdown('<div class="escudo-dica">A comparação usa proporções e médias, que não dependem do tamanho da '
                'cidade. Internações por 100 mil mulheres ainda dependem da população do IBGE, que não está no '
                'banco.</div>', unsafe_allow_html=True)
    opcoes = [m for m in lista_municipios if m["origem"] != ORIGEM]
    if not opcoes:
        st.info("Só há uma cidade com dados no banco.")
    else:
        parecidas = cidades_parecidas(porte_cidades(), ORIGEM, 1)
        indice_outra = next((i for i, m in enumerate(opcoes) if parecidas and m["origem"] == parecidas[0]), 0)
        outro_nome = st.selectbox(f"Comparar {nome_cidade} com", [m["nome"] for m in opcoes], index=indice_outra,
                                  key=f"comparar_com_{ORIGEM}",
                                  help="A sugestão é a cidade com número de internações mais parecido.")
        outra = next(m for m in opcoes if m["nome"] == outro_nome)
        perfil_a, perfil_b = perfil_cidade(serie), perfil_cidade(serie_municipio(outra["origem"]))
        if perfil_a is None or perfil_b is None:
            st.info(f"{outro_nome} não tem internações registradas para comparar.")
        else:
            st.dataframe(tabela_comparacao(perfil_a, perfil_b, nome_cidade, outro_nome),
                         use_container_width=True, hide_index=True)
            mix = mix_comparacao(perfil_a, perfil_b, nome_cidade, outro_nome)
            ordem = list(mix[mix["cidade"] == nome_cidade].sort_values("pct")["doenca"])
            fig = go.Figure()
            for cidade_barra, cor in ((outro_nome, CINZA), (nome_cidade, AZUL)):
                parte = mix[mix["cidade"] == cidade_barra].set_index("doenca").reindex(ordem)
                fig.add_trace(go.Bar(
                    y=ordem, x=parte["pct"], name=cidade_barra, orientation="h", marker={"color": cor, "line": {"width": 0}},
                    text=[f"{formatar_numero(v, 1)}%" for v in parte["pct"]], textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}: %{x:.1f}% das internações<extra>" + cidade_barra + "</extra>"))
            fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
            fig.update_xaxes(ticksuffix="%", rangemode="tozero")
            estilizar(fig, altura=120 + 56 * len(ordem))
            st.markdown('<div class="escudo-dica">Parcela de cada câncer nas internações da cidade (cada cidade soma '
                        '100%).</div>', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
            leitura("O que a comparação mostra", leitura_comparacao(perfil_a, perfil_b, nome_cidade, outro_nome))

    st.download_button(
        "Baixar a série anual desta cidade (CSV)",
        serie.assign(doenca=serie["tipo_cancer"].map(nome_doenca))
             .to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"escudo_{ORIGEM.lower()}_serie_anual.csv", mime="text/csv",
    )


# ============================================================
# PLANEJAMENTO — que evidências entram na discussão?
# ============================================================

if aba == "Planejamento":
    lista = radar(ORIGEM)
    ano_h = lista[0]["ano"] if lista else ano_fim + 3
    pergunta(f"Se nada mudar, onde {nome_cidade} pode ter problema até {ano_h}?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}; o Estado entra só como comparação")
    st.markdown('<div class="escudo-dica">O radar junta, para cada câncer, o que já aconteceu e para onde a tendência '
                'aponta. Alerta = cresce, a tendência passou no teste de acerto e há um agravante (cresce mais que o '
                'Estado, letalidade acima do Estado, mais dias de leito pela frente ou o maior volume). Não define '
                'quanto investir: aponta onde preparar a rede; a decisão é da gestão.</div>', unsafe_allow_html=True)

    ROTULO_NIVEL = {"alerta": "Alerta", "observar": "Observar", "estavel": "Estável"}
    DESCRICAO_NIVEL = {"alerta": "podem virar problema se nada mudar", "observar": "sinais a acompanhar",
                       "estavel": "sem sinal pelos critérios do Escudo"}
    faixa = "".join(
        f'<div><b>{sum(r["nivel"] == n for r in lista)}</b> <span class="radar-selo {n}">{ROTULO_NIVEL[n]}</span><br>'
        f'<span>{DESCRICAO_NIVEL[n]}: {", ".join(r["doenca"] for r in lista if r["nivel"] == n) or "nenhum"}</span></div>'
        for n in ("alerta", "observar", "estavel"))
    st.markdown(f'<div class="radar-faixa">{faixa}</div>', unsafe_allow_html=True)
    fora_est, total_est = ano_atipico_no_estado(serie, ano_fim)
    if total_est and fora_est >= total_est / 2:
        st.markdown(f'<div class="escudo-alerta">{ano_fim} está em investigação (vários cânceres saltaram juntos no '
                    f'Estado inteiro). Se for mudança de registro, parte dos sinais de crescimento pode diminuir.</div>',
                    unsafe_allow_html=True)

    for r in lista:
        p = r["pressao"]
        sinais = "".join(f"<li>{t}</li>" for t in r["sinais"]) or "<li>Nenhum sinal pelos critérios do Escudo.</li>"
        dias = p["dias_permanencia"]
        dias_txt = (f"poucos (faixa de {formatar_numero(dias['minimo'])} a {formatar_numero(dias['maximo'])})"
                    if dias["previsto"] < 1 else f"cerca de {formatar_numero(dias['previsto'])}")
        futuro = (
            f"<li>Internações: cerca de {formatar_numero(p['internacoes']['previsto'])} por ano "
            f"(entre {formatar_numero(p['internacoes']['minimo'])} e {formatar_numero(p['internacoes']['maximo'])}); "
            f"hoje a tendência está em ~{formatar_numero(r['internacoes_hoje'])}</li>"
            f"<li>Dias de leito: {dias_txt} por ano; hoje ~{formatar_numero(r['dias_hoje'])}</li>"
            f"<li>Valor hospitalar registrado: cerca de {reais(p['valor_total']['previsto'])} por ano</li>"
        )
        cuidados = "".join(f'<div class="acao">Cuidado: {c}.</div>' for c in r["cuidados"])
        st.markdown(
            f'<div class="escudo-cartao radar-cartao radar-{r["nivel"]}"><h4>{r["doenca"]}'
            f'<span class="radar-selo {r["nivel"]}">{ROTULO_NIVEL[r["nivel"]]}</span></h4>'
            f'<b>Por quê</b><ul>{sinais}</ul>'
            f'<b>Se nada mudar, em {r["ano"]}</b><ul>{futuro}</ul>'
            + (f'<div class="acao">{r["ponta"]}</div>' if r["ponta"] else "")
            + cuidados
            + (f'<div class="acao">Onde agir antes (linha de ação do INCA): {r["linha_de_acao"]}.</div>'
               if r["linha_de_acao"] and r["nivel"] != "estavel" else "")
            + '</div>',
            unsafe_allow_html=True,
        )

    pontos_q = [r for r in lista if r["letalidade_relativa"] is not None]
    if pontos_q:
        pergunta("Crescimento x gravidade: onde fica cada câncer?", "cidade", f"moradoras de {html.escape(nome_cidade)}")
        COR_NIVEL = {"alerta": LARANJA, "observar": "#7565a8", "estavel": CINZA}
        fig = go.Figure(go.Scatter(
            x=[r["crescimento"] for r in pontos_q], y=[r["letalidade_relativa"] for r in pontos_q],
            mode="markers+text", text=[r["doenca"] for r in pontos_q], textposition="top center",
            marker={"size": [max(12, min(46, r["internacoes"] ** 0.5 * 1.6)) for r in pontos_q],
                    "color": [COR_NIVEL[r["nivel"]] for r in pontos_q], "opacity": 0.8,
                    "line": {"color": "#ffffff", "width": 2}},
            customdata=[[r["internacoes"], ROTULO_NIVEL[r["nivel"]]] for r in pontos_q],
            hovertemplate="<b>%{text}</b> (%{customdata[1]})<br>cresce %{x:.1f}% ao ano<br>letalidade %{y:.2f}× "
                          "a do Estado<br>%{customdata[0]:,.0f} internações<extra></extra>",
            showlegend=False,
        ))
        fig.add_hline(y=1, line={"color": CINZA, "width": 1})
        fig.add_vline(x=0, line={"color": CINZA, "width": 1})
        fig.add_annotation(xref="paper", x=0.01, y=1, xanchor="left", yanchor="bottom", showarrow=False,
                           text="letalidade igual à do Estado", font={"size": 11, "color": TINTA_SUAVE})
        ys = [r["letalidade_relativa"] for r in pontos_q]
        xs = [r["crescimento"] for r in pontos_q]
        fig.update_yaxes(range=[min(min(ys), 1) - 0.1, max(max(ys), 1) + 0.12],
                         title="Letalidade hospitalar ÷ a do Estado", zeroline=False)
        fig.update_xaxes(range=[min(min(xs), 0) - 1, max(xs) + 1.5],
                         title="Crescimento das internações (% ao ano)", ticksuffix="%", zeroline=False)
        estilizar(fig, altura=420)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True, theme=None, config=CONFIG_GRAFICO)
        canto = [r["doenca"] for r in pontos_q if r["crescimento"] >= 3 and r["letalidade_relativa"] > 1]
        fora_q = [r["doenca"] for r in lista if r["letalidade_relativa"] is None]
        leitura("Como ler", [
            "Cor = nível do radar (laranja: alerta; roxo: observar; cinza: estável). Tamanho = internações.",
            (f"No canto de cima à direita (cresce e morre mais no hospital que no Estado): {', '.join(canto)}."
             if canto else "Nenhum câncer cresce e tem letalidade acima do Estado ao mesmo tempo."),
        ] + ([f"Fora do gráfico por ter menos de 5 óbitos: {', '.join(fora_q)}."] if fora_q else []))

    st.caption(f"Projeção de tendência (não é previsão clínica). Valores em R$ nominais registrados no SIH/SUS, sem "
               f"correção de inflação, só como ordem de grandeza da pressão -- não é orçamento.")


# ============================================================
# MÉTODO
# ============================================================

if aba == "Método":
    pergunta("Como ler estes dados")
    st.markdown(f"""
- **Fonte:** internações do SUS (SIH/SUS, DATASUS) de mulheres residentes em {nome_cidade}, {ano_ini}–{ano_fim}, para 7 tipos de câncer.
- **Internação não é caso novo.** Uma mesma mulher pode ser internada mais de uma vez; quem se trata só em
  ambulatório ou por plano privado não aparece aqui.
- **Valor hospitalar registrado** é o valor das AIHs no SIH/SUS. Não é o orçamento do município nem o custo
  total do tratamento (quimioterapia e radioterapia ambulatoriais ficam fora). Valores nominais, sem inflação.
- **O ano é o de processamento da internação** (competência da AIH), que pode não coincidir com o ano em que
  ela aconteceu.
- **Meses que a fonte não oferece:** o DATASUS não disponibiliza todos os meses de 2013 a 2024 (2018 tem só 6).
  Conferimos duas vezes, nos arquivos e na própria fonte: esses dados não existem para recuperar. Mês ausente não
  é zero e ano incompleto não é ano normal: para comparar anos, o Escudo usa a média dos meses disponíveis × 12
  (marcador vazado no gráfico); os totais do período são o que foi registrado.
- **Linha cinza (Estado de SP):** a série do Estado redimensionada para o tamanho de {nome_cidade}. Compara o
  *ritmo*, não o volume. O Estado conta o **atendimento nos hospitais de SP**, e por isso inclui mulheres que
  moram em outros estados; a cidade conta as **moradoras** de {nome_cidade}.
- **Fora do padrão:** o ano ficou longe do esperado pela tendência dos *outros* anos, além da oscilação normal
  e com diferença de pelo menos 3 internações. Aponta onde olhar; não explica a causa.
- **Projeção de tendência:** a reta histórica prolongada, com a faixa onde o valor deve cair em 9 de cada 10
  cenários se o passado se repetir, e um teste de acerto em anos já conhecidos. Não é "IA preditiva" nem
  previsão clínica. Óbitos não são projetados: são poucos por ano.
- **Uma fonte por cidade:** se o banco tiver a mesma internação vinda de duas fontes, o Escudo usa só uma.

**O que estes dados não permitem responder:** causas, incidência (casos novos), orçamento ideal, efeito de uma
política, e — até a população do IBGE entrar no banco — comparação justa entre cidades de tamanhos diferentes.
""")


def desenhar_passeio(indice):
    """PASSEIO PELO ESCUDO (algoritimos/passeio.py): interação a mais,
    com cor e forma próprias; só cliques. A key muda a cada parada."""
    try:
        cartao = st.container(key=f"passeiocard_{'convite' if indice is None else indice}")
    except TypeError:  # Streamlit antigo: container com borda
        cartao = st.container(border=True)
    with cartao:
        if indice is None:
            st.markdown('<div class="passeio-topo">🧭 Passeio pelo Escudo</div>'
                        f'<div class="passeio-titulo">O essencial em {len(PARADAS)} paradas</div>'
                        'A Lia conduz, na ordem, e o painel vai mostrando cada gráfico. Só clicar.',
                        unsafe_allow_html=True)
            st.button("Começar o passeio", key="pbtn_seguir_comecar", on_click=passeio_ir, args=(0,),
                      use_container_width=True)
        else:
            p = passeio_parada(ctx_lia, indice)
            pontos = "●" * p["numero"] + "○" * (p["total"] - p["numero"])
            st.markdown(f'<div class="passeio-topo">🧭 Passeio · parada {p["numero"]} de {p["total"]}</div>'
                        f'<div class="passeio-pontos">{pontos}</div>'
                        f'<div class="passeio-titulo">{p["titulo"]}</div>', unsafe_allow_html=True)
            st.markdown(p["fala"])
            if p["destino"].get("aba"):
                st.caption(f"O painel está na aba {p['destino']['aba']}"
                           + (f" · {nome_doenca(p['destino']['cancer'])}" if p["destino"].get("cancer") else "")
                           + ".")
            c_ant, c_seg = st.columns(2)
            if indice > 0:
                c_ant.button("← anterior", key="pbtn_anterior", on_click=passeio_ir, args=(indice - 1,),
                             use_container_width=True)
            ultima = indice == len(PARADAS) - 1
            c_seg.button("terminar ✓" if ultima else "próxima parada →", key="pbtn_seguir",
                         on_click=passeio_ir, args=(None if ultima else indice + 1,), use_container_width=True)
            if not ultima:
                st.button("sair do passeio", key="pbtn_sair", on_click=passeio_ir, args=(None,))


# ============================================================
# LIA NA LATERAL (atravessa todas as abas)
# ============================================================

with st.sidebar:
    atual = lia_estado["atual"]
    c_rosto, c_nome = st.columns([1, 2.6])
    with c_rosto:
        st.markdown(rosto(atual.expressao, 76), unsafe_allow_html=True)
    with c_nome:
        st.markdown('<div class="lia-nome">Lia</div><div class="lia-cargo">Pesquisadora do Escudo Feminino'
                    f'<br>{nome_cidade}</div>', unsafe_allow_html=True)

    # Passeio ativo: o cartão dele fica aqui, logo abaixo do rosto (a
    # Lia conduz); o convite, quando inativo, fica no fim da lateral.
    lugar_do_passeio = st.container()

    # Tudo o que é dela fica DENTRO do balão, preso ao rosto: fala,
    # números, próximos passos. Antes os botões soltos na lateral
    # pareciam longe dela.
    boas_vindas_aberta = not st.session_state.get("lia_fechada")
    with balao("lateral"):
        if boas_vindas_aberta:
            # a saudação já está no centro da tela: aqui não se repete
            st.markdown("Estou ali no centro da tela. Escolha um caminho por lá.")
        else:
            st.markdown(atual.fala)
            if atual.destino and atual.destino.get("aba") and lia_estado["pilha"]:
                st.caption(f"O painel foi para a aba {atual.destino['aba']}"
                           + (f" · {nome_doenca(atual.destino['cancer'])}" if atual.destino.get("cancer") else "")
                           + ".")
            if atual.numeros:
                with st.expander("Os números por trás"):
                    st.markdown("\n".join(f"- {n}" for n in atual.numeros))
            proximos = [(r, a) for r, a in atual.botoes if a is not INICIO and a.get("tipo") != "inicio"]
            for i, (rotulo, acao) in enumerate(proximos):
                st.button(rotulo, key=f"lia_{i}_{rotulo}", on_click=lia_clicar, args=(acao,),
                          use_container_width=True)
            c_voltar, c_inicio = st.columns(2)
            if lia_estado["pilha"]:
                c_voltar.button("← Voltar", key="lia_discreto_voltar", on_click=lia_voltar)
            c_inicio.button("Começar de novo", key="lia_discreto_inicio", on_click=lia_clicar, args=(INICIO,))

    indice_passeio = st.session_state.get("passeio")
    if indice_passeio is None:
        desenhar_passeio(None)  # convite, no fim da lateral
    else:
        with lugar_do_passeio:  # passeio ativo: logo abaixo do rosto
            desenhar_passeio(indice_passeio)

st.caption("Escudo Feminino · dados públicos do SIH/SUS · internações não equivalem a casos novos.")
