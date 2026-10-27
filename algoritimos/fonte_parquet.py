"""Dados do MISM2 vindos do Parquet (sem guardar o banco no projeto).

A fonte dos dados passou a ser a pasta `dados_parquet/` do site (uma tabela = um arquivo, mais o `esquema.sql`).
Para o painel não precisar mudar uma linha de SQL, o SQLite que ele sempre usou é MONTADO a partir desses
arquivos, uma vez, num cache local (`.cache_mism/escudo_feminino.db`, fora do git e fora da pasta `banco\\`),
e refeito sozinho quando o Parquet muda.

  - `caminho_do_banco(legado)`: devolve o SQLite a usar (é o que `configuracao_geografica.BANCO` chama).
  - CNES: `unidades_saude.py` lê tbEstabelecimento etc. por aqui quando o CSV não está no computador
    (`dados_parquet/cnes/<tabela>.parquet`).

Exportar de novo (SQLite -> Parquet): `py etl\\exportar_banco_parquet.py`.
"""
import os
import re
import sqlite3
import time

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ_SITE = os.path.dirname(RAIZ_PROJETO)
PASTA_PARQUET = os.environ.get("ESCUDO_PARQUET_PASTA") or os.path.join(RAIZ_SITE, "dados_parquet")
PASTA_BANCO = os.path.join(PASTA_PARQUET, "mism2")
PASTA_CNES = os.path.join(PASTA_PARQUET, "cnes")
PASTA_CACHE = os.environ.get("ESCUDO_CACHE_PASTA") or os.path.join(RAIZ_SITE, ".cache_mism")
LOTE = 100_000


# ---------- obter os arquivos (hospedagem) ----------

def garantir_dados():
    """Se a pasta dados_parquet não está no computador (hospedagem), baixa-a de um dataset do Hugging Face.

    Usa as variáveis MISM_DATASET (ex.: "usuario/mism-dados") e HF_TOKEN (dataset privado). Na hospedagem do Streamlit elas
    vêm de st.secrets (segredos de nível superior viram variáveis de ambiente). Com os dados já na pasta, não faz nada."""
    if disponivel():
        return False
    repo = os.environ.get("MISM_DATASET")
    if not repo:
        return False
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, repo_type="dataset", token=os.environ.get("HF_TOKEN") or None, local_dir=PASTA_PARQUET)
    return True


# ---------- banco ----------

def disponivel():
    return os.path.isfile(os.path.join(PASTA_BANCO, "esquema.sql"))


def _carimbo():
    """Muda quando qualquer arquivo do banco em Parquet muda (nome, tamanho, data)."""
    itens = []
    for nome in sorted(os.listdir(PASTA_BANCO)):
        if nome.endswith((".parquet", ".sql")):
            st = os.stat(os.path.join(PASTA_BANCO, nome))
            itens.append(f"{nome}:{st.st_size}:{int(st.st_mtime)}")
    return "\n".join(itens)


def _montar(destino):
    import pyarrow.parquet as pq

    conn = sqlite3.connect(destino)
    conn.execute("pragma journal_mode = off")
    conn.execute("pragma synchronous = off")
    with open(os.path.join(PASTA_BANCO, "esquema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    for nome in sorted(os.listdir(PASTA_BANCO)):
        if not nome.endswith(".parquet"):
            continue
        tabela = nome[:-len(".parquet")]
        arq = pq.ParquetFile(os.path.join(PASTA_BANCO, nome))
        colunas = arq.schema_arrow.names
        sql = f'insert into "{tabela}" ({", ".join(chr(34) + c + chr(34) for c in colunas)}) values ({", ".join("?" * len(colunas))})'
        for lote in arq.iter_batches(batch_size=LOTE):
            conn.executemany(sql, zip(*(c.to_pylist() for c in lote.columns)))
        conn.commit()
    conn.execute("pragma optimize")
    conn.commit()
    conn.close()


def caminho_do_banco(legado):
    """SQLite que o painel deve abrir. `ESCUDO_BANCO_SQLITE` manda sempre (testes, cargas); sem Parquet, vale o `legado`."""
    forcado = os.environ.get("ESCUDO_BANCO_SQLITE")
    if forcado:
        return forcado
    if not disponivel():
        return legado
    os.makedirs(PASTA_CACHE, exist_ok=True)
    destino = os.path.join(PASTA_CACHE, "escudo_feminino.db")
    marca = destino + ".carimbo"
    carimbo = _carimbo()

    def em_dia():
        try:
            with open(marca, encoding="utf-8") as f:
                return os.path.isfile(destino) and f.read() == carimbo
        except OSError:
            return False

    if em_dia():
        return destino
    trava = destino + ".trava"
    try:
        fd = os.open(trava, os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # só um processo monta; os outros esperam
    except FileExistsError:
        for _ in range(600):
            time.sleep(1)
            if em_dia():
                return destino
            if not os.path.exists(trava):
                break
        if em_dia():
            return destino
        return legado if os.path.isfile(legado) else destino
    try:
        os.close(fd)
        if em_dia():
            return destino
        provisorio = destino + ".montando"
        for p in (provisorio, destino):
            if os.path.exists(p):
                os.remove(p)
        _montar(provisorio)
        os.replace(provisorio, destino)
        with open(marca, "w", encoding="utf-8") as f:
            f.write(carimbo)
    finally:
        try:
            os.remove(trava)
        except OSError:
            pass
    return destino


# ---------- CNES (tabelas em Parquet no lugar dos CSVs) ----------

def _tabela_do_csv(caminho):
    """.../tbEstabelecimento202608.csv -> 'tbEstabelecimento' (o nome no Parquet não leva o mês)."""
    m = re.match(r"^(.*?)(\d{6})\.csv$", os.path.basename(caminho), re.IGNORECASE)
    return m.group(1) if m else None


def parquet_do_csv(caminho):
    tabela = _tabela_do_csv(caminho)
    if not tabela:
        return None
    p = os.path.join(PASTA_CNES, tabela + ".parquet")
    return p if os.path.isfile(p) else None


def competencia_cnes():
    """AAAAMM das tabelas do CNES em Parquet (arquivo COMPETENCIA.txt), ou None."""
    try:
        with open(os.path.join(PASTA_CNES, "COMPETENCIA.txt"), encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def existe(caminho):
    """Como os.path.isfile, mas também vale o CSV que só existe como Parquet."""
    return os.path.isfile(caminho) or parquet_do_csv(caminho) is not None


def ler(caminho, usecols=None, nrows=None, chunksize=None, **_ignorados):
    """Como pandas.read_csv(caminho, dtype=str, ...) para uma tabela do CNES em Parquet.
    Com `chunksize` devolve um gerador de pedaços; com `nrows=0`, só o cabeçalho. Tudo vem como texto, sem NaN."""
    import pandas as pd
    import pyarrow.parquet as pq

    arq = pq.ParquetFile(parquet_do_csv(caminho))
    colunas = list(usecols) if usecols is not None else None

    def para_df(tabela):
        return tabela.to_pandas().fillna("").astype(str)

    if nrows == 0:
        return pd.DataFrame(columns=colunas or arq.schema_arrow.names)
    if chunksize:
        def pedacos():
            for lote in arq.iter_batches(batch_size=chunksize, columns=colunas):
                import pyarrow as pa
                yield para_df(pa.Table.from_batches([lote]))
        return pedacos()
    df = para_df(arq.read(columns=colunas))
    return df.head(nrows) if nrows else df
