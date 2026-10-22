import math
import re

import pandas as pd

import entendimento as ent

# =====================================
# ONDE FICAM AS CIDADES E QUAL HOSPITAL DE CÂNCER ESTÁ MAIS PERTO
#
# Lê `municipios_localizacao` (py -3.12 etl\baixar_centroides.py: o ponto central de cada município de SP, do IBGE). Com isso a Lia
# diz "os hospitais de câncer do catálogo mais próximos de Catanduva" em quilômetros.
#
# Limite que a fala sempre diz: é distância em LINHA RETA entre os centros das duas cidades. Não é rota, não é tempo de viagem e, pelo
# SUS, quem decide o hospital é a regulação (CROSS), não a proximidade. Serve para a pessoa se situar, nunca para escolher por ela.
# =====================================

COLUNAS = ["nome", "chave", "latitude", "longitude"]
RAIO_TERRA_KM = 6371.0
# Hospitais de câncer do catálogo do Apoio: a lâmina "Hospitais no Estado" + o Hospital de Amor (Barretos), que mora na lâmina dele.
IDS_EXTRAS = {"ha_quem_e"}


def carregar_localizacao(conexao):
    """DataFrame (nome, chave, latitude, longitude); vazio se a tabela ainda não foi baixada."""
    try:
        df = pd.read_sql("SELECT nome, latitude, longitude FROM municipios_localizacao", conexao)
    except Exception:
        return pd.DataFrame(columns=COLUNAS)
    df["chave"] = df["nome"].map(ent.normalizar)
    return df[COLUNAS]


def distancia_km(lat1, lon1, lat2, lon2):
    """Distância em linha reta (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(a))


def _ponto(localizacao, chave):
    achada = localizacao[localizacao["chave"] == chave]
    return (float(achada.iloc[0]["latitude"]), float(achada.iloc[0]["longitude"])) if len(achada) else None


def pontos_origens(pares, localizacao, cidade):
    """Posição (centro do município) das cidades de onde vêm as mulheres atendidas em `cidade`.

    `pares`: [(nome, internacoes)] (as cidades principais, de `inteligencia.agrupar_origens`). Devolve
    (centro da cidade dos hospitais ou None, DataFrame nome/latitude/longitude/internacoes, internações sem posição).
    Cidade que não está na tabela fica de fora e é contada em "sem posição": nunca ganha um ponto inventado. O ponto é o CENTRO
    da cidade, não o endereço de ninguém."""
    total = sum(int(n) for _, n in pares)
    if localizacao is None or len(localizacao) == 0:
        return None, pd.DataFrame(columns=["nome", "latitude", "longitude", "internacoes"]), total
    centro = _ponto(localizacao, ent.normalizar(cidade))
    linhas, sem_posicao = [], 0
    for nome, n in pares:
        ponto = _ponto(localizacao, ent.normalizar(nome))
        if ponto is None:
            sem_posicao += int(n)
        else:
            linhas.append({"nome": nome, "latitude": ponto[0], "longitude": ponto[1], "internacoes": int(n)})
    return centro, pd.DataFrame(linhas, columns=["nome", "latitude", "longitude", "internacoes"]), sem_posicao


def cidade_do_item(onde):
    """'Piracicaba (região de Rio Claro)' -> 'piracicaba'; 'São Paulo (capital)' -> 'sao paulo'."""
    return ent.normalizar(re.sub(r"\([^)]*\)", "", onde or ""))


def hospitais_proximos(localizacao, cidade, itens, n=3):
    """Os `n` hospitais de câncer do catálogo mais próximos de `cidade` (nome normalizado): [(km, item)], do mais perto ao mais longe.
    Vazio se a cidade não está na tabela (nunca chuta a posição)."""
    if localizacao is None or len(localizacao) == 0:
        return []
    origem = _ponto(localizacao, ent.normalizar(cidade))
    if origem is None:
        return []
    achados, vistos = [], set()
    for item in itens:
        chave = cidade_do_item(item["onde"])
        destino = _ponto(localizacao, chave)
        if destino is None:
            continue  # 'Estado de SP' ou nome que não casa: fica de fora em vez de ganhar uma posição inventada
        achados.append((distancia_km(*origem, *destino), item))
    achados.sort(key=lambda par: par[0])
    saida, cidades = [], {}
    for km, item in achados:  # no máximo 2 por cidade, para São Paulo e Campinas não ocuparem a lista inteira
        chave = cidade_do_item(item["onde"])
        if item["id"] in vistos or cidades.get(chave, 0) >= 2:
            continue
        vistos.add(item["id"])
        cidades[chave] = cidades.get(chave, 0) + 1
        saida.append((km, item))
        if len(saida) == n:
            break
    return saida
