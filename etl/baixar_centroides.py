import gzip
import json
import math
import os
import sqlite3
import sys
import urllib.request

# =====================================
# CENTRO DE CADA MUNICÍPIO DE SP (IBGE) -- rodar no computador do autor
#
# Por que: para a Lia dizer "os hospitais de câncer mais próximos de Catanduva" é preciso saber ONDE fica cada cidade. O IBGE
# publica a malha (os contornos) dos municípios; aqui só se guarda o PONTO CENTRAL de cada um (latitude e longitude), 645 linhas.
# Sem geopandas nem geobr: a malha vem da API do IBGE em GeoJSON e o centro é calculado em Python puro (média ponderada pela área).
#
# Grava `municipios_localizacao` (codigo_ibge, codigo6, nome, uf, latitude, longitude, fonte). Dado público; nenhum dado de paciente.
# Uso:  py -3.12 etl\baixar_centroides.py
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/35?intrarregiao=municipio"
         "&formato=application/vnd.geo+json&qualidade=minima")
NOMES = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios"
FONTE = "IBGE, malha municipal (centro calculado do contorno) e API de localidades"
RIO_CLARO = "3543907"
CAIXA_RIO_CLARO = (-22.55, -22.25, -47.70, -47.40)  # latitude mín/máx, longitude mín/máx: confere que o cálculo caiu no lugar certo


def decodificar(corpo):
    if corpo[:2] == b"\x1f\x8b":
        corpo = gzip.decompress(corpo)
    return json.loads(corpo.decode("utf-8"))


def obter_json(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": "EscudoFeminino/1.0 (trabalho academico)", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(pedido, timeout=180) as resposta:
        return decodificar(resposta.read())


def centro_do_anel(anel):
    """(área com sinal, x, y) do centro de um anel de coordenadas [lon, lat]. Plano simples: serve para o ponto central de uma cidade."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1]):
        cruz = x0 * y1 - x1 * y0
        area += cruz
        cx += (x0 + x1) * cruz
        cy += (y0 + y1) * cruz
    area /= 2
    if area == 0:
        xs, ys = [p[0] for p in anel], [p[1] for p in anel]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return area, cx / (6 * area), cy / (6 * area)


def centro_da_geometria(geometria):
    """(latitude, longitude) do centro de um Polygon ou MultiPolygon (só os anéis externos, ponderados pela área)."""
    tipo = geometria["type"]
    poligonos = [geometria["coordinates"]] if tipo == "Polygon" \
        else geometria["coordinates"]
    peso = sx = sy = 0.0
    for poligono in poligonos:
        area, x, y = centro_do_anel([tuple(p[:2]) for p in poligono[0]])
        a = abs(area) or 1e-12
        peso += a
        sx += x * a
        sy += y * a
    if not peso:
        raise ValueError("geometria sem área")
    return sy / peso, sx / peso


def montar(malha, nomes):
    """Lista de (codigo_ibge, codigo6, nome, uf, latitude, longitude) juntando a malha com os nomes."""
    por_codigo = {str(m["id"]): m["nome"] for m in nomes}
    linhas = []
    for feicao in malha["features"]:
        codigo = str(feicao["properties"].get("codarea") or feicao["properties"].get("CD_MUN") or "")
        if codigo not in por_codigo:
            continue
        lat, lon = centro_da_geometria(feicao["geometry"])
        linhas.append((codigo, codigo[:6], por_codigo[codigo], "SP", round(lat, 5), round(lon, 5)))
    return linhas


def conferir(linhas):
    """Devolve um texto de problema ou None. O centro de Rio Claro precisa cair perto de Rio Claro (lat -22,4 / lon -47,56)."""
    if len(linhas) < 600:
        return f"só {len(linhas)} municípios casaram entre a malha e os nomes (SP tem 645)"
    rio = [l for l in linhas if l[0] == RIO_CLARO]
    if not rio:
        return "Rio Claro (3543907) não está no resultado"
    lat, lon = rio[0][4], rio[0][5]
    a, b, c, d = CAIXA_RIO_CLARO
    if not (a <= lat <= b and c <= lon <= d):
        return f"o centro de Rio Claro caiu em ({lat}, {lon}), fora do esperado: latitude e longitude podem estar trocadas"
    return None


def gravar(linhas, banco=BANCO):
    conn = sqlite3.connect(banco)
    try:
        conn.execute("DROP TABLE IF EXISTS municipios_localizacao")
        conn.execute("""CREATE TABLE municipios_localizacao (codigo_ibge TEXT, codigo6 TEXT, nome TEXT, uf TEXT,
            latitude REAL, longitude REAL, fonte TEXT)""")
        conn.executemany("INSERT INTO municipios_localizacao VALUES (?,?,?,?,?,?,?)", [l + (FONTE,) for l in linhas])
        conn.commit()
    finally:
        conn.close()


def main(obter=obter_json, banco=BANCO):
    print("CENTRO DOS MUNICÍPIOS DE SP (IBGE): baixando a malha e os nomes...")
    malha, nomes = obter(MALHA), obter(NOMES)
    linhas = montar(malha, nomes)
    problema = conferir(linhas)
    if problema:
        print(f"NÃO gravei: {problema}.")
        print("Se a API do IBGE mudou, a alternativa é o pacote geobr (pip install geobr geopandas): "
              "geobr.read_municipality(code_muni='SP').centroid.")
        return [problema]
    gravar(linhas, banco)
    rio = next(l for l in linhas if l[0] == RIO_CLARO)
    print(f"  {len(linhas)} municípios gravados; Rio Claro: latitude {rio[4]}, longitude {rio[5]}")
    return []


if __name__ == "__main__":
    main()
