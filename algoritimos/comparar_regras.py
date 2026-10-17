import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

# =====================================
# COMPARAR AS DUAS REGRAS DA SEGUNDA CHANCE DO GEMINI (rodar no computador do autor; a nuvem não tem a chave)
#
# Regra ANTIGA: se as regras locais não entendem a pergunta, o assunto que o Gemini escolher responde direto.
# Regra NOVA:   só responde direto se o assunto também estiver entre os palpites da busca local; senão vira palpite.
#
# O script chama o Gemini UMA vez por pergunta que as regras locais não resolvem sozinhas (em paralelo, leva
# 1 a 2 minutos) e avalia as duas regras sobre a MESMA escolha dele: sem o ruído de rodar duas vezes e sem trocar de
# branch. Conjuntos: desenvolvimento, teste e final (gabarito_perguntas.json) e adversarial (gabarito_adversarial.json,
# escrito depois de ler o vocabulário, NÃO é às cegas). Só relata; não altera nada.
#
# Uso (da pasta do projeto):  py algoritimos\comparar_regras.py
# =====================================

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import entendimento as ent  # noqa: E402

TODOS = {"MAMA", "COLO_UTERO", "COLORRETAL", "OVARIO", "PELE_NAO_MELANOMA", "PULMAO", "TIREOIDE"}
CIDADE, OUTRAS = "Rio Claro", ["Campinas", "Piracicaba", "Ribeirão Preto"]
OPCOES = [(i, ent.DESCRICOES[i]) for i in ent.IDS]
TRABALHADORES = 6


def entender(pergunta):
    return ent.compreender(pergunta, TODOS, cidade=CIDADE, outras_cidades=OUTRAS)


def carregar():
    def ler(nome):
        return json.load(open(os.path.join(AQUI, nome), encoding="utf-8"))
    geral, adv = ler("gabarito_perguntas.json"), ler("gabarito_adversarial.json")
    return [(c, [g for g in geral if g["conjunto"] == c]) for c in ("desenvolvimento", "teste", "final")] + [("adversarial", adv)]


def perguntar_ao_gemini(classificar, pergunta):
    """(escolha, falhou): até 2 tentativas; uma falha de rede ou de cota não pode virar 'o Gemini não soube'."""
    for tentativa in range(2):
        try:
            resposta = classificar(pergunta, OPCOES)
            return (resposta.get("intencao") if isinstance(resposta, dict) else None), False
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return None, True


def comparar(classificar, conjuntos, andamento=None):
    """Devolve {conjunto: contagens}. `classificar(pergunta, opcoes)` é o do Gemini (ou um simulado, nos testes)."""
    pendentes = []  # (conjunto, gabarito, locais) das perguntas que as regras não resolvem sozinhas
    for nome, lista in conjuntos:
        for g in lista:
            if g["esperado"] in ("saudacao", "risco"):
                continue
            e0 = entender(g["pergunta"])
            if e0.tipo in ("palpites", "fora"):
                pendentes.append((nome, g, {i for i, _ in e0.palpites}))

    def chamar(item):
        resultado = perguntar_ao_gemini(classificar, item[1]["pergunta"])
        if andamento:
            andamento()
        return resultado

    with ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
        respostas = list(pool.map(chamar, pendentes))

    saida = {nome: dict(chamadas=0, falhas_api=0, sem_escolha=0, certo=0, errado=0, antiga_certa=0, antiga_erro=0, nova_certa=0,
                        nova_erro=0, palpite_com_certa=0, palpite_sem_certa=0, erros=[]) for nome, _ in conjuntos}
    for (nome, g, locais), (escolha, falhou) in zip(pendentes, respostas):
        r = saida[nome]
        r["chamadas"] += 1
        if falhou:
            r["falhas_api"] += 1
            continue
        if escolha not in ent.IDS:
            r["sem_escolha"] += 1  # "nenhuma", inválida: as duas regras caem no mesmo lugar
            continue
        aceitas = {g["esperado"], *g.get("aceitavel", [])}
        certo = escolha in aceitas
        r["certo" if certo else "errado"] += 1
        r["antiga_certa" if certo else "antiga_erro"] += 1
        if escolha in locais:
            r["nova_certa" if certo else "nova_erro"] += 1
        else:
            r["palpite_com_certa" if aceitas & (locais | {escolha}) else "palpite_sem_certa"] += 1
        if not certo:
            r["erros"].append((g["pergunta"], g["esperado"], escolha, escolha in locais))
    return saida


