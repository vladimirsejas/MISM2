import asyncio
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

import carga_todas_bases as carga

# =====================================
# BAIXAR DE NOVO O SIH/SUS DE SP: 7 cânceres, 2013 a 2025
#
# Por quê: completude_meses.py mostrou 35 dos 156 meses faltando nos
# CSVs (os mesmos meses nos 7 cânceres). Os scripts antigos de
# download faziam `except Exception: print(...); continue`: um mês que
# falhava sumia em silêncio e o CSV era salvo como se estivesse
# completo. Este script:
#
#   - baixa cada arquivo mensal do SIH/RD de SP UMA vez e tira dele os
#     7 cânceres (156 downloads, não 7 x 156);
#   - filtra por SEXO == "3" e DIAG_PRINC começando com o CID do câncer.
#     NÃO filtra mais a residência (decisão do autor, 10/2026: o Estado
#     conta o ATENDIMENTO em SP, então moradoras de outros estados
#     atendidas em hospitais de SP entram; a carga as grava como
#     OUTRO_ESTADO). Os CIDs são lidos dos CSVs atuais (os que foram
#     usados de verdade) e mostrados antes de começar;
#   - tenta de novo quando falha (TENTATIVAS, com espera crescente) e
#     NUNCA pula em silêncio: o que falhar é listado no fim;
#   - retoma de onde parou: cada mês pronto fica em
#     dados\_download_sih_sp\<ano>_<mes>\ ; rodar de novo pula esses;
#   - só troca os CSVs de dados\cancer_*_sp\ se TODOS os meses vierem,
#     e antes guarda os atuais em dados\_backup_<data>\ . Como o DATASUS
#     não oferece 35 dos 156 meses (docs/FONTE_DOS_DADOS.md), isso nunca
#     acontece; com --aceitar-lacunas-da-fonte o script troca os CSVs
#     pelos meses que EXISTEM, mas só se o único problema for "a fonte
#     não lista o mês" (erro de download de verdade continua barrando).
#
# Uso (no Windows, da pasta do projeto, com internet):
#     py -3.12 etl\baixar_sih_sp.py --aceitar-lacunas-da-fonte
# Pode levar horas (cada mês de SP é grande). Se parar, rode de novo.
# Depois: py etl\completude_meses.py (tudo 12/12?) e
#         py etl\carga_todas_bases.py
# =====================================

ANOS = list(range(2013, 2026))
MESES = list(range(1, 13))
ESTADO = "SP"
VALOR_FEMININO = "3"
# marcador do motivo "a fonte não tem este mês" (distingue de erro de download)
FALTA_NA_FONTE = "o DATASUS/pysus não listou arquivo para este mês"
TENTATIVAS = 4
ESPERA_INICIAL = 10  # segundos; dobra a cada tentativa

BASE_DADOS = Path(carga.BASE_DADOS)
# pasta nova (não "_download_sih_sp"): os meses baixados na regra antiga já
# vinham filtrados por residência em SP e seriam pulados como "prontos".
PASTA_MESES = BASE_DADOS / "_download_sih_sp_atendimento"

# pasta estadual -> (código do câncer, CIDs se não der para ler do CSV
# atual). Os CIDs de mama, colo do útero e colorretal são os dos
# scripts antigos; os outros são o padrão e só valem se o CSV atual
# não existir.
CANCERES = {
    "cancer_mama_sp": ("MAMA", ["C50"]),
    "cancer_colo_utero_sp": ("COLO_UTERO", ["C53"]),
    "cancer_colorretal_sp": ("COLORRETAL", ["C18", "C19", "C20"]),
    "cancer_ovario_sp": ("OVARIO", ["C56"]),
    "cancer_pulmao_sp": ("PULMAO", ["C33", "C34"]),
    "cancer_tireoide_sp": ("TIREOIDE", ["C73"]),
    "cancer_pele_nao_melanoma_sp": ("PELE_NAO_MELANOMA", ["C44"]),
}


# ---------- filtros ----------

def cids_do_csv_atual(pasta):
    """CIDs (3 caracteres) que aparecem no DIAG_PRINC do CSV atual da
    pasta -- o filtro que foi usado de verdade. None se não houver."""
    caminho = BASE_DADOS / pasta
    if not caminho.is_dir():
        return None
    csv = carga.selecionar_csv_unico(str(caminho), pasta)
    if csv is None:
        return None
    separador = carga.detectar_separador(csv)
    diag = pd.read_csv(csv, sep=separador, encoding="latin1", dtype=str,
                       usecols=lambda c: c.strip().strip('"').upper() == "DIAG_PRINC")
    if diag.empty:
        return None
    return sorted(diag.iloc[:, 0].dropna().str.strip().str.upper().str[:3].unique())


def definir_filtros():
    filtros = {}
    for pasta, (codigo, padrao) in CANCERES.items():
        lidos = cids_do_csv_atual(pasta)
        filtros[pasta] = (codigo, lidos or padrao, "do CSV atual" if lidos else "padrão (sem CSV atual)")
    return filtros


