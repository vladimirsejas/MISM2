import json
import os

import pandas as pd

from inteligencia import completar_anos
from lia import CAMINHOS, EXPRESSOES, INICIO, Contexto, caminho, responder, sobre

# =====================================
# TESTE DA LIA (algoritimos/lia.py)
#
# A. Percorre a árvore INTEIRA com a base pública real (Rio Claro x
#    SP): clica em todos os botões de todas as respostas, até não
#    sobrar caminho novo. Nenhum pode quebrar, ficar sem fala, sem
#    botão de recomeço ou com destino inválido.
# B. Regras da Lia: nada de orçamento, projeção com os três níveis e
#    os limites, expressão cautelosa quando o dado pede cuidado.
# =====================================

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CSV_REAL = os.path.join(DIRETORIO_ATUAL, "..", "analises", "base_preditiva_2013_2025.csv")
ABAS = {"Panorama", "Evolução", "Investigar", "Planejamento", "Método"}
MEDIDAS = {"Internações", "Valor hospitalar registrado", "Óbitos na internação", "Dias de internação"}

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


real = pd.read_csv(CSV_REAL, sep=";")
codigos = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL", "Ovário": "OVARIO",
           "Pele não melanoma": "PELE_NAO_MELANOMA", "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}
real["tipo_cancer"] = real["cancer"].map(codigos)
real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
real["dias_permanencia"] = real["dias_internacao_total"]
serie = completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                             "valor_total", "dias_permanencia"]])
faixas = pd.DataFrame([(c, ano, f, 5 + (ano % 3)) for c in codigos.values() for ano in range(2013, 2026)
                       for f in ("até 39 anos", "40 a 49", "50 a 69", "70 ou mais")],
                      columns=["tipo_cancer", "ano", "faixa", "internacoes"])
ctx = Contexto(serie=serie, cidade="Rio Claro", faixas=faixas)

# ---- A. árvore inteira ----
vistos, fila, respostas, erros = set(), [INICIO], {}, []
while fila:
    acao = fila.pop()
    chave = json.dumps(acao, sort_keys=True)
    if chave in vistos:
        continue
    vistos.add(chave)
    try:
        r = responder(ctx, acao)
    except Exception as erro:  # registra e segue, para ver todos os problemas de uma vez
        erros.append(f"{chave}: {type(erro).__name__}: {erro}")
        continue
    respostas[chave] = r
    fila.extend(a for _, a in r.botoes)

checar(f"A. percorreu {len(respostas)} respostas sem erro", not erros and len(respostas) >= 60)
for e in erros[:5]:
    print("   ", e)
checar("A. toda resposta tem fala", all(r.fala.strip() for r in respostas.values()))
checar("A. toda expressão é uma das 5", all(r.expressao in EXPRESSOES for r in respostas.values()))
checar("A. toda resposta (menos a saudação) oferece 'Começar de novo'",
       all(any(a == INICIO for _, a in r.botoes) for k, r in respostas.items() if k != json.dumps(INICIO)))
checar("A. todo destino aponta para uma aba que existe",
       all(r.destino is None or r.destino.get("aba") in ABAS for r in respostas.values()))
checar("A. toda medida pedida existe no painel",
       all(r.destino is None or r.destino.get("medida") in (None, *MEDIDAS) for r in respostas.values()))
checar("A. todos os caminhos da saudação existem", len(responder(ctx, INICIO).botoes) == len(CAMINHOS))

# ---- B. regras ----
r = responder(ctx, caminho("atencao"))
checar("B. atenção: evidências, sem valor de orçamento, decisão da gestão",
       "decisão de quanto investir é da gestão" in r.fala and "R$" not in r.fala and r.expressao == "atenta")
r = responder(ctx, sobre("MAMA", "projecao"))
checar("B. projeção tem os três níveis",
       all(t in r.fala for t in ("O que aconteceu", "O que está acontecendo", "O que pode acontecer")))
checar("B. projeção diz que não é previsão de casos novos", "não previsão de casos novos" in r.fala)
checar("B. projeção com 2025 em investigação fica cautelosa", r.expressao == "cautelosa")
r = responder(ctx, sobre("TIREOIDE", "evolucao"))
checar("B. câncer com poucas internações: expressão cautelosa e aviso", r.expressao == "cautelosa"
       and "poucas internações" in r.fala)
