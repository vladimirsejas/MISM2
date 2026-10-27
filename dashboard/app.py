import html
import math
import os
import sqlite3
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "algoritimos"))

from configuracao_geografica import BANCO, listar_municipios_disponiveis, obter_municipio, UF_REFERENCIA
from lia import INICIO, Contexto, responder as lia_responder
from assistente import IA, acao as acao_assistente, obter_ia, responder_escolha, responder_pergunta
from conversa import registrar_pergunta
from localizacao import carregar_localizacao, pontos_origens
import hospitais_oncologia as hosp_onco
from passeio import PARADAS, parada as passeio_parada
from lia_rosto import img as rosto_lia
from estilo import CSS
from identidade import regua_cobertura as regua_mism
from inteligencia import (
    ranking_municipios,
    ranking_atendimento,
    carregar_tratamento,
    carregar_obitos_sim,
    ano_atipico_no_estado,
    anos_fora_do_padrao,
    anos_incompletos,
    cancer_de,
    canceres_com_duplicidade,
    carregar_faixas,
    carregar_fluxo,
    carregar_serie,
    cidades_parecidas,
    comparar_faixas,
    anos_com_dados,
    internacoes_do_periodo,
    leitura_internacoes_periodo,
    NOMES_MESES,
    totais_faixas,
    TODOS_CANCERES,
    NOME_TODOS_CANCERES,
    confiabilidade,
    destaques_cancer,
    ficha_cancer,
    fluxo_da_cidade,
    agrupar_origens,
    formatar_numero,
    evolucao_fluxo,
    alcance_dados,
    leitura_cidade, leitura_cidade_visao,
    leitura_evolucao,
    leitura_previsao,
    leitura_evolucao_fluxo,
    leitura_faixas,
    leitura_fluxo,
    pontos_mapa_fluxo,
    hospitais_fluxo,
    leitura_hospitais,
    carregar_hospitais,
    lista_hospitais,
    ficha_hospital,
    leitura_hospital,
    leitura_hospital_anos,
    agrupar_estados, leitura_estados_do_hospital,
    nome_uf,
    CENTROS_UF,
    leitura_ponta_projecao,
    ligacoes_fluxo,
    mix_comparacao,
    nome_doenca,
    prever_com_validacao,
    projetar,
    perfil_cidade,
    parcela_fora_por_cancer,
    tabela_fluxo,
    filtrar_tabela_fluxo,
    agrupar_tabela_fluxo,
    leitura_tabela_fluxo,
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
# (no centro, entre as abas e os dados; algoritimos/lia.py, docs/LIA.md) atravessa todas: conduz
# por botões e leva o painel até o gráfico. Sem caixa de texto livre
# (saiu em 09/2026). Dinheiro aparece sempre como "valor hospitalar
# registrado no SIH/SUS", nunca como orçamento.
# O painel antigo continua no histórico do git (commit 273fbe5).
# ============================================================


st.set_page_config(
    page_title="MISM2",
    page_icon="E",
    layout="wide",
    initial_sidebar_state="collapsed",
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
def anos_do_banco():
    try:
        conn = sqlite3.connect(BANCO)
    except Exception:
        return []
    try:
        return anos_com_dados(conn, UF_REFERENCIA)
    finally:
        conn.close()


@st.cache_data
def internacoes_do_ano(origem, codigo_ibge, ano, perspectiva, cancer):
    try:
        conn = sqlite3.connect(BANCO)
    except Exception:
        return None
    try:
        return internacoes_do_periodo(conn, origem, codigo_ibge, ano, perspectiva, cancer, UF_REFERENCIA)
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


@st.cache_data(ttl=600)
def hospitais_habilitados():
    """Hospitais habilitados em oncologia (lista do Ministério + posição do CNES); vazio se os arquivos não existirem."""
    return hosp_onco.carregar()


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
def tabelas_ambulatorial_e_sim():
    """(tratamento SIA, óbitos SIM): vazias se o banco ainda não tem as tabelas (py -3.12 etl\\carregar_tudo_pysus.py)."""
    conn = sqlite3.connect(BANCO)
    try:
        return carregar_tratamento(conn), carregar_obitos_sim(conn)
    finally:
        conn.close()


@st.cache_data
def localizacao_dos_municipios():
    """Centro de cada município de SP (py -3.12 etl\\baixar_centroides.py); vazio sem a tabela (a Lia então não dá distâncias)."""
    conn = sqlite3.connect(BANCO)
    try:
        return carregar_localizacao(conn)
    finally:
        conn.close()


@st.cache_data
def alcance_do_banco():
    """O que o banco guarda (cânceres, período, cidades, outras bases): a Lia responde "quais doenças/cidades você tem?" com isto."""
    conn = sqlite3.connect(BANCO)
    try:
        return alcance_dados(conn)
    finally:
        conn.close()


@st.cache_data
def polos_de_tratamento():
    """{câncer ou None (os 7 somados): cidades que mais tratam (município do hospital)}. Vazio se o banco não guarda o município do hospital."""
    conn = sqlite3.connect(BANCO)
    try:
        tipos = [r[0] for r in conn.execute("SELECT DISTINCT tipo_cancer FROM internacoes WHERE tipo_cancer IS NOT NULL")]
        saida = {}
        for chave in [None] + tipos:
            tabela = ranking_atendimento(conn, chave, UF_REFERENCIA)
            if len(tabela):
                saida[chave] = tabela
        return saida
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


@st.cache_data
def rankings_por_100_mil():
    """{câncer ou None (os 7 somados): ranking por 100 mil mulheres}. Vazio se o banco ainda não tem a população do IBGE
    (py etl\\baixar_populacao.py); a Lia então diz o que falta em vez de inventar um ranking."""
    conn = sqlite3.connect(BANCO)
    try:
        tipos = [r[0] for r in conn.execute("SELECT DISTINCT tipo_cancer FROM internacoes WHERE tipo_cancer IS NOT NULL")]
        saida = {}
        for chave in [None] + tipos:
            tabela = ranking_municipios(conn, chave, UF_REFERENCIA)
            if len(tabela):
                saida[chave] = tabela
        return saida
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


@st.cache_data
def hospitais_dados():
    conn = sqlite3.connect(BANCO)
    try:
        return carregar_hospitais(conn, UF_REFERENCIA)
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


def selo_escopo(tipo, detalhe="", cidade=None):
    """Diz de quem são os números do bloco: "estado" (todas as cidades de SP, não muda
    quando se troca de município) ou "cidade" (a escolhida no topo)."""
    if tipo == "estado":
        rotulo, padrao = "🌎 Todo o Estado de São Paulo", "não muda quando você troca de cidade"
    else:
        rotulo, padrao = f"📍 {html.escape(cidade or nome_cidade)}", "muda quando você troca de cidade"
    st.markdown(f'<div class="escudo-escopo {tipo}">{rotulo} <small>· {detalhe or padrao}</small></div>',
                unsafe_allow_html=True)


def pergunta(texto, escopo=None, detalhe="", cidade=None):
    st.markdown(f'<div class="escudo-pergunta">{texto}</div>', unsafe_allow_html=True)
    if escopo:
        selo_escopo(escopo, detalhe, cidade)


def leitura(titulo, frases):
    st.markdown(
        f'<div class="escudo-leitura"><b>{titulo}</b><ul>'
        + "".join(f"<li>{f}</li>" for f in frases) + "</ul></div>",
        unsafe_allow_html=True,
    )


def estilizar(fig, altura):
    fig.update_layout(
        height=altura,
        font={"family": "DM Sans, sans-serif", "size": 14, "color": TINTA},
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

col_titulo = st.container()
nome_cidade = st.session_state.get("municipio_painel", nomes[indice_padrao])
if nome_cidade not in nomes:
    nome_cidade = nomes[indice_padrao]
cidade = next(m for m in lista_municipios if m["nome"] == nome_cidade)
ORIGEM = cidade["origem"]

serie = serie_municipio(ORIGEM)
resumo = resumo_doencas(serie) if not serie.empty else pd.DataFrame()

with col_titulo:
    st.markdown(f'<div class="mism-marca"><div class="escudo-marca">MISM2'
                f'<span> · saúde da mulher</span></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="escudo-titulo">Câncer em mulheres de <em>{html.escape(nome_cidade)}</em></div>',
                unsafe_allow_html=True)
    if not resumo.empty:
        ano_ini, ano_fim = int(serie["ano"].min()), int(serie["ano"].max())
        st.markdown(
            f'<div class="escudo-sub">De {ano_ini} a {ano_fim}, mulheres que moram em '
            f'{html.escape(nome_cidade)}, nos {len(resumo)} tipos de câncer acompanhados (SIH/SUS).</div>',
            unsafe_allow_html=True,
        )
        NUMEROS_HTML = (
            f'<div class="mism-numeros">'
            f'<div class="mism-grande"><b>{formatar_numero(resumo["internacoes"].sum())}</b><span>internações</span></div>'
            f'<div><b>{formatar_numero(resumo["obitos"].sum())}</b><span>óbitos durante a internação</span></div>'
            f'<div><b>{reais(resumo["valor_total"].sum())}</b><span>valor hospitalar registrado no SIH/SUS</span></div>'
            f'</div>' + regua_mism(serie))

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
    # Onde ser atendida (dashboard/pages/onde_ser_atendida.py): unidades de saúde da
    # cidade pelo CNES. Link discreto (a página substitui a antiga "Rede local").
    try:
        st.page_link("pages/onde_ser_atendida.py", label="Onde ser atendida")
    except Exception:  # Streamlit antigo, sem page_link
        st.markdown('<a href="/onde_ser_atendida" target="_self">Onde ser atendida</a>', unsafe_allow_html=True)
    # Hospitais de câncer (mapa e os mais próximos da cidade onde a mulher mora): mesmo grupo, uma casa só no painel.
    try:
        st.page_link("pages/hospitais_cancer.py", label="Hospitais de câncer")
    except Exception:  # Streamlit antigo, sem page_link
        st.markdown('<a href="/hospitais_cancer" target="_self">Hospitais de câncer</a>', unsafe_allow_html=True)

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

ABAS = ["Panorama", "Evolução", "Rede hospitalar", "Investigar", "Planejamento", "Método"]
PADROES = {"aba": "Panorama", "medida": "Internações",
           "ver_estado": True, "ver_fora": True, "ver_projecao": False, "ver_hospitais": True,
           "fluxo_visao": "Moradoras atendidas em cidades de fora", "fluxo_origens_forma": "Mapa"}
for chave, valor in PADROES.items():
    st.session_state.setdefault(chave, valor)


def definir(chave, valor):
    st.session_state[chave] = valor


def chave_widget(chave):
    return f"w_{chave}_{st.session_state[chave]}"


def sincronizar(chave, chave_do_widget):
    st.session_state[chave] = st.session_state[chave_do_widget]


def valor_valido(chave, opcoes):
    """Garante que o valor guardado existe entre as opções (estado velho ou inválido volta à primeira opção,
    em vez de derrubar a tela com 'x not in list')."""
    if st.session_state.get(chave) not in opcoes:
        st.session_state[chave] = opcoes[0]


def seletor(onde, rotulo, chave, opcoes, **kwargs):
    """st.radio preso à chave persistente (ver ESTADO DA TELA)."""
    valor_valido(chave, opcoes)
    k = chave_widget(chave)
    return onde.radio(rotulo, opcoes, index=opcoes.index(st.session_state[chave]), key=k,
                      on_change=sincronizar, args=(chave, k), **kwargs)


def caixa_presa(onde, rotulo, chave, opcoes, **kwargs):
    """st.selectbox preso à chave persistente (mesma defesa de seletor)."""
    valor_valido(chave, opcoes)
    k = chave_widget(chave)
    return onde.selectbox(rotulo, opcoes, index=opcoes.index(st.session_state[chave]), key=k,
                          on_change=sincronizar, args=(chave, k), **kwargs)


def seguir_o_topo(chave, chave_topo, valor_topo):
    """A escolha local começa igual à do topo e volta a ela quando o topo muda; entre uma troca e outra,
    vale o que a pessoa escolheu no próprio gráfico."""
    if st.session_state.get(chave_topo) != valor_topo or chave not in st.session_state:
        st.session_state[chave_topo] = valor_topo
        st.session_state[chave] = valor_topo


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

tratamento_sia, obitos_sim = tabelas_ambulatorial_e_sim()  # uma leitura só do cache (cada uma cria uma cópia de ~200 MB)
ctx_lia = Contexto(serie=serie, cidade=nome_cidade, faixas=faixas_municipio(ORIGEM),
                   duplicados=tuple(duplicados_municipio(ORIGEM)),
                   fluxo=fluxo_geral(), fluxo_cidade=fluxo_cidade(ORIGEM, cidade["codigo_ibge"]),
                   codigo_ibge=cidade["codigo_ibge"], ranking=rankings_por_100_mil(),
                   tratamento=tratamento_sia, obitos_sim=obitos_sim,
                   localizacao=localizacao_dos_municipios(), atendimento=polos_de_tratamento(),
                   alcance=alcance_do_banco())
st.session_state.setdefault("lia", {"cidade": None, "atual": None, "pilha": []})
lia_estado = st.session_state["lia"]
if lia_estado["cidade"] != ORIGEM:  # trocou de cidade: a Lia recomeça
    lia_estado.update({"cidade": ORIGEM, "atual": lia_responder(ctx_lia, INICIO), "pilha": []})
    st.session_state.pop("lia_memoria", None)


def lia_mostrar(resposta):
    """Guarda a resposta e leva o painel até o gráfico dela."""
    if lia_estado["atual"] is not None:
        lia_estado["pilha"].append(lia_estado["atual"])
    lia_estado["atual"] = resposta
    lia_estado["falas"] = lia_estado.get("falas", 0) + 1  # balão novo -> animação
    st.session_state["lia_fechada"] = True
    st.session_state["lia_recolhida"] = False
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


# ------------------------------------------------------------
# PERGUNTE À LIA (caixa de texto; algoritimos/assistente.py, docs/IA_DO_ESCUDO.md)
# Mais uma forma de chegar a uma resposta da Lia: a pergunta é entendida
# (entendimento.py), respondida com os MESMOS cálculos dos botões e
# redigida pelo Gemini quando ele está ligado. A resposta entra no balão
# da Lia, e o painel vai ao gráfico dela. Sem chave, sem rede ou sem cota,
# a resposta direta aparece. A árvore de botões não muda.
# ------------------------------------------------------------

LIMITE_PERGUNTAS_COM_IA = 40  # por sessão: protege a cota paga do Gemini


def ia_da_sessao():
    ia = obter_ia()
    if ia.ligada and st.session_state.get("lia_perguntas_ia", 0) >= LIMITE_PERGUNTAS_COM_IA:
        return IA()  # passou do limite desta sessão: segue sem Gemini
    return ia


def perfil_da_lia():
    return "SIMPLES" if st.session_state.get("caixa_linguagem") == "Simples" else "TECNICO"


def guardar_resposta_da_caixa(resposta, ia):
    """Memória mínima para 'e no estado?': só o assunto e o câncer da última resposta, na sessão."""
    # o limite protege a cota: conta só as chamadas que o Gemini realmente recebeu (resposta direta do roteador não gasta nada)
    st.session_state["lia_perguntas_ia"] = st.session_state.get("lia_perguntas_ia", 0) + getattr(ia, "chamadas", 0)
    if getattr(resposta, "intencao", None):
        st.session_state["lia_memoria"] = {"intencao": resposta.intencao, "cancer": resposta.cancer}
    lia_mostrar(resposta)


def perguntar_a_lia(texto):
    ia = ia_da_sessao()
    outras = [m["nome"] for m in lista_municipios if m["origem"] != ORIGEM]
    resposta = responder_pergunta(ctx_lia, texto, doenca, memoria=st.session_state.get("lia_memoria"),
                                  perfil=perfil_da_lia(), ia=ia, outras_cidades=outras)
    if resposta.tipo != "risco" and resposta.intencao != "sintoma":  # só o assunto é contado; o texto nunca é guardado
        registrar_pergunta(BANCO, resposta.intencao or resposta.tipo)
    guardar_resposta_da_caixa(resposta, ia)


def enviar_pergunta():
    """Botão do formulário: guarda o texto; a resposta é feita no começo da próxima execução."""
    texto = (st.session_state.get("caixa_texto") or "").strip()
    if texto:
        st.session_state["lia_pergunta_pendente"] = texto[:300]


def lia_clicar(acao):
    if acao.get("tipo") == "assistente":  # palpite ou exemplo da caixa: o assunto já foi escolhido
        ia = ia_da_sessao()
        guardar_resposta_da_caixa(responder_escolha(ctx_lia, acao, doenca, perfil_da_lia(), ia), ia)
        return
    if acao.get("tipo") == "inicio":
        st.session_state.pop("lia_memoria", None)  # recomeçar esquece o contexto
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


_pergunta_pendente = st.session_state.pop("lia_pergunta_pendente", None)
if _pergunta_pendente:
    with st.spinner("A Lia está pensando..."):
        perguntar_a_lia(_pergunta_pendente)

# ------------------------------------------------------------
# NAVEGAÇÃO: abas (e Início) logo abaixo do cabeçalho, depois a Lia, depois os dados
# ------------------------------------------------------------

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
                      width="stretch")
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
                             width="stretch")
            ultima = indice == len(PARADAS) - 1
            c_seg.button("terminar ✓" if ultima else "próxima parada →", key="pbtn_seguir",
                         on_click=passeio_ir, args=(None if ultima else indice + 1,), width="stretch")
            if not ultima:
                st.button("sair do passeio", key="pbtn_sair", on_click=passeio_ir, args=(None,))



_ONDE = {"Panorama": "Panorama · a página inicial: o que está acontecendo",
         "Evolução": "Evolução · como os números mudaram ao longo dos anos",
         "Rede hospitalar": "Rede hospitalar · onde as mulheres são atendidas e de onde vêm",
         "Investigar": "Investigar · perguntas sobre a cidade escolhida: câncer que cresce, idade e comparação",
         "Planejamento": "Planejamento · onde a cidade pode ter problema nos próximos anos",
         "Método": "Método · como os números são feitos"}
col_abas, col_inicio = st.columns([5, 1], vertical_alignment="bottom")
with col_inicio:
    caixa_inicio = st.container(key="botao_inicio_painel")
    caixa_inicio.button("🏠 Início", key="inicio_painel", on_click=definir, args=("aba", "Panorama"),
                        width="stretch", help="Volta à página inicial do Escudo (Panorama).")
with col_abas:
    with st.container(key="abas_painel"):
        aba = seletor(st, "Navegação", "aba", ABAS, horizontal=True, label_visibility="collapsed")
st.markdown(f'<div class="escudo-voce-esta">📍 Você está em: <b>{html.escape(_ONDE.get(aba, aba))}</b>'
            f' · {html.escape(nome_cidade)}</div>', unsafe_allow_html=True)

# ---- A Lia: uma só, no centro, entre a navegação e os dados ----
def desenhar_lia():
    atual = lia_estado["atual"]
    boas_vindas_aberta = not st.session_state.get("lia_fechada")
    recolhida = bool(st.session_state.get("lia_recolhida")) and not boas_vindas_aberta
    if recolhida:  # faixa fina: a Lia continua à vista, mas os dados sobem
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
                boas_vindas = lia_responder(ctx_lia, INICIO)
                st.markdown(f'<div class="lia-nome">Lia <span>· pesquisadora do MISM2</span></div>'
                            f'<div class="lia-fala-grande">{boas_vindas.fala.replace("**", "")}</div>', unsafe_allow_html=True)
                principais = {"mais_aparece", "aumentando", "atencao", "futuro"}
                colunas = st.columns(2)
                for i, (rotulo, acao) in enumerate(a for a in boas_vindas.botoes if a[1].get("id") in principais):
                    colunas[i % 2].button(rotulo, key=f"bv_{i}", on_click=lia_clicar, args=(acao,), width="stretch")
                st.button("Prefiro explorar sozinha", key="bv_fechar",
                          on_click=lambda: st.session_state.update(lia_fechada=True))
            else:
                cab, rec = st.columns([6, 1.4], vertical_alignment="center")
                cab.markdown('<div class="lia-nome">Lia <span>· pesquisadora do MISM2</span></div>', unsafe_allow_html=True)
                rec.button("Recolher a Lia", key="caixa_lia_recolher", on_click=definir, args=("lia_recolhida", True),
                           width="stretch")
                if getattr(atual, "pergunta", None):
                    st.caption(f"Você perguntou: “{atual.pergunta}”")
                st.markdown(atual.fala)
                if getattr(atual, "selo", None):
                    st.caption(atual.selo)
                if getattr(atual, "fonte", None):
                    st.caption(atual.fonte)
                if getattr(atual, "base", None):
                    with st.expander("O que o Escudo calculou (base da resposta)"):
                        st.markdown(atual.base)
                        st.caption("O texto acima foi redigido pela IA a partir disto; os números são os mesmos.")
                for rotulo_link, pagina in getattr(atual, "links", None) or []:
                    try:
                        st.page_link(pagina, label=rotulo_link)
                    except Exception:
                        pass
                if atual.numeros:
                    with st.expander("Os números por trás"):
                        st.markdown("\n".join(f"- {n}" for n in atual.numeros))
                proximos = [(r, a) for r, a in atual.botoes if a is not INICIO and a.get("tipo") != "inicio"]
                colunas = st.columns(4)
                for i, (rotulo, acao) in enumerate(proximos):
                    colunas[i % 4].button(rotulo, key=f"lia_{i}_{rotulo}", on_click=lia_clicar, args=(acao,), width="stretch")
                c_voltar, c_inicio, _resto = st.columns([1, 1.3, 4])
                if lia_estado["pilha"]:
                    c_voltar.button("← Voltar", key="lia_discreto_voltar", on_click=lia_voltar)
                c_inicio.button("Começar de novo", key="lia_discreto_inicio", on_click=lia_clicar, args=(INICIO,))

        # Pergunte à Lia: logo abaixo do balão, numa linha só
        st.markdown("**Pergunte à Lia**")
        with st.form("caixa_form", clear_on_submit=True):
            f1, f2 = st.columns([5, 1.2])
            f1.text_input("Pergunte à Lia", key="caixa_texto", max_chars=300, label_visibility="collapsed",
                          placeholder=f"Pergunte à Lia. Ex.: o câncer de mama está aumentando em {nome_cidade}?")
            f2.form_submit_button("Perguntar", key="caixa_enviar", on_click=enviar_pergunta, width="stretch")
        g1, g2, g3 = st.columns([1.5, 1.3, 1.4], vertical_alignment="bottom")
        with g1:
            st.radio("Linguagem das respostas", ["Técnica", "Simples"], horizontal=True, key="caixa_linguagem")
        with g2:
            with st.expander("Não sabe o que perguntar?"):
                for i, (rotulo, assunto) in enumerate([("Qual câncer mais interna?", "mais_aparece"),
                                                       ("O que a tendência aponta para os próximos anos?", "futuro"),
                                                       ("Onde podemos ter problema?", "atencao"),
                                                       ("Por que os números mudam?", "causa"),
                                                       ("Como a IA funciona?", "sobre_ia")]):
                    st.button(rotulo, key=f"caixa_exemplo_{i}", on_click=lia_clicar,
                              args=(acao_assistente(assunto, pergunta=rotulo),), width="stretch")
        with g3:
            if st.session_state.get("passeio") is None:
                st.button("🧭 Passeio pelo Escudo · 6 paradas", key="pbtn_seguir_comecar", on_click=passeio_ir,
                          args=(0,), width="stretch")
        ia_atual = ia_da_sessao()
        st.caption(("🤖 IA de linguagem (Gemini) ligada. " if ia_atual.ligada else "IA de linguagem desligada. ")
                   + "Os números vêm sempre dos cálculos do Escudo. Não escreva dados pessoais.")
        if st.session_state.get("passeio") is not None:
            desenhar_passeio(st.session_state["passeio"])


desenhar_lia()

# Seletor de município (autor, 22/10/2026: "tem de ficar perto dos dados que ele muda"). Ele é desenhado UMA vez por execução, em
# toda aba (o Streamlit esquece um seletor que deixa de ser desenhado): no começo dos dados, nas abas da cidade; na Rede hospitalar,
# logo acima do bloco da cidade (os gráficos de cima são do Estado e não mudam). O valor é lido do estado da sessão lá no topo.
DICA_CIDADE = ('A cidade escolhida vale para os gráficos marcados com <b>📍</b>; os marcados com <b>🌎</b> são do Estado de SP '
               'e não mudam. Trocar a cidade recomeça a conversa com a Lia.')
DICA_CIDADE_REDE = ('A cidade escolhida muda só o bloco abaixo (<b>📍</b>). Os gráficos de cima são do Estado de SP (<b>🌎</b>) '
                    'e não mudam. Trocar a cidade recomeça a conversa com a Lia.')
_seletor_cidade = {"feito": False}


def desenhar_seletor_cidade(dica):
    _seletor_cidade["feito"] = True
    with st.container(key="seletor_cidade"):
        _c1, _c2 = st.columns([1.3, 3], vertical_alignment="center")
        _c1.selectbox("Município", nomes, index=nomes.index(nome_cidade), key="municipio_painel",
                      help="Digite para procurar entre os municípios de SP.")
        _c2.markdown(f'<div class="escudo-dica" style="margin:0">{dica}</div>', unsafe_allow_html=True)


if aba != "Rede hospitalar":
    desenhar_seletor_cidade(DICA_CIDADE)



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
    st.markdown(NUMEROS_HTML, unsafe_allow_html=True)
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
        evento = st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO,
                                 on_select="rerun", selection_mode="points", key="barras")
    except TypeError:  # Streamlit antigo, sem clique em gráfico
        st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
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
    st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)

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

        # Previsão com validação (aprendizado de máquina simples; inteligencia.prever_com_validacao):
        # 5 modelos testados em anos que já conhecemos, e vale o que errou menos. Não muda o gráfico acima.
        prev = prever_com_validacao(mun)
        if prev:
            with st.expander("Como o Escudo escolheu o modelo de previsão (aprendizado de máquina simples)"):
                pergunta("Qual modelo errou menos ao prever anos que já conhecemos?", "cidade",
                         f"internações por {cancer_de(doenca)} de mulheres de {html.escape(nome_cidade)}")
                tabela_modelos = prev["tabela"].assign(
                    Escolhido=lambda t: t["modelo"].map(lambda m: "✔" if m == prev["modelo"] else ""))
                st.dataframe(
                    tabela_modelos[["descricao", "mae", "vies", "testes", "Escolhido"]].rename(columns={
                        "descricao": "Modelo", "mae": "Erro médio (internações/ano)", "vies": "Viés (negativo: prevê a mais)",
                        "testes": "Previsões testadas"}).round(1),
                    hide_index=True, width="stretch")
                leitura("O que a validação mostra", [f.replace("**", "") for f in leitura_previsao(prev, doenca)])
                st.caption("Cada modelo é ajustado só com os anos anteriores a cada teste e prevê 1, 2 e 3 anos à frente; "
                           "o erro é a média dessas previsões. É projeção de tendência de internações, não previsão de "
                           "casos novos, e não indica causa.")

    # Confiabilidade: a casa dos avisos é aqui, junto da tendência.
    avisos = confiabilidade(serie, doenca, duplicados_municipio(ORIGEM))
    st.markdown(
        '<div class="escudo-info"><b>Confiabilidade desta informação</b><ul>'
        + "".join(f"<li>{'⚠️ ' if nivel == 'atencao' else ''}{texto}</li>" for nivel, texto in avisos)
        + "</ul></div>",
        unsafe_allow_html=True,
    )

    # ---- Quantas internações em um ano, mês a mês? (pedido da Secretaria da Mulher, 20/10/2026) ----
    anos_ip = anos_do_banco()
    if st.session_state.get("ip_ano") not in anos_ip and anos_ip:
        st.session_state["ip_ano"] = anos_ip[-1]
    if st.session_state.get("ip_quem") not in ("moradoras", "hospitais"):
        st.session_state["ip_quem"] = "moradoras"
    if st.session_state.get("ip_cancer") not in [TODOS_CANCERES] + list(codigos):
        st.session_state["ip_cancer"] = TODOS_CANCERES
    st.markdown("---")
    if not anos_ip:
        pergunta("Quantas internações o SIH registrou em cada ano, mês a mês?", "cidade",
                 f"moradoras de {html.escape(nome_cidade)} ou hospitais da cidade, conforme a escolha")
        st.info("Este dado não existe: o painel não conseguiu ler os anos do banco.")
    else:
        col_a, col_q, col_k = st.columns([1, 2, 2])
        with col_a:
            ano_ip = caixa_presa(st, "Ano das internações", "ip_ano", anos_ip)
        with col_q:
            quem_ip = caixa_presa(st, "Quem contar", "ip_quem", ["moradoras", "hospitais"], format_func={
                "moradoras": f"Mulheres que moram em {nome_cidade}",
                "hospitais": f"Internações nos hospitais de {nome_cidade}"}.get)
        with col_k:
            cancer_ip = caixa_presa(st, "Câncer das internações", "ip_cancer", [TODOS_CANCERES] + list(codigos),
                                    format_func=lambda c: NOME_TODOS_CANCERES if c == TODOS_CANCERES else nome_doenca(c))
        pergunta(f"Quantas internações o SIH registrou em {ano_ip}, mês a mês?", "cidade",
                 (f"moradoras de {html.escape(nome_cidade)}" if quem_ip == "moradoras"
                  else f"hospitais de {html.escape(nome_cidade)}") + f" · {ano_ip}")
        info_ip = internacoes_do_ano(ORIGEM, cidade["codigo_ibge"], ano_ip, quem_ip,
                                     None if cancer_ip == TODOS_CANCERES else cancer_ip)
        if info_ip is None or not info_ip["na_fonte"]:
            st.info(" ".join(leitura_internacoes_periodo(info_ip, nome_cidade)[:1]))
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Internações registradas em {ano_ip}", formatar_numero(info_ip["total"]))
            m2.metric("Meses que a fonte tem", f"{len(info_ip['na_fonte'])} de 12")
            m3.metric("Último mês publicado", NOMES_MESES[info_ip["ultimo_mes"] - 1])
            rotulos = [nm[:3] for nm in NOMES_MESES]
            com_dado = [m for m in range(1, 13) if info_ip["meses"][m] is not None]
            fig_ip = go.Figure(go.Bar(x=[rotulos[m - 1] for m in com_dado], y=[info_ip["meses"][m] for m in com_dado],
                                      name="Internações registradas", marker={"color": AZUL, "line": {"width": 0}},
                                      text=[formatar_numero(info_ip["meses"][m]) for m in com_dado],
                                      textposition="outside", cliponaxis=False))
            if info_ip["sem_dado"]:
                fig_ip.add_trace(go.Scatter(
                    x=[rotulos[m - 1] for m in info_ip["sem_dado"]], y=[0] * len(info_ip["sem_dado"]), mode="markers",
                    name="Sem dado na fonte (não é zero)", marker={"symbol": "x", "size": 9, "color": LARANJA},
                    hovertemplate="%{x}: a fonte não tem este mês<extra></extra>"))
            fig_ip.update_xaxes(categoryorder="array", categoryarray=rotulos)
            fig_ip.update_yaxes(rangemode="tozero")
            estilizar(fig_ip, altura=300)
            st.plotly_chart(fig_ip, width="stretch", theme=None, config=CONFIG_GRAFICO)
            if cancer_ip == TODOS_CANCERES and info_ip["por_cancer"]:
                st.dataframe(pd.DataFrame(sorted(((nome_doenca(c), n) for c, n in info_ip["por_cancer"].items()),
                                                 key=lambda x: -x[1]), columns=["Câncer", "Internações registradas"]),
                             hide_index=True, width="stretch")
            leitura("O que o gráfico mostra", leitura_internacoes_periodo(info_ip, nome_cidade))