def filtrar(df, cids):
    """Mulher + CID do câncer. A residência não filtra: atendimento em SP."""
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    faltando = {"DIAG_PRINC", "MUNIC_RES", "SEXO"} - set(df.columns)
    if faltando:
        raise RuntimeError(f"arquivo sem as colunas {sorted(faltando)}")
    cid = df["DIAG_PRINC"].astype("string").fillna("").str.strip().str.upper()
    sexo = df["SEXO"].astype("string").fillna("").str.strip()
    mascara = cid.str[:3].isin(cids) & (sexo == VALOR_FEMININO)
    return df.loc[mascara]


# ---------- arquivos mensais ----------

def nome_do_arquivo(arquivo):
    for atributo in ("name", "filename", "basename", "path", "id"):
        valor = getattr(arquivo, atributo, None)
        if valor:
            return os.path.basename(str(valor))
    return str(arquivo)


def mes_do_arquivo(nome):
    """RDSP2402.dbc / RDSP2402.parquet -> (2024, 2). None se não der."""
    achado = re.search(r"RD[A-Z]{2}(\d{2})(\d{2})", nome.upper())
    if not achado:
        return None
    return 2000 + int(achado.group(1)), int(achado.group(2))


def pasta_do_mes(ano, mes):
    return PASTA_MESES / f"{ano}_{mes:02d}"


def mes_pronto(ano, mes):
    return (pasta_do_mes(ano, mes) / "PRONTO").exists()


