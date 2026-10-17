import asyncio
import sys

# =====================================
# RECONHECER O QUE O PYSUS OFERECE (rodar no computador do autor; a nuvem não alcança o DATASUS)
#
# NÃO baixa dados. Para cada base candidata (população, mortalidade SIM, produção ambulatorial SIA, CNES), pergunta ao PySUS
# quais arquivos existem para SP em 2023 e mostra quantos são e como se chamam; se o nome da base ou do grupo estiver errado,
# mostra o erro (que costuma listar os nomes certos). Serve para escrever o ETL de cada base com os nomes REAIS, sem chute.
#
# Uso (Python 3.12, o mesmo do baixar_sih_sp.py):
#   py -3.12 etl\explorar_pysus.py             só lista (nada é baixado)
#   py -3.12 etl\explorar_pysus.py --amostra   também baixa UM mês de cada base de quimio, radio e CNES e mostra só as colunas
# =====================================

ESTADO, ANO = "SP", 2023
CANDIDATOS = [
    ("sih", "RD", "o que o Escudo já usa (referência: precisa funcionar)"),
    ("sim", "CID10", "óbitos por causa, por município (mortalidade real, dentro e fora do hospital)"),
    ("sim", "CID10", "óbitos: o mesmo, em 2021 (o 2023 pode ainda não estar publicado)", 2021),
    ("sia", "PA", "produção ambulatorial: quimioterapia, radioterapia, mamografia, biópsia"),
    ("sia", "AQ", "APAC de quimioterapia: paciente, sexo, idade, CID e município de residência", 2023),
    ("sia", "AR", "APAC de radioterapia: paciente, sexo, idade, CID e município de residência", 2023),
    ("cnes", "EQ", "equipamentos dos estabelecimentos (ex.: mamógrafos)"),
    ("cnes", "LT", "leitos dos estabelecimentos (ex.: leitos oncológicos)"),
    ("cnes", "ST", "estabelecimentos"),
]


async def reconhecer(pysus_cls=None):
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    async with pysus_cls() as pysus:
        for nome in ("datasets", "list_datasets", "groups", "list_groups"):
            if hasattr(pysus, nome):
                try:
                    valor = getattr(pysus, nome)
                    valor = valor() if callable(valor) else valor
                    if asyncio.iscoroutine(valor):
                        valor = await valor
                    print(f"PySUS.{nome}: {valor}")
                except Exception as erro:  # noqa: BLE001
                    print(f"PySUS.{nome}: erro {type(erro).__name__}: {str(erro)[:200]}")
        for candidato in CANDIDATOS:
            base, grupo, para_que = candidato[:3]
            ano = candidato[3] if len(candidato) > 3 else ANO
            print(f"\n=== {base.upper()} / {grupo}: {para_que}")
            try:
                arquivos = await pysus.query(dataset=base, group=grupo, state=ESTADO, year=ano)
                arquivos = list(arquivos)
                print(f"  OK: {len(arquivos)} arquivo(s) para {ESTADO} em {ano}")
                for a in arquivos[:3]:
                    print(f"    - {getattr(a, 'name', a)}")
            except Exception as erro:  # noqa: BLE001
                print(f"  NÃO FUNCIONOU: {type(erro).__name__}: {str(erro)[:300]}")


SONDAGEM_SIM = [dict(dataset="sim"), dict(dataset="sim", state=ESTADO), dict(dataset="sim", year=2021),
                dict(dataset="sim", group="CID10", state=ESTADO), dict(dataset="sim", group="CID9", state=ESTADO)]
AMOSTRAS = [("sia", "AQ"), ("sia", "AR"), ("cnes", "EQ"), ("cnes", "LT")]


