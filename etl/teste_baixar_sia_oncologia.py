import asyncio
import os
import sqlite3
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baixar_sia_oncologia as sia  # noqa: E402

# Teste do ETL de quimio e radio com um PySUS simulado (a nuvem não alcança o DATASUS).

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def apacs(grupo, n_extra=0):
    """APACs sintéticas com as colunas reais de AQ/AR. Linhas: 2 mulheres de mama (uma delas com 2 APACs), 1 de colo, 1 homem de
    mama, 1 mulher com CID de outro câncer (C61), 1 mulher de pulmão com CID principal vazio e CID da APAC C34."""
    linhas = [
        ("F", "C509", "3543907", "55", "111", "01", "2"), ("F", "C509", "3543907", "55", "111", "01", "2"),
        ("F", "C508", "3543907", "35", "222", "02", "3"), ("F", "C530", "3550308", "62", "333", "03", ""),
        ("M", "C509", "3543907", "60", "444", "01", "1"), ("F", "C619", "3543907", "70", "555", "01", "1"),
        ("F", "", "3543907", "72", "666", "99", "4"),
    ]
    df = pd.DataFrame(linhas, columns=["AP_SEXO", "AP_CIDPRI", "AP_MUNPCN", "AP_NUIDADE", "AP_CNSPCN", "AP_RACACOR", f"{grupo}_ESTADI"])
    df[f"{grupo}_CID10"] = ["C509", "C509", "C508", "C530", "C509", "C619", "C349"]
    return df


class Arq:
    def __init__(self, nome):
        self.name = nome


def pysus_falso(pasta, grupos_sem_mes=()):
    class Falso:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def query(self, dataset, group, state, year):
            return [Arq(f"{group}SP{year % 100:02d}{m:02d}.parquet") for m in range(1, 13)
                    if not (group in grupos_sem_mes and m == 12)]

        async def download(self, arquivo):
            caminho = os.path.join(pasta, arquivo.name)
            apacs(arquivo.name[:2]).to_parquet(caminho)
            return caminho
    return Falso


def main():
    checar("mes_do_arquivo lê AQSP2301.parquet", sia.mes_do_arquivo("AQSP2301.parquet") == (2023, 1) and sia.mes_do_arquivo("x") is None)
    prep = sia.preparar(apacs("AQ"), "AQ")
    checar("preparar: só mulheres com os 7 cânceres (fica fora o homem e o C61); CID vazio usa o da APAC (C34 = pulmão)",
           len(prep) == 5 and sorted(prep["tipo_cancer"]) == ["COLO_UTERO", "MAMA", "MAMA", "MAMA", "PULMAO"])
    checar("preparar: faixa etária com os rótulos do Escudo e residência de 6 dígitos",
           set(prep["faixa"].dropna()) <= {"até 39 anos", "40 a 49", "50 a 69", "70 ou mais"} and prep["codigo_residencia"].str.len().eq(6).all())
    agg = sia.agregar(prep, "QUIMIO", 2023, 1)
    mama = agg[(agg["tipo_cancer"] == "MAMA") & (agg["faixa"] == "50 a 69")].iloc[0]
    checar("agregar: 2 APACs da mesma mulher = 2 APACs e 1 paciente no mês; nenhum identificador no resultado",
           mama["apacs"] == 2 and mama["pacientes"] == 1 and "cartao" not in agg.columns)
    try:
        sia.preparar(pd.DataFrame({"AP_SEXO": ["F"]}), "AQ")
        checar("arquivo sem as colunas dá erro claro", False)
    except RuntimeError as erro:
        checar("arquivo sem as colunas dá erro claro", "AP_CIDPRI" in str(erro))
    with tempfile.TemporaryDirectory() as pasta:
        banco = os.path.join(pasta, "t.db")
        falhas_etl, resumo = asyncio.run(sia.baixar([2023], pysus_falso(pasta), banco))
        conn = sqlite3.connect(banco)
        colunas = [c[1] for c in conn.execute("PRAGMA table_info(oncologia_ambulatorial)")]
        total = conn.execute("SELECT modalidade, COUNT(*), SUM(apacs) FROM oncologia_ambulatorial GROUP BY modalidade").fetchall()
        checar("grava quimio e radio, 12 meses cada, só agregados (sem cartão, CEP ou nascimento)",
               sorted(m for m, _, _ in total) == ["QUIMIO", "RADIO"] and all(a == 5 * 12 for _, _, a in total)
               and not {"cartao", "cep", "nascimento"} & set(colunas))
        checar("sem falhas quando a fonte tem os 12 meses", falhas_etl == [] and len(resumo) == 2)
        asyncio.run(sia.baixar([2023], pysus_falso(pasta), banco))
        checar("rodar de novo substitui (não duplica)",
               conn.execute("SELECT SUM(apacs) FROM oncologia_ambulatorial WHERE modalidade = 'QUIMIO'").fetchone()[0] == 60)
        conn.close()
        banco2 = os.path.join(pasta, "u.db")
        falhas_etl, _ = asyncio.run(sia.baixar([2023], pysus_falso(pasta, grupos_sem_mes=("AR",)), banco2))
        checar("mês que a fonte não lista aparece na lista de falhas (nunca some em silêncio)",
               any("AR 2023/12" in f and "não listou" in f for f in falhas_etl))
    print()
    if falhas:
        print(f"{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("Todas as checagens da quimio e radio passaram.")


if __name__ == "__main__":
    main()
