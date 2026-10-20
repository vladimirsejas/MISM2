import asyncio
import sys

import pandas as pd

import baixar_sih_sp as sih
import baixar_sim_obitos as sim

# =====================================
# SONDAR o arquivo "Mortalidade_Geral_<ANO>" do SIM (rodar no computador do autor; a nuvem não alcança o DATASUS)
#
# Por que: para 2025 e 2026 o PySUS NÃO lista o DO<UF><ANO> que o Escudo lê (ex.: DOSP2024), só `Mortalidade_Geral_<ANO>.parquet`,
# que parece ser do Brasil inteiro. Antes de ensinar o ETL a ler esse arquivo, é preciso saber se ele serve: tem as colunas que o Escudo
# usa? É por residência ou por ocorrência? Até que mês vai? Os números de SP são parecidos com os do DOSP do ano anterior?
#
# NÃO grava nada no banco e NÃO imprime linhas de declaração: só contagens e os nomes das colunas.
#
# Uso (Python 3.12):  py -3.12 etl\sondar_mortalidade_geral.py --ano 2025
# =====================================


def diagnosticar(df):
    """Contagens do arquivo (sem linhas individuais): colunas, se serve ao Escudo e quantos óbitos de mulheres pelos 7 cânceres há
    entre moradores de SP (CODMUNRES começando em 35) e no arquivo todo."""
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    saida = {"linhas": len(df), "colunas": list(df.columns),
             "faltando": [c for c in sim.OBRIGATORIAS if c not in df.columns]}
    if saida["faltando"]:
        return saida
    residencia = df["CODMUNRES"].astype("string").str.replace(r"\D", "", regex=True)
    saida["residentes_sp"] = int(residencia.str.startswith("35").sum())
    saida["ufs_de_residencia"] = int(residencia.str[:2].nunique())
    todos = sim.preparar(df)
    saida["cancer_mulheres_brasil"] = len(todos)
    saida["cancer_mulheres_residentes_sp"] = int(todos["codigo_residencia"].astype("string").str.startswith("35").sum())
    if "DTOBITO" in df.columns:   # só o menor e o maior (nada individual); DDMMAAAA
        datas = pd.to_datetime(df["DTOBITO"].astype("string").str.strip().str.zfill(8), format="%d%m%Y", errors="coerce").dropna()
        if len(datas):
            saida["primeiro_obito"], saida["ultimo_obito"] = str(datas.min().date()), str(datas.max().date())
            saida["meses_com_obito"] = int(datas.dt.to_period("M").nunique())
    saida["tem_local_obito"] = "LOCOCOR" in df.columns
    saida["tem_raca_cor"] = "RACACOR" in df.columns
    saida["tem_idade"] = "IDADE" in df.columns
    return saida


def imprimir(ano, d):
    print(f"\n=== Mortalidade_Geral_{ano}: {d['linhas']:,} linhas".replace(",", "."))
    print("  colunas: " + ", ".join(d["colunas"][:60]) + (" ..." if len(d["colunas"]) > 60 else ""))
    if d["faltando"]:
        print(f"  NÃO SERVE ao Escudo: faltam as colunas {d['faltando']}.")
        return
    print(f"  moradores de SP: {d['residentes_sp']:,} linhas (UFs de residência no arquivo: {d['ufs_de_residencia']})".replace(",", "."))
    print(f"  mulheres com os 7 cânceres: {d['cancer_mulheres_brasil']:,} no arquivo todo; {d['cancer_mulheres_residentes_sp']:,} moradoras de SP".replace(",", "."))
    if "primeiro_obito" in d:
        print(f"  óbitos de {d['primeiro_obito']} a {d['ultimo_obito']} ({d['meses_com_obito']} meses com registro)")
    print(f"  local do óbito: {'sim' if d['tem_local_obito'] else 'NÃO'}; raça/cor: {'sim' if d['tem_raca_cor'] else 'NÃO'}; idade: {'sim' if d['tem_idade'] else 'NÃO'}")
    if d["ufs_de_residencia"] > 1:
        print("  O arquivo é NACIONAL (várias UFs de residência): para o Escudo seria preciso filtrar SP pela residência, e isso não é igual ao DOSP.")


async def sondar(ano, pysus_cls=None):
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    async with pysus_cls() as pysus:
        arquivos = list(await pysus.query(dataset="sim", state=sim.ESTADO, year=ano))
        nomes = [sih.nome_do_arquivo(a) for a in arquivos]
        print(f"O PySUS lista para {ano}: {', '.join(nomes) or 'nada'}")
        alvo = next((a for a in arquivos if sih.nome_do_arquivo(a).upper().startswith("MORTALIDADE_GERAL")), None)
        if alvo is None:
            print("  nenhum Mortalidade_Geral listado: nada a sondar.")
            return None
        print(f"  baixando {sih.nome_do_arquivo(alvo)} (pode ser grande)...")
        baixado, erro = await sih.com_tentativas(sih.nome_do_arquivo(alvo), lambda: pysus.download(alvo))
        if erro:
            print(f"  FALHOU: {erro.splitlines()[0]}")
            return None
        local = sih.caminho_local(baixado)
        try:
            return diagnosticar(pd.read_parquet(local))
        finally:
            sih.remover(local)


def main(ano=None, pysus_cls=None):
    if ano is None:
        ano = int(sys.argv[sys.argv.index("--ano") + 1]) if "--ano" in sys.argv else 2025
    print(f"SONDAR O SIM (Mortalidade_Geral) -- {ano}. Nada é gravado e nenhuma declaração é mostrada.")
    d = asyncio.run(sondar(ano, pysus_cls))
    if d:
        imprimir(ano, d)
        print("\nCole esta saída no chat: com ela eu decido se o ETL do SIM pode ler este arquivo para 2025 e 2026.")
    return d


if __name__ == "__main__":
    main()
