import os
import sqlite3

import pandas as pd

# =====================================
# VALIDAR O BANCO DEPOIS DA CARGA
# Mostra quantas internações há por câncer (no Estado e em Rio
# Claro), quantos municípios entraram e se o mês foi gravado. Os 7
# cânceres precisam aparecer: se faltar algum, a carga avisa no fim
# qual arquivo ficou de fora e por quê.
# Uso: py etl\validar_banco.py
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
CANCERES = ["COLORRETAL", "COLO_UTERO", "MAMA", "OVARIO", "PELE_NAO_MELANOMA", "PULMAO", "TIREOIDE"]

conexao = sqlite3.connect(BANCO)

print("\nTOTAL DE REGISTROS\n")
print(pd.read_sql("SELECT COUNT(*) AS total FROM internacoes", conexao))

print("\nINTERNAÇÕES POR CÂNCER (Estado, Rio Claro e moradoras de outro estado)\n")
por_cancer = pd.read_sql(
    """
    SELECT tipo_cancer,
           COUNT(*) AS estado,
           SUM(CASE WHEN municipio = 'RIO_CLARO' THEN 1 ELSE 0 END) AS rio_claro,
           SUM(CASE WHEN municipio = 'OUTRO_ESTADO' THEN 1 ELSE 0 END) AS outro_estado,
           MIN(ano) AS primeiro_ano, MAX(ano) AS ultimo_ano
    FROM internacoes
    GROUP BY tipo_cancer
    ORDER BY tipo_cancer
    """,
    conexao,
)
print(por_cancer.to_string(index=False))

print("\nMUNICÍPIOS COM INTERNAÇÕES:",
      conexao.execute("SELECT COUNT(DISTINCT municipio) FROM internacoes WHERE municipio <> 'OUTRO_ESTADO'").fetchone()[0])

colunas = [linha[1] for linha in conexao.execute("PRAGMA table_info(internacoes)")]
if "mes" in colunas:
    com_mes = conexao.execute("SELECT COUNT(*) FROM internacoes WHERE mes IS NOT NULL").fetchone()[0]
    print("MÊS GRAVADO:", "sim" if com_mes else "não (a carga não achou MES_CMPT)")
else:
    print("MÊS GRAVADO: não (banco de uma carga antiga -- rode py etl\\carga_todas_bases.py)")

conexao.close()

faltando = sorted(set(CANCERES) - set(por_cancer["tipo_cancer"]))
print()
if faltando:
    print("FALTAM NO BANCO:", ", ".join(faltando))
    print("Rode py etl\\carga_todas_bases.py e veja no fim da mensagem por que ficaram de fora.")
else:
    print("OK: os 7 cânceres estão no banco.")
