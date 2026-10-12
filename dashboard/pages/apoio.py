import html
import os
import sys

import pandas as pd
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "algoritimos"))
sys.path.insert(0, os.path.join(AQUI, ".."))

import apoio  # noqa: E402
from estilo import CSS  # noqa: E402
from lia import INICIO  # noqa: E402
from lia_rosto import img as rosto_lia  # noqa: E402

# ============================================================
# APOIO À MULHER — "Encontre um caminho" (combinado com o autor, 09/2026)
#
# Outras lâminas, SEPARADAS do painel de estudo da doença: aqui a
# pergunta é "onde a mulher encontra ajuda?". O painel principal
# (dashboard/app.py) não muda; só ganhou, no topo, o botão vermelho
# "Apoio à mulher" que traz para cá. Mesmo layout (estilo.py) e a MESMA Lia (rosto, balão,
# botões), com a árvore de algoritimos/apoio.py.
# Lâminas: Encontre um caminho (as 8 portas da Lia, com "Preciso de
# ajuda" e o fluxo da rede oncológica), Hospitais no Estado e
# Carretas (recursos), Rio Claro (a cidade do trabalho), Barretos
# (Hospital de Amor) e Sobre estas informações. Cada item tem uma
# casa só; nos outros lugares aparece em cartão curto.
# O estado desta página usa chaves "ap_" (o session_state é
# compartilhado com o painel) e a mesma defesa contra a armadilha do
# Streamlit: chave do widget atrelada ao valor (ver app.py).
# ============================================================

