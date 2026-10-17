import os
import sys

os.environ.setdefault("STREAMLIT_LOGGER_LEVEL", "error")

# =====================================
# TESTE COM UMA PESSOA (o autor) NA CAIXA "PERGUNTE À LIA", COM O BANCO E O GEMINI REAIS
#
# Você digita uma pergunta do jeito que escreveria de verdade, vê o que a Lia respondeu e diz se era o que queria
# (s = sim, n = não, p = em parte, Enter = pular). A memória da conversa vale: dá para testar "me explica isso melhor",
# "e no estado?" e pedidos com duas partes. No fim sai um resumo para colar no chat.
# Não grava nada: nem o banco (a contagem de perguntas é desligada) nem arquivo. As perguntas ficam só na tela.
#
# Uso (da pasta do projeto):  py dashboard\teste_perguntas_humano.py
# (ESCUDO_PAINEL_SINTETICO=1 usa a base pública no lugar do banco: só para validar este script na nuvem.)
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "dashboard"))
os.makedirs(os.path.join(RAIZ, "banco"), exist_ok=True)

import configuracao_geografica  # noqa: E402
import conversa  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402


def main():
    if os.environ.get("ESCUDO_PAINEL_SINTETICO"):
        import teste_painel
        teste_painel.preparar_dados()
        print("(modo sintético: base pública no lugar do banco)")
    elif not os.path.exists(configuracao_geografica.BANCO):
        print(f"SEM BANCO: {configuracao_geografica.BANCO} não existe.")
        raise SystemExit(2)
    conversa.registrar_pergunta = lambda *a: None  # nunca grava no banco

    print("Abrindo o painel (alguns segundos)...")
    at = AppTest.from_file(os.path.join(RAIZ, "dashboard", "app.py"), default_timeout=300)
    at.run()
    if at.exception:
        print("O painel não abriu:", "; ".join(str(e.value)[:200] for e in at.exception))
        raise SystemExit(1)
    try:
        at.button(key="bv_fechar").click().run()
    except Exception:  # noqa: BLE001
        pass

    print("\nEscreva perguntas como você escreveria de verdade. Para cada resposta, diga se era o que queria:")
    print("  s = sim   n = não   p = em parte   Enter = pular.   Enter numa pergunta vazia = terminar.")
    registros = []
    while True:
        try:
            texto = input("\nSua pergunta: ").strip()
        except EOFError:
            break
        if not texto:
            break
        at.text_input(key="caixa_texto").set_value(texto)
        at.button(key="caixa_enviar").click().run()
        if at.exception:
            print("  ERRO NO PAINEL:", "; ".join(str(e.value)[:200] for e in at.exception))
            registros.append((texto, "ERRO", "", "", "-", ""))
            continue
        a = at.session_state["lia"]["atual"]
        assunto = getattr(a, "intencao", None) or "-"
        tipo, origem = getattr(a, "tipo", "?"), getattr(a, "origem", "?")
        ia = "IA redigiu" if getattr(a, "usou_ia", False) else "sem IA"
        fala = " ".join((getattr(a, "fala", "") or "").split())
        print(f"  assunto: {assunto} | tipo: {tipo} | origem: {origem} | {ia}")
        print(f"  Lia: {fala[:380]}{'...' if len(fala) > 380 else ''}")
        botoes = [r for r, _ in getattr(a, "botoes", [])][:4]
        if tipo == "palpites" and botoes:
            print(f"  (ofereceu opções: {', '.join(botoes)})")
        try:
            veredito = input("  Foi o que você queria? [s/n/p/Enter]: ").strip().lower()[:1]
        except EOFError:
            veredito = ""
        registros.append((texto, assunto, tipo, origem, ia, veredito or "-"))

    if not registros:
        print("Nenhuma pergunta feita.")
        return
    contagem = {k: sum(1 for r in registros if r[5] == k) for k in "snp-"}
    print("\n" + "=" * 70 + "\nRESUMO (copie daqui para baixo e cole no chat)\n" + "=" * 70)
    print(f"{len(registros)} perguntas: {contagem['s']} certas, {contagem['p']} em parte, {contagem['n']} erradas, "
          f"{contagem['-']} sem avaliar")
    for i, (texto, assunto, tipo, origem, ia, v) in enumerate(registros, 1):
        print(f"{i}. [{v}] \"{texto}\" -> {assunto} ({tipo}/{origem}, {ia})")


if __name__ == "__main__":
    main()
