"""Teste de integração focado em memória temporária da caixa de Apoio."""
import os
import sys

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))

from streamlit.testing.v1 import AppTest


def main():
    at = AppTest.from_file(os.path.join(RAIZ, "dashboard", "pages", "apoio.py"), default_timeout=60).run()
    assert not at.exception

    at.text_input(key="caixa_ap_texto").set_value(
        "onde consulto quando a carreta da mamografia vai passar"
    )
    at.button(key="caixa_ap_enviar").click().run()
    assert not at.exception
    assert at.session_state["caixa_ap_contexto"] == "item:carretas_estado"

    at.text_input(key="caixa_ap_texto").set_value("e agora?")
    at.button(key="caixa_ap_enviar").click().run()
    resposta = at.session_state["ap_lia"]["atual"]
    assert not at.exception
    assert resposta.tipo == "esclarecimento"
    assert "continua falando" in resposta.fala.lower()
    assert at.session_state["caixa_ap_contexto"] == "item:carretas_estado"

    at.text_input(key="caixa_ap_texto").set_value("telefone da regulação de oncologia")
    at.button(key="caixa_ap_enviar").click().run()
    resposta = at.session_state["ap_lia"]["atual"]
    assert not at.exception
    assert resposta.tipo == "itens" and resposta.candidatos == ["lista_regulacao"]
    assert at.session_state["caixa_ap_contexto"] == "item:lista_regulacao"

    at.text_input(key="caixa_ap_texto").set_value("recebi diagnóstico de câncer, e agora?")
    at.button(key="caixa_ap_enviar").click().run()
    assert not at.exception
    assert at.session_state["caixa_ap_contexto"] == "etapa:diagnostico_cancer"
    at.text_input(key="caixa_ap_texto").set_value("estou com medo")
    at.button(key="caixa_ap_enviar").click().run()
    resposta = at.session_state["ap_lia"]["atual"]
    assert not at.exception
    assert resposta.tipo == "esclarecimento" and "diagnóstico" in resposta.fala.lower()

    at.button(key="lia_discreto_inicio_ap").click().run()
    assert not at.exception
    assert at.session_state["caixa_ap_contexto"] is None

    print("A caixa Streamlit preservou contexto de catálogo, esclareceu seguimento vago e trocou de assunto.")


if __name__ == "__main__":
    main()
