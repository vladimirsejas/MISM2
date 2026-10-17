import os
import sqlite3
import tempfile

import pandas as pd

from conversa import entender, registrar_pergunta, responder
from inteligencia import completar_anos

# =====================================
# TESTE DO CHAT (conversa.py)
#
# A. Entender: perguntas reais -> assunto e câncer certos, incluindo
#    as que o chat antigo errava.
# B. Responder com a base pública real (Rio Claro x SP), sem IA:
#    os números batem com o painel e nada de orçamento em reais.
# C. Com uma "IA" falsa: usa a IA quando ela responde, cai na
#    resposta direta quando ela falha.
# =====================================

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CSV_REAL = os.path.join(DIRETORIO_ATUAL, "..", "analises", "base_preditiva_2013_2025.csv")

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


DISPONIVEIS = {"MAMA", "COLO_UTERO", "COLORRETAL", "OVARIO", "PELE_NAO_MELANOMA", "PULMAO", "TIREOIDE"}

# ---- A. entender ----
CASOS = [
    # (pergunta, assunto esperado, câncer esperado)
    ("Qual a mortalidade do câncer de mama?", "MORTALIDADE", "MAMA"),        # antigo: virava ficha de mama
    ("Como está o câncer de colo do útero?", "EVOLUCAO", "COLO_UTERO"),      # antigo: não reconhecia
    ("Quanto foi gasto com câncer de intestino?", "CUSTO", "COLORRETAL"),
    ("Me responda de forma direta: qual câncer mais mata?", "MORTALIDADE", None),  # 'direta' não é 'reto'
    ("O que podemos esperar nos próximos anos?", "PROJECAO", None),
    ("Qual a previsão para mama em 2028?", "PROJECAO", "MAMA"),
    ("Onde devemos investir o orçamento?", "ATENCAO", None),
    ("O que merece mais atenção?", "ATENCAO", None),
    ("Houve algum ano fora do padrão?", "FORA_PADRAO", None),
    ("O que aconteceu em 2025?", "FORA_PADRAO", None),
    ("Estamos crescendo mais que o Estado?", "ESTADO", None),
    ("Pulmão em Rio Claro comparado a SP", "ESTADO", "PULMAO"),
    ("Como evoluiu o câncer de pele?", "EVOLUCAO", "PELE_NAO_MELANOMA"),
    ("Quanto tempo as mulheres ficam internadas?", "PERMANENCIA", None),
    ("Como está a situação geral?", "PANORAMA", None),
    ("Quais cânceres mais afetam as mulheres?", "PANORAMA", None),
    ("Quantas internações de tireoide?", "EVOLUCAO", "TIREOIDE"),
    ("Como esses números foram calculados? São confiáveis?", "METODO", None),
    ("ovário", "EVOLUCAO", "OVARIO"),
    ("oi", "PANORAMA", None),
]
for pergunta, assunto, cancer in CASOS:
    e = entender(pergunta, DISPONIVEIS)
    checar(f"A. '{pergunta}' -> {assunto}/{cancer}",
           e["assunto"] == assunto and e["cancer"] == cancer)

e = entender("como evoluiu?", DISPONIVEIS, cancer_em_foco="PULMAO")
checar("A. sem câncer na pergunta, evolução usa o câncer em foco no painel",
       e["cancer"] is None and e["cancer_em_foco"] == "PULMAO")

# ---- B. responder com a base real ----
if os.path.exists(CSV_REAL):
    real = pd.read_csv(CSV_REAL, sep=";")
    codigos = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL",
               "Ovário": "OVARIO", "Pele não melanoma": "PELE_NAO_MELANOMA",
               "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}
    real["tipo_cancer"] = real["cancer"].map(codigos)
    real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
    real["dias_permanencia"] = real["dias_internacao_total"]
    serie = completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                                 "valor_total", "dias_permanencia"]])

    sem_ia = lambda *a: (_ for _ in ()).throw(RuntimeError("sem chave"))

    r = responder("Como está a situação geral?", serie, "Rio Claro", explicar=sem_ia)
    checar("B. panorama cita o total real (1.668 internações)", "1.668 internações" in r["texto"])
    checar("B. sem IA: responde mesmo assim (resposta direta)", not r["usou_ia"] and len(r["fatos"]) >= 3)

    r = responder("Qual a mortalidade do câncer de mama?", serie, "Rio Claro", explicar=sem_ia)
    checar("B. mortalidade de mama compara com o Estado", "Mama:" in r["texto"] and "no Estado" in r["texto"])

    r = responder("Como evoluiu o colo do útero?", serie, "Rio Claro", explicar=sem_ia)
    checar("B. colo do útero: 11,6% ao ano, igual ao painel", "11,6% ao ano" in r["texto"])

    r = responder("O que podemos esperar para 2028?", serie, "Rio Claro", explicar=sem_ia)
    checar("B. projeção traz faixa e o aviso de exploratória",
           "faixa provável" in r["texto"] and "exploratória" in r["texto"])
    checar("B. projeção avisa que 2025 está em investigação", "em investigação" in r["texto"])

    r = responder("Onde devemos investir o orçamento?", serie, "Rio Claro", explicar=sem_ia)
    checar("B. orçamento: responde com sinais e evidências", "merecem atenção" in r["texto"])
    checar("B. orçamento: não prescreve valor em reais", "R$" not in r["texto"])
    checar("B. orçamento: deixa a decisão com a gestão", "não define quanto investir" in r["texto"])

    r = responder("Houve algum ano fora do padrão?", serie, "Rio Claro", explicar=sem_ia)
    checar("B. fora do padrão: lembra que detectar não explica a causa", "não explica a causa" in r["texto"])

    # ---- C. com IA ----
    ia_ok = lambda pergunta, contexto, perfil: f"[IA {perfil}] resumo de {len(contexto.splitlines())} fatos"
    r = responder("Como está a situação geral?", serie, "Rio Claro", perfil="TECNICO", explicar=ia_ok)
    checar("C. usa a IA quando ela responde, com o perfil pedido", r["usou_ia"] and "[IA TECNICO]" in r["texto"])
    checar("C. a IA recebe os fatos calculados como contexto", "fatos" in r["texto"])
    checar("C. resposta da IA ainda diz onde ver no painel", "painel" in r["texto"])

    ia_vazia = lambda *a: "   "
    r = responder("Como está a situação geral?", serie, "Rio Claro", explicar=ia_vazia)
    checar("C. IA com resposta vazia: cai na resposta direta", not r["usou_ia"] and "1.668" in r["texto"])
else:
    print("(pulado) B e C: base real não encontrada em " + CSV_REAL)

# ---- D. privacidade: o texto da pergunta nunca é gravado, só o assunto ----
with tempfile.TemporaryDirectory() as pasta:
    banco = os.path.join(pasta, "teste.db")
    registrar_pergunta(banco, "apoio")
    registrar_pergunta(banco, "evolucao")
    conn = sqlite3.connect(banco)
    linhas = conn.execute("SELECT pergunta, categoria FROM perguntas_usuarios ORDER BY id").fetchall()
    conn.close()
    checar("D. privacidade: cada pergunta conta só o assunto", [c for _, c in linhas] == ["apoio", "evolucao"])
    checar("D. privacidade: a coluna do texto fica vazia (nada escrito pela pessoa é guardado)",
           all(texto is None for texto, _ in linhas))

print()
if falhas:
    print(f"{len(falhas)} checagem(ns) falharam.")
    raise SystemExit(1)
print("Todas as checagens passaram.")
