import asyncio
import os
import re
import sqlite3
import sys

import pandas as pd

import baixar_sia_oncologia as sia
import baixar_sih_sp as sih

# =====================================
# MORTALIDADE REAL POR CÂNCER (SIM, declarações de óbito) -- rodar no computador do autor
#
# Por que: o Escudo só conhece os óbitos que acontecem DURANTE uma internação (SIH). O SIM conta todas as mortes por causa básica,
# em qualquer lugar (hospital, casa, via pública), por município de RESIDÊNCIA. Isso mostra o que o SIH não vê.
#
# Privacidade: SÓ agregados são gravados (tabela `obitos_sim`: ano, codigo_residencia, tipo_cancer, faixa, local_obito, raca_cor,
# obitos). Nenhum número de declaração, data exata ou endereço entra no banco.
#
# O SIM se oferece no PySUS sem grupo: DO<UF><ANO> (ex.: DOSP2022) e Mortalidade_Geral_<ANO>. Usa-se o DOSP.
#
# Uso (Python 3.12):  py -3.12 etl\baixar_sim_obitos.py [--anos 2013-2023]
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
ESTADO = "SP"
FEMININO = {"2", "F", "FEMININO"}  # SIM: 1 masculino, 2 feminino, 0/9 ignorado
OBRIGATORIAS = ["CAUSABAS", "SEXO", "CODMUNRES"]


def idade_sim(valor):
    """O SIM codifica a idade em 3 dígitos: 4xx = anos (435 = 35 anos), 5xx = 100 anos ou mais, 0xx a 3xx = menos de 1 ano."""
    texto = str(valor).strip()
    if not texto.isdigit() or len(texto) != 3:
        return None
    unidade, numero = texto[0], int(texto[1:])
    if unidade == "4":
        return numero
    if unidade == "5":
        return 100 + numero
    if unidade in "0123":
        return 0
    return None


