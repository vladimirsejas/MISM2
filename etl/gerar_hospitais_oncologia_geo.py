"""Endereço, telefone e POSIÇÃO dos estabelecimentos habilitados em oncologia (Brasil), vindos do CNES.

Junta a lista oficial (dados_geograficos\\hospitais_oncologia_br.csv) com o tbEstabelecimento do CNES (banco\\cnes) e grava
dados_geograficos\\hospitais_oncologia_br_geo.csv, que a página "Hospitais de câncer" lê. Só dado público (nome, endereço,
telefone e coordenada do cadastro do estabelecimento). Só LÊ o CNES e o banco; nunca altera nada.

A posição só vira ponto no mapa quando PASSA nas conferências; senão o hospital fica na lista, sem ponto (nunca se
põe o ponto no centro da cidade como se fosse o hospital):
  - o cadastro existe e está ativo no CNES;
  - o prefixo do CO_UNIDADE (2 primeiros dígitos = UF) bate com a UF da planilha do Ministério;
  - a coordenada cai dentro do retângulo do estado (com folga) e, em SP, a até 35 km do centro do município do hospital;
  - a coordenada cai dentro do CONTORNO de um dos municípios candidatos (o do código do CNES ou o do nome da planilha),
    com o contorno baixado do IBGE (uma vez; fica em analises\\municipios_ibge_caixas.csv). Sem internet, essa conferência é pulada.

    py etl\\gerar_hospitais_oncologia_geo.py
"""
import csv
import math
import os
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "etl"))
import baixar_centroides as bc  # noqa: E402
import cruzar_hospitais_oncologia as c  # noqa: E402
import unidades_saude as us  # noqa: E402

LISTA = os.path.join(RAIZ, "dados_geograficos", "hospitais_oncologia_br.csv")
SAIDA = os.path.join(RAIZ, "dados_geograficos", "hospitais_oncologia_br_geo.csv")
CACHE_CAIXAS = os.path.join(RAIZ, "analises", "municipios_ibge_caixas.csv")
MARGEM_MUNICIPIO = 0.03  # graus (~3 km) de tolerância nas bordas do contorno do município
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


def _norm(t):
    return "".join(ch for ch in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(ch) != "Mn").lower().strip()


def caixa_da_geometria(geometria):
    """(lat_min, lat_max, lon_min, lon_max) de um Polygon ou MultiPolygon do IBGE (coordenadas [lon, lat])."""
    lats, lons = [], []

    def anda(no):
        if no and isinstance(no[0], (int, float)):
            lons.append(no[0])
            lats.append(no[1])
        else:
            for filho in no:
                anda(filho)
    anda(geometria["coordinates"])
    if not lats:
        raise ValueError("geometria sem coordenadas")
    return min(lats), max(lats), min(lons), max(lons)


