import os
import sys
import time

# =====================================
# DIAGNÓSTICO DO GEMINI (rodar no computador do autor; a nuvem não tem a chave)
#
# Responde, com uma chamada de verdade, o que o código sozinho não prova:
#   1. a chave está no .env e é aceita?
#   2. o nome do modelo (ia_linguagem.MODELO) existe para esta chave?
#   3. uma chamada simples funciona e quanto demora?
#   4. as duas tarefas da caixa "Pergunte à Lia" funcionam: escolher o assunto
#      (classificar_pergunta) e redigir uma resposta que passe na conferência
#      de números (redigir_resposta + assistente.conferir)?
# Nunca mostra a chave. Se o modelo não existir, sugere um e diz como trocar
# (GEMINI_MODEL=... no .env).
#
# Uso (da pasta do projeto):  py algoritimos\testar_gemini.py
# ou dê dois cliques em "Testar IA (Gemini).bat".
# =====================================

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

resultados = []


def passo(nome, ok, detalhe=""):
    resultados.append(ok)
    print(("[OK]    " if ok else "[FALHOU] ") + nome + (f"\n          {detalhe}" if detalhe else ""))


def main():
    import ia_linguagem as ia

    env = os.path.normpath(os.path.join(AQUI, "..", ".env"))
    print(f"Pasta do .env: {env}  ({'existe' if os.path.exists(env) else 'NÃO existe'})")
    chave = os.getenv("GEMINI_API_KEY")
    passo("1. GEMINI_API_KEY definida", bool(chave),
          f"{len(chave)} caracteres (a chave não é mostrada)" if chave else
          "Crie o arquivo .env na pasta do projeto com a linha GEMINI_API_KEY=sua_chave (o .env nunca vai para o GitHub).")
    if not chave:
        print("\nSem chave não dá para continuar.")
        raise SystemExit(1)

    cliente = ia.obter_cliente()
    print(f"Modelo configurado: {ia.MODELO}")
    disponiveis = []
    try:
        for m in cliente.models.list():
            nome = str(getattr(m, "name", "")).replace("models/", "")
            acoes = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or []
            if nome.startswith("gemini") and (not acoes or "generateContent" in acoes):
                disponiveis.append(nome)
        passo("2. a chave é aceita e lista os modelos", True, f"{len(disponiveis)} modelos Gemini com generateContent")
    except Exception as erro:  # noqa: BLE001
        passo("2. a chave é aceita e lista os modelos", False, f"{type(erro).__name__}: {str(erro)[:200]}")
    if disponiveis:
        existe = ia.MODELO in disponiveis
        passo(f"2b. o modelo '{ia.MODELO}' existe para esta chave", existe,
              "" if existe else "Modelos 'flash' disponíveis: " + ", ".join(sorted(n for n in disponiveis if "flash" in n)[:8]) +
              "\n          Para trocar, ponha no .env a linha GEMINI_MODEL=<um dos nomes acima>")

    inicio = time.time()
    try:
        texto = ia._gerar("Responda apenas com a palavra OK.")
        passo("3. chamada simples", "ok" in texto.lower(), f"respondeu '{texto.strip()[:40]}' em {time.time() - inicio:.1f} s")
    except Exception as erro:  # noqa: BLE001
        passo("3. chamada simples", False, f"{type(erro).__name__}: {str(erro)[:200]}")
        print("\nSem uma chamada simples funcionando, os próximos passos não fazem sentido.")
        raise SystemExit(1)

    import entendimento as ent
    try:
        r = ia.classificar_pergunta("me explica de onde vocês tiraram esses números", [(i, ent.DESCRICOES[i]) for i in ent.IDS])
        passo("4. escolher o assunto de uma pergunta (lista fechada)", isinstance(r, dict) and r.get("intencao") in ent.IDS + ["nenhuma"],
              f"devolveu {r}")
    except Exception as erro:  # noqa: BLE001
        passo("4. escolher o assunto de uma pergunta", False, f"{type(erro).__name__}: {str(erro)[:200]}")

    import assistente
    base = ("Em 2025 foram 93 internações por câncer de mama em Rio Claro. Desde 2013, as internações crescem 5,3% ao ano.\n"
            "- Mama: 670 internações")
    try:
        texto = ia.redigir_resposta("o câncer de mama está aumentando?", base, "TECNICO")
        motivo = assistente.conferir(texto, base, "o câncer de mama está aumentando?")
        passo("5. redigir uma resposta que passa na conferência (sem número novo, sem promessa, sem causa)", motivo is None,
              f"texto: {texto.strip()[:160]}" + (f"\n          descartado: {motivo}" if motivo else ""))
    except Exception as erro:  # noqa: BLE001
        passo("5. redigir uma resposta", False, f"{type(erro).__name__}: {str(erro)[:200]}")

    print(f"\n{sum(resultados)} de {len(resultados)} passos OK.")
    if not all(resultados):
        raise SystemExit(1)
    print("O Gemini está pronto para a caixa 'Pergunte à Lia'.")


if __name__ == "__main__":
    main()
