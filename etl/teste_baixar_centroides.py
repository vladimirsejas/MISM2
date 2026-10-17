import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baixar_centroides as bc  # noqa: E402

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def quadrado(x, y, lado):
    return [[x, y], [x + lado, y], [x + lado, y + lado], [x, y + lado], [x, y]]


def main():
    lat, lon = bc.centro_da_geometria({"type": "Polygon", "coordinates": [quadrado(-47.6, -22.5, 0.2)]})
    checar("centro de um quadrado de 0,2 grau é o meio dele", abs(lat - (-22.4)) < 1e-9 and abs(lon - (-47.5)) < 1e-9)
    multi = {"type": "MultiPolygon", "coordinates": [[quadrado(0, 0, 2)], [quadrado(10, 0, 1)]]}
    lat, lon = bc.centro_da_geometria(multi)
    esperado_x = (1.0 * 4 + 10.5 * 1) / 5  # médias dos centros ponderadas pela área (4 e 1)
    checar("MultiPolygon: centro ponderado pela área (a ilha pequena puxa pouco)", abs(lon - esperado_x) < 1e-9 and abs(lat - 0.9) < 1e-9)
    nomes = [{"id": 3543907 + i if i == 0 else 3500000 + i, "nome": "Rio Claro" if i == 0 else f"Cidade {i}"} for i in range(650)]
    feicoes = [{"properties": {"codarea": str(n["id"])},
                "geometry": {"type": "Polygon", "coordinates": [quadrado(-47.6 if n["id"] == 3543907 else -48.0 + (n["id"] % 7) * 0.1, -22.5, 0.2)]}}
               for n in nomes]
    linhas = bc.montar({"features": feicoes}, nomes)
    checar("montar casa a malha com os nomes (650 municípios)", len(linhas) == 650 and all(len(l) == 6 for l in linhas))
    checar("conferência passa quando Rio Claro cai no lugar certo", bc.conferir(linhas) is None)
    trocadas = [(l[0], l[1], l[2], l[3], l[5], l[4]) if l[0] == bc.RIO_CLARO else l for l in linhas]
    checar("conferência recusa latitude e longitude trocadas", "trocadas" in (bc.conferir(trocadas) or ""))
    checar("conferência recusa resultado pequeno demais", "só" in (bc.conferir(linhas[:100]) or ""))
    with tempfile.TemporaryDirectory() as pasta:
        banco = os.path.join(pasta, "t.db")
        resposta = {bc.MALHA: {"features": feicoes}, bc.NOMES: nomes}
        problemas = bc.main(obter=lambda url: resposta[url], banco=banco)
        conn = sqlite3.connect(banco)
        n, = conn.execute("SELECT COUNT(*) FROM municipios_localizacao").fetchone()
        checar("grava a tabela sem problema e sem dado de paciente", problemas == [] and n == 650
               and [c[1] for c in conn.execute("PRAGMA table_info(municipios_localizacao)")][:6]
               == ["codigo_ibge", "codigo6", "nome", "uf", "latitude", "longitude"])
        conn.close()
    print()
    if falhas:
        raise SystemExit(1)
    print("Todas as checagens dos centros dos municípios passaram.")


if __name__ == "__main__":
    main()