def baixar_caixas(ufs, obter=bc.obter_json):
    """{'por_codigo': {codigo6: (caixa, nome, uf)}, 'por_nome': {(uf, nome normalizado): codigo6}} dos municípios dos estados pedidos."""
    codigo_da_uf = {v: k for k, v in UF_POR_CODIGO.items()}
    por_codigo, por_nome = {}, {}
    for uf in sorted(ufs):
        cod = codigo_da_uf[uf]
        malha = obter(f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{cod}?intrarregiao=municipio"
                      "&formato=application/vnd.geo+json&qualidade=minima")
        nomes = {str(m["id"]): m["nome"] for m in obter(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{cod}/municipios")}
        for f in malha["features"]:
            codigo = str(f["properties"].get("codarea") or "")
            if codigo not in nomes:
                continue
            por_codigo[codigo[:6]] = (caixa_da_geometria(f["geometry"]), nomes[codigo], uf)
            por_nome[(uf, _norm(nomes[codigo]))] = codigo[:6]
    return {"por_codigo": por_codigo, "por_nome": por_nome}


def gravar_caixas(caixas, caminho=CACHE_CAIXAS):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["codigo6", "uf", "nome", "lat_min", "lat_max", "lon_min", "lon_max"])
        for cod6, (cx, nome, uf) in caixas["por_codigo"].items():
            w.writerow([cod6, uf, nome, *cx])


def ler_caixas(caminho=CACHE_CAIXAS):
    """O cache de contornos, ou None se não existe."""
    if not os.path.isfile(caminho):
        return None
    por_codigo, por_nome = {}, {}
    with open(caminho, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            por_codigo[r["codigo6"]] = ((float(r["lat_min"]), float(r["lat_max"]), float(r["lon_min"]), float(r["lon_max"])), r["nome"], r["uf"])
            por_nome[(r["uf"], _norm(r["nome"]))] = r["codigo6"]
    return {"por_codigo": por_codigo, "por_nome": por_nome} if por_codigo else None


def municipios_candidatos(item, cadastro, caixas):
    """Códigos de 6 dígitos dos municípios onde o hospital pode estar: o do CO_UNIDADE do CNES e o do nome da planilha
    (a planilha às vezes traz dois nomes, 'Sorocaba e Itu'; cada parte conta). Só os que existem nos contornos."""
    cands = []
    prefixo = ((cadastro or {}).get("unidade") or "")[:6]
    if prefixo in caixas["por_codigo"]:
        cands.append(prefixo)
    nome = _norm(item.get("municipio"))
    for parte in [nome] + [p.strip() for p in nome.replace(",", " e ").split(" e ") if p.strip()]:
        cod = caixas["por_nome"].get((item["uf"], parte))
        if cod and cod not in cands:
            cands.append(cod)
    return cands


def onde_cai(lat, lon, caixas, uf, limite=3):
    """Nomes dos municípios do estado cujo retângulo contém o ponto, do menor para o maior (o mais específico primeiro).
    Os retângulos se sobrepõem nas divisas: é uma pista, não um endereço."""
    achados = []
    for _, (cx, nome, u) in caixas["por_codigo"].items():
        if u == uf and cx[0] <= lat <= cx[1] and cx[2] <= lon <= cx[3]:
            achados.append(((cx[1] - cx[0]) * (cx[3] - cx[2]), nome))
    return [n for _, n in sorted(achados)[:limite]]


def _km_fora(lat, lon, caixas_candidatas):
    """Distância aproximada (km), em linha reta, do ponto até o retângulo do município mais próximo (0 se estiver dentro)."""
    melhor = None
    for la0, la1, lo0, lo1 in caixas_candidatas:
        dlat = max(la0 - lat, 0, lat - la1) * 111.0
        dlon = max(lo0 - lon, 0, lon - lo1) * 111.0 * max(math.cos(math.radians(lat)), 0.1)
        d = math.hypot(dlat, dlon)
        melhor = d if melhor is None else min(melhor, d)
    return melhor or 0.0


def conferir(item, cadastro, centro=None, caixas=None):
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
    if caixas:
        cands = municipios_candidatos(item, cadastro, caixas)
        if cands:  # sem candidato conhecido, vale só o retângulo do estado
            dentro = any(cx[0] - MARGEM_MUNICIPIO <= lat <= cx[1] + MARGEM_MUNICIPIO and cx[2] - MARGEM_MUNICIPIO <= lon <= cx[3] + MARGEM_MUNICIPIO
                         for cx in (caixas["por_codigo"][k][0] for k in cands))
            if not dentro:
                nomes = " / ".join(caixas["por_codigo"][k][1] for k in cands)
                km = _km_fora(lat, lon, [caixas["por_codigo"][k][0] for k in cands])
                onde = onde_cai(lat, lon, caixas, item["uf"])
                pista = f"; o ponto cai em {', '.join(onde)}" if onde else "; o ponto não cai em nenhum município do estado"
                return "não", f"a coordenada cai fora do município ({nomes}), a cerca de {km:.0f} km do contorno{pista}"
    return "sim", ""


def montar(lista, cadastros, centros=None, caixas=None):
    centros = centros or {}
    saida = []
    for item in lista:
        cad = cadastros.get(item["cnes"])
        ok, motivo = conferir(item, cad, centros.get(item["cnes"]), caixas)
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
    caixas = ler_caixas()
    if caixas is None:
        print("Baixando os contornos dos municípios do IBGE (uma vez; 1 a 3 minutos)...")
        try:
            caixas = baixar_caixas({i["uf"] for i in lista if i["uf"] in CAIXA_UF})
            gravar_caixas(caixas)
        except Exception as erro:  # sem internet ou API fora do ar: só o retângulo do estado
            print("AVISO: não consegui os contornos do IBGE (", erro, "): vale só o retângulo do estado.")
            caixas = None
    linhas = montar(lista, cadastros, centros, caixas)
    gravar(linhas)
    sim = sum(1 for l in linhas if l["no_mapa"] == "sim")
    print(f"{len(linhas)} estabelecimentos | {sim} com posição confirmada no mapa | {len(linhas) - sim} só na lista"
          + ("" if caixas else " | SEM a conferência do contorno do município"))
    por_motivo = {}
    for l in linhas:
        if l["no_mapa"] != "sim":
            por_motivo.setdefault(l["motivo"].split(" a ")[0] if "km" in l["motivo"] else l["motivo"].split(" (")[0], []).append(l)
    for motivo, itens in sorted(por_motivo.items(), key=lambda x: -len(x[1])):
        print(f"\n{len(itens)} sem ponto: {motivo}")
        for l in itens[:12]:
            print(f"   - {l['uf']} | {l['municipio']} | {l['nome_ministerio'][:44]} | CNES {l['cnes']} | {l['motivo']}")
            cad = cadastros.get(l["cnes"]) or {}
            if cad.get("lat") is not None and cad.get("lon") is not None:
                print(f"       onde o CNES diz que fica: https://www.google.com/maps?q={cad['lat']:.6f},{cad['lon']:.6f}")
    print("\nGravado em dados_geograficos\\hospitais_oncologia_br_geo.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