st.set_page_config(page_title="Escudo Feminino · Apoio à mulher", page_icon="E", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<style>
div[data-testid="stRadio"]:has(input[value="Encontre um caminho"]) > div { gap: 4px; border-bottom: 1px solid #e6e3ef; }
.apoio-selo { display: inline-block; font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
              border-radius: 999px; padding: 2px 10px; margin-left: 8px; vertical-align: middle;
              background: #ece7f7; color: #4d3f7a; }
.apoio-selo.confirmar { background: #fff1e6; color: #a2400f; }
.apoio-cartao { border-left: 6px solid #cdbfeb; }
.apoio-cartao.confirmar { border-left-color: #f0b58d; }
.apoio-cartao.destaque { box-shadow: 0 0 0 2px #7565a8; }
.apoio-cartao.curto { border-left-style: dashed; }
/* "Onde a carreta está agora?" (lâmina Carretas) */
.carreta-grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; margin: 8px 0; }
.carreta { background: #fff; border: 1px solid #ebe8f2; border-radius: 14px; padding: 10px 14px; }
.carreta b { font-family: 'Manrope', sans-serif; color: #292541; }
.carreta .quando { color: #4d4863; font-size: .92rem; margin-top: 2px; }
.carreta .local { color: #706b82; font-size: .85rem; margin-top: 4px; }
.carreta-selo { display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
                border-radius: 999px; padding: 2px 9px; margin-bottom: 4px; }
.carreta-selo.agora { background: #dcf3e8; color: #11734f; }
.carreta-selo.em_breve { background: #e3eefc; color: #1f5fae; }
.carreta-selo.sem_data { background: #efeef3; color: #625d72; }
.apoio-resumo { color: #4d4863; margin: 2px 0 6px; }
.apoio-cartao ul { padding-left: 18px; margin: 4px 0; }
.apoio-fonte { color: #8a8599; font-size: .85rem; margin-top: 8px; }
.apoio-fonte { margin-top: 4px; }
/* "saber onde clicar": o link oficial é um botão azul grande */
a.apoio-botao { display: inline-block; margin-top: 10px; padding: 9px 18px; border-radius: 999px;
                background: #2a78d6; color: #ffffff !important; font-weight: 700; text-decoration: none; }
a.apoio-botao:hover { background: #1f5fae; }
.apoio-onde-clicar { background: #eef4fd; border: 1px solid #c9dcf6; border-radius: 12px; padding: 8px 14px;
                     color: #1f4f8f; font-size: .92rem; margin: 8px 0 4px; }
/* caminhos e temas com cara de botão (em vez de bolinhas soltas): o
   seletor fica num container "ap_pilulas_*"; vale para o Streamlit
   novo (stRadioOption) e o antigo (baseweb) */
[class*="st-key-ap_pilulas"] label[data-testid="stRadioOption"],
[class*="st-key-ap_pilulas"] label[data-baseweb="radio"] {
    border: 1px solid #cdbfeb; border-radius: 999px; padding: 7px 16px 7px 12px; background: #ffffff;
    margin: 0 6px 6px 0; cursor: pointer; }
[class*="st-key-ap_pilulas"] label[data-testid="stRadioOption"]:not([data-selected="true"]):hover,
[class*="st-key-ap_pilulas"] label[data-baseweb="radio"]:not(:has(input:checked)):hover {
    background: #f4f0fb; border-color: #9b8fc4; }
[class*="st-key-ap_pilulas"] label[data-selected="true"],
[class*="st-key-ap_pilulas"] label[data-baseweb="radio"]:has(input:checked) {
    background: #4a3d78; border-color: #4a3d78; }
[class*="st-key-ap_pilulas"] label[data-selected="true"] p,
[class*="st-key-ap_pilulas"] label[data-baseweb="radio"]:has(input:checked) div { color: #ffffff; font-weight: 600; }
.apoio-fluxo { background: #fff; border: 1px solid #e3dcf2; border-radius: 14px; padding: 10px 12px; min-height: 150px; }
.apoio-fluxo .n { color: #9b8fc4; font-weight: 700; font-size: .8rem; }
.apoio-fluxo b { font-family: 'Manrope', sans-serif; color: #292541; display: block; }
.apoio-fluxo span { color: #625d72; font-size: .85rem; }
.apoio-etapa { background: #fff; border: 1px solid #e3dcf2; border-left: 6px solid #4a3d78; border-radius: 14px;
               padding: 12px 16px; margin: 8px 0; color: #3d3852; font-size: 1.02rem; }
.apoio-jornada span { border-radius: 999px; padding: 4px 12px; background: #fff; border: 1px solid #e3dcf2;
                      color: #4a3d78; font-weight: 600; font-size: .9rem; }
.apoio-jornada span.ativo { background: #4a3d78; border-color: #4a3d78; color: #fff; }
.apoio-jornada i { color: #9b8fc4; font-style: normal; }
.apoio-grupo { font-family: 'Manrope', sans-serif; font-weight: 700; color: #4a3d78; font-size: 1rem; margin: 18px 0 0; }
</style>
""", unsafe_allow_html=True)

ABAS = list(apoio.LAMINAS.values())
ROTULO = apoio.NOME_CAMINHO
TODOS = {"barretos": "Todos os temas", "hospitais": "Todas as regiões", "carretas": "Todas as carretas"}
PADROES = {"ap_aba": ABAS[0], "ap_caminho": "mama", "ap_item": None, "ap_etapa": apoio.ETAPAS[0][0],
           **{f"ap_grupo_{lam}": TODOS[lam] for lam in apoio.GRUPOS}}
for chave, valor in PADROES.items():
    st.session_state.setdefault(chave, valor)
st.session_state.setdefault("ap_lia", {"atual": apoio.responder(INICIO), "pilha": [], "falas": 0})
lia_estado = st.session_state["ap_lia"]


def definir(chave, valor):
    st.session_state[chave] = valor


def seletor(onde, rotulo, chave, opcoes, **kwargs):
    """st.radio preso à chave persistente (mesma defesa de app.py)."""
    k = f"w_{chave}_{st.session_state[chave]}"

    def sincronizar():
        st.session_state[chave] = st.session_state[k]
        st.session_state["ap_item"] = None
    return onde.radio(rotulo, opcoes, index=opcoes.index(st.session_state[chave]), key=k,
                      on_change=sincronizar, **kwargs)


def aplicar_destino(destino):
    destino = destino or {}
    if destino.get("aba") in ABAS:
        definir("ap_aba", destino["aba"])
    if destino.get("caminho") in ROTULO:
        definir("ap_caminho", destino["caminho"])
    if destino.get("etapa") in apoio.NOME_ETAPA:
        definir("ap_etapa", destino["etapa"])
    definir("ap_item", destino.get("item"))
    for lam in apoio.GRUPOS:  # lâmina com temas/regiões: vai ao do item (ou a todos)
        if destino.get("aba") == apoio.LAMINAS[lam]:
            definir(f"ap_grupo_{lam}", destino.get("grupo") or TODOS[lam])


def lia_clicar(acao):
    resposta = apoio.responder(acao)
    if lia_estado["atual"] is not None:
        lia_estado["pilha"].append(lia_estado["atual"])
    lia_estado["atual"] = resposta
    lia_estado["falas"] += 1
    st.session_state["ap_boas_vindas_fechada"] = True
    aplicar_destino(resposta.destino)


def lia_voltar():
    if lia_estado["pilha"]:
        lia_estado["atual"] = lia_estado["pilha"].pop()
        lia_estado["falas"] += 1
        aplicar_destino(lia_estado["atual"].destino)


def balao(nome):
    """Balão da Lia (CSS em estilo.py): a key muda a cada fala."""
    chave = f"lia_balao_{nome}_apoio_{lia_estado['falas']}"
    try:
        return st.container(key=chave)
    except TypeError:
        return st.container(border=True)


def rosto(expressao, tamanho):
    return f'<div class="lia-rosto">{rosto_lia(expressao, tamanho)}</div>'


def botao_inicio(onde, chave):
    """Botão "Início" (pedido do autor, 09/2026): volta ao painel já na aba
    Panorama, a página inicial do Escudo. O session_state é o mesmo nas
    duas páginas, então basta marcar a aba do painel antes de trocar."""
    try:
        caixa = onde.container(key=f"botao_inicio_{chave}")
    except TypeError:  # Streamlit antigo: sem key em container
        caixa = onde.container()
    with caixa:
        if st.button("🏠 Início", key=f"inicio_{chave}", use_container_width=True,
                     help="Volta à página inicial do Escudo."):
            st.session_state["aba"] = "Panorama"
            try:
                st.switch_page("app.py")
            except Exception:  # Streamlit antigo, ou esta página aberta sozinha num teste
                st.markdown('<a href="/" target="_self">Ir para o início</a>', unsafe_allow_html=True)


def pergunta(texto):
    st.markdown(f'<div class="escudo-pergunta">{texto}</div>', unsafe_allow_html=True)


def dica(texto):
    st.markdown(f'<div class="escudo-dica">{texto}</div>', unsafe_allow_html=True)


def leitura(titulo, frases):
    st.markdown(f'<div class="escudo-leitura"><b>{titulo}</b><ul>'
                + "".join(f"<li>{f}</li>" for f in frases) + "</ul></div>", unsafe_allow_html=True)


def pilulas(nome):
    """Container cujo radio aparece como botões (ver CSS "ap_pilulas")."""
    try:
        return st.container(key=f"ap_pilulas_{nome}")
    except TypeError:  # Streamlit antigo: sem key em container
        return st.container()


def onde_clicar(texto):
    st.markdown(f'<div class="apoio-onde-clicar">👉 {texto}</div>', unsafe_allow_html=True)


def cartao(i):
    """Um item do catálogo: o que é, para quem, como, fonte oficial."""
    e = html.escape
    linhas = "".join(f"<li><b>{r}:</b> {e(i[c])}</li>" for r, c in (
        ("Para quem", "para_quem"), ("O que levar", "levar"), ("Como funciona", "como"), ("Onde e contato", "contato"))
        if i[c])
    classes = "escudo-cartao apoio-cartao" + (" confirmar" if i["confirmar"] else "") \
        + (" destaque" if st.session_state["ap_item"] == i["id"] else "")
    st.markdown(
        f'<div class="{classes}"><h4>{e(i["titulo"])}<span class="apoio-selo">{e(i["onde"])}</span>'
        + ('<span class="apoio-selo confirmar">a confirmar</span>' if i["confirmar"] else "") + "</h4>"
        + f'<div class="apoio-resumo">{e(i["resumo"][0].upper() + i["resumo"][1:])}.</div>'
        + (f"<ul>{linhas}</ul>" if linhas else "")
        + (f'<div class="acao">Atenção: {e(i["cuidado"])}</div>' if i["cuidado"] else "")
        + (f'<div class="acao">A confirmar: {e(i["confirmar"])}</div>' if i["confirmar"] else "")
        + f'<a class="apoio-botao" href="{e(i["link"])}" target="_blank" rel="noopener">Abrir a página oficial ↗</a>'
        f'<div class="apoio-fonte">Fonte: {e(i["fonte"])} · conferido em {apoio.CONFERIDO}</div></div>',
        unsafe_allow_html=True,
    )


def cartao_curto(i):
    """Item que mora em outra lâmina: título, resumo e o botão azul (o
    texto completo fica na casa dele, sem repetir)."""
    e = html.escape
    st.markdown(
        f'<div class="escudo-cartao apoio-cartao curto"><h4>{e(i["titulo"])}<span class="apoio-selo">{e(i["onde"])}'
        f'</span></h4><div class="apoio-resumo">{e(i["resumo"][0].upper() + i["resumo"][1:])}.</div>'
        f'<a class="apoio-botao" href="{e(i["link"])}" target="_blank" rel="noopener">Abrir a página oficial ↗</a>'
        f'<div class="apoio-fonte">Detalhes completos na {apoio.onde_mora(i)}.</div></div>',
        unsafe_allow_html=True,
    )


def onde_esta_a_carreta():
    """Quadro do itinerário das Carretas da Mamografia no dia de hoje."""
    e = html.escape
    dia = apoio.hoje()
    pergunta("Onde a carreta da mamografia está agora?")
    dica(f"Itinerário do Estado (Programa Mulheres de Peito) conferido em {apoio.CONFERIDO}; hoje é {dia:%d/%m/%Y}. "
         "Gratuito e sem agendamento, com senhas limitadas por dia.")
    if apoio.itinerario_vencido(dia):
        st.markdown(f'<div class="escudo-alerta">{e(apoio.frase_carretas(dia))}</div>', unsafe_allow_html=True)
    else:
        lista = [c for c in apoio.carretas(dia) if c["situacao"] != "encerrada"]
        st.markdown('<div class="carreta-grade">' + "".join(
            f'<div class="carreta"><span class="carreta-selo {c["situacao"]}">{apoio.SITUACOES[c["situacao"]]}</span>'
            f'<br><b>{e(c["cidade"])}</b><div class="quando">{e(apoio.periodo(c))}</div>'
            + (f'<div class="local">{e(c["local"])}</div>' if c["local"] else "") + "</div>"
            for c in lista) + "</div>", unsafe_allow_html=True)
        passou = [c for c in apoio.carretas(dia) if c["situacao"] == "encerrada"]
        if passou:
            st.caption("Já passou: " + "; ".join(f"{c['cidade']} ({apoio.periodo(c)})" for c in passou) + ".")
    levar = apoio.POR_ID["carretas_estado"]["levar"]
    st.markdown(f'<div class="escudo-info"><b>O que levar:</b> {e(levar)} Fontes: '
                + " · ".join(f'<a href="{e(link)}" target="_blank" rel="noopener">{e(nome)}</a>'
                             for nome, link in apoio.FONTES_ITINERARIO.values())
                + ". O itinerário completo e atualizado fica no Poupatempo (cartão Carretas da Mamografia).</div>",
                unsafe_allow_html=True)


def lamina_por_grupos(lam, rotulo_seletor):
    """Lâmina organizada em temas ou regiões, escolhidos como botões."""
    with pilulas(lam):
        escolha = seletor(st, rotulo_seletor, f"ap_grupo_{lam}", [TODOS[lam]] + apoio.GRUPOS[lam], horizontal=True,
                          label_visibility="collapsed")
    for g in (apoio.GRUPOS[lam] if escolha == TODOS[lam] else [escolha]):
        casa, visitas = apoio.do_grupo(lam, g)
        if casa or visitas:
            st.markdown(f'<div class="apoio-grupo">{g}</div>', unsafe_allow_html=True)
            for i in casa:
                cartao(i)
            for i in visitas:
                cartao_curto(i)


def apontados(c):
    """O que serve a esta porta mas mora em outra porta ou lâmina."""
    for lam, fora in apoio.nas_laminas(c).items():
        nome = "outras portas" if lam == "caminho" else f"lâmina {apoio.LAMINAS[lam]}"
        st.markdown(f'<div class="apoio-grupo">Também para esta porta: {nome}</div>', unsafe_allow_html=True)
        if lam != "caminho" and len(fora) > apoio.MAX_APONTADOS:
            st.button(f"Ver os {len(fora)} itens na lâmina {apoio.LAMINAS[lam]} →", key=f"ir_{c}_{lam}",
                      type="primary", on_click=aplicar_destino, args=({"aba": apoio.LAMINAS[lam]},))
        else:
            for i in fora:
                cartao_curto(i)


def fluxo_rede():
    """A rede oncológica em passos, cada um levando à sua porta."""
    colunas = st.columns(len(apoio.FLUXO_REDE))
    for n, (col, (passo, o_que, porta_id)) in enumerate(zip(colunas, apoio.FLUXO_REDE), start=1):
        seta = " →" if n < len(apoio.FLUXO_REDE) else ""
        col.markdown(f'<div class="apoio-fluxo"><span class="n">{n}{seta}</span><b>{passo}</b>'
                     f'<span>{o_que}</span></div>', unsafe_allow_html=True)
        destino = ({"aba": apoio.LAMINAS["hospitais"]} if passo == "Especialista"
                   else {"aba": apoio.LAMINAS["caminho"], "caminho": porta_id})
        col.button("Hospitais" if passo == "Especialista" else ROTULO[porta_id], key=f"fluxo_{n}",
                   on_click=aplicar_destino, args=(destino,), use_container_width=True)


def porta(c, rotulo, dentro, abertura):
    pergunta(f"{rotulo}: {dentro}")
    dica(abertura)
    if c == "rede":
        fluxo_rede()
    if c == "mama":
        st.button("Carretas da mamografia: onde estão agora →", key="ir_carretas_mama", type="primary",
                  on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["carretas"]},))
    for i in apoio.itens(caminho=c, lamina="caminho"):
        cartao(i)
    apontados(c)
    if c in apoio.PROXIMO:
        seguinte = apoio.PROXIMO[c]
        st.button(f"Próximo passo: {ROTULO[seguinte]} →", key=f"prox_{c}", on_click=aplicar_destino,
                  args=({"aba": apoio.LAMINAS["caminho"], "caminho": seguinte},))


def porta_ajuda():
    """Preciso de ajuda: em que ponto a mulher está -> o próximo passo."""
    pergunta("Em que ponto você está?")
    dica("Escolha o que está acontecendo com você. A Lia mostra o próximo passo na rede de saúde.")
    with pilulas("etapa"):
        e = seletor(st, "Em que ponto você está?", "ap_etapa", list(apoio.NOME_ETAPA),
                    format_func=apoio.NOME_ETAPA.get, horizontal=True, label_visibility="collapsed")
    _, _, fala, portas, _ = next(x for x in apoio.ETAPAS if x[0] == e)
    st.markdown(f'<div class="apoio-etapa">{html.escape(fala)}</div>', unsafe_allow_html=True)
    if portas or e == "nao_fiz":
        colunas = st.columns(max(len(portas) + (e == "nao_fiz"), 1))
        for col, porta_id in zip(colunas, portas):
            col.button(f"Porta {ROTULO[porta_id]} →", key=f"etapa_{e}_{porta_id}", type="primary",
                       on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["caminho"], "caminho": porta_id},),
                       use_container_width=True)
        if e == "nao_fiz":
            colunas[-1].button("Carretas: onde estão agora →", key="etapa_carretas", type="primary",
                               on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["carretas"]},),
                               use_container_width=True)
    for i in apoio.itens_da_etapa(e):
        (cartao if i["caminho"] == "ajuda" else cartao_curto)(i)
    if e == "violencia":
        for i in apoio.itens(caminho="ajuda", lamina="rio_claro"):
            cartao_curto(i)


# ============================================================
# TOPO
# ============================================================

col_titulo, col_link = st.columns([2.2, 1])
with col_titulo:
    st.markdown('<div class="escudo-marca">Escudo Feminino · Apoio à mulher</div>', unsafe_allow_html=True)
    st.markdown('<div class="escudo-titulo">Encontre um caminho</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="escudo-sub">Onde a mulher de {apoio.CIDADE} encontra prevenção, diagnóstico, '
                'tratamento e proteção, com as páginas oficiais do Estado de SP, da região e da cidade. '
                'Um guia de onde procurar, não orientação médica.</div>', unsafe_allow_html=True)
with col_link:
    botao_inicio(st, "topo")
    st.caption(f"Informações conferidas em {apoio.CONFERIDO}. Confirme antes de ir.")

# Boas-vindas da Lia no centro (primeiro acesso), como no painel.
if not st.session_state.get("ap_boas_vindas_fechada"):
    inicio = apoio.responder(INICIO)
    c_rosto, c_fala = st.columns([1, 4.6])
    with c_rosto:
        st.markdown(rosto("acolhedora", 150), unsafe_allow_html=True)
    with c_fala, balao("centro"):
        st.markdown(f'<div class="lia-nome">Lia <span>· pesquisadora do Escudo Feminino</span></div>'
                    f'<div class="lia-fala-grande">{inicio.fala.replace("**", "")}</div>', unsafe_allow_html=True)
        colunas = st.columns(2)
        for n, (c, rotulo, dentro, _) in enumerate(apoio.CAMINHOS):
            colunas[n % 2].button(f"{rotulo} · {dentro}", key=f"bv_ap_{c}", on_click=lia_clicar,
                                  args=(apoio.caminho(c),), use_container_width=True)
        st.caption("Recursos:")
        r1, r2 = st.columns(2)
        r1.button("Hospitais no Estado", key="bv_ap_hospitais", on_click=lia_clicar,
                  args=(apoio.lamina("hospitais"),), use_container_width=True)
        r2.button("Carretas: onde estão agora", key="bv_ap_carretas", on_click=lia_clicar,
                  args=(apoio.lamina("carretas"),), use_container_width=True)
        st.button("Prefiro explorar sozinha", key="bv_fechar_apoio",
                  on_click=lambda: st.session_state.update(ap_boas_vindas_fechada=True))

aba = seletor(st, "Lâmina", "ap_aba", ABAS, horizontal=True, label_visibility="collapsed")


# ============================================================
# ENCONTRE UM CAMINHO — Estado de SP e itens das cidades, por caminho
# ============================================================

if aba == apoio.LAMINAS["caminho"]:
    pergunta("O que você precisa?")
    dica("Oito portas para a mulher andar pela rede de saúde. Hospitais e Carretas têm lâmina própria (abas acima). "
         "Não sabe por onde começar? Use <b>Preciso de ajuda</b>.")
    codigos = [c for c, _, _, _ in apoio.CAMINHOS]
    onde_clicar("Clique numa porta. Depois, em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    with pilulas("caminho"):
        c = seletor(st, "Caminho", "ap_caminho", codigos, format_func=ROTULO.get, horizontal=True,
                    label_visibility="collapsed")
    _, rotulo, dentro, abertura = next(x for x in apoio.CAMINHOS if x[0] == c)

    if c == "ajuda":
        porta_ajuda()
    else:
        porta(c, rotulo, dentro, abertura)
    leitura("Como usar", [
        "Cada cartão traz a página oficial e a data em que foi conferido. Borda laranja = ainda falta confirmar "
        "algum detalhe na própria página.",
        "Pelo SUS, o caminho quase sempre começa na unidade de saúde do bairro, e o encaminhamento é feito pela "
        "regulação; os hospitais de referência não são porta de entrada.",
    ])


# ============================================================
# HOSPITAIS NO ESTADO — onde se trata câncer pelo SUS, por região
# ============================================================

if aba == apoio.LAMINAS["hospitais"]:
    pergunta("Onde se trata câncer pelo SUS no Estado de São Paulo?")
    dica("Hospitais habilitados para tratar câncer (CACON e UNACON), por região. Eles não são porta de entrada: "
         "a vaga é pedida pela unidade de saúde, pela regulação do Estado (CROSS).")
    onde_clicar("Clique numa região. Em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    lamina_por_grupos("hospitais", "Região")
    leitura("Como chegar a um destes hospitais", [
        "Com suspeita ou diagnóstico de câncer, procure a unidade de saúde do bairro: o médico do SUS pede a vaga "
        "pela CROSS, que encaminha a um centro perto de onde você mora.",
        "Se o tratamento for longe (mais de 50 km) e não existir na sua região, o SUS pode pagar transporte e "
        "diárias (TFD, na porta Direitos e acesso).",
        "A lista completa e oficial é a da FOSP (primeira região desta lâmina).",
    ])


# ============================================================
# CARRETAS — onde a carreta da mamografia está agora
# ============================================================

if aba == apoio.LAMINAS["carretas"]:
    onde_esta_a_carreta()
    onde_clicar("Em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    lamina_por_grupos("carretas", "Carretas")


# ============================================================
# RIO CLARO — a cidade do trabalho
# ============================================================

if aba == apoio.LAMINAS["rio_claro"]:
    pergunta(f"O que {apoio.CIDADE} oferece às mulheres?")
    dica(f"{apoio.CIDADE} faz parte da {apoio.REGIAO}. As referências de câncer da região são Rio Claro e "
         "Piracicaba, e o HC da Unicamp também atende a região (lâmina Hospitais no Estado).")
    onde_clicar("Em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    lista = apoio.itens(lamina="rio_claro")
    for c in [c for c, _, _, _ in apoio.CAMINHOS]:
        do_caminho = [i for i in lista if i["caminho"] == c]
        if do_caminho:
            titulo_grupo = "Proteção contra a violência" if c == "ajuda" else ROTULO[c]
            st.markdown(f'<div class="apoio-grupo">{titulo_grupo}</div>', unsafe_allow_html=True)
            for i in do_caminho:
                cartao(i)
    st.button("Hospitais de referência da região →", key="ir_referencia_rc", type="primary",
              on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["hospitais"],
                                              "grupo": "Rio Claro e Piracicaba (RRAS 14)"},))
    leitura("Como usar", [
        "Para quase tudo, a porta é a Unidade de Saúde da Família ou a UBS do bairro.",
        "Vários dados de Rio Claro vêm de páginas antigas da Prefeitura e da Fundação Municipal de Saúde: estão "
        "marcados para confirmar.",
    ])


# ============================================================
# BARRETOS — Hospital de Amor
# ============================================================

if aba == apoio.LAMINAS["barretos"]:
    pergunta("Barretos: referência em oncologia e prevenção")
    dica("Barretos concentra, no Hospital de Amor, prevenção, diagnóstico, tratamento, ensino e pesquisa em câncer, "
         "com ações que chegam a outros municípios, como Rio Claro.")
    onde_clicar("Clique num tema. Em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    lamina_por_grupos("barretos", "Tema")
    st.markdown('<div class="escudo-alerta">Para quem mora em Rio Claro, o caminho do SUS passa primeiro pela '
                'referência da própria região (RRAS 14: Rio Claro e Piracicaba). Converse com a equipe que '
                'acompanha você.</div>', unsafe_allow_html=True)
    leitura("A ligação com Rio Claro", [
        "A carreta do Hospital de Amor já esteve em Rio Claro, com mamografia e Papanicolau agendados nas USF "
        "(lâmina Rio Claro).",
        "Prevenção e tratamento têm portas diferentes: a prevenção chega pelas ações com a prefeitura; o "
        "tratamento, com o câncer confirmado, segue os fluxos do SUS.",
    ])


# ============================================================
# SOBRE ESTAS INFORMAÇÕES
# ============================================================

if aba == apoio.LAMINAS["sobre"]:
    pergunta("De onde vêm estas informações?")
    st.markdown(f"""
- **O que é:** um guia de onde procurar ajuda, montado a partir de páginas oficiais: portal da Saúde do Estado
  de SP, Poupatempo, rede oncológica da FOSP, Ministério da Saúde, Fundação Municipal de Saúde de Rio Claro,
  prefeituras de Campinas, Ribeirão Preto, São José do Rio Preto e Piracicaba e Hospital de Amor.
- **Quando:** conferido em {apoio.CONFERIDO}. Regras, endereços, telefones e itinerários mudam.
- **O que ainda falta confirmar:** a pesquisa foi feita pela busca na web, com trechos das páginas oficiais.
  Quando o detalhe veio de página antiga, de reportagem ou não pôde ser aberto por inteiro, o item está marcado
  "a confirmar".
- **O que isto não é:** não é orientação médica, não garante vaga e não substitui a unidade de saúde.
  A Lia não é médica.
- **Cidades:** não há uma lâmina por cidade. Campinas, Ribeirão Preto, Rio Preto e Piracicaba entram nas portas
  quando têm algo útil; Rio Claro (a cidade do trabalho) e Barretos (Hospital de Amor) têm lâmina própria.
- **Para gestores:** o Plano Estadual de Oncologia 2025–2028 organiza a rede por região (RRAS); Rio Claro está na
  {apoio.REGIAO}.
""")
    tabela = pd.DataFrame([{
        "Item": i["titulo"], "Onde": i["onde"], "Lâmina": apoio.LAMINAS[i["lamina"]],
        "Caminho": ROTULO.get(i["caminho"], "—"), "Tema ou região": i["grupo"] or "—", "Fonte": i["fonte"], "Situação": "a confirmar" if i["confirmar"] else "conferido",
        "Página": i["link"]} for i in apoio.ITENS])
    st.dataframe(tabela, use_container_width=True, hide_index=True)


# ============================================================
# LIA NA LATERAL (a mesma Lia do painel)
# ============================================================

with st.sidebar:
    atual = lia_estado["atual"]
    c_rosto, c_nome = st.columns([1, 2.6])
    with c_rosto:
        st.markdown(rosto(atual.expressao, 76), unsafe_allow_html=True)
    with c_nome:
        st.markdown('<div class="lia-nome">Lia</div><div class="lia-cargo">Pesquisadora do Escudo Feminino'
                    f'<br>Apoio à mulher · {apoio.CIDADE}</div>', unsafe_allow_html=True)
    with balao("lateral"):
        if not st.session_state.get("ap_boas_vindas_fechada"):
            st.markdown("Estou ali no centro da tela. Escolha um caminho por lá.")
        else:
            st.markdown(atual.fala)
            if atual.numeros:
                with st.expander("Onde a Lia conferiu"):
                    st.markdown("\n".join(f"- {n}" for n in atual.numeros))
            proximos = [(r, a) for r, a in atual.botoes if a is not INICIO and a.get("tipo") != "inicio"]
            for n, (rotulo, acao) in enumerate(proximos):
                st.button(rotulo, key=f"lia_ap_{n}_{rotulo}", on_click=lia_clicar, args=(acao,),
                          use_container_width=True)
            c_voltar, c_inicio = st.columns(2)
            if lia_estado["pilha"]:
                c_voltar.button("← Voltar", key="lia_discreto_voltar_ap", on_click=lia_voltar)
            c_inicio.button("Começar de novo", key="lia_discreto_inicio_ap", on_click=lia_clicar, args=(INICIO,))
    st.divider()
    botao_inicio(st.sidebar, "lateral")

st.caption("Escudo Feminino · Apoio à mulher · guia de onde procurar; confirme sempre na unidade de saúde.")