# ============================================================
# INVESTIGAR — o que merece ser pesquisado?
# ============================================================

if aba == "Rede hospitalar":
    # Divisão da aba Investigar (20/10/2026, "o dashboard tem de ser legível, não um quebra-cabeça"): tudo o que é fluxo
    # de pacientes e hospitais mora aqui (quase tudo é do Estado, selo roxo); as perguntas da cidade escolhida ficam em Investigar.
    st.markdown('<div class="escudo-dica"><b>Nesta aba:</b> onde as mulheres são atendidas. Primeiro, as mulheres de '
                'outros estados atendidas em São Paulo e os hospitais (todo o Estado, selo roxo); no fim, a sua cidade '
                '(selo azul). Os hospitais habilitados em oncologia mostram onde há rede; habilitação não é vaga.</div>',
                unsafe_allow_html=True)
    # ---- fluxo: mulheres de outros estados atendidas em SP (pedido do autor, 10/2026) ----
    pergunta("De onde vêm as mulheres de outros estados atendidas em São Paulo?", "estado",
             f"todas as cidades de SP, 7 cânceres somados, {ano_ini}–{ano_fim} · não muda quando você troca de cidade")
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
        hosp_df = hospitais_habilitados()
        hosp_pontos = hosp_df[hosp_df["no_mapa"]] if len(hosp_df) else hosp_df
        ver_hospitais = False
        if len(hosp_pontos):
            ver_hospitais = chave_liga(st, "Mostrar também onde ficam os hospitais habilitados em oncologia", "ver_hospitais",
                                       help="Pontos pequenos coloridos pelo tipo (UNACON, CACON...). Lista do Ministério da Saúde, habilitação 2023; "
                                            "a posição vem do cadastro do CNES e só entra quem passou nas conferências.")
        else:
            st.caption("Os hospitais habilitados em oncologia ainda não têm posição neste computador "
                       "(py etl\\gerar_hospitais_oncologia_geo.py); por isso não aparecem no mapa.")
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
            if ver_hospitais:
                for tipo_h in hosp_onco.ORDEM_TIPOS:
                    q = hosp_pontos[hosp_pontos["tipo"].astype(str) == tipo_h]
                    if q.empty:
                        continue
                    fig.add_trace(go.Scatter(
                        x=q["lon"], y=q["lat"], mode="markers", name=tipo_h, showlegend=True,
                        marker={"size": 7, "color": hosp_onco.TIPOS[tipo_h][0], "line": {"width": 1, "color": "#ffffff"}},
                        hovertext=[f"{n} · {m} ({u}) · {tipo_h}" for n, m, u in zip(q["nome"], q["municipio"], q["uf"])],
                        hoverinfo="text"))
            fig.add_trace(go.Scatter(
                x=[CENTROS_UF["SP"][1]], y=[CENTROS_UF["SP"][0]], mode="markers+text", text=["SP"],
                textposition="bottom center", textfont={"size": 10, "color": "#c0392b"},
                marker={"size": 14, "color": "#c0392b", "symbol": "diamond", "line": {"width": 1, "color": "#ffffff"}},
                hovertext=["Estado de São Paulo (onde estão os hospitais)"], hoverinfo="text", showlegend=False))
            fig.update_xaxes(visible=False, range=[-76, -32])
            fig.update_yaxes(visible=False, range=[-35, 6], scaleanchor="x", scaleratio=1)
            estilizar(fig, altura=560)
            fig.update_layout(showlegend=ver_hospitais, margin={"l": 0, "r": 0, "t": 10, "b": 0},
                              legend={"orientation": "h", "x": 0, "y": 0.02, "bgcolor": "rgba(255,255,255,0.7)"})
            st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
            topo = pontos.iloc[0]
            frases = [f"{topo['estado']} é o estado com mais internações de mulheres de fora "
                      f"({formatar_numero(topo['internacoes'])}, {formatar_numero(topo['pct'], 1)}% das de fora); "
                      f"ao todo são {formatar_numero(len(pontos))} estados de origem.",
                      "O losango vermelho marca o Estado de São Paulo, onde ficam os hospitais."]
            if sem_posicao:
                frases.append(f"{formatar_numero(sem_posicao)} internações vêm de residência sem posição no mapa "
                              "e não aparecem nas bolhas.")
            if ver_hospitais:
                n_h, n_sp_h = len(hosp_pontos), int((hosp_pontos["uf"] == "SP").sum())
                frases.append(f"Os pontos pequenos são {formatar_numero(n_h)} hospitais habilitados em oncologia pelo Ministério da Saúde "
                              f"(lista de 2023): {formatar_numero(n_sp_h)} em SP e {formatar_numero(n_h - n_sp_h)} em outros estados. "
                              "O mapa mostra de onde elas vêm e onde ficam os hospitais; não explica por que vêm. "
                              "Habilitado não quer dizer vaga: o acesso é pela regulação.")
            leitura("O que o mapa mostra", frases)
            try:
                st.page_link("pages/hospitais_cancer.py", label="🗺️ Ver o mapa dos hospitais com mais detalhes (nome, telefone, os mais próximos da sua cidade)")
            except Exception:  # Streamlit antigo, sem page_link
                pass

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
        st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
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
            st.dataframe(tabela_h, width="stretch", hide_index=True)
        leitura("O que a tabela mostra", leitura_hospitais(fluxo, hosp))

        # Ficha de um hospital (área do gestor e do pesquisador). O título sai depois dos controles porque mostra o período escolhido.
        def guardar_hospital(chave, rotulos, cnes_lista):
            """Guarda o hospital pelo CNES: a escolha continua quando o câncer ou os anos mudam (se ele ainda tiver internações)."""
            try:
                st.session_state["hospital_cnes"] = cnes_lista[rotulos.index(st.session_state[chave])]
            except (KeyError, ValueError):
                pass

        def abrir_tabela_do_hospital(cnes, nome_cancer, periodo):
            """Atalho da ficha: filtra a tabela completa do fluxo ("Quem vem de fora...") para este hospital, este câncer e estes anos."""
            todas_t, fluxo_t = None, fluxo_geral()
            try:
                todas_t = tabela_fluxo(fluxo_t) if fluxo_t is not None else None
            except Exception:
                todas_t = None
            st.session_state["fluxo_tab_busca"] = cnes
            st.session_state["fluxo_tab_estado"] = []
            st.session_state["fluxo_tab_cancer"] = ([nome_cancer] if nome_cancer and todas_t is not None
                                                   and nome_cancer in set(todas_t["cancer"]) else [])
            anos_t_ = sorted(int(a) for a in todas_t["ano"].unique()) if todas_t is not None else []
            dentro = [a for a in anos_t_ if periodo and periodo[0] <= a <= periodo[1]]
            if len(anos_t_) > 1 and dentro:
                st.session_state["fluxo_tab_anos"] = (dentro[0], dentro[-1])
            else:
                st.session_state.pop("fluxo_tab_anos", None)

        cabecalho_hospital = st.container()
        dados_h = hospitais_dados()
        if dados_h is None:
            with cabecalho_hospital:
                pergunta("Como é o atendimento em um hospital específico?", "estado",
                         f"um hospital por vez, todas as pacientes do hospital (de qualquer lugar), {ano_ini}–{ano_fim}")
            st.info("O banco ainda não guarda o CNES e a residência de cada internação. Rode a carga de novo "
                    "(py etl\\carga_todas_bases.py) para consultar um hospital.")
        else:
            codigos_h = sorted(dados_h["base"]["tipo_cancer"].unique(), key=nome_doenca)
            nomes_h = ["Todos os cânceres"] + [nome_doenca(c) for c in codigos_h]
            anos_h_todos = sorted(int(a) for a in dados_h["base"]["ano"].unique())
            col_c, col_h = st.columns([1, 2])
            nome_c = col_c.selectbox("Câncer", nomes_h, index=0, key="hospital_cancer",
                                     help="Limita a lista, os números, o gráfico e a referência do Estado a um câncer.")
            cancer_h = None if nome_c == nomes_h[0] else codigos_h[nomes_h.index(nome_c) - 1]
            col_anos, _vazio = st.columns([3, 2])
            if len(anos_h_todos) > 1:
                faixa_h = col_anos.select_slider(
                    "Anos", options=anos_h_todos, value=(anos_h_todos[0], anos_h_todos[-1]), key="hospital_anos",
                    help="Limita a lista de hospitais, os números, o gráfico, os estados de origem e a referência do Estado ao período.")
            else:
                faixa_h = (anos_h_todos[0], anos_h_todos[0])
                col_anos.caption(f"Só há dados de {anos_h_todos[0]}.")
            periodo_h = None if faixa_h == (anos_h_todos[0], anos_h_todos[-1]) else faixa_h
            with cabecalho_hospital:
                pergunta("Como é o atendimento em um hospital específico?", "estado",
                         f"um hospital por vez, todas as pacientes do hospital (de qualquer lugar), {faixa_h[0]}–{faixa_h[1]}")
            todos_h = lista_hospitais(dados_h, cancer_h, periodo_h)
            if todos_h.empty:
                st.info("Nenhum hospital registrou internações com estes filtros (câncer e anos). Amplie o período.")
            else:
                rotulos = [f"{h.hospital} · {h.municipio} ({formatar_numero(h.internacoes)} internações)"
                           for h in todos_h.itertuples()]
                cnes_lista = list(todos_h["cnes"])
                guardado = st.session_state.get("hospital_cnes")
                chave_sel = f"hospital_perfil_{cancer_h or 'todos'}" + (f"_{faixa_h[0]}_{faixa_h[1]}" if periodo_h else "")
                escolhido = col_h.selectbox("Escolha um hospital (pode digitar o nome)", rotulos,
                                            index=cnes_lista.index(guardado) if guardado in cnes_lista else 0,
                                            key=chave_sel, on_change=guardar_hospital, args=(chave_sel, rotulos, cnes_lista),
                                            help="Do que mais interna para o que menos, no câncer e nos anos escolhidos. A escolha "
                                                 "continua se você mudar o câncer ou os anos e o hospital ainda tiver internações.")
                ficha = ficha_hospital(dados_h, cnes_lista[rotulos.index(escolhido)], cancer_h, periodo_h)
                st.caption(f"CNES {ficha['cnes']} · {ficha['municipio']}")
                assunto_h = nome_doenca(cancer_h).lower() if cancer_h else "7 cânceres somados"
                h1, h2, h3, h4 = st.columns(4)
                h1.metric("Internações", formatar_numero(ficha["internacoes"]))
                h2.metric("De outros estados", f"{formatar_numero(ficha['pct_fora'], 1)}%",
                          help=f"{formatar_numero(ficha['procedencia']['fora'])} internações de mulheres que moram em outros estados")
                h3.metric("Urgência", "—" if ficha["pct_urgencia"] is None else f"{formatar_numero(ficha['pct_urgencia'], 1)}%",
                          help="Parcela das internações em que o caráter foi informado como urgência. "
                               + ("" if ficha["estado"]["pct_urgencia"] is None
                                  else f"No Estado: {formatar_numero(ficha['estado']['pct_urgencia'], 1)}%."))
                h4.metric("Permanência média", f"{formatar_numero(ficha['permanencia'], 1)} dias",
                          help=f"No Estado: {formatar_numero(ficha['estado']['permanencia'], 1)} dias")
                pergunta(f"Quantas internações {ficha['hospital']} registrou em cada ano?", "estado",
                         f"este hospital, {assunto_h} · anos com meses ausentes na fonte na escala de 12 meses")
                anos_h = ficha["por_ano"]
                fig = go.Figure()
                for coluna, nome_barra, cor in (("cidade", f"Moradoras de {ficha['municipio']}", CINZA),
                                                ("outra_cidade", "Outras cidades de SP", "#8db8ec"),
                                                ("fora", "Outros estados", AZUL)):
                    fig.add_trace(go.Bar(
                        x=anos_h["ano"], y=anos_h[coluna], name=nome_barra, marker_color=cor,
                        customdata=anos_h[["registrado", "meses"]].fillna(12).values,
                        hovertemplate=nome_barra + " em %{x}: %{y:.0f} (escala de 12 meses)"
                                      "<br>registrado: %{customdata[0]:.0f} internações em %{customdata[1]:.0f} meses"
                                      "<extra></extra>"))
                sem_registro = anos_h[anos_h["registrado"] == 0]
                if len(sem_registro):  # ano vazio não pode parecer "dado que sumiu": o x marca e o mouse explica
                    fig.add_trace(go.Scatter(
                        x=sem_registro["ano"], y=[0] * len(sem_registro), mode="markers", cliponaxis=False,
                        name="Sem internação registrada", marker={"symbol": "x", "size": 9, "color": LARANJA},
                        customdata=sem_registro[["meses"]].fillna(12).values,
                        hovertemplate="%{x}: nenhuma internação registrada neste hospital "
                                      "(a fonte oferece %{customdata[0]:.0f} de 12 meses)<extra></extra>"))
                fig.update_layout(barmode="stack", legend={"orientation": "h", "y": -0.2})
                fig.update_xaxes(dtick=1)
                estilizar(fig, altura=340)
                fig.update_layout(showlegend=True)
                st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
                tabela_anos = anos_h.rename(columns={
                    "ano": "Ano", "meses": "Meses que a fonte oferece", "registrado": "Internações registradas",
                    "ajustado": "Internações (escala de 12 meses)", "cidade": f"Moradoras de {ficha['municipio']} (escala de 12 meses)",
                    "outra_cidade": "Outras cidades de SP (escala de 12 meses)", "fora": "Outros estados (escala de 12 meses)"})
                tabela_anos.insert(0, "Câncer", assunto_h)
                tabela_anos.insert(0, "Hospital", ficha["hospital"])
                tabela_anos.insert(0, "CNES", ficha["cnes"])
                st.download_button("Baixar os números por ano (CSV)",
                                   tabela_anos.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                                   file_name=f"escudo_hospital_{ficha['cnes']}_por_ano.csv", mime="text/csv",
                                   key="hospital_baixar_anos")
                leitura("O que o gráfico mostra", leitura_hospital_anos(ficha))
                if len(sem_registro):
                    with st.expander("Por que alguns anos ficam sem barra?"):
                        st.markdown(
                            "Um **x** no gráfico marca um ano em que este hospital não tem nenhuma internação "
                            "registrada na base do SIH/SUS, a fonte oficial das internações. **O banco não guarda o "
                            "motivo**, e o Escudo não chuta um. O que dá para dizer com segurança é o seguinte.")
                        st.markdown(
                            "Primeiro, o DATASUS não oferece todos os meses de todos os anos. Quando o ano tem menos "
                            "de 12 meses na fonte, o hospital pode ficar sem registro naquele ano; passe o mouse sobre "
                            "o x para ver quantos meses a fonte tem. Segundo, ausência no SIH não é ausência de "
                            "atendimento: o hospital pode ter atendido pelo ambulatório, por convênio ou de forma "
                            "particular, ou ter registrado as internações sob outro número de CNES. Terceiro, um "
                            "hospital com poucos casos por ano pode simplesmente não ter internado esse câncer em "
                            "certo ano. Para saber o que houve em um hospital específico, é preciso conferir com o "
                            "próprio hospital ou no cadastro do CNES.")

                # De quais estados vêm as mulheres de fora deste hospital (autor, 22/10/2026: ficha mais completa para gestor e pesquisador)
                pergunta(f"De quais estados vêm as mulheres de fora de {ficha['hospital']}?", "estado",
                         f"este hospital, {assunto_h}, só mulheres que moram em outros estados · {faixa_h[0]}–{faixa_h[1]}")
                if not ficha["ufs"]:
                    st.info("Nenhuma internação de mulher de outro estado neste hospital, com estes filtros.")
                else:
                    principais_e, resto_e, n_resto_e = agrupar_estados(ficha["ufs"])
                    total_e = sum(n for _, n in ficha["ufs"])
                    rotulos_e = [nome for nome, _ in principais_e]
                    valores_e = [n for _, n in principais_e]
                    cores_e = [AZUL] * len(principais_e)
                    if resto_e:
                        rotulos_e.append(f"Outros {formatar_numero(n_resto_e)} {'estado' if n_resto_e == 1 else 'estados'}")
                        valores_e.append(resto_e)
                        cores_e.append(CINZA)
                    figura_e = go.Figure(go.Bar(
                        x=valores_e[::-1], y=rotulos_e[::-1], orientation="h",
                        text=[f"{formatar_numero(v)} · {formatar_numero(100 * v / total_e, 1)}%" for v in valores_e[::-1]],
                        textposition="outside", cliponaxis=False, marker={"color": cores_e[::-1], "line": {"width": 0}},
                        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>", showlegend=False))
                    figura_e.update_xaxes(visible=False, range=[0, max(valores_e) * 1.28])
                    figura_e.update_yaxes(showgrid=False)
                    estilizar(figura_e, altura=70 + 38 * len(rotulos_e))
                    figura_e.update_layout(bargap=0.3, showlegend=False)
                    st.plotly_chart(figura_e, width="stretch", theme=None, config=CONFIG_GRAFICO, key="hospital_estados")
                leitura("O que o gráfico mostra", leitura_estados_do_hospital(ficha))
                if ficha["ufs"]:
                    st.button("Ver estas internações na tabela completa (mais abaixo)", key="hospital_ver_na_tabela",
                              on_click=abrir_tabela_do_hospital, args=(ficha["cnes"], nome_c if cancer_h else None, periodo_h),
                              help="Filtra a tabela \"Quem vem de fora, de qual câncer e para qual hospital?\" para este hospital, "
                                   "este câncer e estes anos.")
                    if st.session_state.get("fluxo_tab_busca") == ficha["cnes"]:
                        st.caption("A tabela completa mais abaixo (\"Quem vem de fora, de qual câncer e para qual hospital?\") "
                                   "está filtrada para este hospital. Para voltar a ver tudo, limpe a busca dela.")

                if cancer_h is None:  # com um câncer escolhido, a tabela teria uma linha só
                    st.dataframe(pd.DataFrame({
                        "Câncer": ficha["cancer"]["doenca"],
                        "Internações": [formatar_numero(v) for v in ficha["cancer"]["internacoes"]],
                        "Parcela": [f"{formatar_numero(v, 1)}%" for v in ficha["cancer"]["pct"]],
                    }), width="stretch", hide_index=True)
                leitura("O que a ficha mostra", leitura_hospital(ficha))


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
        st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
        leitura("O que o gráfico mostra", leitura_evolucao_fluxo(e_fluxo))

        pergunta("Quem vem de fora, de qual câncer e para qual hospital? Pesquise tudo", "estado",
                 f"todas as internações de mulheres de outros estados em hospitais de SP, {ano_ini}–{ano_fim} · "
                 "uma linha por câncer, estado de origem e hospital")
        st.markdown('<div class="escudo-dica">Digite um nome na busca (hospital, cidade, estado ou câncer) ou use os '
                    'filtros. Clique no título de uma coluna para ordenar. "De fora" = mulher que mora em outro '
                    'estado. Cada linha soma as internações daquele câncer, daquele estado de origem, naquele '
                    'hospital; some as linhas para ter um total.</div>', unsafe_allow_html=True)
        todas = tabela_fluxo(fluxo)
        anos_t = sorted(todas["ano"].unique())
        t1, t2 = st.columns(2)
        sel_cancer = t1.multiselect("Câncer", sorted(todas["cancer"].unique()), key="fluxo_tab_cancer",
                                    placeholder="Todos os cânceres")
        sel_estado = t2.multiselect("Estado de origem", sorted(todas["estado"].unique()), key="fluxo_tab_estado",
                                    placeholder="Todos os estados")
        t3, t4 = st.columns([3, 2])
        if len(anos_t) > 1:
            faixa_anos = t3.select_slider("Anos", options=anos_t, value=(anos_t[0], anos_t[-1]),
                                          key="fluxo_tab_anos")
        else:
            faixa_anos = (anos_t[0], anos_t[0])
            t3.caption(f"Só há dados de {anos_t[0]}.")
        busca_t = t4.text_input("Pesquisar", key="fluxo_tab_busca",
                                placeholder="ex.: Barretos, Minas Gerais, mama")
        separar_ano = st.toggle("Mostrar um ano por linha", value=False, key="fluxo_tab_por_ano",
                                help="Desligado, cada linha soma os anos escolhidos. Ligado, cada ano vira uma linha.")
        filtrada = filtrar_tabela_fluxo(todas, sel_cancer, sel_estado, faixa_anos, busca_t)
        agrupada = agrupar_tabela_fluxo(filtrada, por_ano=separar_ano)
        if agrupada.empty:
            st.info("Nenhuma internação de fora com esses filtros.")
        else:
            st.dataframe(
                agrupada.rename(columns={"cancer": "Câncer", "ano": "Ano", "estado": "Estado de origem",
                                         "hospital": "Hospital", "municipio": "Município do hospital",
                                         "internacoes": "Internações", "obitos": "Óbitos",
                                         "dias_leito": "Dias de leito"}),
                width="stretch", hide_index=True,
                column_config={"Ano": st.column_config.NumberColumn(format="%d"),
                               "Internações": st.column_config.NumberColumn(format="%d"),
                               "Óbitos": st.column_config.NumberColumn(format="%d"),
                               "Dias de leito": st.column_config.NumberColumn(format="%d")})
            st.download_button(
                "Baixar esta tabela (CSV)",
                agrupada.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name="escudo_fluxo_mulheres_de_fora.csv", mime="text/csv", key="fluxo_tab_baixar")
        filtros_ativos = bool(sel_cancer or sel_estado or busca_t.strip() or faixa_anos != (anos_t[0], anos_t[-1]))
        leitura("O que a tabela mostra",
                leitura_tabela_fluxo(filtrada, parcela_fora_por_cancer(fluxo, faixa_anos), filtros_ativos))

        desenhar_seletor_cidade(DICA_CIDADE_REDE)
        pergunta(f"Quem é atendida nos hospitais de {nome_cidade}, e para onde vão as moradoras?", "cidade",
                 f"só hospitais de {html.escape(nome_cidade)} e só moradoras de {html.escape(nome_cidade)}, "
                 "7 cânceres somados")
        info_cidade = fluxo_cidade(ORIGEM, cidade["codigo_ibge"])
        if info_cidade is None:
            st.info("Sem o município do hospital no banco não dá para ver o fluxo da cidade.")
        else:
            VISOES = ["Moradoras atendidas em cidades de fora", "Mulheres de fora da cidade atendidas na cidade"]
            visao = seletor(st, "O que você quer ver?", "fluxo_visao", VISOES, horizontal=True)
            atend, morad = info_cidade["atendimentos"], info_cidade["moradoras"]

            def parte(valor, todo):
                return f"{formatar_numero(100 * valor / todo, 1)}%" if todo else "—"

            if visao == VISOES[0]:
                st.markdown(f"**Quando as mulheres que moram em {html.escape(nome_cidade)} são atendidas em hospitais de outras cidades**")
                sem_h = info_cidade.get("moradoras_sem_hospital", 0)
                if not morad:
                    st.warning(f"**Este dado não existe para {nome_cidade}.** "
                               + (f"Há {formatar_numero(sem_h)} internações de moradoras no banco, mas nenhuma traz o município do hospital."
                                  if sem_h else "O banco não tem internações de moradoras da cidade."))
                else:
                    d0, d1, d2 = st.columns(3)
                    d0.metric("Internações de moradoras", formatar_numero(morad))
                    d1.metric("Na própria cidade", formatar_numero(info_cidade["moradoras_na_cidade"]),
                              help=f"{parte(info_cidade['moradoras_na_cidade'], morad)} das internações das moradoras")
                    d2.metric("Em outras cidades de SP", formatar_numero(info_cidade["moradoras_fora"]),
                              help=f"{parte(info_cidade['moradoras_fora'], morad)} das internações das moradoras")
                    if sem_h:
                        st.caption(f"Outras {formatar_numero(sem_h)} internações de moradoras ficaram fora desta conta por não "
                                   "trazerem o município do hospital.")
                    if info_cidade["destinos"]:
                        st.dataframe(pd.DataFrame({
                            "Cidade do hospital": [nome for nome, _ in info_cidade["destinos"]],
                            "Internações": [n for _, n in info_cidade["destinos"]],
                            "% das moradoras": [parte(n, morad) for _, n in info_cidade["destinos"]],
                        }), width="stretch", hide_index=True)
                    else:
                        st.info(f"Nenhuma moradora de {nome_cidade} foi atendida em hospital de outra cidade de SP.")
                leitura("O que mostra", leitura_cidade_visao(info_cidade, nome_cidade, "fora"))
            else:
                st.markdown(f"**Quando mulheres de fora são atendidas em hospitais de {html.escape(nome_cidade)}**")
                e0, e1, e2, e3 = st.columns(4)
                e0.metric("Internações nos hospitais", formatar_numero(atend))
                e1.metric(f"Moradoras de {nome_cidade}", formatar_numero(info_cidade["da_cidade"]),
                          help=f"{parte(info_cidade['da_cidade'], atend)} das internações nos hospitais da cidade")
                e2.metric("De outras cidades de SP", formatar_numero(info_cidade["outras_cidades"]),
                          help=f"{parte(info_cidade['outras_cidades'], atend)} das internações nos hospitais da cidade")
                e3.metric("De outros estados", formatar_numero(info_cidade["outros_estados"]),
                          help=f"{parte(info_cidade['outros_estados'], atend)} das internações nos hospitais da cidade")
                origens_cidade = info_cidade.get("origens") or []
                if origens_cidade and info_cidade["outras_cidades"]:
                    # De quais cidades de SP vêm as mulheres de fora (pedido do autor, 22/10/2026). Cidades com poucos
                    # casos viram uma barra só; as barras somam o número "De outras cidades de SP" acima.
                    principais, resto_n, resto_c = agrupar_origens(origens_cidade)
                    total_o = info_cidade["outras_cidades"]
                    centro_o, pontos_o, sem_pos_o = pontos_origens(principais, localizacao_dos_municipios(), nome_cidade)
                    tem_mapa = centro_o is not None and not pontos_o.empty
                    st.markdown("**De quais cidades de SP vêm as mulheres de fora?**")
                    forma = "Barras"
                    if tem_mapa:
                        forma = seletor(st, "Ver como", "fluxo_origens_forma", ["Mapa", "Barras"], horizontal=True)
                    nomes_principais = {nome for nome, _ in principais}
                    resto_max = max([o["internacoes"] for o in origens_cidade if o["nome"] not in nomes_principais] or [0])
                    juntas = ""
                    if resto_n:
                        unidade = "internação" if resto_max == 1 else "internações"
                        if resto_c == 1:
                            juntas = (f" A outra cidade ({formatar_numero(resto_max)} {unidade}) aparece à parte nas barras e "
                                      "não entra no mapa." if tem_mapa else
                                      f" A outra cidade ({formatar_numero(resto_max)} {unidade}) aparece à parte.")
                        else:
                            juntas = (f" As {formatar_numero(resto_c)} cidades menores (até {formatar_numero(resto_max)} {unidade} "
                                      "cada) aparecem juntas" + (" nas barras e não entram no mapa." if tem_mapa else "."))
                    if forma == "Mapa":
                        st.markdown(f'<div class="escudo-dica">Cada círculo fica no <b>centro da cidade</b> onde a mulher mora '
                                    f'(não é o endereço de ninguém); o tamanho é o número de internações nos hospitais de '
                                    f'{html.escape(nome_cidade)}, {ano_ini}–{ano_fim}, 7 cânceres somados. O losango vermelho '
                                    f'marca {html.escape(nome_cidade)}.{juntas}</div>', unsafe_allow_html=True)
                        lat0, lon0 = centro_o
                        maior_o = float(pontos_o["internacoes"].max())
                        fig_m = go.Figure()
                        linhas_x, linhas_y = [], []
                        for lat_p, lon_p in zip(pontos_o["latitude"], pontos_o["longitude"]):
                            linhas_x += [lon_p, lon0, None]
                            linhas_y += [lat_p, lat0, None]
                        fig_m.add_trace(go.Scatter(x=linhas_x, y=linhas_y, mode="lines", hoverinfo="skip", showlegend=False,
                                                   line={"width": 1.2, "color": "rgba(42,120,214,0.35)"}))
                        def lado_do_nome(lat_p, lon_p):  # o nome fica do lado de fora do círculo, longe da cidade dos hospitais
                            if abs(lat_p - lat0) < 0.04:
                                return "middle right" if lon_p > lon0 else "middle left"
                            return "top center" if lat_p > lat0 else "bottom center"
                        fig_m.add_trace(go.Scatter(
                            x=pontos_o["longitude"], y=pontos_o["latitude"], mode="markers+text",
                            text=[f"{n} · {formatar_numero(v)}" for n, v in zip(pontos_o["nome"], pontos_o["internacoes"])],
                            textposition=[lado_do_nome(a, b) for a, b in zip(pontos_o["latitude"], pontos_o["longitude"])],
                            textfont={"size": 11, "color": TINTA},
                            marker={"size": 14 + 46 * (pontos_o["internacoes"] / maior_o) ** 0.5, "color": AZUL, "opacity": 0.82,
                                    "line": {"width": 1, "color": "#ffffff"}},
                            hovertext=[f"{n}: {formatar_numero(v)} internações ({formatar_numero(100 * v / total_o, 1)}% das de outras cidades de SP)"
                                       for n, v in zip(pontos_o["nome"], pontos_o["internacoes"])],
                            hoverinfo="text", showlegend=False))
                        fig_m.add_trace(go.Scatter(
                            x=[lon0], y=[lat0], mode="markers+text", text=[f"<b>{html.escape(nome_cidade)}</b>"],
                            textposition="top right", textfont={"size": 12, "color": "#c0392b"},
                            marker={"size": 16, "color": "#c0392b", "symbol": "diamond", "line": {"width": 1, "color": "#ffffff"}},
                            hovertext=[f"{nome_cidade}: onde ficam os hospitais"], hoverinfo="text", showlegend=False))
                        lons_m = list(pontos_o["longitude"]) + [lon0]
                        lats_m = list(pontos_o["latitude"]) + [lat0]
                        folga = max(0.1, 0.22 * max(max(lons_m) - min(lons_m), max(lats_m) - min(lats_m)))
                        fig_m.update_xaxes(visible=False, range=[min(lons_m) - folga, max(lons_m) + folga])
                        fig_m.update_yaxes(visible=False, range=[min(lats_m) - folga, max(lats_m) + folga], scaleanchor="x",
                                           scaleratio=1 / math.cos(math.radians(lat0)))
                        estilizar(fig_m, altura=520)
                        fig_m.update_layout(showlegend=False, margin={"l": 0, "r": 0, "t": 10, "b": 0})
                        st.plotly_chart(fig_m, width="stretch", theme=None, config=CONFIG_GRAFICO, key="fluxo_origens_mapa")
                        if sem_pos_o:
                            st.caption(f"{formatar_numero(sem_pos_o)} internações vêm de cidades sem posição na tabela e não "
                                       "aparecem no mapa.")
                    else:
                        st.markdown(f'<div class="escudo-dica">Cidade onde a mulher mora, nas internações dos hospitais de '
                                    f'{html.escape(nome_cidade)}, {ano_ini}–{ano_fim}, 7 cânceres somados.{juntas}</div>',
                                    unsafe_allow_html=True)
                        rotulos_b = [nome for nome, _ in principais]
                        valores_b = [n for _, n in principais]
                        cores_b = [AZUL] * len(principais)
                        if resto_n:
                            rotulos_b.append(f"Outras {formatar_numero(resto_c)} {'cidade' if resto_c == 1 else 'cidades'} "
                                             f"(até {formatar_numero(resto_max)} cada)")
                            valores_b.append(resto_n)
                            cores_b.append(CINZA)
                        figura_o = go.Figure(go.Bar(
                            x=valores_b[::-1], y=rotulos_b[::-1], orientation="h",
                            text=[f"{formatar_numero(v)} · {formatar_numero(100 * v / total_o, 1)}%" for v in valores_b[::-1]],
                            textposition="outside", cliponaxis=False,
                            marker={"color": cores_b[::-1], "line": {"width": 0}},
                            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>", showlegend=False))
                        figura_o.update_xaxes(visible=False, range=[0, max(valores_b) * 1.28])
                        figura_o.update_yaxes(showgrid=False)
                        estilizar(figura_o, altura=70 + 38 * len(rotulos_b))
                        figura_o.update_layout(bargap=0.3, showlegend=False)
                        st.plotly_chart(figura_o, width="stretch", theme=None, config=CONFIG_GRAFICO, key="fluxo_origens")
                leitura("O que mostra", leitura_cidade_visao(info_cidade, nome_cidade, "aqui"))
        st.markdown("---")


if aba == "Rede hospitalar" and not _seletor_cidade["feito"]:
    desenhar_seletor_cidade(DICA_CIDADE_REDE)


# ============================================================
# INVESTIGAR — perguntas sobre a cidade escolhida (câncer que cresce, idade, comparação)
# ============================================================

if aba == "Investigar":
    st.markdown(f'<div class="escudo-dica"><b>Nesta aba:</b> perguntas sobre {html.escape(nome_cidade)}, a cidade '
                'escolhida no topo: qual câncer cresce mais, se a idade mudou e como a cidade se compara com outra. '
                'Tudo aqui conta internações de moradoras.</div>', unsafe_allow_html=True)
    pergunta("Qual câncer cresce mais rápido, e quando foi o ponto mais alto?", "cidade",
             f"moradoras de {html.escape(nome_cidade)}, {ano_ini}–{ano_fim}")
    st.markdown('<div class="escudo-dica">Do que mais cresce para o que menos cresce. Uma linha por câncer.</div>',
                unsafe_allow_html=True)
    aparece = quando_aparece(serie)
    st.dataframe(tabela_aparece_para_tela(aparece, ano_ini), width="stretch", hide_index=True)
    leitura("O que a tabela mostra", leitura_aparece(aparece, anos_incompletos(serie), ano_fim, ano_ini))

    # Cidade e câncer deste gráfico (pedido da Secretaria da Mulher): começam iguais aos do topo, mas se escolhem aqui.
    seguir_o_topo("faixas_origem", "faixas_origem_topo", ORIGEM)
    nomes_por_origem = {m["origem"]: m["nome"] for m in lista_municipios}
    st.markdown('<div class="escudo-dica">Escolha a cidade e o câncer deste gráfico. Eles começam iguais aos do topo '
                'da página, mas valem só aqui.</div>', unsafe_allow_html=True)
    col_c, col_d = st.columns(2)
    with col_c:
        origem_faixas = caixa_presa(st, "Cidade (onde as mulheres moram)", "faixas_origem",
                                    list(nomes_por_origem), format_func=nomes_por_origem.get)
    faixas = faixas_municipio(origem_faixas)
    nome_faixas = nomes_por_origem[origem_faixas]
    existentes = [c for c in codigos if c in set(faixas["tipo_cancer"])] + sorted(
        c for c in set(faixas["tipo_cancer"]) - set(codigos))
    opcoes_cancer = ([TODOS_CANCERES] if existentes else []) + existentes
    seguir_o_topo("faixas_cancer", "faixas_cancer_topo", doenca)
    if st.session_state["faixas_cancer"] not in opcoes_cancer and opcoes_cancer:
        st.session_state["faixas_cancer"] = opcoes_cancer[0]
    with col_d:
        if opcoes_cancer:
            cancer_faixas = caixa_presa(
                st, "Câncer deste gráfico", "faixas_cancer", opcoes_cancer,
                format_func=lambda c: NOME_TODOS_CANCERES if c == TODOS_CANCERES else nome_doenca(c))
        else:
            cancer_faixas = None
    if cancer_faixas is None:
        pergunta("A idade das mulheres internadas por câncer mudou?", "cidade",
                 f"moradoras de {html.escape(nome_faixas)}", cidade=nome_faixas)
        st.info(f"Este dado não existe para {nome_faixas}: não há internação com idade registrada para os cânceres "
                "acompanhados.")
    else:
        sujeito = "pelos cânceres acompanhados" if cancer_faixas == TODOS_CANCERES else f"por {cancer_de(cancer_faixas)}"
        pergunta(f"A idade das mulheres internadas {sujeito} mudou?", "cidade",
                 f"moradoras de {html.escape(nome_faixas)}", cidade=nome_faixas)
        tabela_faixas, periodos = comparar_faixas(faixas, cancer_faixas)
        if periodos is None:
            st.info(f"Este dado não existe para {nome_faixas}: não há idade registrada para "
                    f"{NOME_TODOS_CANCERES.lower() if cancer_faixas == TODOS_CANCERES else cancer_de(cancer_faixas)} "
                    "nesta cidade. Isso não significa zero internações: o banco não tem o registro.")
        else:
            totais = totais_faixas(tabela_faixas)
            fig = go.Figure()
            for periodo, cor in zip(periodos, [CINZA, AZUL]):
                parte = tabela_faixas[tabela_faixas["periodo"] == periodo]
                fig.add_trace(go.Bar(
                    x=parte["faixa"], y=parte["pct"], name=f"{periodo} ({formatar_numero(totais[periodo])} internações)",
                    marker={"color": cor, "line": {"width": 0}},
                    text=[f"{formatar_numero(v)}%" for v in parte["pct"]], textposition="outside", cliponaxis=False,
                    customdata=parte[["internacoes"]].values,
                    hovertemplate="%{x}: %{y:.1f}% (%{customdata[0]} internações)<extra>" + periodo + "</extra>",
                ))
            fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
            fig.update_yaxes(ticksuffix="%", rangemode="tozero")
            estilizar(fig, altura=340)
            st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
            leitura("O que o gráfico mostra", leitura_faixas(tabela_faixas, periodos)
                    + ["A faixa de 50 a 69 anos é a do rastreamento de câncer de mama recomendado pelo INCA."
                       if cancer_faixas == "MAMA" else "Percentual de cada faixa dentro de cada período.",
                       "Compara a distribuição das internações registradas por faixa de idade; não prova que a idade "
                       "de cada mulher mudou. Só entram internações com idade registrada."])

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
                         width="stretch", hide_index=True)
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
            st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
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
        st.plotly_chart(fig, width="stretch", theme=None, config=CONFIG_GRAFICO)
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
- **Meses que a fonte não oferece:** o DATASUS não disponibiliza todos os meses desde 2013 (2018 tem só 6) e o ano mais recente só tem os meses já publicados.
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