r = responder(ctx, caminho("valores"))
checar("B. valores: termo certo e aviso de que não é orçamento",
       "valores hospitalares registrados no SIH/SUS" in r.fala and "não é o orçamento" in r.fala)
r = responder(ctx, caminho("metodo"))
checar("B. método: expressão pensativa e o que os dados não permitem", r.expressao == "pensativa"
       and "não" in r.fala and "causas" in r.fala)
checar("B. câncer inexistente na cidade volta ao começo",
       responder(ctx, sobre("XYZ", "evolucao")).expressao == "acolhedora")

# ---- E. dados incompletos na fonte (mês ausente não é zero; ano incompleto não é normal) ----
from inteligencia import ajustar_meses
from lia import completude
meses_fonte = {2013: 10, 2014: 10, 2015: 8, 2016: 9, 2017: 11, 2018: 6, 2019: 7, 2020: 8,
               2021: 11, 2022: 10, 2023: 11, 2024: 8, 2025: 12}
ctx_m = Contexto(serie=ajustar_meses(serie, meses_fonte), cidade="Rio Claro", faixas=faixas)
r = responder(ctx_m, caminho("completude"))
checar("E. 'Os dados estão completos?': não, com os meses de cada ano e as duas regras",
       r.fala.startswith("**Não.**") and "2018: 6 de 12" in r.fala and "mês ausente não é zero" in r.fala
       and "ano incompleto não é ano normal" in r.fala and "Conferimos duas vezes" in r.fala
       and r.destino["aba"] == "Método")
checar("E. sem a informação de meses, a Lia diz que ainda não sabe (não inventa)",
       "Ainda não consigo dizer" in completude(ctx).fala)
r = responder(ctx_m, caminho("fora_padrao"))
checar("E. ano fora do padrão em ano incompleto vem com cautela",
       "2019 (acima do esperado — ano com 7 de 12 meses na fonte: leia com cautela)" in r.fala and any(
           b[0] == "Os dados estão completos?" for b in r.botoes))
r = responder(ctx_m, sobre("MAMA", "projecao"))
checar("E. projeção sem promessa ('deve ficar' não aparece; 'a tendência aponta')",
       "deve ficar" not in r.fala and "a tendência aponta" in r.fala)
r = responder(ctx_m, sobre("MAMA", "evolucao"))
checar("E. a Lia avisa os anos incompletos ao falar de evolução", "não oferece todos os meses" in r.fala)

# ---- F. fluxo de mulheres de outros estados ----
r = responder(ctx, caminho("fluxo"))
checar("F. sem o fluxo no banco, a Lia diz que ainda não sabe e manda rodar a carga",
       "carga" in r.fala and r.expressao == "cautelosa" and r.destino == {"aba": "Investigar"})
ufs_f = pd.DataFrame({"uf": ["MG", "GO"], "estado": ["Minas Gerais", "Goiás"], "internacoes": [60, 20], "pct": [75.0, 25.0]})
fluxo_falso = {"internacoes_fora": 80, "internacoes_total": 800, "pct_fora": 10.0, "n_ufs": 2, "ufs": ufs_f,
               "concentracao": {"destino": "Barretos", "pct": 88.0, "hospitais": 2, "n_para_90": 2}}
import lia as _lia
_original = _lia.resumo_fluxo
_lia.resumo_fluxo = lambda f, c=None: fluxo_falso
try:
    r = responder(Contexto(serie=serie, cidade="Rio Claro", faixas=faixas, fluxo=object()), caminho("fluxo"))
finally:
    _lia.resumo_fluxo = _original
checar("F. com o fluxo: cita estados e destino, vai para Investigar, descreve sem atribuir causa",
       "Minas Gerais" in r.fala and "Barretos" in r.fala and r.destino == {"aba": "Investigar"}
       and "internações, não pessoas" in r.fala and "porque" not in r.fala.lower() and "R$" not in r.fala)

print()
if falhas:
    print(f"{len(falhas)} checagem(ns) falharam.")
    raise SystemExit(1)
print("Todas as checagens passaram.")
