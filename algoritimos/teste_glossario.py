import os
import re
import sys

import pandas as pd

import assistente as asst
import entendimento as ent
import glossario as g
import inteligencia as ti
from lia import Contexto

# =====================================
# TESTE DO GLOSSÁRIO DA LIA (glossario.py, 18/10/2026)
#
# Pergunta do autor: "o que são APACs?" -- termo do painel que a própria Lia não sabia explicar (respondia "foge do que sei"),
# e "qual o preço da diária de internação?". Confere: cada termo tem definição e uso no Escudo; as perguntas de significado
# chegam ao termo certo; perguntas de DADOS que citam as mesmas palavras continuam indo para o assunto de dados; segurança vem
# primeiro; a IA nunca é chamada para definição.
# =====================================

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, ".."))
MESES = {2013: 10, 2014: 10, 2015: 8, 2016: 9, 2017: 11, 2018: 6, 2019: 7, 2020: 8, 2021: 11, 2022: 10, 2023: 11, 2024: 8, 2025: 12}
CODIGOS = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL", "Ovário": "OVARIO",
           "Pele não melanoma": "PELE_NAO_MELANOMA", "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}
falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def contexto():
    real = pd.read_csv(os.path.join(RAIZ, "analises", "base_preditiva_2013_2025.csv"), sep=";")
    real["tipo_cancer"] = real["cancer"].map(CODIGOS)
    real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
    real["dias_permanencia"] = real["dias_internacao_total"]
    serie = ti.ajustar_meses(ti.completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                                                     "valor_total", "dias_permanencia"]]), MESES)
    faixas = pd.DataFrame([(c, a, f, 5 + a % 3) for c in CODIGOS.values() for a in range(2013, 2026)
                           for f in ("até 39 anos", "40 a 49", "50 a 69", "70 ou mais")],
                          columns=["tipo_cancer", "ano", "faixa", "internacoes"])
    return Contexto(serie=serie, cidade="Rio Claro", faixas=faixas)


# ---------- 1. o glossário ----------
checar("todo termo tem rótulo, nomes, definição e uso no Escudo",
       all(rotulo and nomes and definicao and uso for rotulo, nomes, definicao, uso in g.TERMOS.values()))
checar("nenhuma definição promete futuro, atribui causa ou fala em orçamento afirmativo",
       not any(re.search(r"\b(vai (ficar|aumentar|crescer)|deve ficar|por causa d[eo])\b", d + " " + u, re.I)
               for _, _, d, u in g.TERMOS.values()))
checar("os termos do assunto 'metodo' (AIH, SIH, internação, caso novo, incidência) ficam de fora, como combinado",
       not any(n in nomes for _, nomes, _, _ in g.TERMOS.values() for n in ("aih", "sih", "internacao", "incidencia", "datasus")))

# ---------- 2. perguntas de significado chegam ao termo ----------
casos = [
    ("o que são APACs?", ["apac"]), ("O que é APAC", ["apac"]), ("APAC", ["apac"]), ("apacs", ["apac"]),
    ("o que quer dizer APAC?", ["apac"]), ("não sei o que é APAC", ["apac"]),
    ("o que significa valor hospitalar registrado?", ["valor_hospitalar"]),
    ("qual o preço da diária de internação?", ["diaria"]), ("quanto custa a diária?", ["diaria"]),
    ("o que é a diária de internação", ["diaria"]),
    ("o que é UNACON?", ["unacon_cacon"]), ("unacon", ["unacon_cacon"]), ("o que é CACON", ["unacon_cacon"]),
    ("o que é CNES?", ["cnes"]), ("CNES", ["cnes"]), ("o que é CID?", ["cid"]),
    ("o que é letalidade hospitalar?", ["letalidade"]), ("o que é permanência média?", ["permanencia"]),
    ("o que é o SIM?", ["sim"]), ("o que é SIA?", ["sia"]),
    ("o que significa óbito durante a internação?", ["obito_internacao"]),
    ("o que é projeção de tendência?", ["projecao"]), ("o que são anos fora do padrão?", ["fora_padrao"]),
    ("o que são meses ausentes?", ["meses_ausentes"]), ("o que é regulação?", ["regulacao"]),
    ("o que é a UBS?", ["ubs_usf"]), ("o que é estadiamento?", ["estadiamento"]), ("o que é RRAS?", ["rras_drs"]),
    ("qual a diferença entre APAC e SIA?", ["apac", "sia"]),
    ("o que é o SUS?", ["sus"]), ("o que é IBGE?", ["ibge"]), ("o que é o INCA?", ["inca"]), ("o que é leito?", ["leito"]),
    ("o que é um backtest?", ["teste_acerto"]),
]
for pergunta, esperado in casos:
    checar(f"'{pergunta}' -> {esperado}", g.achar_termos(pergunta) == esperado)

