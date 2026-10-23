import html
import os
import sys

import pandas as pd
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "algoritimos"))
sys.path.insert(0, os.path.join(AQUI, ".."))

import apoio  # noqa: E402
import apoio_busca  # noqa: E402
from estilo import CSS  # noqa: E402
from navegacao import barra_de_navegacao  # noqa: E402
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

st.set_page_config(page_title="MISM2 · Apoio à mulher", page_icon="E", layout="wide",
                   initial_sidebar_state="collapsed")
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
.apoio-jornada-diagnostico { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px;
                              list-style: none; padding: 0; margin: 14px 0; }
.apoio-jornada-diagnostico li { position: relative; display: grid; grid-template-columns: 42px minmax(0, 1fr);
                                gap: 10px; align-items: start; background: #fff; border: 1px solid #d4cbe8;
                                border-radius: 12px; padding: 12px; min-width: 0; }
.apoio-jornada-diagnostico li.atual { background: #f1eef8; border-color: #4a3d78; }
.apoio-jornada-numero { display: grid !important; place-items: center; width: 34px; height: 34px; margin: 0 !important;
                        border-radius: 50%; background: #4a3d78; color: #fff !important; font-weight: 700; }
.apoio-jornada-conteudo b, .apoio-jornada-conteudo span { display: block; }
.apoio-jornada-conteudo span { color: #514b64; font-size: .92rem; margin-top: 4px; }
.apoio-jornada-conector { position: absolute; left: 22px; bottom: -22px; z-index: 1; color: #4a3d78;
                          font-size: 1.15rem; font-weight: 800; }
.apoio-jornada-diagnostico li:last-child .apoio-jornada-conector { display: none; }
.apoio-recuperar-caminho { margin-top: 18px; padding: 12px 14px; background: #f6f3fb;
                           border-left: 5px solid #7565a8; border-radius: 10px; color: #292541; }
.apoio-emergencia { background: #fdeceb; border: 1px solid #e8a39d; border-left: 6px solid #c62839; border-radius: 10px;
                    padding: 8px 14px; margin: 4px 0 10px; color: #6d1220; font-size: .98rem; }
.apoio-emergencia b { color: #a51f2e; }
[class*="st-key-apoio_ajuda_destaque"] button { background: linear-gradient(135deg, #5b2a55, #7a3c8f); border: 0; border-radius: 14px;
    min-height: 68px; box-shadow: 0 4px 14px rgba(91, 42, 85, .28); }
[class*="st-key-apoio_ajuda_destaque"] button p { color: #ffffff !important; font-weight: 800; font-size: 1.35rem; }
[class*="st-key-apoio_ajuda_destaque"] button:hover { background: linear-gradient(135deg, #4a2046, #6a2f7e); }
[class*="st-key-apoio_ajuda_aqui"] button { background: #efe9f5; border: 3px solid #5b2a55; border-radius: 14px; min-height: 68px; }
[class*="st-key-apoio_ajuda_aqui"] button p { color: #5b2a55 !important; font-weight: 800; font-size: 1.35rem; }
.apoio-ajuda-sub { color: #4b3a52; font-size: .98rem; margin: 6px 2px 14px; }
.apoio-ajuda-sub b { color: #5b2a55; }
.apoio-grupo { font-family: 'Manrope', sans-serif; font-weight: 700; color: #4a3d78; font-size: 1rem; margin: 18px 0 0; }
</style>
""", unsafe_allow_html=True)

# Primeiro as entradas mais úteis para quem procura atendimento; depois, os recursos de referência.
ABAS = [apoio.LAMINAS[k] for k in ("caminho", "rio_claro", "hospitais", "sobre")]   # Carretas e Barretos moram dentro de outras (20/10/2026)
ROTULO = apoio.NOME_CAMINHO
TODOS = {"barretos": "Todos os temas", "hospitais": "Todas as regiões", "carretas": "Todas as carretas"}
PADROES = {"ap_aba": ABAS[0], "ap_caminho": "mama", "ap_item": None, "ap_etapa": None, "ap_hosp_modo": "regiao",
           **{f"ap_grupo_{lam}": TODOS[lam] for lam in apoio.GRUPOS}}
for chave, valor in PADROES.items():
    st.session_state.setdefault(chave, valor)
st.session_state.setdefault("caixa_ap_gemini_ativo", False)
st.session_state.setdefault("caixa_ap_contexto", None)
st.session_state.setdefault("ap_lia", {"atual": apoio.responder(INICIO), "pilha": [], "falas": 0})
lia_estado = st.session_state["ap_lia"]
if st.session_state["ap_aba"] not in ABAS:   # sessão aberta antes de Carretas/Barretos virarem parte de outras áreas
    st.session_state["ap_aba"] = ABAS[0]


def definir(chave, valor):
    st.session_state[chave] = valor


def seletor(onde, rotulo, chave, opcoes, **kwargs):
    """st.radio preso à chave persistente (mesma defesa de app.py)."""
    k = f"w_{chave}_{st.session_state[chave]}"
    atual = st.session_state[chave]
    indice = opcoes.index(atual) if atual in opcoes else None

    def sincronizar():
        st.session_state[chave] = st.session_state[k]
        st.session_state["ap_item"] = None
        st.session_state["caixa_ap_contexto"] = None
    return onde.radio(rotulo, opcoes, index=indice, key=k,
                      on_change=sincronizar, **kwargs)


def aplicar_destino(destino):
    destino = destino or {}
    # Carretas e Barretos deixaram de ter botão próprio (autor, 20/10/2026): as carretas moram em Câncer de mama e o Hospital de
    # Amor em Hospitais no Estado. Quem ainda aponta para as áreas antigas (Lia, busca, atalhos) cai no lugar novo.
    aba_pedida = destino.get("aba")
    if aba_pedida == apoio.LAMINAS["carretas"]:
        destino = {**destino, "aba": apoio.LAMINAS["caminho"], "caminho": "mama"}
    elif aba_pedida == apoio.LAMINAS["barretos"]:
        definir("ap_hosp_modo", "barretos")
        destino = {**destino, "aba": apoio.LAMINAS["hospitais"]}
    elif aba_pedida == apoio.LAMINAS["hospitais"]:
        definir("ap_hosp_modo", "regiao")
    if destino.get("aba") in ABAS:
        definir("ap_aba", destino["aba"])
    if destino.get("caminho") in ROTULO:
        definir("ap_caminho", destino["caminho"])
    if destino.get("etapa") in apoio.NOME_ETAPA:
        definir("ap_etapa", destino["etapa"])
    definir("ap_item", destino.get("item"))
    for lam in apoio.GRUPOS:  # lâmina com temas/regiões: vai ao do item (ou a todos)
        if aba_pedida == apoio.LAMINAS[lam]:
            definir(f"ap_grupo_{lam}", destino.get("grupo") or TODOS[lam])


def normalizar_destino(destino):
    """O destino como a página o mostra de fato (Carretas e Barretos moram dentro de outras áreas)."""
    if not destino:
        return destino
    if destino.get("aba") == apoio.LAMINAS["carretas"]:
        return {**destino, "aba": apoio.LAMINAS["caminho"], "caminho": "mama"}
    if destino.get("aba") == apoio.LAMINAS["barretos"]:
        return {**destino, "aba": apoio.LAMINAS["hospitais"]}
    return destino


def lia_mostrar(resposta):
    if lia_estado["atual"] is not None:
        lia_estado["pilha"].append(lia_estado["atual"])
    lia_estado["atual"] = resposta
    lia_estado["falas"] += 1
    st.session_state["ap_boas_vindas_fechada"] = True
    st.session_state["lia_recolhida"] = False
    aplicar_destino(resposta.destino)
    resposta.destino = normalizar_destino(resposta.destino)   # a fala passa a apontar para onde a página realmente foi


def lia_clicar(acao):
    st.session_state["caixa_ap_contexto"] = None
    lia_mostrar(apoio.responder(acao))


def atualizar_contexto_conversa(resposta):
    """Guarda só um identificador de catálogo; nunca guarda relatos anteriores como contexto."""
    if getattr(resposta, "tipo", None) == "esclarecimento":
        return
    candidatos = getattr(resposta, "candidatos", []) or []
    if getattr(resposta, "tipo", None) == "itens" and len(candidatos) == 1 and candidatos[0] in apoio.POR_ID:
        st.session_state["caixa_ap_contexto"] = f"item:{candidatos[0]}"
    elif getattr(resposta, "tipo", None) == "etapa" and (resposta.destino or {}).get("etapa") in apoio.NOME_ETAPA:
        st.session_state["caixa_ap_contexto"] = f"etapa:{resposta.destino['etapa']}"
    else:
        st.session_state["caixa_ap_contexto"] = None


def contexto_da_resposta(resposta):
    destino = getattr(resposta, "destino", None) or {}
    aba = destino.get("aba")
    caminho = destino.get("caminho")
    etapa = destino.get("etapa")
    if aba == apoio.LAMINAS["caminho"]:
        chave = caminho or "caminho"
        rotulo = apoio.NOME_ETAPA.get(etapa) or ROTULO.get(chave) or aba
        return (aba, caminho, etapa), rotulo
    chave = next((k for k, nome in apoio.LAMINAS.items() if nome == aba), None)
    return (aba, chave, None), aba or "esta área"


def contexto_da_aba_atual():
    aba = st.session_state.get("ap_aba", ABAS[0])
    if aba == apoio.LAMINAS["caminho"]:
        caminho = st.session_state.get("ap_caminho")
        etapa = st.session_state.get("ap_etapa") if caminho == "ajuda" else None
        rotulo = apoio.NOME_ETAPA.get(etapa) or ROTULO.get(caminho) or aba
        return (aba, caminho, etapa), rotulo
    chave = next((k for k, nome in apoio.LAMINAS.items() if nome == aba), None)
    return (aba, chave, None), aba


def falar_sobre_aba_atual():
    aba = st.session_state.get("ap_aba", ABAS[0])
    if aba == apoio.LAMINAS["caminho"]:
        etapa = st.session_state.get("ap_etapa") if st.session_state.get("ap_caminho") == "ajuda" else None
        acao = apoio.etapa(etapa) if etapa in apoio.NOME_ETAPA else apoio.caminho(
            st.session_state.get("ap_caminho", "mama"))
    elif aba == apoio.LAMINAS["sobre"]:
        acao = apoio.SOBRE
    else:
        chave = next((k for k, nome in apoio.LAMINAS.items() if nome == aba), None)
        acao = apoio.lamina(chave) if chave else INICIO
    lia_clicar(acao)


# Pergunte à Lia no Apoio (algoritimos/apoio_busca.py): a pessoa escreve e a Lia mostra o item do guia.
# Nenhuma IA escreve sobre serviço (o texto é do catálogo conferido); o Gemini, se ligado, só ajuda a entender
# a pergunta. As perguntas desta página NÃO são gravadas. Chaves "caixa_ap_*".
LIMITE_PERGUNTAS_COM_IA = 40


def enviar_pergunta(texto=None):
    texto = (texto if texto is not None else st.session_state.get("caixa_ap_texto") or "").strip()
    if texto:
        st.session_state["caixa_ap_pendente"] = texto[:300]


def assuntos_do_guia():
    """Gera a lista de atalhos a partir dos caminhos, etapas e lâminas do catálogo."""
    caminhos = {id: rotulo for id, rotulo, _, _ in apoio.CAMINHOS}
    etapas = apoio.NOME_ETAPA
    grupos = [
        ("Prevenção e exames", [("caminho", "mama"), ("caminho", "colo"), ("caminho", "outros"), ("etapa", "nao_fiz")]),
        ("Exame alterado e diagnóstico", [("etapa", "alterado"), ("etapa", "diagnostico_cancer")]),
        ("Tratamento e direitos", [("caminho", "tratamento"), ("caminho", "direitos"),
                                   ("etapa", "encaminhada"), ("etapa", "em_tratamento")]),
        ("Onde procurar", [("lamina", "hospitais"), ("lamina", "rio_claro")]),
        ("Proteção", [("etapa", "violencia")]),
    ]
    for titulo, referencias in grupos:
        assuntos = []
        for tipo, id in referencias:
            if tipo == "caminho" and id in caminhos:
                rotulo = caminhos[id]
                acao = apoio.caminho(id)
                pergunta_modelo = f"Quero orientação sobre {rotulo.lower()}."
            elif tipo == "etapa" and id in etapas:
                rotulo = etapas[id]
                acao = apoio.etapa(id)
                pergunta_modelo = f"Minha situação é: {rotulo.lower()}."
            elif tipo == "lamina" and id in apoio.LAMINAS:
                rotulo = apoio.LAMINAS[id]
                acao = apoio.lamina(id)
                pergunta_modelo = f"Quero consultar {rotulo.lower()}."
            else:
                continue
            assuntos.append({"tipo": tipo, "id": id, "rotulo": rotulo,
                             "pergunta": pergunta_modelo, "acao": acao})
        yield titulo, assuntos


def mostrar_assunto(pergunta_modelo, acao=None):
    """Mostra resposta do guia a partir de um atalho, sem classificador de IA."""
    st.session_state["caixa_ap_contexto"] = None
    st.session_state["caixa_ap_texto"] = pergunta_modelo
    if acao is None:
        resposta = apoio_busca.responder_pergunta(pergunta_modelo, classificar=None)
    else:
        resposta = apoio.responder(acao)
        resposta.pergunta = pergunta_modelo
    lia_mostrar(resposta)


def classificador_da_sessao():
    if not st.session_state.get("caixa_ap_gemini_ativo", False):
        return None
    if st.session_state.get("caixa_ap_ia", 0) >= LIMITE_PERGUNTAS_COM_IA:
        return None
    classificar = apoio_busca.obter_classificador()
    if classificar is None:
        return None

    def classificar_contando(*args, **kwargs):
        chamadas = st.session_state.get("caixa_ap_ia", 0)
        if chamadas >= LIMITE_PERGUNTAS_COM_IA:
            return None
        st.session_state["caixa_ap_ia"] = chamadas + 1
        return classificar(*args, **kwargs)

    return classificar_contando


def lia_voltar():
    if lia_estado["pilha"]:
        lia_estado["atual"] = lia_estado["pilha"].pop()
        lia_estado["falas"] += 1
        atualizar_contexto_conversa(lia_estado["atual"])
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
        if st.button("🏠 Início", key=f"inicio_{chave}", width="stretch",
                     help="Volta à página inicial do Escudo."):
            st.session_state["aba"] = "Panorama"
            try:
                st.switch_page(os.path.abspath(os.path.join(AQUI, "..", "app.py")))
            except Exception:  # Esta página pode ser executada fora do app multipágina.
                st.warning("Esta página foi aberta como prévia isolada. Para voltar ao Panorama, abra o Apoio "
                           "à mulher pelo dashboard principal.")


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
        ("Para quem", "para_quem"), ("Como funciona", "como"), ("Onde e contato", "contato"), ("O que levar", "levar"))
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
        + f'<a class="apoio-botao" href="{e(i["link"])}" target="_blank" rel="noopener">{e(apoio.rotulo_do_link(i))} ↗</a>'
        + "".join(f'<br><a class="apoio-botao" href="{e(u)}" target="_blank" rel="noopener">{e(r)} ↗</a>'
                  for r, u in i["mais_links"])
        + f'<div class="apoio-fonte">Fonte: {e(i["fonte"])} · conferido em {i.get("conferido", apoio.CONFERIDO)}</div></div>',
        unsafe_allow_html=True,
    )


def cartao_curto(i):
    """Item que mora em outra lâmina: título, resumo e o botão azul (o
    texto completo fica na casa dele, sem repetir)."""
    e = html.escape
    st.markdown(
        f'<div class="escudo-cartao apoio-cartao curto"><h4>{e(i["titulo"])}<span class="apoio-selo">{e(i["onde"])}'
        f'</span></h4><div class="apoio-resumo">{e(i["resumo"][0].upper() + i["resumo"][1:])}.</div>'
        f'<a class="apoio-botao" href="{e(i["link"])}" target="_blank" rel="noopener">{e(apoio.rotulo_do_link(i))} ↗</a>'
        + "".join(f'<br><a class="apoio-botao" href="{e(u)}" target="_blank" rel="noopener">{e(r)} ↗</a>'
                  for r, u in i["mais_links"])
        + f'<div class="apoio-fonte">Detalhes completos na {apoio.onde_mora(i)}.</div></div>',
        unsafe_allow_html=True,
    )


def cartao_carretas(titulo, resumo):
    """O quadro com os dois canais oficiais das carretas (uma casa só para o texto dos botões)."""
    e = html.escape
    st.markdown(
        f'<div class="escudo-cartao apoio-cartao"><h4>{e(titulo)}</h4><div class="apoio-resumo">{e(resumo)}</div>'
        f'<a class="apoio-botao" href="{e(apoio.URL_CARRETAS_SP_POR_TODAS)}" target="_blank" rel="noopener">'
        'Consultar cidades e locais · SP Por Todas ↗</a><br>'
        f'<a class="apoio-botao" href="{e(apoio.URL_CARRETAS_POUPATEMPO)}" target="_blank" rel="noopener">'
        'Consultar itinerário, horários e documentos · Poupatempo ↗</a></div>',
        unsafe_allow_html=True,
    )


def onde_esta_a_carreta():
    """Direciona para a programação oficial atualizada das Carretas da Mamografia."""
    e = html.escape
    st.markdown('<div class="apoio-grupo">Carretas da mamografia: consulte o itinerário atualizado</div>', unsafe_allow_html=True)
    dica("As cidades, datas e endereços mudam. Confira a programação oficial antes de sair de casa.")
    cartao_carretas("Carretas da Mamografia · Mulheres de Peito",
                    "Veja no canal oficial quais cidades estão no roteiro e onde a carreta vai atender.")
    info = apoio.POR_ID["carretas_estado"]
    st.markdown(
        '<div class="escudo-info"><b>Para quem:</b> '
        f'{e(info["para_quem"])}<br><b>O que levar:</b> {e(info["levar"])}'
        f'<br><b>Como funciona:</b> {e(info["como"])}'
        f'<br><small>Fonte: {e(info["fonte"])} · conferido em {e(info["conferido"])}</small></div>',
        unsafe_allow_html=True,
    )


def lamina_por_grupos(lam, rotulo_seletor):
    """Lâmina organizada em temas ou regiões, escolhidos como botões."""
    if len(apoio.GRUPOS[lam]) == 1:
        escolha = apoio.GRUPOS[lam][0]
    else:
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
        if lam == "carretas":   # já aparece inteira dentro de Câncer de mama
            continue
        nome = "outros assuntos" if lam == "caminho" else f"área {apoio.LAMINAS[lam]}"
        st.markdown(f'<div class="apoio-grupo">Também serve a este assunto: {nome}</div>', unsafe_allow_html=True)
        if lam != "caminho" and len(fora) > apoio.MAX_APONTADOS:
            st.button(f"Ver os {len(fora)} itens na área {apoio.LAMINAS[lam]} →", key=f"ir_{c}_{lam}",
                      type="primary", on_click=aplicar_destino, args=({"aba": apoio.LAMINAS[lam]},))
        else:
            for i in fora:
                cartao_curto(i)


def fluxo_rede():
    """O caminho na rede em passos, cada um levando ao seu lugar (a vaga leva à situação 'Fui encaminhada')."""
    colunas = st.columns(len(apoio.FLUXO_REDE))
    for n, (col, (passo, o_que, destino_id)) in enumerate(zip(colunas, apoio.FLUXO_REDE), start=1):
        seta = " →" if n < len(apoio.FLUXO_REDE) else ""
        col.markdown(f'<div class="apoio-fluxo"><span class="n">{n}{seta}</span><b>{passo}</b>'
                     f'<span>{o_que}</span></div>', unsafe_allow_html=True)
        if destino_id == "hospitais":
            destino, rotulo = {"aba": apoio.LAMINAS["hospitais"]}, "Hospitais"
        elif destino_id.startswith("etapa:"):
            etapa = destino_id.split(":", 1)[1]
            destino = {"aba": apoio.LAMINAS["caminho"], "caminho": "ajuda", "etapa": etapa}
            rotulo = {"encaminhada": "Acompanhar a fila", "alterado": "Meu exame deu alterado"}.get(etapa, apoio.NOME_ETAPA[etapa])
        elif destino_id == "tratamento":
            destino, rotulo = None, None   # é esta mesma página
        else:
            destino, rotulo = {"aba": apoio.LAMINAS["caminho"], "caminho": destino_id}, ROTULO[destino_id]
        if destino:
            col.button(rotulo, key=f"fluxo_{n}", on_click=aplicar_destino, args=(destino,), width="stretch")


# Ordem dos cartões da página Tratamento pelo SUS: primeiro onde se tratar, depois o prazo, a fila e o apoio.
ORDEM_TRATAMENTO = ["como_chegar_cross", "inca_onde_tratar", "fosp_hospitais_sus", "rede_oncologica", "lei_60_dias",
                    "lista_regulacao", "nao_achei_nome", "rede_feminina"]


def porta(c, rotulo, dentro, abertura):
    pergunta(f"{rotulo}: {dentro}")
    dica(abertura)
    if c == "tratamento":
        fluxo_rede()
    if c == "mama":
        onde_esta_a_carreta()
    lista = apoio.itens(caminho=c, lamina="caminho")
    if c == "tratamento":
        lista = sorted(lista, key=lambda i: ORDEM_TRATAMENTO.index(i["id"]) if i["id"] in ORDEM_TRATAMENTO else 99)
    for i in lista:
        cartao(i)
    apontados(c)
    if c in apoio.PROXIMO:
        seguinte = apoio.PROXIMO[c]
        if seguinte.startswith("etapa:"):   # o próximo passo é uma situação do Preciso de ajuda
            st.button(f"Próximo passo: {apoio.NOME_ETAPA[seguinte[6:]]} →", key=f"prox_{c}", on_click=aplicar_destino,
                      args=({"aba": apoio.LAMINAS["caminho"], "caminho": "ajuda", "etapa": seguinte[6:]},))
        else:
            st.button(f"Próximo passo: {ROTULO[seguinte]} →", key=f"prox_{c}", on_click=aplicar_destino,
                      args=({"aba": apoio.LAMINAS["caminho"], "caminho": seguinte},))


def porta_ajuda():
    """Preciso de ajuda: em que ponto a mulher está -> o próximo passo."""
    pergunta("Qual destas situações parece com a sua?")
    dica("Escolha uma opção para ver o próximo passo. Se ainda não souber, não precisa escolher agora.")
    with pilulas("etapa"):
        e = seletor(st, "Escolha uma situação", "ap_etapa", list(apoio.NOME_ETAPA),
                    format_func=apoio.NOME_ETAPA.get, horizontal=False)
    if e is None:
        st.info("Escolha uma situação acima. A Lia organiza as opções sem presumir o que aconteceu com você.")
        return
    _, _, fala, portas, _ = next(x for x in apoio.ETAPAS if x[0] == e)
    st.markdown(f'<div class="apoio-etapa">{html.escape(fala)}</div>', unsafe_allow_html=True)
    if e == "diagnostico_cancer":
        st.markdown("""
<ol class="apoio-jornada-diagnostico" aria-label="Próximos passos depois do diagnóstico">
  <li class="atual"><span class="apoio-jornada-numero" aria-hidden="true">1</span><div class="apoio-jornada-conteudo"><b>Diagnóstico confirmado</b><span>Você está aqui.</span></div><span class="apoio-jornada-conector" aria-hidden="true">↓</span></li>
  <li><span class="apoio-jornada-numero" aria-hidden="true">2</span><div class="apoio-jornada-conteudo"><b>Converse com sua equipe de saúde</b><span><strong>Próximo passo:</strong> pergunte quem acompanha seu encaminhamento e como receber notícias da vaga.</span></div><span class="apoio-jornada-conector" aria-hidden="true">↓</span></li>
  <li><span class="apoio-jornada-numero" aria-hidden="true">3</span><div class="apoio-jornada-conteudo"><b>Regulação do SUS</b><span>A rede organiza o acesso ao serviço especializado.</span></div><span class="apoio-jornada-conector" aria-hidden="true">↓</span></li>
  <li><span class="apoio-jornada-numero" aria-hidden="true">4</span><div class="apoio-jornada-conteudo"><b>Serviço especializado</b><span>A equipe avalia seu caso e conversa com você sobre o tratamento indicado.</span></div></li>
</ol>
""", unsafe_allow_html=True)
        st.markdown("**Perguntas que você pode levar à equipe:** qual serviço está responsável pelo encaminhamento? Como acompanho a vaga? Quando devo voltar se ainda não tiver resposta? Leve o laudo e os exames que já tem, se puder."
                    )
        st.markdown('<div class="apoio-recuperar-caminho"><b>Se a resposta demorar ou o encaminhamento não chegar</b></div>',
                    unsafe_allow_html=True)
        ids_retomada = ["nao_achei_nome", "lista_regulacao", "como_chegar_cross"]
        if apoio.CIDADE.casefold() == "rio claro":
            ids_retomada.append("rc_unidades")
        for id_item in ids_retomada:
            cartao_curto(apoio.POR_ID[id_item])
    if portas or e == "nao_fiz":
        colunas = st.columns(max(len(portas) + (e == "nao_fiz"), 1))
        for col, porta_id in zip(colunas, portas):
            col.button(f"Ver: {ROTULO[porta_id]} →", key=f"etapa_{e}_{porta_id}", type="primary",
                       on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["caminho"], "caminho": porta_id},),
                       width="stretch")
        if e == "nao_fiz":
            colunas[-1].button("Consultar itinerário das carretas →", key="etapa_carretas", type="primary",
                               on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["carretas"]},),
                               width="stretch")
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
    st.markdown('<div class="escudo-marca">MISM2 · Apoio à mulher</div>', unsafe_allow_html=True)
    st.markdown('<div class="escudo-titulo">Encontre um caminho</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="escudo-sub">Onde a mulher de {apoio.CIDADE} encontra prevenção, diagnóstico, '
                'tratamento e proteção, com as páginas oficiais do Estado de SP, da região e da cidade. '
                'Um guia de onde procurar, não orientação médica.</div>', unsafe_allow_html=True)
with col_link:
    botao_inicio(st, "topo")
    st.caption("Cada cartão informa sua fonte e data de conferência. Itens marcados “a confirmar” precisam ser verificados antes de usar.")

# Barra de navegação igual à das outras páginas (autor, 20/10/2026): Unidades, telefones e como chegar = "Onde ser atendida";
# o hospital de câncer mais perto de onde a mulher mora = "Hospitais de câncer". Sempre à vista, em botões grandes.
barra_de_navegacao("apoio")

# Emergência sempre à vista (auditoria de usabilidade, 20/10/2026): o número não pode ficar dentro de um menu fechado.
st.markdown('<div class="apoio-emergencia" role="note">🚨 <b>Em perigo agora?</b> Polícia: <b>190</b> · '
            'Violência contra a mulher: <b>180</b> · Emergência de saúde (SAMU): <b>192</b></div>', unsafe_allow_html=True)



def ir_aba(nome):
    st.session_state["ap_aba"] = nome
    st.session_state["ap_item"] = None
    st.session_state["caixa_ap_contexto"] = None


def ir_assunto():
    """Orientação por assunto: se estava em 'Preciso de ajuda', volta a um assunto (a ajuda é uma área à parte)."""
    ir_aba(apoio.LAMINAS["caminho"])
    if st.session_state.get("ap_caminho") == "ajuda":
        definir("ap_caminho", PADROES["ap_caminho"])


def ir_ajuda():
    """Preciso de ajuda: área à parte, em destaque (autor, 20/10/2026: "um dos mais importantes")."""
    ir_aba(apoio.LAMINAS["caminho"])
    lia_clicar(apoio.caminho("ajuda"))   # a Lia pergunta "em que ponto você está?" e abre a área (fecha as boas-vindas)
    definir("ap_caminho", "ajuda")


_na_ajuda = st.session_state["ap_aba"] == apoio.LAMINAS["caminho"] and st.session_state.get("ap_caminho") == "ajuda" \
    and st.session_state.get("ap_boas_vindas_fechada")
_no_assunto = st.session_state["ap_aba"] == apoio.LAMINAS["caminho"] and not _na_ajuda

# DESTAQUE: "Preciso de ajuda" não é um assunto da lista, é a porta de quem não sabe por onde começar (e onde mora a proteção
# contra a violência). Fica logo abaixo da faixa de emergência (perigo agora = 190/180/192; precisa de orientação = aqui),
# em TODA tela do Apoio, antes de qualquer menu.
try:
    _caixa_ajuda = st.container(key="apoio_ajuda_aqui" if _na_ajuda else "apoio_ajuda_destaque")
except TypeError:  # Streamlit antigo, sem key em container
    _caixa_ajuda = st.container()
with _caixa_ajuda:
    st.button("💜 Preciso de ajuda" + ("  ·  você está aqui" if _na_ajuda else ""), key="apoio_ajuda_botao", on_click=ir_ajuda,
              width="stretch", help="A Lia pergunta em que ponto você está e mostra o próximo passo, sem presumir nada.")
    if not _na_ajuda:
        st.markdown('<div class="apoio-ajuda-sub">Não sabe por onde começar? <b>Comece por aqui.</b> Você escolhe a sua situação '
                    '(ainda não fiz o exame, meu exame deu alterado, fui encaminhada, recebi um diagnóstico, estou em tratamento '
                    'ou estou em situação de violência) e vê o próximo passo.</div>', unsafe_allow_html=True)

# Entrada guiada: poucas escolhas principais; o catálogo completo continua nas abas abaixo.
_pergunta_pendente = st.session_state.pop("caixa_ap_pendente", None)
if _pergunta_pendente:
    with st.spinner("A Lia está procurando no guia..."):
        _classificador = classificador_da_sessao()
        # contexto: token do catálogo ("item:id") para "e agora?"; cancer_em_foco: o câncer da resposta na tela, para "e os sinais?".
        # Só memória da sessão; o texto da pergunta nunca é guardado.
        _resposta = apoio_busca.responder_pergunta(
            _pergunta_pendente, classificar=_classificador,
            contexto=st.session_state.get("caixa_ap_contexto"),
            cancer_em_foco=getattr(lia_estado.get("atual"), "tipo_cancer", None),
        )
        atualizar_contexto_conversa(_resposta)
        lia_mostrar(_resposta)

# Navegação organizada em dois grupos: primeiro o que a mulher procura; depois os recursos de referência.
n1, n2, r1, r2 = st.columns(4)
n1.button("Orientação por assunto", key="nav_apoio_caminho", type="primary" if _no_assunto else "secondary",
          on_click=ir_assunto, width="stretch")
_rc = apoio.LAMINAS["rio_claro"]
n2.button(_rc, key="nav_apoio_rio_claro", type="primary" if st.session_state["ap_aba"] == _rc else "secondary",
          on_click=ir_aba, args=(_rc,), width="stretch")
r1.button("Hospitais no Estado", key="nav_apoio_hospitais", type="primary" if st.session_state["ap_aba"] == apoio.LAMINAS["hospitais"] else "secondary",
          on_click=aplicar_destino, args=({"aba": apoio.LAMINAS["hospitais"]},), width="stretch",
          help="Hospitais de câncer por região do Estado e o Hospital de Amor, em Barretos.")
r2.button("Sobre as informações", key="nav_apoio_sobre", type="primary" if st.session_state["ap_aba"] == apoio.LAMINAS["sobre"] else "secondary",
          on_click=ir_aba, args=(apoio.LAMINAS["sobre"],), width="stretch")

aba = st.session_state["ap_aba"]

# "Você está em" (auditoria de usabilidade, 20/10/2026): a mulher vê onde está sem decifrar o seletor.
_boas_vindas_abertas = not st.session_state.get("ap_boas_vindas_fechada")
if aba == apoio.LAMINAS["caminho"]:
    _c = st.session_state.get("ap_caminho")
    if _c == "ajuda" and not _boas_vindas_abertas:
        _onde = ["Preciso de ajuda"]
        _e = st.session_state.get("ap_etapa")
        if _e in apoio.NOME_ETAPA:
            _onde.append(apoio.NOME_ETAPA[_e])
    else:
        _onde = ["Orientação por assunto"]
        if _boas_vindas_abertas:
            _onde.append("escolha uma situação abaixo")
        else:
            _onde.append(ROTULO.get(_c, ""))
    _onde = " › ".join(x for x in _onde if x)
elif aba == apoio.LAMINAS["hospitais"] and st.session_state.get("ap_hosp_modo") == "barretos":
    _onde = f"{aba} › Barretos: Hospital de Amor"
else:
    _onde = aba
st.markdown(f'<div class="escudo-voce-esta">📍 Você está em: <b>{html.escape(_onde)}</b> · {apoio.CIDADE}</div>',
            unsafe_allow_html=True)


# ---- A Lia: uma só, no centro, entre a navegação e o conteúdo ----
def desenhar_lia_apoio():
    atual = lia_estado["atual"]
    boas_vindas_aberta = not st.session_state.get("ap_boas_vindas_fechada")
    recolhida = bool(st.session_state.get("lia_recolhida")) and not boas_vindas_aberta
    if recolhida:
        c_rosto, c_fala, c_abrir = st.columns([0.5, 6, 1.6], vertical_alignment="center")
        c_rosto.markdown(rosto(atual.expressao, 68), unsafe_allow_html=True)
        c_fala.markdown('<div class="lia-nome">Lia <span>· pergunte ou escolha um caminho quando quiser</span></div>',
                        unsafe_allow_html=True)
        c_abrir.button("Abrir a Lia", key="caixa_lia_abrir", on_click=definir, args=("lia_recolhida", False), width="stretch")
        return
    c_rosto, c_fala = st.columns([1.3, 4.6] if boas_vindas_aberta else [1.0, 6])
    with c_rosto:
        st.markdown(rosto("acolhedora" if boas_vindas_aberta else atual.expressao, 210 if boas_vindas_aberta else 140),
                    unsafe_allow_html=True)
    with c_fala:
        with balao("centro"):
            if boas_vindas_aberta:
                st.markdown('<div class="lia-nome">Lia <span>· pesquisadora do MISM2</span></div>'
                            '<div class="lia-fala-grande">Vamos por partes. Escolha o que mais se parece com a sua situação; '
                            'você pode voltar e mudar de caminho.</div>', unsafe_allow_html=True)
                st.markdown("**Por onde você quer começar?**")
                a1, a2 = st.columns(2)
                a3 = st.container()
                a1.button("Prevenção e exames", key="bv_ap_prevencao", help="Mamografia, Papanicolau, vacina e prevenção.",
                          on_click=lia_clicar, args=(apoio.etapa("nao_fiz"),), width="stretch")
                a2.button("Meu exame deu alterado", key="bv_ap_alterado",
                          help="Um resultado alterado precisa ser explicado pela equipe de saúde; não significa, por si só, câncer.",
                          on_click=lia_clicar, args=(apoio.etapa("alterado"),), width="stretch")
                a3.button("Recebi diagnóstico de câncer", key="bv_ap_diagnostico",
                          help="Veja o caminho depois de um diagnóstico confirmado.", on_click=lia_clicar,
                          args=(apoio.etapa("diagnostico_cancer"),), width="stretch")
                st.caption("Não sabe por onde começar? Use o botão **💜 Preciso de ajuda**, logo acima. "
                           "Prefere escrever? Use a caixa **Pergunte à Lia**, logo abaixo.")
                st.button("Ver todas as áreas abaixo", key="bv_fechar_apoio",
                          on_click=lambda: st.session_state.update(ap_boas_vindas_fechada=True))
            else:
                cab, rec = st.columns([6, 1.4], vertical_alignment="center")
                cab.markdown('<div class="lia-nome">Lia <span>· pesquisadora do MISM2</span></div>', unsafe_allow_html=True)
                rec.button("Recolher a Lia", key="caixa_lia_recolher", on_click=definir, args=("lia_recolhida", True),
                           width="stretch")
                if getattr(atual, "pergunta", None):
                    st.caption(f"Você perguntou: “{atual.pergunta}”")
                contexto_resposta, rotulo_resposta = contexto_da_resposta(atual)
                contexto_atual, rotulo_atual = contexto_da_aba_atual()
                se_contexto_diferente = contexto_resposta[0] != contexto_atual[0]
                if not se_contexto_diferente and contexto_resposta[1] == "caminho":
                    se_contexto_diferente = contexto_resposta[1:] != contexto_atual[1:]
                if se_contexto_diferente:
                    st.info(f"Esta resposta é sobre {rotulo_resposta}. Você está em {rotulo_atual}.")
                    st.button("Falar sobre " + rotulo_atual, key="lia_falar_sobre_aba",
                              on_click=falar_sobre_aba_atual, width="stretch")
                fala_lateral = atual.fala
                if getattr(atual, "tipo", None) is None and not se_contexto_diferente:
                    linhas = fala_lateral.split("\n")
                    sem_lista = [ln for ln in linhas if not ln.startswith("- ")]
                    if len(sem_lista) < len(linhas):
                        fala_lateral = "\n".join(sem_lista)
                        while "\n\n\n" in fala_lateral:
                            fala_lateral = fala_lateral.replace("\n\n\n", "\n\n")
                        fala_lateral = fala_lateral.strip() + "\n\n*Os detalhes de cada serviço estão nos cartões, abaixo.*"
                st.markdown(fala_lateral)
                if getattr(atual, "selo", None):
                    st.caption(atual.selo)
                if atual.numeros:
                    with st.expander("Onde a Lia conferiu"):
                        st.markdown("\n".join(f"- {n}" for n in atual.numeros))
                proximos = [(r, a) for r, a in atual.botoes if a is not INICIO and a.get("tipo") != "inicio"]
                colunas = st.columns(3)
                for n, (rotulo, acao) in enumerate(proximos):
                    colunas[n % 3].button(rotulo, key=f"lia_ap_{n}_{rotulo}", on_click=lia_clicar, args=(acao,),
                                          width="stretch")
                c_voltar, c_inicio, _resto = st.columns([1, 1.3, 4])
                if lia_estado["pilha"]:
                    c_voltar.button("← Voltar", key="lia_discreto_voltar_ap", on_click=lia_voltar)
                c_inicio.button("Começar de novo", key="lia_discreto_inicio_ap", on_click=lia_clicar, args=(INICIO,))
        # Pergunte à Lia: logo abaixo do balão
        st.markdown("**Pergunte à Lia**")
        with st.form("caixa_ap_form", clear_on_submit=True):
            f1, f2 = st.columns([5, 1.2])
            f1.text_input("Pergunte à Lia", key="caixa_ap_texto", max_chars=300, label_visibility="collapsed",
                          placeholder="Ex.: onde faço mamografia pelo SUS?")
            f2.form_submit_button("Perguntar", key="caixa_ap_enviar", on_click=enviar_pergunta, width="stretch")
        st.caption("Não sabe o que perguntar? Escreva: **o que você sabe responder?**")
        gemini_disponivel = apoio_busca.obter_classificador()
        if gemini_disponivel:
            st.toggle("Permitir que o Google Gemini ajude a identificar o assunto", key="caixa_ap_gemini_ativo",
                      help="Opcional e desligado por padrão. A resposta continua sendo escrita pelo guia oficial.")
            if st.session_state.get("caixa_ap_ia", 0) >= LIMITE_PERGUNTAS_COM_IA:
                st.info("Limite de 40 classificações Gemini nesta sessão atingido. A busca local no guia continua disponível.")
            else:
                st.caption("Se ligado e a busca local precisar de ajuda, o texto da pergunta vai ao Google Gemini "
                           "somente para escolher o assunto. A IA não escreve a resposta. Não envie nomes, telefones "
                           "ou outros dados pessoais.")
        else:
            st.caption("Busca no guia; o Gemini está indisponível nesta sessão. A resposta vem do catálogo conferido.")
        with st.expander("Assuntos: ver todos"):
            for titulo, assuntos in assuntos_do_guia():
                st.markdown(f"**{titulo}**")
                for assunto in assuntos:
                    st.button(assunto["rotulo"], key=f"assunto_{assunto['tipo']}_{assunto['id']}",
                              on_click=mostrar_assunto, args=(assunto["pergunta"], assunto["acao"]), width="stretch")
                if titulo == "Proteção":
                    st.button("Estou em perigo agora", key="assunto_urgencia_agora", on_click=mostrar_assunto,
                              args=("meu marido me bate", None), width="stretch")
        st.caption("Não escreva dados pessoais. Esta página não guarda as perguntas. "
                   + ("Com o Gemini desligado, a busca é feita localmente no guia."
                      if not st.session_state.get("caixa_ap_gemini_ativo", False)
                      else "Com o Gemini ligado, se a busca local precisar de ajuda, a pergunta vai ao Google "
                           "apenas para classificar o assunto."))


desenhar_lia_apoio()



# ============================================================
# ENCONTRE UM CAMINHO — Estado de SP e itens das cidades, por caminho
# ============================================================

if aba == apoio.LAMINAS["caminho"] and not _boas_vindas_abertas:
    if st.session_state.get("ap_caminho") == "ajuda":
        porta_ajuda()   # área à parte: não aparece entre os assuntos
    else:
        pergunta("O que você precisa?")
        dica("Escolha um assunto abaixo: prevenção, diagnóstico, encaminhamento, tratamento e direitos. "
             "Hospitais, Carretas e os serviços de Rio Claro ficam em áreas próprias. Se estiver em dúvida, use o botão "
             "<b>💜 Preciso de ajuda</b>, acima.")
        codigos = [c for c, _, _, _ in apoio.CAMINHOS if c != "ajuda"]
        if st.session_state.get("ap_caminho") not in codigos:   # assunto que não existe mais (sessão antiga): volta ao primeiro
            definir("ap_caminho", PADROES["ap_caminho"])
        onde_clicar("Clique num assunto. Depois, em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
        with pilulas("caminho"):
            c = seletor(st, "Caminho", "ap_caminho", codigos, format_func=ROTULO.get, horizontal=True,
                        label_visibility="collapsed")
        _, rotulo, dentro, abertura = next(x for x in apoio.CAMINHOS if x[0] == c)
        porta(c, rotulo, dentro, abertura)
    with st.expander("O que significam estas palavras? (UBS, regulação, UNACON...)"):
        for termo, explicacao in apoio.GLOSSARIO:
            st.markdown(f"**{termo}:** {explicacao}")
    leitura("Como usar", [
        "Cada cartão traz a página oficial e a data em que foi conferido. Borda laranja = ainda falta confirmar "
        "algum detalhe na própria página.",
        "Pelo SUS, o caminho quase sempre começa na unidade de saúde do bairro, e o encaminhamento é feito pela "
        "regulação; os hospitais de referência não são porta de entrada.",
    ])


def hospital_de_amor_barretos():
    """Hospital de Amor (Barretos), dentro de Hospitais no Estado (autor, 20/10/2026: não precisa de botão só dele)."""
    pergunta("Barretos: referência em oncologia e prevenção")
    dica("Barretos concentra, no Hospital de Amor, prevenção, diagnóstico, tratamento, ensino e pesquisa em câncer, "
         "com ações que chegam a outros municípios, como Rio Claro.")
    onde_clicar("Clique num tema. Em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    lamina_por_grupos("barretos", "Tema")
    st.markdown('<div class="escudo-alerta">Para quem mora em Rio Claro, o caminho do SUS passa primeiro pela '
                'referência da própria região (RRAS 14: Rio Claro e Piracicaba). Converse com a equipe que '
                'acompanha você.</div>', unsafe_allow_html=True)
    leitura("A ligação com Rio Claro", [
        "Prevenção e tratamento têm caminhos diferentes: a prevenção chega pelas ações com a prefeitura; o "
        "tratamento, com o câncer confirmado, segue os fluxos do SUS.",
    ])


# ============================================================
# HOSPITAIS NO ESTADO — onde se trata câncer pelo SUS, por região
# ============================================================

if aba == apoio.LAMINAS["hospitais"]:
    with pilulas("hosp_modo"):
        _modo = seletor(st, "Ver", "ap_hosp_modo", ["regiao", "barretos"], horizontal=True, label_visibility="collapsed",
                        format_func={"regiao": "Hospitais por região", "barretos": "Barretos: Hospital de Amor"}.get)
    if _modo == "barretos":
        hospital_de_amor_barretos()
if aba == apoio.LAMINAS["hospitais"] and st.session_state.get("ap_hosp_modo") != "barretos":
    pergunta("Onde se trata câncer pelo SUS no Estado de São Paulo?")
    dica("Hospitais habilitados para tratar câncer (CACON e UNACON), por região. Eles não são porta de entrada: "
         "a vaga é pedida pela unidade de saúde, pela regulação do Estado (CROSS).")
    onde_clicar("Clique numa região. Em cada cartão, clique no botão azul <b>Abrir a página oficial</b>.")
    # Mapa com TODOS os hospitais habilitados (Estado e Brasil), endereço, telefone e os mais próximos da sua cidade: página própria
    # (uma casa só); o Apoio aponta para ela, como faz com "Onde ser atendida".
    try:
        st.page_link("pages/hospitais_cancer.py", label="🗺️ Ver todos os hospitais habilitados no mapa, com os mais próximos da sua cidade")
    except Exception:  # Streamlit antigo, sem page_link
        st.markdown('<a href="/hospitais_cancer" target="_self">Ver todos os hospitais habilitados no mapa</a>', unsafe_allow_html=True)
    lamina_por_grupos("hospitais", "Região")
    leitura("Como chegar a um destes hospitais", [
        "Com suspeita ou diagnóstico de câncer, procure a unidade de saúde do bairro: o médico do SUS pede a vaga "
        "pela CROSS, que encaminha a um centro perto de onde você mora.",
        "Se o tratamento não existir no município onde você mora, o SUS pode pagar transporte e diárias (TFD, "
        "no assunto Direitos e acesso).",
        "A lista completa e oficial é a da FOSP (primeira região desta área).",
    ])


# ============================================================
# CARRETAS — onde a carreta da mamografia está agora
# ============================================================

# ============================================================
# RIO CLARO — a cidade do trabalho
# ============================================================

if aba == apoio.LAMINAS["rio_claro"]:
    pergunta(f"O que {apoio.CIDADE} oferece às mulheres?")
    dica(f"{apoio.CIDADE} faz parte da {apoio.REGIAO}. As referências de câncer da região são Rio Claro e "
         "Piracicaba, e o HC da Unicamp também atende a região (área Hospitais no Estado).")
    cartao_carretas("Carretas da Mamografia: veja a programação atual",
                    "As cidades e datas das Carretas da Mamografia do Estado (Mulheres de Peito) mudam. "
                    "Consulte o roteiro atual nos canais oficiais antes de sair:")
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
        "Para quase tudo, o começo é a Unidade de Saúde da Família ou a UBS do bairro.",
        "Vários dados de Rio Claro vêm de páginas antigas da Prefeitura e da Fundação Municipal de Saúde: estão "
        "marcados para confirmar.",
    ])


# ============================================================
# SOBRE ESTAS INFORMAÇÕES
# ============================================================

if aba == apoio.LAMINAS["sobre"]:
    pergunta("De onde vêm estas informações?")
    # Transparência do catálogo fica junto às fontes, fora da entrada de quem procura cuidado.
    pendentes = sum(bool(i["confirmar"]) for i in apoio.ITENS)
    m1, m2, m3 = st.columns(3)
    m1.metric("Caminhos de orientação", len(apoio.CAMINHOS))
    m2.metric("Informações cadastradas", len(apoio.ITENS))
    m3.metric("Pedem confirmação", pendentes)
    st.markdown(f"""
- **O que é:** um guia de onde procurar ajuda, montado a partir de páginas oficiais: portal da Saúde do Estado
  de SP, Poupatempo, rede oncológica da FOSP, Ministério da Saúde, Fundação Municipal de Saúde de Rio Claro,
  prefeituras de Campinas, Ribeirão Preto, São José do Rio Preto e Piracicaba e Hospital de Amor.
- **Data de conferência:** cada cartão mostra a data registrada para aquele item. A pesquisa-base foi reunida em {apoio.CONFERIDO}; itens atualizados depois têm data própria. Regras, endereços, telefones e itinerários podem mudar.
- **O que ainda falta confirmar:** a pesquisa foi feita pela busca na web, com trechos das páginas oficiais.
  Quando o detalhe veio de página antiga, de reportagem ou não pôde ser aberto por inteiro, o item está marcado
  "a confirmar".
- **O que isto não é:** não é orientação médica, não garante vaga e não substitui a unidade de saúde.
  A Lia não é médica.
- **Cidades:** não há uma área por cidade. Campinas, Ribeirão Preto, Rio Preto e Piracicaba entram nos assuntos
  quando têm algo útil; Rio Claro (a cidade do trabalho) e Barretos (Hospital de Amor) têm área própria.
- **Para gestores:** o Plano Estadual de Oncologia 2025–2028 organiza a rede por região (RRAS); Rio Claro está na
  {apoio.REGIAO}.
""")
    tabela = pd.DataFrame([{
        "Item": i["titulo"], "Onde": i["onde"], "Área": apoio.LAMINAS[i["lamina"]],
        "Caminho": ROTULO.get(i["caminho"], "—"), "Tema ou região": i["grupo"] or "—", "Fonte": i["fonte"], "Situação": "a confirmar" if i["confirmar"] else "conferido",
        "Página": i["link"]} for i in apoio.ITENS])
    st.dataframe(tabela, width="stretch", hide_index=True)


st.caption("MISM2 · Apoio à mulher · guia de onde procurar; confirme sempre na unidade de saúde.")
