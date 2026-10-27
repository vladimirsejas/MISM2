"""Exporta o banco SQLite do MISM2 para Parquet (uma tabela = um arquivo) e guarda o esquema em esquema.sql.

Saída: <raiz do site>/dados_parquet/mism2/<tabela>.parquet  e  esquema.sql
O caminho inverso (Parquet -> SQLite, usado pelo painel) está em algoritimos/fonte_parquet.py.

  python etl/exportar_banco_parquet.py [caminho_do_banco.db]

perguntas_usuarios guarda o texto digitado por pessoas na Lia: só o esquema é exportado, sem as linhas.
"""
import os
import sqlite3
import sys

import pyarrow as pa
import pyarrow.parquet as pq

RAIZ_PROJETO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BANCO_PADRAO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
DESTINO = os.path.abspath(os.path.join(RAIZ_PROJETO, "..", "dados_parquet", "mism2"))
SEM_LINHAS = {"perguntas_usuarios"}
PEDACO = 200_000


def tipo_arrow(conn, tabela, coluna):
    """Tipo Arrow pelo que existe de fato nos dados (SQLite não impõe tipo por coluna)."""
    tipos = {t for (t,) in conn.execute(f'select distinct typeof("{coluna}") from "{tabela}"') if t != "null"}
    if not tipos:
        return pa.string()
    if tipos == {"integer"}:
        return pa.int64()
    if tipos <= {"integer", "real"}:
        return pa.float64()
    if tipos == {"text"}:
        return pa.string()
    if tipos == {"blob"}:
        return pa.binary()
    raise ValueError(f"{tabela}.{coluna} mistura tipos {sorted(tipos)}: decidir a conversão antes de exportar")


def main(banco):
    os.makedirs(DESTINO, exist_ok=True)
    conn = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    ddl = conn.execute("select type, name, tbl_name, sql from sqlite_master where sql is not null "
                       "and name not like 'sqlite_%' order by case type when 'table' then 0 else 1 end, name").fetchall()
    with open(os.path.join(DESTINO, "esquema.sql"), "w", encoding="utf-8") as f:
        for _, _, _, sql in ddl:
            f.write(sql.strip() + ";\n\n")
    tabelas = [n for t, n, _, _ in ddl if t == "table"]
    for tabela in tabelas:
        colunas = [r[1] for r in conn.execute(f'pragma table_info("{tabela}")')]
        tipos = [tipo_arrow(conn, tabela, c) for c in colunas]
        esquema = pa.schema(list(zip(colunas, tipos)))
        destino = os.path.join(DESTINO, f"{tabela}.parquet")
        total = 0
        with pq.ParquetWriter(destino, esquema, compression="zstd") as w:
            if tabela in SEM_LINHAS:
                w.write_table(esquema.empty_table())
            else:
                cur = conn.execute(f'select * from "{tabela}" order by rowid')
                while True:
                    linhas = cur.fetchmany(PEDACO)
                    if not linhas:
                        break
                    cols = list(zip(*linhas))
                    w.write_table(pa.table([pa.array(c, type=t) for c, t in zip(cols, tipos)], schema=esquema))
                    total += len(linhas)
        print(f"{tabela}: {total} linhas, {os.path.getsize(destino) / 1024:.0f} KB")
    conn.close()


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else BANCO_PADRAO)
