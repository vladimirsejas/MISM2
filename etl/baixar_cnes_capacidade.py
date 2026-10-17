import asyncio
import os
import re
import sqlite3
import sys

import pandas as pd

import baixar_sih_sp as sih

# =====================================
# CAPACIDADE DOS SERVIÇOS (CNES): EQUIPAMENTOS E LEITOS POR MUNICÍPIO -- rodar no computador do autor
#
# Guarda, por município e ano (competência de dezembro, ou a mais recente do ano), quantos equipamentos (EQ) e leitos (LT) existem,
# por código CRU do CNES. Os códigos (TIPEQUIP/CODEQUIP e TP_LEITO/CODLEITO) NÃO são traduzidos aqui: o dicionário do CNES não vem no
# arquivo, então o Escudo ainda não nomeia "mamógrafo" ou "leito oncológico" -- só guarda para usar quando o dicionário for conferido.
#
# Tabelas: cnes_equipamentos (ano, competencia, codufmun, tipequip, codequip, existentes, em_uso, sus) e
#          cnes_leitos (ano, competencia, codufmun, tp_leito, codleito, existentes, sus).
#
# Uso (Python 3.12):  py -3.12 etl\baixar_cnes_capacidade.py [--anos 2013-2025]
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
ESTADO = "SP"
RIO_CLARO = "354390"
TABELAS = {"EQ": "cnes_equipamentos", "LT": "cnes_leitos"}
CHAVES = {"EQ": ("TIPEQUIP", "CODEQUIP"), "LT": ("TP_LEITO", "CODLEITO")}


def mes_do_arquivo(nome):
    achado = re.search(r"(?:EQ|LT)[A-Z]{2}(\d{2})(\d{2})", nome.upper())
    return (2000 + int(achado.group(1)), int(achado.group(2))) if achado else None


def numero(serie):
    return pd.to_numeric(serie, errors="coerce").fillna(0)


def agregar(df, grupo, ano, mes):
    """Soma por município e código. EQ: existentes, em uso e os que atendem o SUS (IND_SUS = 1). LT: existentes e do SUS."""
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    chave1, chave2 = CHAVES[grupo]
    exigidas = ["CODUFMUN", chave1, chave2, "QT_EXIST"] + (["QT_USO", "IND_SUS"] if grupo == "EQ" else ["QT_SUS"])
    faltando = [c for c in exigidas if c not in df.columns]
    if faltando:
        raise RuntimeError(f"arquivo sem as colunas {faltando}; colunas: {list(df.columns)[:40]}")
    base = pd.DataFrame({
        "codufmun": df["CODUFMUN"].astype("string").str.replace(r"\D", "", regex=True).str[:6],
        chave1.lower(): df[chave1].astype("string").str.strip(),
        chave2.lower(): df[chave2].astype("string").str.strip(),
        "existentes": numero(df["QT_EXIST"]),
    })
    if grupo == "EQ":
        base["em_uso"] = numero(df["QT_USO"])
        base["sus"] = base["existentes"].where(df["IND_SUS"].astype("string").str.strip() == "1", 0)
    else:
        base["sus"] = numero(df["QT_SUS"])
    chaves = ["codufmun", chave1.lower(), chave2.lower()]
    soma = base.groupby(chaves, dropna=False).sum(numeric_only=True).reset_index()
    soma = soma[soma["existentes"] > 0]
    soma.insert(0, "competencia", mes)
    soma.insert(0, "ano", ano)
    return soma


def perfil(tabela, grupo, ano):
    chave1, chave2 = (c.lower() for c in CHAVES[grupo])
    topo = lambda t: ", ".join(f"{r[chave1]}/{r[chave2]}={int(r.existentes)}" for _, r in
                               t.sort_values("existentes", ascending=False).head(10).iterrows())
    rio = tabela[tabela["codufmun"] == RIO_CLARO]
    por_codigo = tabela.groupby([chave1, chave2])["existentes"].sum().reset_index()
    print(f"    PERFIL CNES {grupo} {ano}: {len(tabela):,} linhas (município x código)".replace(",", "."))
    print(f"      SP, mais comuns (tipo/código=quantidade): {topo(por_codigo)}")
    print(f"      Rio Claro: {topo(rio) if len(rio) else 'sem linhas'}")


