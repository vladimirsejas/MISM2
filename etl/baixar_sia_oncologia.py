import asyncio
import os
import re
import sqlite3
import sys

import pandas as pd

import baixar_sih_sp as sih

# =====================================
# QUIMIOTERAPIA E RADIOTERAPIA AMBULATORIAIS (SIA/SUS, APACs AQ e AR) DAS 7 NEOPLASIAS -- rodar no computador do autor
#
# Por que: o maior ponto cego declarado do Escudo é "quem se trata só em ambulatório não aparece" (o SIH só tem internações). As
# APACs de quimioterapia (AQ) e de radioterapia (AR) trazem o tratamento ambulatorial: mulheres, município de residência, idade, CID,
# estadiamento e raça/cor.
#
# Privacidade: SÓ agregados são gravados. Nenhum número de cartão SUS, CEP, data de nascimento ou número da APAC entra no banco; o
# cartão SUS é usado apenas para contar mulheres diferentes por mês e é descartado. Tabela `oncologia_ambulatorial`
# (modalidade, ano, mes, codigo_residencia, tipo_cancer, faixa, estadiamento, raca_cor, apacs, pacientes).
#
# O que `apacs` e `pacientes` significam: uma APAC é a cobrança MENSAL de um tratamento; `pacientes` é o número de mulheres
# diferentes naquele mês. Somar meses dá mulheres-mês em tratamento, não mulheres diferentes no ano.
#
# Como os códigos de estadiamento e raça/cor vêm crus do DATASUS, cada execução imprime um PERFIL dos valores reais (sem nenhum
# dado individual) para conferir antes de interpretar.
#
# Uso (Python 3.12, da pasta do projeto):
#   py -3.12 etl\baixar_sia_oncologia.py                 só 2023 (confere os valores reais antes de rodar tudo)
#   py -3.12 etl\baixar_sia_oncologia.py --anos 2013-2025
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
GRUPOS = {"AQ": "QUIMIO", "AR": "RADIO"}
ESTADO = "SP"
CID_PARA_CANCER = {cid: codigo for codigo, cids in sih.CANCERES.values() for cid in cids}
FEMININO = {"F", "FEMININO", "2", "3"}  # SIA usa F/M; o SIH usa 3; aceito os dois e confiro no perfil
COLUNAS_BASE = ["AP_SEXO", "AP_CIDPRI", "AP_MUNPCN", "AP_NUIDADE", "AP_CNSPCN", "AP_RACACOR"]


def mes_do_arquivo(nome):
    """AQSP2301.parquet -> (2023, 1). None se não der."""
    achado = re.search(r"A[QR][A-Z]{2}(\d{2})(\d{2})", nome.upper())
    return (2000 + int(achado.group(1)), int(achado.group(2))) if achado else None


def faixa_etaria(idade):
    idade = pd.to_numeric(idade, errors="coerce")
    return pd.cut(idade, [-1, 39, 49, 69, 200], labels=["até 39 anos", "40 a 49", "50 a 69", "70 ou mais"]).astype("string")


def preparar(df, grupo):
    """Mulheres com um dos 7 cânceres, uma linha por APAC, só com o que o Escudo usa. Levanta erro claro se faltar coluna."""
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    estadio = f"{grupo}_ESTADI"
    faltando = [c for c in COLUNAS_BASE + [estadio] if c not in df.columns]
    if faltando:
        raise RuntimeError(f"arquivo sem as colunas {faltando}; colunas: {list(df.columns)[:40]}")
    cid = df["AP_CIDPRI"].astype("string").fillna("").str.strip().str.upper()
    if f"{grupo}_CID10" in df.columns:  # o CID principal às vezes vem vazio: usa o da própria APAC
        cid = cid.where(cid != "", df[f"{grupo}_CID10"].astype("string").fillna("").str.strip().str.upper())
    sexo = df["AP_SEXO"].astype("string").fillna("").str.strip().str.upper()
    tipo = cid.str[:3].map(CID_PARA_CANCER)
    manter = sexo.isin(FEMININO) & tipo.notna()
    saida = pd.DataFrame({
        "tipo_cancer": tipo[manter],
        "codigo_residencia": df.loc[manter, "AP_MUNPCN"].astype("string").str.replace(r"\D", "", regex=True).str[:6],
        "faixa": faixa_etaria(df.loc[manter, "AP_NUIDADE"]),
        "estadiamento": df.loc[manter, estadio].astype("string").fillna("").str.strip().replace("", "sem_info"),
        "raca_cor": df.loc[manter, "AP_RACACOR"].astype("string").fillna("").str.strip().replace("", "sem_info"),
        "cartao": df.loc[manter, "AP_CNSPCN"].astype("string"),
    })
    return saida


def agregar(preparado, modalidade, ano, mes):
    """Uma linha por (residência, câncer, faixa, estadiamento, raça/cor): APACs e mulheres diferentes no mês. Sem identificador."""
    if preparado.empty:
        return pd.DataFrame(columns=["modalidade", "ano", "mes", "codigo_residencia", "tipo_cancer", "faixa", "estadiamento",
                                     "raca_cor", "apacs", "pacientes"])
    chaves = ["codigo_residencia", "tipo_cancer", "faixa", "estadiamento", "raca_cor"]
    tabela = (preparado.fillna({"faixa": "sem_info"}).groupby(chaves, dropna=False)
              .agg(apacs=("cartao", "size"), pacientes=("cartao", "nunique")).reset_index())
    tabela.insert(0, "mes", mes)
    tabela.insert(0, "ano", ano)
    tabela.insert(0, "modalidade", modalidade)
    return tabela


