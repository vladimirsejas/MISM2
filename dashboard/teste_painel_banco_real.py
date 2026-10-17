import os
import sqlite3
import sys

os.environ.setdefault("STREAMLIT_LOGGER_LEVEL", "error")  # sem os avisos de versão no resultado

# =====================================
# PAINEL COM O BANCO REAL (rodar no computador do autor; a nuvem não tem o banco)
#
# Abre o painel DE VERDADE (dashboard/app.py, via Streamlit AppTest) lendo banco\escudo_feminino.db, sem dados falsos,
# e confere o que o teste com a base pública não consegue: que as 5 abas abrem com os números do banco, que a
# Lia responde e que a caixa "Pergunte à Lia" funciona de ponta a ponta (com o Gemini real, se a chave estiver no .env).
# NÃO escreve no banco: a contagem de perguntas é desligada aqui. Só relata o que viu; nada é alterado.
#
# Uso (da pasta do projeto):  py dashboard\teste_painel_banco_real.py
# (ESCUDO_PAINEL_SINTETICO=1 usa a base pública no lugar do banco: só para validar este próprio script na nuvem.)
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "dashboard"))
os.makedirs(os.path.join(RAIZ, "banco"), exist_ok=True)

import configuracao_geografica  # noqa: E402
import conversa  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

falhas = []


def checar(nome, condicao, detalhe=""):
    print(("OK   " if condicao else "FALHOU ") + nome + (f"\n       {detalhe}" if detalhe and not condicao else ""))
    if not condicao:
        falhas.append(nome)


def erros(at):
    return [str(e.value)[:200] for e in at.exception]


def main():
    sintetico = bool(os.environ.get("ESCUDO_PAINEL_SINTETICO"))
    if sintetico:
        import teste_painel
        teste_painel.preparar_dados()
        print("(modo sintético: base pública no lugar do banco)")
    else:
        banco = configuracao_geografica.BANCO
        if not os.path.exists(banco):
            print(f"SEM BANCO: {banco} não existe. Rode a carga (py etl\\carga_todas_bases.py) e tente de novo.")
            raise SystemExit(2)
        conn = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
        try:
            total = conn.execute("SELECT COUNT(*) FROM internacoes").fetchone()[0]
            canceres = conn.execute("SELECT COUNT(DISTINCT tipo_cancer) FROM internacoes").fetchone()[0]
        except sqlite3.Error as erro:
            print(f"BANCO SEM A TABELA 'internacoes' ({erro}). Rode a carga e tente de novo.")
            raise SystemExit(2)
        finally:
            conn.close()
        print(f"Banco: {banco}\n  {total:,} internações, {canceres} cânceres".replace(",", "."))
        checar("o banco tem os 7 cânceres", canceres == 7, f"só {canceres} entraram: rode py etl\\validar_banco.py")

    conversa.registrar_pergunta = lambda *a: None  # nunca grava no banco do autor

    at = AppTest.from_file(os.path.join(RAIZ, "dashboard", "app.py"), default_timeout=300)
    at.run()
    checar("o painel abre sem erro", not erros(at), "; ".join(erros(at)))
    if erros(at):
        raise SystemExit(1)
    try:
        at.button(key="bv_fechar").click().run()
    except Exception:  # noqa: BLE001  (boas-vindas já fechadas)
        pass

    for aba in ["Panorama", "Evolução", "Investigar", "Planejamento", "Método"]:
        at.session_state["aba"] = aba
        for camada in ("ver_estado", "ver_fora", "ver_projecao"):
            at.session_state[camada] = True
        at.run()
        checar(f"aba {aba} abre sem erro com os dados reais", not erros(at), "; ".join(erros(at)))

    print("\nCaixa 'Pergunte à Lia' (usa o Gemini real se houver chave no .env):")
    perguntas = [("o câncer de mama está aumentando?", "evolucao"), ("qual câncer mais interna?", "mais_aparece"),
                 ("tem mulher de outro estado se tratando em são paulo?", "fluxo")]
    for texto, esperado in perguntas:
        at.text_input(key="caixa_texto").set_value(texto)
        at.button(key="caixa_enviar").click().run()
        atual = at.session_state["lia"]["atual"]
        checar(f"'{texto}' responde sem quebrar o painel", not erros(at), "; ".join(erros(at)))
        checar(f"'{texto}' é entendida como {esperado}", getattr(atual, "intencao", None) == esperado,
               f"entendeu {getattr(atual, 'intencao', None)} ({getattr(atual, 'tipo', None)})")
        print(f"       selo: {(getattr(atual, 'selo', '') or '')[:110]} | IA redigiu: {getattr(atual, 'usou_ia', False)}"
              + (f" | motivo: {atual.ia_motivo}" if getattr(atual, "ia_motivo", None) else ""))

    print()
    if falhas:
        print(f"{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("O painel passou com a base pública (modo sintético)." if sintetico else "O painel passou com o banco real.")


if __name__ == "__main__":
    main()