def gravar(tabela, grupo, ano, banco=BANCO):
    nome = TABELAS[grupo]
    conn = sqlite3.connect(banco)
    try:
        if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (nome,)).fetchone():
            conn.execute(f"DELETE FROM {nome} WHERE ano = ?", (ano,))
        tabela.to_sql(nome, conn, if_exists="append", index=False)
        conn.commit()
    finally:
        conn.close()


async def baixar(anos, pysus_cls=None, banco=BANCO, verboso=True):
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    falhas, resumo, perfilados = [], [], set()
    async with pysus_cls() as pysus:
        for grupo in TABELAS:
            for ano in anos:
                arquivos, erro = await sih.com_tentativas(
                    f"consulta CNES {grupo} {ano}", lambda: pysus.query(dataset="cnes", group=grupo, state=ESTADO, year=ano))
                if erro:
                    falhas.append(f"CNES {grupo} {ano}: a consulta falhou: {erro.splitlines()[0]}")
                    continue
                por_mes = {}
                for arquivo in arquivos or []:
                    chave = mes_do_arquivo(sih.nome_do_arquivo(arquivo))
                    if chave and chave[0] == ano:
                        por_mes.setdefault(chave[1], []).append(arquivo)
                if not por_mes:
                    falhas.append(f"CNES {grupo} {ano}: a fonte não listou nenhum mês")
                    continue
                mes = 12 if 12 in por_mes else max(por_mes)  # dezembro, ou a competência mais recente do ano
                partes = []
                for arquivo in por_mes[mes]:
                    baixado, erro_arq = await sih.com_tentativas(sih.nome_do_arquivo(arquivo), lambda: pysus.download(arquivo))
                    if erro_arq:
                        falhas.append(f"CNES {grupo} {ano}/{mes:02d}: {erro_arq.splitlines()[0]}")
                        continue
                    local = sih.caminho_local(baixado)
                    try:
                        partes.append(agregar(pd.read_parquet(local), grupo, ano, mes))
                    except Exception as erro_leitura:  # noqa: BLE001
                        falhas.append(f"CNES {grupo} {ano}/{mes:02d}: {type(erro_leitura).__name__}: {str(erro_leitura)[:200]}")
                    finally:
                        sih.remover(local)
                if partes:
                    tabela = pd.concat(partes, ignore_index=True)
                    if grupo not in perfilados:
                        perfil(tabela, grupo, ano)
                        perfilados.add(grupo)
                    gravar(tabela, grupo, ano, banco)
                    resumo.append((grupo, ano, mes, len(tabela)))
                    print(f"  CNES {grupo} {ano} (competência {mes:02d}): {len(tabela):,} linhas".replace(",", "."))
    return falhas, resumo


def _anos(argv):
    if "--anos" in argv:
        inicio, _, fim = argv[argv.index("--anos") + 1].partition("-")
        return list(range(int(inicio), int(fim or inicio) + 1))
    return list(range(2013, 2026))


def main(pysus_cls=None, anos=None, banco=BANCO, verboso=True):
    anos = anos or _anos(sys.argv)
    print(f"CAPACIDADE (CNES: equipamentos e leitos) {anos[0]}-{anos[-1]}: códigos crus, sem tradução")
    falhas, resumo = asyncio.run(baixar(anos, pysus_cls, banco, verboso))
    if falhas:
        print(f"\nO QUE FALHOU OU NÃO EXISTE NA FONTE ({len(falhas)}):")
        for f in falhas[:30]:
            print("  -", f)
    return falhas, resumo


if __name__ == "__main__":
    main()