def perfil(bruto, preparado, grupo):
    """Valores reais das colunas de código (nenhum dado individual) para conferir antes de interpretar."""
    b = bruto.copy()
    b.columns = [str(c).strip().upper() for c in b.columns]
    print(f"    PERFIL {grupo}: {len(b):,} APACs no mês; {len(preparado):,} de mulheres com os 7 cânceres".replace(",", "."))
    for coluna in ("AP_SEXO", f"{grupo}_ESTADI", "AP_RACACOR"):
        if coluna in b:
            valores = b[coluna].astype("string").fillna("(vazio)").value_counts().head(8)
            print(f"      {coluna}: " + ", ".join(f"{v}={n}" for v, n in valores.items()))
    if "AP_CIDPRI" in b:
        cids = b["AP_CIDPRI"].astype("string").fillna("(vazio)").str[:3].value_counts().head(10)
        print("      AP_CIDPRI (3 primeiros caracteres): " + ", ".join(f"{v}={n}" for v, n in cids.items()))
    if len(preparado):
        print("      por câncer (mulheres): " + ", ".join(f"{k}={v}" for k, v in preparado["tipo_cancer"].value_counts().items()))
    else:
        print("      ATENÇÃO: nenhuma APAC de mulher com os 7 cânceres. Confira o perfil acima (sexo e CID).")


def gravar(agregado, modalidade, ano, banco=BANCO):
    conn = sqlite3.connect(banco)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS oncologia_ambulatorial (modalidade TEXT, ano INTEGER, mes INTEGER,
            codigo_residencia TEXT, tipo_cancer TEXT, faixa TEXT, estadiamento TEXT, raca_cor TEXT, apacs INTEGER, pacientes INTEGER)""")
        conn.execute("DELETE FROM oncologia_ambulatorial WHERE modalidade = ? AND ano = ?", (modalidade, ano))
        agregado.to_sql("oncologia_ambulatorial", conn, if_exists="append", index=False)
        conn.commit()
    finally:
        conn.close()


async def baixar(anos, pysus_cls=None, banco=BANCO):
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    falhas, resumo = [], []
    async with pysus_cls() as pysus:
        for grupo, modalidade in GRUPOS.items():
            for ano in anos:
                print(f"\n{modalidade} ({grupo}) {ano}: consultando o DATASUS...")
                arquivos, erro = await sih.com_tentativas(
                    f"consulta {grupo} {ano}", lambda: pysus.query(dataset="sia", group=grupo, state=ESTADO, year=ano))
                if erro:
                    falhas.append(f"{grupo} {ano}: a consulta falhou: {erro.splitlines()[0]}")
                    continue
                por_mes = {}
                for arquivo in arquivos or []:
                    chave = mes_do_arquivo(sih.nome_do_arquivo(arquivo))
                    if chave and chave[0] == ano:
                        por_mes.setdefault(chave[1], []).append(arquivo)
                print(f"  meses listados: {', '.join(f'{m:02d}' for m in sorted(por_mes)) or 'nenhum'}")
                partes, perfilado = [], False
                for mes in range(1, 13):
                    if mes not in por_mes:
                        falhas.append(f"{grupo} {ano}/{mes:02d}: o DATASUS não listou o mês")
                        continue
                    for arquivo in por_mes[mes]:
                        nome = sih.nome_do_arquivo(arquivo)
                        baixado, erro_mes = await sih.com_tentativas(nome, lambda: pysus.download(arquivo))
                        if erro_mes:
                            falhas.append(f"{grupo} {ano}/{mes:02d}: {erro_mes.splitlines()[0]}")
                            continue
                        local = sih.caminho_local(baixado)
                        try:
                            bruto = pd.read_parquet(local)
                            preparado = preparar(bruto, grupo)
                            if not perfilado:
                                perfil(bruto, preparado, grupo)
                                perfilado = True
                            partes.append(agregar(preparado, modalidade, ano, mes))
                            print(f"  {ano}/{mes:02d}: ok ({len(preparado)} APACs de mulheres)")
                        except Exception as erro_leitura:  # noqa: BLE001
                            falhas.append(f"{grupo} {ano}/{mes:02d}: {type(erro_leitura).__name__}: {str(erro_leitura)[:200]}")
                        finally:
                            sih.remover(local)
                if partes:
                    agregado = pd.concat(partes, ignore_index=True)
                    gravar(agregado, modalidade, ano, banco)
                    resumo.append((modalidade, ano, len(agregado), int(agregado["apacs"].sum())))
    return falhas, resumo


def _anos_da_linha(argv):
    if "--anos" in argv:
        valor = argv[argv.index("--anos") + 1]
        inicio, _, fim = valor.partition("-")
        return list(range(int(inicio), int(fim or inicio) + 1))
    return [2023]


def main(pysus_cls=None, anos=None, banco=BANCO):
    anos = anos or _anos_da_linha(sys.argv)
    print(f"QUIMIO E RADIO AMBULATORIAIS (SIA): {anos[0]}-{anos[-1]}, só agregados (nenhum identificador é gravado)")
    falhas, resumo = asyncio.run(baixar(anos, pysus_cls, banco))
    print("\nGRAVADO em oncologia_ambulatorial:")
    for modalidade, ano, linhas, apacs in resumo:
        print(f"  {modalidade} {ano}: {linhas:,} linhas agregadas, {apacs:,} APACs de mulheres".replace(",", "."))
    if falhas:
        print(f"\nO QUE FALHOU OU NÃO EXISTE NA FONTE ({len(falhas)}):")
        for f in falhas[:40]:
            print("  -", f)
    print("\nCole o PERFIL e o resumo no chat: com os códigos reais de estadiamento e raça/cor eu uso estes dados no Escudo.")
    return falhas, resumo


if __name__ == "__main__":
    main()
