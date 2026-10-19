"""Teste do módulo de hospitais habilitados em oncologia (dados sintéticos)."""
import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd  # noqa: E402

import entendimento as ent  # noqa: E402
import hospitais_oncologia as h  # noqa: E402

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


LISTA = [
    {"cnes": "2000001", "uf": "SP", "municipio": "Barretos", "nome_ministerio": "Fundação Pio XII", "tipo": "CACON", "habilitacao": "CACON", "codigo_habilitacao": "17.12", "regiao_de_saude": "RRAS 13"},
    {"cnes": "2000002", "uf": "SP", "municipio": "Rio Claro", "nome_ministerio": "Santa Casa de Rio Claro", "tipo": "UNACON", "habilitacao": "UNACON", "codigo_habilitacao": "17.06", "regiao_de_saude": "RRAS 14"},
    {"cnes": "2000003", "uf": "MG", "municipio": "Uberaba", "nome_ministerio": "Hospital de Clínicas", "tipo": "UNACON", "habilitacao": "UNACON", "codigo_habilitacao": "17.06", "regiao_de_saude": "Macro"},
    {"cnes": "2000004", "uf": "BA", "municipio": "Salvador", "nome_ministerio": "Sem tipo", "tipo": "Tipo não informado", "habilitacao": "", "codigo_habilitacao": "", "regiao_de_saude": "Macro"},
]
GEO_CAMPOS = ["cnes", "uf", "municipio", "nome", "nome_ministerio", "tipo", "habilitacao", "endereco", "cep", "telefone", "lat", "lon", "no_mapa", "motivo"]
GEO = [
    {"cnes": "2000001", "uf": "SP", "municipio": "Barretos", "nome": "Hospital de Amor", "tipo": "CACON", "habilitacao": "CACON", "endereco": "Rua A, 1", "cep": "", "telefone": "(17) 3321-6600", "lat": "-20.557000", "lon": "-48.568000", "no_mapa": "sim", "motivo": ""},
    {"cnes": "2000002", "uf": "SP", "municipio": "Rio Claro", "nome": "Santa Casa de Rio Claro", "tipo": "UNACON", "habilitacao": "UNACON", "endereco": "Rua Dois, 297", "cep": "", "telefone": "(19) 3535-7000", "lat": "-22.411000", "lon": "-47.561000", "no_mapa": "sim", "motivo": ""},
    {"cnes": "2000003", "uf": "MG", "municipio": "Uberaba", "nome": "Hospital de Clínicas", "tipo": "UNACON", "habilitacao": "UNACON", "endereco": "", "cep": "", "telefone": "", "lat": "-19.750000", "lon": "-47.930000", "no_mapa": "sim", "motivo": ""},
    {"cnes": "2000004", "uf": "BA", "municipio": "Salvador", "nome": "Sem tipo", "tipo": "Tipo não informado", "habilitacao": "", "endereco": "", "cep": "", "telefone": "", "lat": "", "lon": "", "no_mapa": "não", "motivo": "o cadastro não tem coordenada"},
]