async def sondar_sim(pysus):
    """O SIM veio com 0 arquivos nas consultas por grupo e ano: tenta com menos filtros para descobrir como ele se oferece."""
    print("\n=== SIM: o que aparece com menos filtros")
    for filtros in SONDAGEM_SIM:
        try:
            arquivos = list(await pysus.query(**filtros))
            nomes = ", ".join(str(getattr(a, "name", a)) for a in arquivos[:4])
            print(f"  {filtros}: {len(arquivos)} arquivo(s) {('-> ' + nomes) if arquivos else ''}")
        except Exception as erro:  # noqa: BLE001
            print(f"  {filtros}: NÃO FUNCIONOU {type(erro).__name__}: {str(erro)[:200]}")


async def amostrar(pysus):
    """Baixa UM mês de cada base e mostra só NOMES e tipos das colunas e o número de linhas (nenhum dado de paciente é mostrado)."""
    from baixar_sih_sp import caminho_local, remover
    import pandas as pd
    for base, grupo in AMOSTRAS:
        print(f"\n=== COLUNAS de {base.upper()} / {grupo} ({ESTADO} {ANO}, um mês)")
        try:
            arquivos = sorted(await pysus.query(dataset=base, group=grupo, state=ESTADO, year=ANO),
                              key=lambda a: str(getattr(a, "name", a)))
            if not arquivos:
                print("  nenhum arquivo")
                continue
            baixado = await pysus.download(arquivos[0])
            local = caminho_local(baixado)
            try:
                tabela = pd.read_parquet(local)
            finally:
                remover(local)
            print(f"  arquivo: {getattr(arquivos[0], 'name', arquivos[0])} | {len(tabela):,} linhas".replace(",", "."))
            print("  colunas: " + ", ".join(f"{c}({t})" for c, t in tabela.dtypes.astype(str).items()))
        except Exception as erro:  # noqa: BLE001
            print(f"  NÃO FUNCIONOU: {type(erro).__name__}: {str(erro)[:300]}")


async def amostrar_sim(pysus):
    """O SIM se oferece sem grupo: Mortalidade_Geral_ANO e DO<UF><ANO>. Mostra os nomes de SP em 2022 e as colunas do DOSP."""
    from baixar_sih_sp import caminho_local, remover
    import pandas as pd
    print("\n=== COLUNAS do SIM (óbitos) de SP em 2022")
    try:
        arquivos = list(await pysus.query(dataset="sim", state=ESTADO, year=2022))
        nomes = [str(getattr(a, "name", a)) for a in arquivos]
        print(f"  {len(arquivos)} arquivo(s): " + ", ".join(nomes[:12]))
        alvo = next((a for a in arquivos if str(getattr(a, "name", a)).upper().startswith("DOSP")), None)
        if alvo is None:
            print("  nenhum arquivo DOSP; Mortalidade_Geral pode ser o do Brasil inteiro (grande): não baixei")
            return
        local = caminho_local(await pysus.download(alvo))
        try:
            tabela = pd.read_parquet(local)
        finally:
            remover(local)
        print(f"  arquivo: {getattr(alvo, 'name', alvo)} | {len(tabela):,} linhas".replace(",", "."))
        print("  colunas: " + ", ".join(f"{c}({t})" for c, t in tabela.dtypes.astype(str).items()))
    except Exception as erro:  # noqa: BLE001
        print(f"  NÃO FUNCIONOU: {type(erro).__name__}: {str(erro)[:300]}")


async def tudo(pysus_cls, com_amostra):
    await reconhecer(pysus_cls)
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    async with pysus_cls() as pysus:
        await sondar_sim(pysus)
        if com_amostra:
            await amostrar(pysus)
            await amostrar_sim(pysus)


def main(pysus_cls=None, com_amostra=None):
    if com_amostra is None:
        com_amostra = "--amostra" in sys.argv
    print(f"RECONHECER O PYSUS ({'baixa UM mês de 4 bases só para ver as colunas' if com_amostra else 'nada é baixado'}): {ESTADO}, {ANO}")
    asyncio.run(tudo(pysus_cls, com_amostra))
    print("\nCole esta saída no chat: com os nomes reais eu escrevo o ETL de cada base.")


if __name__ == "__main__":
    main()