def guardar_mes(ano, mes, df, filtros, origem):
    pasta = pasta_do_mes(ano, mes)
    pasta.mkdir(parents=True, exist_ok=True)
    resumo = []
    for pasta_cancer, (codigo, cids, _) in filtros.items():
        parte = filtrar(df, cids)
        parte.to_parquet(pasta / f"{codigo}.parquet", index=False)
        resumo.append(f"{codigo}: {len(parte)}")
    (pasta / "PRONTO").write_text(f"{origem}\n{datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
    return resumo


def caminho_local(baixado):
    return Path(str(getattr(baixado, "path", baixado)))


def remover(caminho):
    try:
        if caminho.is_dir():
            shutil.rmtree(caminho)
        elif caminho.exists():
            caminho.unlink()
    except OSError as erro:
        print(f"      (aviso: não consegui apagar o arquivo temporário {caminho}: {erro})")


async def com_tentativas(descricao, funcao):
    """Tenta TENTATIVAS vezes, esperando cada vez mais. Devolve
    (resultado, None) ou (None, texto do último erro)."""
    espera = ESPERA_INICIAL
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            return await funcao(), None
        except Exception as erro:  # registra tudo; nunca some em silêncio
            detalhe = f"{type(erro).__name__}: {erro}"
            print(f"      falhou ({descricao}, tentativa {tentativa}/{TENTATIVAS}): {detalhe}")
            if tentativa == TENTATIVAS:
                return None, detalhe + "\n" + traceback.format_exc(limit=3)
            await asyncio.sleep(espera)
            espera *= 2


# ---------- download ----------

async def baixar(filtros, pysus_cls=None):
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    falhas = {}  # (ano, mes) ou ("ano", ano) -> motivo
    async with pysus_cls() as pysus:
        for ano in ANOS:
            faltam = [m for m in MESES if not mes_pronto(ano, m)]
            if not faltam:
                print(f"{ano}: os 12 meses já estão prontos.")
                continue
            print(f"\n{ano}: faltam {len(faltam)} meses -> consultando o DATASUS...")
            arquivos, erro = await com_tentativas(
                f"consulta {ano}",
                lambda: pysus.query(dataset="sih", group="RD", state=ESTADO, year=ano))
            if erro:
                for m in faltam:
                    falhas[(ano, m)] = f"a consulta do ano falhou: {erro.splitlines()[0]}"
                continue
            por_mes = {}
            for arquivo in arquivos or []:
                chave = mes_do_arquivo(nome_do_arquivo(arquivo))
                if chave and chave[0] == ano:
                    por_mes.setdefault(chave[1], []).append(arquivo)
            listados = sorted(por_mes)
            print(f"  o DATASUS listou {len(arquivos or [])} arquivo(s); meses reconhecidos: "
                  f"{', '.join(f'{m:02d}' for m in listados) or 'nenhum'}")
            if len(listados) < len(MESES):  # ajuda a diagnosticar: como os arquivos se chamam?
                print(f"  nomes listados: {', '.join(nome_do_arquivo(a) for a in (arquivos or [])[:15])}")
            for mes in faltam:
                if mes not in por_mes:
                    falhas[(ano, mes)] = FALTA_NA_FONTE
                    print(f"  {ano}/{mes:02d}: NÃO LISTADO pelo DATASUS")
                    continue
                partes = []
                erro_mes = None
                for arquivo in por_mes[mes]:  # às vezes um mês vem em mais de uma parte
                    nome = nome_do_arquivo(arquivo)
                    print(f"  {ano}/{mes:02d}: baixando {nome}...")
                    baixado, erro_mes = await com_tentativas(nome, lambda: pysus.download(arquivo))
                    if erro_mes:
                        break
                    local = caminho_local(baixado)
                    try:
                        partes.append(pd.read_parquet(local))
                    except Exception as erro:
                        erro_mes = f"não consegui ler {local}: {type(erro).__name__}: {erro}"
                        break
                    finally:
                        remover(local)
                if erro_mes:
                    falhas[(ano, mes)] = erro_mes
                    print(f"  {ano}/{mes:02d}: FALHOU -> {erro_mes.splitlines()[0]}")
                    continue
                try:
                    resumo = guardar_mes(ano, mes, pd.concat(partes, ignore_index=True), filtros,
                                         ", ".join(nome_do_arquivo(a) for a in por_mes[mes]))
                    print(f"  {ano}/{mes:02d}: ok ({'; '.join(resumo)})")
                except Exception as erro:
                    falhas[(ano, mes)] = f"{type(erro).__name__}: {erro}"
                    print(f"  {ano}/{mes:02d}: FALHOU ao filtrar/guardar -> {erro}")
    return falhas


# ---------- consolidação ----------

def consolidar(filtros):
    """Junta os meses PRONTOS e troca os CSVs de dados\\cancer_*_sp\\,
    guardando os atuais numa pasta de backup (fora das pastas da carga,
    que exige um CSV só por pasta). Com a fonte completa são os 156
    meses; com lacunas da fonte, os que existem."""
    backup = BASE_DADOS / f"_backup_{datetime.now():%Y%m%d_%H%M}"
    for pasta_cancer, (codigo, _, _) in filtros.items():
        partes = [pd.read_parquet(pasta_do_mes(a, m) / f"{codigo}.parquet")
                  for a in ANOS for m in MESES if mes_pronto(a, m)]
        df = pd.concat(partes, ignore_index=True)
        destino = BASE_DADOS / pasta_cancer
        if destino.is_dir():
            antigos = [p for p in destino.iterdir() if p.suffix.lower() in (".csv", ".parquet")]
            if antigos:
                (backup / pasta_cancer).mkdir(parents=True, exist_ok=True)
                for p in antigos:
                    shutil.move(str(p), str(backup / pasta_cancer / p.name))
        destino.mkdir(parents=True, exist_ok=True)
        nome = f"{pasta_cancer.replace('_sp', '')}_mulheres_sp_{ANOS[0]}_{ANOS[-1]}"
        df.to_parquet(destino / f"{nome}.parquet", index=False)
        # latin1, como a carga lê (utf-8-sig põe uma marca invisível que
        # estraga o nome da 1ª coluna quando lida em latin1)
        df.to_csv(destino / f"{nome}.csv", index=False, encoding="latin1", errors="replace")
        print(f"  {codigo}: {len(df):,} internações -> {destino / (nome + '.csv')}".replace(",", "."))
    return backup


def main(pysus_cls=None, aceitar_lacunas=False):
    print("BAIXAR SIH/SUS DE SP -- 7 cânceres, 2013 a 2025 (atendimento em SP, inclusive moradoras de outros estados)")
    filtros = definir_filtros()
    print("\nFiltros (SEXO 3 e DIAG_PRINC; sem filtro de residência):")
    for pasta, (codigo, cids, origem) in filtros.items():
        print(f"  {codigo:18} CID {', '.join(cids):14} ({origem})")

    falhas = asyncio.run(baixar(filtros, pysus_cls))

    total = len(ANOS) * len(MESES)
    prontos = sum(mes_pronto(a, m) for a in ANOS for m in MESES)
    print("\n" + "=" * 70)
    print(f"MESES PRONTOS: {prontos} de {total}")
    so_lacunas_da_fonte = bool(falhas) and all(m == FALTA_NA_FONTE for m in falhas.values())
    if prontos < total and not (aceitar_lacunas and so_lacunas_da_fonte):
        print("\nFALTAM (os CSVs atuais NÃO foram trocados):")
        for (ano, mes), motivo in sorted(falhas.items()):
            print(f"  {ano}/{mes:02d}: {motivo.splitlines()[0]}")
        if so_lacunas_da_fonte:
            print("\nTodos os que faltam são meses que a FONTE não lista. Para trocar os CSVs pelos meses que")
            print("existem, rode com: py -3.12 etl\\baixar_sih_sp.py --aceitar-lacunas-da-fonte")
        else:
            print("\nRode de novo: os meses prontos são pulados. Se um mês falhar sempre com o MESMO erro,")
            print("me mande esta lista -- aí o problema não é a internet.")
        return 1
    if prontos < total:
        print(f"\nA fonte não oferece {total - prontos} dos {total} meses (confirmado). "
              f"Trocando os CSVs pelos {prontos} que existem (os atuais vão para backup)...")
    else:
        print("\nTodos os meses vieram. Trocando os CSVs (os atuais vão para backup)...")
    backup = consolidar(filtros)
    print(f"\nCSVs antigos guardados em {backup}")
    print("Próximos passos: py etl\\completude_meses.py  (tudo 12/12?)  e  py etl\\carga_todas_bases.py")
    print(f"(Pode apagar {PASTA_MESES} depois de conferir.)")
    return 0


if __name__ == "__main__":
    sys.exit(main(aceitar_lacunas="--aceitar-lacunas-da-fonte" in sys.argv))