def gravar(pasta, nome, campos, linhas):
    with open(os.path.join(pasta, nome), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


with tempfile.TemporaryDirectory() as pasta:
    vazio = h.carregar(pasta)
    checar("sem nenhum arquivo: vazio, sem exceção", vazio.empty and vazio.attrs["fonte"] == "nenhuma")
    gravar(pasta, h.ARQ_LISTA, ["cnes", "uf", "municipio", "regiao_de_saude", "nome_ministerio", "codigo_habilitacao", "habilitacao", "tipo"], LISTA)
    so_lista = h.carregar(pasta)
    checar("só a lista oficial: 4 estabelecimentos, nenhum no mapa, e diz o que falta",
           len(so_lista) == 4 and not so_lista["no_mapa"].any() and so_lista.attrs["fonte"] == "lista" and not so_lista.attrs["tem_posicao"]
           and "gerar_hospitais_oncologia_geo" in so_lista.iloc[0]["motivo"])
    gravar(pasta, h.ARQ_GEO, GEO_CAMPOS, GEO)
    df = h.carregar(pasta)
    checar("com as posições: 3 no mapa e 1 só na lista", int(df["no_mapa"].sum()) == 3 and df.attrs["tem_posicao"] and df.attrs["fonte"] == "geo")
    checar("quem não passou nas conferências nunca vira ponto", df[df["cnes"] == "2000004"].iloc[0]["no_mapa"] == False)  # noqa: E712
    checar("conta por estado (total e com ponto), do maior para o menor",
           h.contar_por_uf(df) == [("SP", 2, 2), ("BA", 1, 0), ("MG", 1, 1)] or h.contar_por_uf(df)[0] == ("SP", 2, 2))
    checar("conta por tipo", h.contar_por_tipo(df) == {"UNACON": 2, "CACON": 1, "Tipo não informado": 1})
    checar("filtra por estado", set(h.filtrar(df, ufs=["SP"])["cnes"]) == {"2000001", "2000002"})
    checar("filtra por tipo", set(h.filtrar(df, tipos=["CACON"])["cnes"]) == {"2000001"})
    checar("busca por início de palavra, sem acento e sem maiúscula (clinicas -> Clínicas)", set(h.filtrar(df, busca="clinicas")["cnes"]) == {"2000003"})
    checar("busca pelo município", set(h.filtrar(df, busca="rio cla")["cnes"]) == {"2000002"})
    checar("trecho no meio da palavra não casa", h.filtrar(df, busca="ropolis").empty and h.filtrar(df, busca="zzz").empty)

    local = pd.DataFrame({"nome": ["Rio Claro", "Piracicaba", "Catanduva"], "latitude": [-22.373, -22.725, -21.137], "longitude": [-47.580, -47.649, -48.973]})
    local["chave"] = local["nome"].map(ent.normalizar)
    perto = h.mais_proximos(df, local, "Rio Claro", n=2)
    checar("o mais próximo de Rio Claro é a Santa Casa (poucos km), depois Barretos; só entra quem tem ponto",
           [r.cnes for _, r in perto] == ["2000002", "2000001"] and perto[0][0] < 10 and perto[1][0] > 100)
    checar("cidade fora da tabela: nenhuma distância, nunca posição inventada", h.mais_proximos(df, local, "Cidade Inexistente") == [] and h.mais_proximos(df, None, "Rio Claro") == [])
    lista = h.ordenar_por_distancia(df, local, "Rio Claro")
    com_ponto = int(df["no_mapa"].sum())
    checar("a lista de baixo segue a cidade: todos os estabelecimentos, o mais perto primeiro (km crescente) e quem não tem ponto por último, sem km",
           len(lista) == len(df) and lista.iloc[0]["cnes"] == "2000002" and lista.iloc[0]["km"] < 10
           and lista["km"].iloc[:com_ponto].is_monotonic_increasing and lista["km"].iloc[:com_ponto].notna().all()
           and lista["km"].iloc[com_ponto:].isna().all())
    checar("cidade fora da tabela ou sem cidade: a lista segue como veio, sem coluna km (não finge ordem)",
           "km" not in h.ordenar_por_distancia(df, local, "Cidade Inexistente").columns and "km" not in h.ordenar_por_distancia(df, local, "").columns
           and "km" not in h.ordenar_por_distancia(df, None, "Rio Claro").columns)
    checar("cidades disponíveis em ordem alfabética sem acento", h.cidades_disponiveis(local) == ["Catanduva", "Piracicaba", "Rio Claro"])

    checar("link de rota leva nome, endereço, município e UF", "destination=Hospital+de+Amor%2C+Rua+A%2C+1%2C+Barretos%2C+SP" in h.link_chegar("Hospital de Amor", "Rua A, 1", "Barretos", "SP"))
    checar("ligar: só com DDD (nunca chuta o DDD)", h.link_ligar("(17) 3321-6600") == "tel:+551733216600" and h.link_ligar("3321-6600") == "" and h.link_ligar("") == "")
    txt = h.leitura(df)
    checar("leitura descreve, conta no mapa e na lista, e lembra que habilitado não é vaga",
           "4 estabelecimentos" in txt and "3 aparecem no mapa" in txt and "1 está só na lista" in txt and "acesso é pela regulação" in txt
           and "porque" in txt and "estáão" not in txt)
    checar("leitura sem nada: mensagem simples", h.leitura(h.filtrar(df, ufs=["AC"])) == "Nenhum estabelecimento com esse filtro.")

import math  # noqa: E402


def _cabe(coords, w=1000, a=460):
    """Projeta cada ponto na tela com o centro e o zoom de vista_do_mapa (projeção web) e diz se todos caem dentro."""
    v = h.vista_do_mapa(coords, w, a)
    esc = 512 * 2 ** v["zoom"]  # o mapa (MapLibre) usa blocos de 512 px
    px = lambda lon: (lon + 180) / 360 * esc
    py = lambda lat: (1 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / math.pi) / 2 * esc
    cx, cy = px(v["longitude"]), py(v["latitude"])
    return all(abs(px(lo) - cx) <= w / 2 and abs(py(la) - cy) <= a / 2 for lo, la in coords)


barretos_jau_rc = [[-48.567, -20.557], [-48.558, -22.296], [-47.560, -22.410], [-47.070, -22.818], [-47.649, -22.725]]  # Barretos ao norte, Unicamp a leste
brasil = [[-60.0, 2.8], [-34.9, -8.0], [-52.0, -32.0], [-70.5, -9.9], [-47.9, -15.8]]
checar("enquadramento: Barretos (ao norte) não fica fora da tela, nem a visão Brasil", _cabe(barretos_jau_rc) and _cabe(brasil))
checar("enquadramento: um ponto só dá zoom de cidade; sem pontos não quebra",
       h.vista_do_mapa([[-47.5, -22.4]])["zoom"] == 10 and h.vista_do_mapa([])["zoom"] == 6)

if falhas:
    print("\nFALHARAM:", *falhas, sep="\n  - ")
    sys.exit(1)
print("\nTodas as checagens dos hospitais habilitados em oncologia passaram.")
