import asyncio
import os
import sqlite3
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baixar_cnes_capacidade as cnes  # noqa: E402
import baixar_sia_oncologia as sia  # noqa: E402
import baixar_sim_obitos as sim  # noqa: E402

# Teste dos ETLs de mortalidade (SIM) e capacidade (CNES) com um PySUS simulado.

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


class Arq:
    def __init__(self, nome):
        self.name = nome


def obitos():
    linhas = [  # SEXO, CAUSABAS, CODMUNRES, IDADE, LOCOCOR, RACACOR
        ("2", "C509", "354390", "455", "1", "1"), ("2", "C509", "354390", "455", "3", "1"), ("2", "C539", "355030", "462", "1", "4"),
        ("1", "C509", "354390", "460", "1", "1"), ("2", "C619", "354390", "470", "1", "1"), ("2", "I219", "354390", "480", "1", "1"),
        ("2", "C349", "354390", "501", "2", "2"),
    ]
    return pd.DataFrame(linhas, columns=["SEXO", "CAUSABAS", "CODMUNRES", "IDADE", "LOCOCOR", "RACACOR"])


def equipamentos():
    return pd.DataFrame({"CODUFMUN": ["354390", "354390", "355030"], "TIPEQUIP": ["1", "1", "2"], "CODEQUIP": ["12", "12", "30"],
                         "QT_EXIST": [2, 1, 5], "QT_USO": [2, 0, 4], "IND_SUS": ["1", "0", "1"]})


def leitos():
    return pd.DataFrame({"CODUFMUN": ["354390", "354390"], "TP_LEITO": ["1", "1"], "CODLEITO": ["45", "45"],
                         "QT_EXIST": [10, 4], "QT_SUS": [8, 0]})


def pysus_falso(pasta):
    class Falso:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def query(self, dataset, state, year, group=None):
            if dataset == "sim":
                return [Arq(f"DOSP{year}.parquet"), Arq(f"DOBR{year}.parquet")]
            return [Arq(f"{group}SP{year % 100:02d}{m:02d}.parquet") for m in range(1, 13)]

        async def download(self, arquivo):
            caminho = os.path.join(pasta, arquivo.name)
            n = arquivo.name
            (obitos() if n.startswith("DO") else equipamentos() if n.startswith("EQ") else leitos()).to_parquet(caminho)
            return caminho
    return Falso


def main():
    checar("idade do SIM: 455 = 55 anos, 501 = 101, 010 = menos de 1 ano, lixo = None",
           sim.idade_sim("455") == 55 and sim.idade_sim("501") == 101 and sim.idade_sim("010") == 0 and sim.idade_sim("x") is None)
    prep = sim.preparar(obitos())
    checar("SIM: só mulheres com os 7 cânceres (fica fora o homem, o C61 e o infarto)",
           len(prep) == 4 and sorted(prep["tipo_cancer"]) == ["COLO_UTERO", "MAMA", "MAMA", "PULMAO"])
    checar("SIM: município de residência com 6 dígitos e faixas do Escudo",
           prep["codigo_residencia"].str.len().eq(6).all() and set(prep["faixa"]) <= {"até 39 anos", "40 a 49", "50 a 69", "70 ou mais", "sem_info"})
    agg = sim.agregar(prep, 2022)
    checar("SIM: agregado soma 4 óbitos e não carrega número de declaração", int(agg["obitos"].sum()) == 4 and "numerodo" not in agg.columns)
    try:
        sim.preparar(pd.DataFrame({"SEXO": ["2"]}))
        checar("SIM: arquivo sem as colunas dá erro claro", False)
    except RuntimeError as erro:
        checar("SIM: arquivo sem as colunas dá erro claro", "CAUSABAS" in str(erro))
    checar("alerta de raça/cor dispara quando parda < amarela e fica calado quando está certo",
           sia.alerta_raca({"4": 1, "3": 9}, "4", "3") is not None and sia.alerta_raca({"4": 9, "3": 1}, "4", "3") is None)

    eq = cnes.agregar(equipamentos(), "EQ", 2023, 12)
    rio = eq[eq["codufmun"] == "354390"].iloc[0]
    checar("CNES EQ: soma existentes (3), em uso (2) e os do SUS (2) por município e código",
           rio["existentes"] == 3 and rio["em_uso"] == 2 and rio["sus"] == 2)
    lt = cnes.agregar(leitos(), "LT", 2023, 12)
    checar("CNES LT: soma 14 leitos, 8 do SUS", lt.iloc[0]["existentes"] == 14 and lt.iloc[0]["sus"] == 8)
    checar("CNES: mês do arquivo lido do nome", cnes.mes_do_arquivo("EQSP2312.parquet") == (2023, 12))

    with tempfile.TemporaryDirectory() as pasta:
        banco = os.path.join(pasta, "t.db")
        f1, r1 = asyncio.run(sim.baixar([2022, 2023], pysus_falso(pasta), banco))
        conn = sqlite3.connect(banco)
        total = conn.execute("SELECT ano, SUM(obitos) FROM obitos_sim GROUP BY ano").fetchall()
        checar("SIM: grava os dois anos (4 óbitos cada), usa DOSP e ignora DOBR", total == [(2022, 4), (2023, 4)] and f1 == [])
        asyncio.run(sim.baixar([2022], pysus_falso(pasta), banco))
        checar("SIM: rodar de novo substitui o ano (não duplica)",
               conn.execute("SELECT SUM(obitos) FROM obitos_sim WHERE ano = 2022").fetchone()[0] == 4)
        f2, r2 = asyncio.run(cnes.baixar([2023], pysus_falso(pasta), banco))
        n_eq = conn.execute("SELECT COUNT(*) FROM cnes_equipamentos").fetchone()[0]
        n_lt = conn.execute("SELECT COUNT(*) FROM cnes_leitos").fetchone()[0]
        checar("CNES: usa dezembro e grava equipamentos e leitos agregados", n_eq == 2 and n_lt == 1 and f2 == [])
        conn.close()
    print()
    if falhas:
        print(f"{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("Todas as checagens de SIM e CNES passaram.")


if __name__ == "__main__":
    main()
