import asyncio
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sondar_mortalidade_geral as sm  # noqa: E402

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


nacional = pd.DataFrame({
    "CAUSABAS": ["C509", "C509", "C189", "I10", "C509", "C73"],
    "SEXO": ["2", "2", "2", "2", "1", "2"],
    "CODMUNRES": ["3543907", "3304557", "3550308", "3550308", "3543907", "3543907"],   # Rio Claro, RJ, SP capital, SP, Rio Claro, Rio Claro
    "IDADE": ["460", "455", "470", "450", "460", "440"],
    "LOCOCOR": ["1", "3", "1", "1", "1", "1"], "RACACOR": ["1"] * 6,
    "DTOBITO": ["05012025", "20022025", "01032025", "15032025", "10032025", "30042025"],
})
d = sm.diagnosticar(nacional)
checar("conta mulheres com os 7 cânceres: 4 no arquivo (o homem e a causa I10 ficam fora) e 3 moradoras de SP",
       d["cancer_mulheres_brasil"] == 4 and d["cancer_mulheres_residentes_sp"] == 3)
checar("reconhece arquivo nacional (2 UFs de residência) e conta moradores de SP (5 de 6 linhas)",
       d["ufs_de_residencia"] == 2 and d["residentes_sp"] == 5)
checar("lê o primeiro e o último óbito (só datas limite) e os meses com registro",
       d["primeiro_obito"] == "2025-01-05" and d["ultimo_obito"] == "2025-04-30" and d["meses_com_obito"] == 4)
checar("sem as colunas obrigatórias diz o que falta e não calcula nada",
       sm.diagnosticar(pd.DataFrame({"X": [1]}))["faltando"] == ["CAUSABAS", "SEXO", "CODMUNRES"])


class Arq:
    def __init__(self, n):
        self.name = n


class PySUSFalso:
    baixados = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def query(self, dataset, state, year):
        return [Arq(f"Mortalidade_Geral_{year}.parquet")] if year != 2020 else [Arq("DOSP2020.dbc")]

    async def download(self, a):
        PySUSFalso.baixados.append(a.name)
        caminho = os.path.join(__import__("tempfile").mkdtemp(), a.name)
        nacional.to_parquet(caminho, index=False)
        return type("B", (), {"path": caminho})()


r = asyncio.run(sm.sondar(2025, PySUSFalso))
checar("sonda baixa SÓ o Mortalidade_Geral e devolve a contagem", PySUSFalso.baixados == ["Mortalidade_Geral_2025.parquet"]
       and r["cancer_mulheres_brasil"] == 4)
PySUSFalso.baixados.clear()
checar("sem Mortalidade_Geral listado não baixa nada", asyncio.run(sm.sondar(2020, PySUSFalso)) is None and PySUSFalso.baixados == [])
print()
print("Todas as checagens passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
