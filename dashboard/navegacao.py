"""Barra de navegação única das páginas do MISM2 (20/10/2026, autor: "poucas opções de retorno, é um labirinto").

Mesmos quatro destinos, na mesma ordem e em botões grandes, no topo de todas as páginas: Início, Apoio à mulher,
Onde ser atendida e Hospitais de câncer. A página em que a pessoa está aparece marcada e sem link. Só navegação:
não calcula nada e não abre o banco.
"""
import os

import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))

DESTINOS = [
    ("apoio", "💜 Apoio à mulher", "pages/apoio.py", "/apoio"),
    ("onde", "📍 Onde ser atendida", "pages/onde_ser_atendida.py", "/onde_ser_atendida"),
    ("hospitais", "🗺️ Hospitais de câncer", "pages/hospitais_cancer.py", "/hospitais_cancer"),
]


def _ir_ao_inicio():
    st.session_state["aba"] = "Panorama"
    try:
        st.switch_page(os.path.abspath(os.path.join(AQUI, "app.py")))
    except Exception:  # página aberta fora do painel (teste isolado): sem destino
        pass


def barra_de_navegacao(atual, chave_inicio=None):
    """Desenha a barra. `atual`: 'apoio', 'onde' ou 'hospitais' (marcada, sem link). `chave_inicio`: chave do botão Início;
    None não desenha o Início (a página já tem o dela)."""
    try:
        caixa = st.container(key=f"barra_navegacao_{atual}")
    except TypeError:  # Streamlit antigo, sem key em container
        caixa = st.container()
    with caixa:
        colunas = st.columns(len(DESTINOS) + (1 if chave_inicio else 0))
        i = 0
        if chave_inicio:
            if colunas[0].button("🏠 Início", key=chave_inicio, width="stretch", help="Volta à página inicial (Panorama)."):
                _ir_ao_inicio()
            i = 1
        for chave, rotulo, pagina, url in DESTINOS:
            with colunas[i]:
                if chave == atual:
                    st.markdown(f'<div class="nav-aqui">{rotulo}<small>você está aqui</small></div>', unsafe_allow_html=True)
                else:
                    try:
                        st.page_link(pagina, label=rotulo, width="stretch")
                    except TypeError:  # Streamlit sem width no page_link
                        st.page_link(pagina, label=rotulo)
                    except Exception:  # Streamlit antigo, sem page_link
                        st.markdown(f'<a href="{url}" target="_self">{rotulo}</a>', unsafe_allow_html=True)
            i += 1
