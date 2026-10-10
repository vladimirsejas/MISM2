"""Leitura segura do CNES local para apoiar o MISM2.

Este módulo é independente do dashboard e do banco principal. Ele apenas lê os
arquivos locais do CNES; não altera escudo_feminino.db nem grava dados.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import pandas as pd

CODIGO_RIO_CLARO = "3543907"
PASTA_PADRAO = Path(__file__).resolve().parents[1] / "banco" / "cnes"

ALIASES = {
    "municipio": ("CO_MUNICIPIO_GESTOR", "CO_MUNICIPIO", "COD_MUNICIPIO"),
    "cnes": ("CO_CNES", "CNES", "COD_CNES"),
    "nome": ("NO_FANTASIA", "NO_RAZAO_SOCIAL", "NOME_FANTASIA", "NOME"),
    "tipo": ("TP_UNIDADE", "DS_TIPO_UNIDADE", "TIPO_UNIDADE"),
    "uf": ("CO_UF", "UF"),
    "situacao": ("CO_MOTIVO_DESAB", "ST_STATUS", "SITUACAO"),
}


def _normalizar_coluna(valor: object) -> str:
    return str(valor).strip().lstrip("\ufeff").upper()


def _detectar_separador(caminho: Path) -> str:
    # Lê só uma amostra pequena; não carrega o arquivo inteiro na memória.
    with caminho.open("r", encoding="latin-1", newline="") as arquivo:
        amostra = arquivo.read(8192)
    try:
        return csv.Sniffer().sniff(amostra, delimiters=";|,\t").delimiter
    except csv.Error:
        return ";"


def _encontrar_coluna(colunas: Iterable[str], aliases: Iterable[str]) -> str | None:
    mapa = {_normalizar_coluna(c): c for c in colunas}
    for alias in aliases:
        if alias in mapa:
            return mapa[alias]
    return None


def carregar_estabelecimentos(
    pasta: str | Path = PASTA_PADRAO,
    codigo_municipio: str = CODIGO_RIO_CLARO,
) -> pd.DataFrame:
    """Carrega apenas estabelecimentos de Rio Claro a partir do CSV CNES.

    Procura o arquivo tbEstabelecimento*.csv mais recente. O código municipal
    é comparado como texto para preservar zeros à esquerda em outros municípios.
    Se a base não existir ou não tiver coluna municipal reconhecida, retorna
    DataFrame vazio com uma mensagem explicativa em attrs["aviso"].
    """
    pasta = Path(pasta)
    arquivos = sorted(pasta.glob("tbEstabelecimento*.csv"), key=lambda p: p.stat().st_mtime)
    if not arquivos:
        vazio = pd.DataFrame()
        vazio.attrs["aviso"] = f"Nenhum arquivo tbEstabelecimento*.csv encontrado em {pasta}"
        return vazio

    caminho = arquivos[-1]
    separador = _detectar_separador(caminho)
    try:
        cabecalho = pd.read_csv(
            caminho, sep=separador, encoding="latin-1", dtype=str, nrows=0,
            engine="python",
        )
    except Exception as erro:
        vazio = pd.DataFrame()
        vazio.attrs["aviso"] = f"Não foi possível ler o cabeçalho de {caminho.name}: {erro}"
        return vazio

    colunas = list(cabecalho.columns)
    coluna_municipio = _encontrar_coluna(colunas, ALIASES["municipio"])
    if coluna_municipio is None:
        vazio = pd.DataFrame()
        vazio.attrs["aviso"] = (
            f"O arquivo {caminho.name} não apresenta uma coluna municipal reconhecida. "
            f"Colunas encontradas: {', '.join(map(str, colunas[:25]))}"
        )
        return vazio

    colunas_utilizadas = [coluna_municipio]
    for grupo in ("cnes", "nome", "tipo", "uf", "situacao"):
        coluna = _encontrar_coluna(colunas, ALIASES[grupo])
        if coluna and coluna not in colunas_utilizadas:
            colunas_utilizadas.append(coluna)

    try:
        dados = pd.read_csv(
            caminho, sep=separador, encoding="latin-1", dtype=str,
            usecols=colunas_utilizadas, low_memory=False, engine="python",
        )
    except Exception as erro:
        vazio = pd.DataFrame()
        vazio.attrs["aviso"] = f"Falha ao ler {caminho.name}: {erro}"
        return vazio

    codigo = "".join(c for c in str(codigo_municipio) if c.isdigit())
    municipio = dados[coluna_municipio].fillna("").str.replace(r"\D", "", regex=True)
    dados = dados.loc[municipio == codigo].copy()

    renomear = {}
    for grupo, nome_saida in (
        ("cnes", "cnes"), ("nome", "nome"), ("tipo", "tipo_unidade"),
        ("uf", "uf"), ("situacao", "situacao_cadastral"),
    ):
        coluna = _encontrar_coluna(dados.columns, ALIASES[grupo])
        if coluna and coluna != nome_saida:
            renomear[coluna] = nome_saida
    if coluna_municipio in dados.columns:
        renomear[coluna_municipio] = "codigo_municipio"
    dados = dados.rename(columns=renomear)

    if "nome" in dados.columns:
        dados["nome"] = dados["nome"].fillna("").str.strip()
    if "cnes" in dados.columns:
        dados = dados.drop_duplicates(subset=["cnes"], keep="first")
    else:
        dados = dados.drop_duplicates()

    dados = dados.reset_index(drop=True)
    dados.attrs["arquivo_origem"] = str(caminho)
    dados.attrs["codigo_municipio"] = codigo
    dados.attrs["aviso"] = (
        "Recorte municipal por código CNES. Confirme situação cadastral e data "
        "de competência antes de tratar a lista como unidades atualmente ativas."
    )
    return dados


def resumir_rede_local(dados: pd.DataFrame) -> dict[str, object]:
    """Produz contagens descritivas sem inferir capacidade ou qualidade assistencial."""
    if dados.empty:
        return {
            "total_estabelecimentos": 0,
            "por_tipo": pd.Series(dtype="int64"),
            "aviso": dados.attrs.get("aviso", "Nenhum estabelecimento encontrado."),
        }

    if "tipo_unidade" in dados.columns:
        tipos = (
            dados["tipo_unidade"].fillna("").replace("", "Não informado")
            .value_counts().sort_values(ascending=False)
        )
    else:
        tipos = pd.Series(dtype="int64")

    return {
        "total_estabelecimentos": int(len(dados)),
        "por_tipo": tipos,
        "arquivo_origem": dados.attrs.get("arquivo_origem", ""),
        "aviso": dados.attrs.get("aviso", ""),
    }