# ---------- 3. perguntas que NÃO são pedido de significado ----------
nao = ["sim", "sim, e no estado?", "permanência média", "anos fora do padrão", "valores hospitalares", "o que é câncer de mama?",
       "o que significa internação?", "o que é AIH?", "onde fazer mamografia?", "qual cidade tem mais casos?",
       "como a projeção é calculada?", "o que a tendência aponta?", "o que é isso?", "oi", ""]
for pergunta in nao:
    checar(f"'{pergunta}' não vira glossário", g.achar_termos(pergunta) == [])

# ---------- 4. entendimento e assistente ----------
e = ent.compreender("o que são APACs?", {"MAMA", "COLO_UTERO"})
checar("entendimento: 'o que são APACs?' é o assunto glossario, por regras", e.tipo == "intencao" and e.intencao == "glossario"
       and e.termos == ["apac"] and e.origem == "regras")
checar("segurança vem primeiro: relato de violência com o termo não vira definição",
       ent.compreender("meu marido está me agredindo, o que é APAC?").tipo == "risco")
guardas = {"o que significa internação?": "metodo", "o que é AIH": "metodo", "valores hospitalares": "valores",
           "qual câncer mais interna?": "mais_aparece", "está aumentando?": "evolucao"}
for pergunta, assunto in guardas.items():
    checar(f"continua igual: '{pergunta}' -> {assunto}", ent.compreender(pergunta, {"MAMA", "COLO_UTERO"}).intencao == assunto)

ctx = contexto()
chamadas = []
ia = asst.IA(explicar=lambda *a: chamadas.append(("explicar", a)) or "TEXTO DA IA",
             classificar=lambda *a: chamadas.append(("classificar", a)) or {"intencao": "mais_aparece"}, ligada=True)
r = asst.responder_pergunta(ctx, "o que são APACs?", None, ia=ia)
checar("assistente: define APAC com texto fixo, sem chamar a IA", r.intencao == "glossario" and "Autorização de Procedimento Ambulatorial" in r.fala and "registros, não mulheres" in r.fala and chamadas == [] and "Texto fixo" in (r.selo or ""))
checar("assistente: a resposta traz botões (método, o que posso perguntar) e o botão de início",
       any("Como esses dados funcionam" in rot for rot, _ in r.botoes) and any(a.get("tipo") == "inicio" for _, a in r.botoes))
r = asst.responder_pergunta(ctx, "qual o preço da diária de internação?", None, ia=ia)
checar("assistente: a diária explica que o Escudo não calcula o preço e não devolve o total de valores",
       "não calcula nem informa o preço da diária" in r.fala and "R$" not in r.fala and chamadas == [])
r = asst.responder_pergunta(ctx, "qual a diferença entre APAC e SIA?", None, ia=ia)
checar("assistente: dois termos na mesma pergunta respondem os dois", "APAC" in r.fala and "SIA/SUS" in r.fala)
r = asst.responder_pergunta(ctx, "o que posso perguntar?", None, ia=ia)
checar("ajuda: avisa que dá para perguntar o significado dos termos", "o que é ...?" in r.fala)
r = asst.responder_pergunta(ctx, "qual câncer mais interna?", None)
checar("pergunta de dados continua com os números", "internações" in r.fala and r.intencao == "mais_aparece")

# Perguntas reais de quem escreve rápido (teste humano, 18/10/2026: "o que é unacon e cacon" funcionava, as variações não)
for frase in ("oq é unacon e cacon", "unacon e cacon", "UNACON ou CACON?", "me explica unacon e cacon", "para que serve unacon e cacon", "oque é cacon"):
    r = asst.responder_pergunta(ctx, frase, None, ia=ia)
    checar(f"assistente: '{frase}' explica UNACON e CACON em texto fixo", r.intencao == "glossario" and "Alta Complexidade em Oncologia" in r.fala and chamadas == [])
for frase in ("me explica a projeção de tendência", "explica como calculam a tendência", "quero saber a tendência do câncer de mama"):
    checar(f"pergunta de dados não vira definição: '{frase}'", g.achar_termos(frase) == [])

print("Todas as checagens passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
