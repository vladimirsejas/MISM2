import asyncio
import sys

# =====================================
# RECONHECER O QUE O PYSUS OFERECE (rodar no computador do autor; a nuvem não alcança o DATASUS)
#
# NÃO baixa dados. Para cada base candidata (população, mortalidade SIM, produção ambulatorial SIA, CNES), pergunta ao PySUS
# quais arquivos existem para SP em 2023 e mostra quantos são e como se chamam; se o nome da base ou do grupo estiver errado,
# mostra o erro (que costuma listar os nomes certos). Serve para escrever o ETL de cada base com os nomes REAIS, sem chute.
#
# Uso (Python 3.12, o mesmo do baixar_sih_sp.py):  py -3.12 etl\explorar_pysus.py
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


def main(pysus_cls=None):
    print(f"RECONHECER O PYSUS (nada é baixado): {ESTADO}, {ANO}")
    asyncio.run(reconhecer(pysus_cls))
    print("\nCole esta saída no chat: com os nomes reais eu escrevo o ETL de cada base.")


if __name__ == "__main__":
    main()