def preparar(df):
    """Mulheres que morreram de um dos 7 cânceres (causa básica), só com o que o Escudo usa."""
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    faltando = [c for c in OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise RuntimeError(f"arquivo sem as colunas {faltando}; colunas: {list(df.columns)[:40]}")
    sexo = df["SEXO"].astype("string").fillna("").str.strip().str.upper()
    causa = df["CAUSABAS"].astype("string").fillna("").str.strip().str.upper()
    tipo = causa.str[:3].map(sia.CID_PARA_CANCER)
    manter = sexo.isin(FEMININO) & tipo.notna()
    idade = df.loc[manter, "IDADE"].map(idade_sim) if "IDADE" in df.columns else pd.Series(None, index=df.index[manter], dtype=float)
    texto = lambda coluna: (df.loc[manter, coluna].astype("string").fillna("").str.strip().replace("", "sem_info")
                            if coluna in df.columns else pd.Series("sem_info", index=df.index[manter], dtype="string"))
    return pd.DataFrame({
        "tipo_cancer": tipo[manter],
        "codigo_residencia": df.loc[manter, "CODMUNRES"].astype("string").str.replace(r"\D", "", regex=True).str[:6],
        "faixa": sia.faixa_etaria(idade).fillna("sem_info"),
        "local_obito": texto("LOCOCOR"),
        "raca_cor": texto("RACACOR"),
    })


def agregar(preparado, ano):
    colunas = ["ano", "codigo_residencia", "tipo_cancer", "faixa", "local_obito", "raca_cor", "obitos"]
    if preparado.empty:
        return pd.DataFrame(columns=colunas)
    chaves = ["codigo_residencia", "tipo_cancer", "faixa", "local_obito", "raca_cor"]
    tabela = preparado.groupby(chaves, dropna=False).size().rename("obitos").reset_index()
    tabela.insert(0, "ano", ano)
    return tabela


def perfil(bruto, preparado, ano):
    b = bruto.copy()
    b.columns = [str(c).strip().upper() for c in b.columns]
    print(f"    PERFIL SIM {ano}: {len(b):,} óbitos no arquivo; {len(preparado):,} de mulheres por um dos 7 cânceres".replace(",", "."))
    for coluna in ("SEXO", "LOCOCOR", "RACACOR"):
        if coluna in b:
            valores = b[coluna].astype("string").fillna("(vazio)").value_counts().head(8)
            print(f"      {coluna}: " + ", ".join(f"{v}={n}" for v, n in valores.items()))
    if "RACACOR" in b:
        aviso = sia.alerta_raca(b["RACACOR"].astype("string").str.strip().value_counts().to_dict(), "4", "3")
        if aviso:
            print("      " + aviso)
    if "CAUSABAS" in b:
        cids = b["CAUSABAS"].astype("string").fillna("(vazio)").str[:3].value_counts().head(8)
        print("      CAUSABAS (3 primeiros caracteres, os mais comuns): " + ", ".join(f"{v}={n}" for v, n in cids.items()))
    if len(preparado):
        print("      por câncer (mulheres): " + ", ".join(f"{k}={v}" for k, v in preparado["tipo_cancer"].value_counts().items()))
    else:
        print("      ATENÇÃO: nenhum óbito de mulher pelos 7 cânceres. Confira o perfil acima (sexo e causa).")


def gravar(agregado, ano, banco=BANCO):
    conn = sqlite3.connect(banco)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS obitos_sim (ano INTEGER, codigo_residencia TEXT, tipo_cancer TEXT, faixa TEXT,
            local_obito TEXT, raca_cor TEXT, obitos INTEGER)""")
        conn.execute("DELETE FROM obitos_sim WHERE ano = ?", (ano,))
        agregado.to_sql("obitos_sim", conn, if_exists="append", index=False)
        conn.commit()
    finally:
        conn.close()


async def baixar(anos, pysus_cls=None, banco=BANCO, verboso=True):
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    falhas, resumo, perfilado = [], [], False
    async with pysus_cls() as pysus:
        for ano in anos:
            arquivos, erro = await sih.com_tentativas(
                f"consulta SIM {ano}", lambda: pysus.query(dataset="sim", state=ESTADO, year=ano))
            if erro:
                falhas.append(f"SIM {ano}: a consulta falhou: {erro.splitlines()[0]}")
                continue
            doe = [a for a in arquivos or [] if sih.nome_do_arquivo(a).upper().startswith(f"DO{ESTADO}{ano}")]
            if not doe:
                nomes = ", ".join(sih.nome_do_arquivo(a) for a in (arquivos or [])[:6])
                falhas.append(f"SIM {ano}: não há arquivo DO{ESTADO}{ano} (a fonte lista: {nomes or 'nada'})")
                continue
            partes = []
            for arquivo in doe:
                baixado, erro_arq = await sih.com_tentativas(sih.nome_do_arquivo(arquivo), lambda: pysus.download(arquivo))
                if erro_arq:
                    falhas.append(f"SIM {ano}: {erro_arq.splitlines()[0]}")
                    continue
                local = sih.caminho_local(baixado)
                try:
                    bruto = pd.read_parquet(local)
                    preparado = preparar(bruto)
                    if not perfilado:
                        perfil(bruto, preparado, ano)
                        perfilado = True
                    partes.append(agregar(preparado, ano))
                except Exception as erro_leitura:  # noqa: BLE001
                    falhas.append(f"SIM {ano}: {type(erro_leitura).__name__}: {str(erro_leitura)[:200]}")
                finally:
                    sih.remover(local)
            if partes:
                agregado = pd.concat(partes, ignore_index=True)
                gravar(agregado, ano, banco)
                resumo.append((ano, len(agregado), int(agregado["obitos"].sum())))
                print(f"  SIM {ano}: {int(agregado['obitos'].sum()):,} óbitos de mulheres pelos 7 cânceres".replace(",", "."))
    return falhas, resumo


def _anos(argv):
    if "--anos" in argv:
        inicio, _, fim = argv[argv.index("--anos") + 1].partition("-")
        return list(range(int(inicio), int(fim or inicio) + 1))
    return list(range(2013, 2024))


def main(pysus_cls=None, anos=None, banco=BANCO, verboso=True):
    anos = anos or _anos(sys.argv)
    print(f"MORTALIDADE (SIM) {anos[0]}-{anos[-1]}: só agregados, nenhum número de declaração é gravado")
    falhas, resumo = asyncio.run(baixar(anos, pysus_cls, banco, verboso))
    if falhas:
        print(f"\nO QUE FALHOU OU NÃO EXISTE NA FONTE ({len(falhas)}):")
        for f in falhas[:30]:
            print("  -", f)
    return falhas, resumo


if __name__ == "__main__":
    main()
