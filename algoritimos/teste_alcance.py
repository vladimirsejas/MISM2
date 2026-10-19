"""Teste do alcance do banco (autor, 19/10/2026): a Lia sabe quantas doenças e cidades o banco tem."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entendimento as ent
import inteligencia as ig
from lia import Contexto, caminho, responder

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE internacoes (ano INT, tipo_cancer TEXT, municipio TEXT, uf_residencia TEXT, municipio_hospital TEXT, cnes TEXT)")
conn.execute("CREATE TABLE municipios (codigo_ibge TEXT, origem TEXT, nome TEXT, uf TEXT)")
conn.executemany("INSERT INTO municipios VALUES (?,?,?,?)", [("3543907", "RIO_CLARO", "Rio Claro", "SP"), ("3509502", "CAMPINAS", "Campinas", "SP")])
linhas = ([(2020, "MAMA", "RIO_CLARO", "SP", "354390", "1")] * 5 + [(2021, "COLO_UTERO", "CAMPINAS", "SP", "350950", "2")] * 3
          + [(2022, "MAMA", "OUTRO_ESTADO", "MG", "350950", "2")] * 2)
conn.executemany("INSERT INTO internacoes VALUES (?,?,?,?,?,?)", linhas)
conn.execute("CREATE TABLE populacao_mulheres (codigo_ibge TEXT, municipio TEXT, ano INT, populacao INT, fonte TEXT)")
conn.execute("INSERT INTO populacao_mulheres VALUES ('3543907','Rio Claro',2022,100,'IBGE')")

info = ig.alcance_dados(conn)
checar("lê os cânceres do banco (2 tipos), o período e o total", info and len(info["canceres"]) == 2
       and (info["ano_ini"], info["ano_fim"], info["internacoes"]) == (2020, 2022, 10))
checar("conta as cidades de SP (2) sem contar OUTRO_ESTADO e lista a de mais internações primeiro",
       info["n_cidades"] == 2 and info["cidades"][0][0] == "Rio Claro" and info["internacoes_de_fora"] == 2
       and info["ufs_de_fora"] == ["MG"])
com = {b["tabela"] for b in info["bases"] if b["linhas"]}
checar("sabe que a população foi carregada e que as outras bases faltam", com == {"populacao_mulheres"})
texto = " ".join(ig.leitura_alcance(info))
checar("a leitura diz doenças, cidades, período, outros estados e o que não tem",
       "2 tipos de câncer" in texto and "mama (7)" in texto and "2 cidades" in texto and "2020 a 2022" in texto
       and "outros estados (de MG)" in texto and "Ainda não foram carregados" in texto and "casos novos" in texto)
checar("banco vazio: None, sem quebrar", ig.alcance_dados(sqlite3.connect(":memory:")) is None)

for pergunta in ("quais doenças você tem?", "quantas cidades tem no banco?", "quais cidades você conhece", "que dados você tem",
                 "qual o alcance dos dados", "quais cânceres vocês acompanham", "o que tem no banco de dados"):
    e = ent.compreender(pergunta)
    checar(f"entende {pergunta!r} como alcance do banco", e.tipo == "intencao" and e.intencao == "alcance")
for pergunta in ("quais cânceres estão aumentando?", "quais cidades têm mais câncer de mama proporcionalmente?",
                 "quantas internações de mama?", "quais os sintomas do câncer de mama?"):
    e = ent.compreender(pergunta)
    checar(f"não confunde {pergunta!r} com o alcance", e.intencao != "alcance")

import pandas as pd
serie = pd.DataFrame({"grupo": ["MUNICIPIO"], "ano": [2020], "tipo_cancer": ["MAMA"], "internacoes": [1]})
r = responder(Contexto(serie=serie, cidade="Rio Claro", alcance=info), caminho("alcance"))
checar("a Lia responde o alcance com os números do banco, sem IA", "2 tipos de câncer" in r.fala and "Rio Claro" in r.fala)
r = responder(Contexto(serie=serie, cidade="Rio Claro"), caminho("alcance"))
checar("sem a leitura do banco, a Lia admite em vez de inventar", "Não consegui ler o banco" in r.fala)

print()
print("Todas as checagens do alcance passaram." if not falhas else f"{len(falhas)} checagem(ns) falharam.")
sys.exit(1 if falhas else 0)