def relatorio(saida):
    linhas = ["COMPARAÇÃO DAS DUAS REGRAS (mesma resposta do Gemini avaliada pelas duas)"]
    soma = dict.fromkeys(("chamadas", "falhas_api", "antiga_erro", "nova_erro", "palpite_com_certa", "palpite_sem_certa",
                          "antiga_certa", "nova_certa"), 0)
    for nome, r in saida.items():
        for k in soma:
            soma[k] += r[k]
        linhas.append(f"  [{nome}] Gemini consultado em {r['chamadas']} perguntas: escolheu certo {r['certo']}, errado {r['errado']}, "
                      f"sem escolha {r['sem_escolha']}, falhas da API {r['falhas_api']}")
        linhas.append(f"  [{nome}]   regra ANTIGA: diretas certas {r['antiga_certa']}, diretas ERRADAS {r['antiga_erro']}")
        linhas.append(f"  [{nome}]   regra NOVA:   diretas certas {r['nova_certa']}, diretas ERRADAS {r['nova_erro']}, "
                      f"viraram palpite com a certa {r['palpite_com_certa']} e sem a certa {r['palpite_sem_certa']}")
        for pergunta, esperado, escolha, nos_locais in r["erros"]:
            linhas.append(f"  [{nome}]   Gemini errou: \"{pergunta}\" -> {escolha}; esperado {esperado}; "
                          f"{'estava entre os palpites locais' if nos_locais else 'NÃO estava entre os palpites locais'}")
    cliques = soma["palpite_com_certa"] + soma["palpite_sem_certa"]
    linhas.append(f"  TOTAL: Gemini consultado {soma['chamadas']} vezes; regra ANTIGA errou direto {soma['antiga_erro']}; "
                  f"regra NOVA errou direto {soma['nova_erro']} e pediu confirmação em {cliques}")
    if soma["falhas_api"]:
        linhas.append(f"  VEREDITO: INCOMPLETO, {soma['falhas_api']} chamadas falharam (rede ou cota). Rode de novo mais tarde.")
    elif soma["antiga_erro"] == 0:
        linhas.append(f"  VEREDITO: a regra antiga não errou nenhuma resposta direta; a nova só custaria {cliques} confirmações. Não vale.")
    elif soma["nova_erro"] < soma["antiga_erro"]:
        linhas.append(f"  VEREDITO: a regra nova evitou {soma['antiga_erro'] - soma['nova_erro']} respostas erradas "
                      f"em troca de {cliques} confirmações. Vale levar para o main.")
    else:
        linhas.append("  VEREDITO: a regra nova não evitou nenhum erro (o Gemini erra entre candidatos que a busca local já tinha). "
                      "O problema é de vocabulário, não da regra.")
    return "\n".join(linhas)


def main():
    import ia_linguagem
    if not ia_linguagem.chave_configurada():
        print("GEMINI_API_KEY não encontrada no .env: este teste precisa do Gemini de verdade.")
        raise SystemExit(1)
    conjuntos = carregar()
    print("Consultando o Gemini (cada ponto é uma chamada; leva 1 a 2 minutos) ", end="", flush=True)
    saida = comparar(ia_linguagem.classificar_pergunta, conjuntos, andamento=lambda: print(".", end="", flush=True))
    print(" pronto\n")
    print(relatorio(saida))


if __name__ == "__main__":
    main()
