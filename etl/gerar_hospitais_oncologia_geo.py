"""Endereço, telefone e POSIÇÃO dos estabelecimentos habilitados em oncologia (Brasil), vindos do CNES.

Junta a lista oficial (dados_geograficos\\hospitais_oncologia_br.csv) com o tbEstabelecimento do CNES (banco\\cnes) e grava
dados_geograficos\\hospitais_oncologia_br_geo.csv, que a página "Hospitais de câncer" lê. Só dado público (nome, endereço,
telefone e coordenada do cadastro do estabelecimento). Só LÊ o CNES e o banco; nunca altera nada.

A posição só vira ponto no mapa quando PASSA nas conferências; senão o hospital fica na lista, sem ponto (nunca se
põe o ponto no centro da cidade como se fosse o hospital):
  - o cadastro existe e está ativo no CNES;
  - o prefixo do CO_UNIDADE (2 primeiros dígitos = UF) bate com a UF da planilha do Ministério;
  - a coordenada cai dentro do retângulo do estado (com folga) e, em SP, a até 35 km do centro do município do hospital.

    py etl\\gerar_hospitais_oncologia_geo.py
"""
import csv
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "etl"))
import cruzar_hospitais_oncologia as c  # noqa: E402
import unidades_saude as us  # noqa: E402

LISTA = os.path.join(RAIZ, "dados_geograficos", "hospitais_oncologia_br.csv")
SAIDA = os.path.join(RAIZ, "dados_geograficos", "hospitais_oncologia_br_geo.csv")
FOLGA = 0.15  # graus (~16 km) de tolerância nas bordas do retângulo do estado

# Código IBGE da UF (2 primeiros dígitos do CO_UNIDADE) -> sigla
UF_POR_CODIGO = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
                 "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
                 "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
# Retângulo aproximado de cada estado: (lat_min, lat_max, lon_min, lon_max). Serve só para pegar erro GROSSO de cadastro
# (coordenada em outro estado, no mar, com sinal trocado); não é a fronteira.
CAIXA_UF = {"AC": (-11.2, -7.1, -74.0, -66.6), "AL": (-10.6, -8.8, -38.3, -35.1), "AP": (-1.3, 4.5, -54.9, -49.8),
            "AM": (-9.9, 2.3, -73.9, -56.1), "BA": (-18.4, -8.5, -46.7, -37.3), "CE": (-7.9, -2.7, -41.5, -37.2),
            "DF": (-16.1, -15.45, -48.3, -47.3), "ES": (-21.4, -17.8, -41.9, -39.6), "GO": (-19.6, -12.3, -53.3, -45.8),
            "MA": (-10.3, -1.0, -48.8, -41.7), "MT": (-18.1, -7.3, -61.7, -50.1), "MS": (-24.1, -17.1, -58.2, -50.9),
            "MG": (-22.95, -14.2, -51.1, -39.8), "PA": (-9.9, 2.7, -58.9, -46.0), "PB": (-8.4, -6.0, -38.8, -34.7),
            "PR": (-26.8, -22.5, -54.7, -48.0), "PE": (-9.6, -7.2, -41.4, -34.8), "PI": (-10.95, -2.7, -45.99, -40.3),
            "RJ": (-23.4, -20.7, -44.9, -40.9), "RN": (-6.99, -4.8, -38.6, -34.9), "RS": (-33.8, -27.0, -57.7, -49.6),
            "RO": (-13.7, -7.9, -66.9, -59.7), "RR": (-1.6, 5.3, -64.9, -58.8), "SC": (-29.4, -25.9, -53.9, -48.3),
            "SP": (-25.4, -19.7, -53.2, -44.1), "SE": (-11.6, -9.5, -38.3, -36.3), "TO": (-13.5, -5.1, -50.8, -45.6)}
CAMPOS = ["cnes", "uf", "municipio", "nome", "nome_ministerio", "tipo", "habilitacao", "endereco", "cep", "telefone", "lat", "lon",
          "no_mapa", "motivo"]


