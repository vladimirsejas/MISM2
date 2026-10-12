"""Localização de serviços públicos de Rio Claro para o MISM2.

Implementação independente: consome um catálogo público e um índice CEP
gerados no MISM3, sem importar código do MISM3 nem alterar o banco analítico.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
PASTA_DADOS = RAIZ_PROJETO / "dados_geograficos"
ARQUIVO_SERVICOS = PASTA_DADOS / "catalogo_servicos_rioclaro.json"
ARQUIVO_CEPS = PASTA_DADOS / "indice_cep_rioclaro.json"

# Caixa de validação ampla de Rio Claro/SP. Serve para rejeitar erros grosseiros,
# não para provar que um endereço está correto.
CAIXA_RIO_CLARO = (-22.60, -22.20, -47.82, -47.41)
RAIO_MAX_CEP_M = 800


def normalizar_cep(valor: Any) -> str:
    """Retorna somente os dígitos do CEP."""
    return re.sub(r"\D", "", str(valor or ""))


def coordenada_valida(lat: Any, lon: Any) -> bool:
    """Confere formato, finitude e se a coordenada cai na caixa de Rio Claro."""
    try:
        latitude, longitude = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return False
    lat_min, lat_max, lon_min, lon_max = CAIXA_RIO_CLARO
    return lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max


def carregar_bases(
    arquivo_servicos: Path | str = ARQUIVO_SERVICOS,
    arquivo_ceps: Path | str = ARQUIVO_CEPS,
) -> tuple[dict, dict]:
    """Carrega as duas bases e valida o formato mínimo esperado."""
    with Path(arquivo_servicos).open(encoding="utf-8") as arquivo:
        catalogo = json.load(arquivo)
    with Path(arquivo_ceps).open(encoding="utf-8") as arquivo:
        indice = json.load(arquivo)

    if not isinstance(catalogo.get("servicos"), list):
        raise ValueError("Catálogo de serviços sem a lista 'servicos'.")
    if not isinstance(indice.get("ceps"), dict):
        raise ValueError("Índice geográfico sem o dicionário 'ceps'.")
    return catalogo, indice


def resolver_localizacao(servico: dict, indice_ceps: dict) -> dict:
    """Resolve localização de serviço sem inventar coordenadas.

    Prioriza coordenadas cadastradas e válidas. Como alternativa, aceita o
    centro aproximado do CEP somente quando o raio de incerteza é <= 800 m.
    """
    try:
        lat = float(servico.get("lat"))
        lon = float(servico.get("lon"))
    except (TypeError, ValueError):
        lat = lon = None

    if lat is not None and lon is not None and coordenada_valida(lat, lon):
        return {
            "lat": lat,
            "lon": lon,
            "precisao": "coordenada_da_fonte",
            "raio_m": 0,
            "localizavel": True,
        }

    cep = normalizar_cep(servico.get("cep"))
    ponto = indice_ceps.get(cep) if cep else None
    if isinstance(ponto, (list, tuple)) and len(ponto) >= 3:
        try:
            lat_cep, lon_cep, raio = float(ponto[0]), float(ponto[1]), float(ponto[2])
        except (TypeError, ValueError):
            ponto = None
        else:
            if coordenada_valida(lat_cep, lon_cep) and 0 <= raio <= RAIO_MAX_CEP_M:
                return {
                    "lat": lat_cep,
                    "lon": lon_cep,
                    "precisao": "aproximada_por_cep",
                    "raio_m": int(raio),
                    "localizavel": True,
                }

    return {
        "lat": None,
        "lon": None,
        "precisao": "sem_localizacao_confiavel",
        "raio_m": None,
        "localizavel": False,
    }


def preparar_servicos(servicos: list[dict], indice_ceps: dict) -> list[dict]:
    """Retorna cópias dos serviços com localização validada."""
    preparados = []
    for servico in servicos:
        item = dict(servico)
        localizacao = resolver_localizacao(item, indice_ceps)
        item.update(localizacao)
        preparados.append(item)
    return preparados



def _chave_texto(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.casefold())


def combinar_catalogos(servicos_manuais: list[dict], servicos_cnes: list[dict]) -> list[dict]:
    """Combina fontes sem duplicar CNES já registrado manualmente.

    A chave preferida é o código CNES. Como alternativa, remove duplicata
    apenas quando nome E endereço normalizados coincidem; nomes iguais com
    endereços diferentes continuam separados.
    """
    resultado = [dict(item) for item in servicos_manuais]
    codigos = {
        re.sub(r"\D", "", str(item.get("cnes") or ""))
        for item in resultado
        if re.sub(r"\D", "", str(item.get("cnes") or ""))
    }
    pares = {
        (_chave_texto(item.get("nome")), _chave_texto(item.get("endereco")))
        for item in resultado
        if _chave_texto(item.get("nome")) and _chave_texto(item.get("endereco"))
    }
    for item in servicos_cnes:
        codigo = re.sub(r"\D", "", str(item.get("cnes") or ""))
        par = (_chave_texto(item.get("nome")), _chave_texto(item.get("endereco")))
        if codigo and codigo in codigos:
            continue
        if par[0] and par[1] and par in pares:
            continue
        resultado.append(dict(item))
        if codigo:
            codigos.add(codigo)
        if par[0] and par[1]:
            pares.add(par)
    return resultado


def filtrar_servicos(
    servicos: list[dict],
    texto: str = "",
    tipos: set[str] | None = None,
    somente_localizados: bool = False,
    somente_exatos: bool = False,
) -> list[dict]:
    """Filtra por texto/categoria e, opcionalmente, precisão da localização."""
    consulta = str(texto or "").strip().casefold()
    resultado = []
    for servico in servicos:
        if tipos is not None and servico.get("tipo") not in tipos:
            continue
        if somente_localizados and not servico.get("localizavel"):
            continue
        if somente_exatos and servico.get("precisao") != "coordenada_da_fonte":
            continue
        if consulta:
            campos = (
                servico.get("nome"),
                servico.get("endereco"),
                servico.get("cep"),
                servico.get("bairros"),
                servico.get("tipo"),
                servico.get("subtipo"),
            )
            texto_servico = " ".join(str(c or "") for c in campos).casefold()
            if consulta not in texto_servico:
                continue
        resultado.append(servico)
    return resultado