def ler_lista(caminho=LISTA):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def conferir(item, cadastro, centro=None):
    """(no_mapa, motivo): 'sim' + '' quando a posição passa em todas as conferências; senão 'não' + o que falhou."""
    if not cadastro:
        return "não", "não achei o CNES no cadastro (banco\\cnes)"
    if not cadastro.get("ativo", True):
        return "não", "cadastro desabilitado no CNES"
    prefixo = (cadastro.get("unidade") or "")[:2]
    if prefixo and UF_POR_CODIGO.get(prefixo) not in (None, item["uf"]):
        return "não", f"o CNES é de {UF_POR_CODIGO[prefixo]}, e a planilha diz {item['uf']}"
    lat, lon = cadastro.get("lat"), cadastro.get("lon")
    if lat is None or lon is None:
        return "não", "o cadastro não tem coordenada"
    caixa = CAIXA_UF.get(item["uf"])
    if caixa and not (caixa[0] - FOLGA <= lat <= caixa[1] + FOLGA and caixa[2] - FOLGA <= lon <= caixa[3] + FOLGA):
        return "não", f"a coordenada cai fora de {item['uf']}"
    if item["uf"] == "SP" and centro is not None:
        km = c.localizacao.distancia_km(lat, lon, centro[0], centro[1])
        if km > c.LIMITE_KM_DO_CENTRO:
            return "não", f"a coordenada fica a {km:.0f} km do centro do município"
    return "sim", ""


def montar(lista, cadastros, centros=None):
    centros = centros or {}
    saida = []
    for item in lista:
        cad = cadastros.get(item["cnes"])
        ok, motivo = conferir(item, cad, centros.get(item["cnes"]))
        saida.append({
            "cnes": item["cnes"], "uf": item["uf"], "municipio": item["municipio"],
            "nome": (cad or {}).get("nome") or item["nome_ministerio"], "nome_ministerio": item["nome_ministerio"],
            "tipo": item["tipo"], "habilitacao": item["habilitacao"],
            "endereco": (cad or {}).get("endereco", ""), "cep": (cad or {}).get("cep", ""), "telefone": (cad or {}).get("telefone", ""),
            "lat": f"{cad['lat']:.6f}" if ok == "sim" else "", "lon": f"{cad['lon']:.6f}" if ok == "sim" else "",
            "no_mapa": ok, "motivo": motivo})
    return saida


def gravar(linhas, caminho=SAIDA):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
        w.writeheader()
        w.writerows(linhas)


def main():
    lista = ler_lista()
    cadastros, aviso = c.ler_cnes(us.PASTA_CNES, {i["cnes"] for i in lista})
    if aviso:
        print("AVISO:", aviso)
    centros = {}
    if os.path.exists(c.BANCO):
        try:
            centros = c.centros_dos_municipios(c.BANCO, [i["cnes"] for i in lista if i["uf"] == "SP"])
        except Exception as erro:  # sem banco/tabela de localização: só a conferência pelo retângulo do estado
            print("Sem os centros dos municípios de SP (", erro, "): em SP vale só o retângulo do estado.")
    linhas = montar(lista, cadastros, centros)
    gravar(linhas)
    sim = sum(1 for l in linhas if l["no_mapa"] == "sim")
    print(f"{len(linhas)} estabelecimentos | {sim} com posição confirmada no mapa | {len(linhas) - sim} só na lista")
    por_motivo = {}
    for l in linhas:
        if l["no_mapa"] != "sim":
            por_motivo.setdefault(l["motivo"].split(" a ")[0] if "km" in l["motivo"] else l["motivo"], []).append(l)
    for motivo, itens in sorted(por_motivo.items(), key=lambda x: -len(x[1])):
        print(f"\n{len(itens)} sem ponto: {motivo}")
        for l in itens[:12]:
            print(f"   - {l['uf']} | {l['municipio']} | {l['nome_ministerio'][:44]} | CNES {l['cnes']} | {l['motivo']}")
    print("\nGravado em dados_geograficos\\hospitais_oncologia_br_geo.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
