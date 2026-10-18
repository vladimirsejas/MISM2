"""Teste da conferência de posição dos hospitais habilitados (CNES sintético, um caso por motivo de rejeição)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cruzar_hospitais_oncologia as c  # noqa: E402
import gerar_hospitais_oncologia_geo as g  # noqa: E402

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


def item(cnes, uf, municipio, nome="Hospital"):
    return {"cnes": cnes, "uf": uf, "municipio": municipio, "nome_ministerio": nome, "tipo": "UNACON", "habilitacao": "UNACON"}


LISTA = [item("2000001", "SP", "Rio Claro", "Santa Casa"), item("2000002", "RJ", "Niterói", "Hospital RJ"),
         item("2000003", "RJ", "Niterói", "Coordenada em SP"), item("2000004", "BA", "Salvador", "Sem coordenada"),
         item("2000005", "MG", "Uberaba", "Desabilitado"), item("2000006", "RS", "Porto Alegre", "Não está no CNES"),
         item("2000007", "SP", "Barretos", "Longe do centro"), item("2000008", "PR", "Curitiba", "UF do CNES diferente")]
CABECALHO = "CO_UNIDADE;CO_CNES;NO_FANTASIA;NO_LOGRADOURO;NU_ENDERECO;NO_BAIRRO;CO_CEP;NU_TELEFONE;NU_LATITUDE;NU_LONGITUDE;CO_MOTIVO_DESAB"
CNES = [
    "3543902000001;2000001;SANTA CASA;RUA DOIS;297;CENTRO;13500000;1935357000;-22,400000;-47,560000;",
    "3330302000002;2000002;HOSPITAL RJ;AV 1;10;CENTRO;24000000;2134000000;-22,890000;-43,120000;",
    "3330302000003;2000003;COORDENADA EM SP;AV 2;20;CENTRO;24000000;;-22,400000;-47,560000;",   # RJ com coordenada de Rio Claro
    "2930302000004;2000004;SEM COORDENADA;AV 3;30;CENTRO;40000000;;;;",
    "3131302000005;2000005;DESABILITADO;AV 4;40;CENTRO;38000000;;-19,750000;-47,930000;12",
    "3543702000007;2000007;LONGE DO CENTRO;AV 5;50;CENTRO;14780000;;-23,500000;-46,600000;",    # em SP, mas a ~400 km de Barretos
    "3543202000008;2000008;UF ERRADA;AV 6;60;CENTRO;80000000;;-25,430000;-49,270000;",          # CO_UNIDADE de SP (35), planilha diz PR
]
CENTROS = {"2000001": (-22.373, -47.580), "2000007": (-20.557, -48.568)}

with tempfile.TemporaryDirectory() as pasta:
    with open(os.path.join(pasta, "tbEstabelecimento202608.csv"), "w", encoding="latin-1", newline="") as f:
        f.write(CABECALHO + "\n" + "\n".join(CNES) + "\n")
    cadastros, aviso = c.ler_cnes(pasta, {i["cnes"] for i in LISTA})
    checar("lê o CNES sintético sem aviso e traz o código da unidade", not aviso and cadastros["2000001"]["unidade"] == "3543902000001")
    linhas = {l["cnes"]: l for l in g.montar(LISTA, cadastros, CENTROS)}
    checar("posição boa vira ponto (com seis casas)", linhas["2000001"]["no_mapa"] == "sim" and linhas["2000001"]["lat"] == "-22.400000")
    checar("RJ com coordenada de outro estado: sem ponto, e diz por quê", linhas["2000003"]["no_mapa"] == "não" and "fora de RJ" in linhas["2000003"]["motivo"] and linhas["2000003"]["lat"] == "")
    checar("sem coordenada: sem ponto", linhas["2000004"]["no_mapa"] == "não" and "não tem coordenada" in linhas["2000004"]["motivo"])
    checar("cadastro desabilitado: sem ponto", linhas["2000005"]["no_mapa"] == "não" and "desabilitado" in linhas["2000005"]["motivo"])
    checar("não está no CNES: sem ponto", linhas["2000006"]["no_mapa"] == "não" and "não achei" in linhas["2000006"]["motivo"])
    checar("em SP, longe do centro do município: sem ponto", linhas["2000007"]["no_mapa"] == "não" and "km do centro" in linhas["2000007"]["motivo"])
    checar("UF do CO_UNIDADE diferente da planilha: sem ponto", linhas["2000008"]["no_mapa"] == "não" and "o CNES é de SP" in linhas["2000008"]["motivo"])
    checar("hospital sem ponto continua na lista com nome e endereço (nunca some)", all(l["nome"] for l in linhas.values()) and len(linhas) == 8)
    checar("nunca grava coordenada de quem não passou", all(l["lat"] == "" and l["lon"] == "" for l in linhas.values() if l["no_mapa"] != "sim"))
    destino = os.path.join(pasta, "geo.csv")
    g.gravar(list(linhas.values()), destino)
    checar("grava o CSV com o cabeçalho esperado", open(destino, encoding="utf-8-sig").readline().strip().split(";") == g.CAMPOS)

# ---------- contorno do município (IBGE) ----------
poligono = {"type": "Polygon", "coordinates": [[[-47.60, -22.45], [-47.50, -22.45], [-47.50, -22.30], [-47.60, -22.30], [-47.60, -22.45]]]}
multi = {"type": "MultiPolygon", "coordinates": [[[[-48.0, -20.0], [-47.9, -20.0], [-47.9, -19.9], [-48.0, -20.0]]],
                                                  [[[-48.5, -20.5], [-48.4, -20.5], [-48.4, -20.4], [-48.5, -20.5]]]]}
checar("caixa de um Polygon", g.caixa_da_geometria(poligono) == (-22.45, -22.30, -47.60, -47.50))
checar("caixa de um MultiPolygon cobre todas as partes", g.caixa_da_geometria(multi) == (-20.5, -19.9, -48.5, -47.9))


def falso_ibge(url):
    if "/malhas/estados/35" in url:
        return {"features": [{"properties": {"codarea": "3543907"}, "geometry": poligono},
                             {"properties": {"codarea": "3503208"}, "geometry": multi},
                             {"properties": {"codarea": "9999999"}, "geometry": poligono}]}   # sem nome: ignorado
    if "/localidades/estados/35/" in url:
        return [{"id": 3543907, "nome": "Rio Claro"}, {"id": 3503208, "nome": "Araraquara"}]
    if "/malhas/estados/33" in url:
        return {"features": [{"properties": {"codarea": "3304557"}, "geometry": poligono}]}
    if "/localidades/estados/33/" in url:
        return [{"id": 3304557, "nome": "Rio de Janeiro"}]
    raise AssertionError("URL inesperada: " + url)


caixas = g.baixar_caixas({"SP", "RJ"}, obter=falso_ibge)
checar("baixa os contornos por estado (ignora o que não tem nome) e indexa por código e por nome",
       set(caixas["por_codigo"]) == {"354390", "350320", "330455"} and caixas["por_nome"][("SP", "rio claro")] == "354390")
with tempfile.TemporaryDirectory() as pasta:
    caminho = os.path.join(pasta, "caixas.csv")
    g.gravar_caixas(caixas, caminho)
    volta = g.ler_caixas(caminho)
    checar("o cache grava e lê de volta a mesma coisa", volta["por_codigo"] == caixas["por_codigo"] and volta["por_nome"] == caixas["por_nome"])
    checar("sem cache: devolve None (e o script baixa)", g.ler_caixas(os.path.join(pasta, "nao_existe.csv")) is None)

hosp = item("2000010", "SP", "Rio Claro", "Santa Casa")
cad = {"unidade": "3543902000010", "ativo": True, "lat": -22.40, "lon": -47.55}
checar("candidatos: o do código do CNES e o do nome da planilha", g.municipios_candidatos(hosp, cad, caixas) == ["354390"])
checar("planilha com dois nomes ('Rio Claro e Araraquara'): cada parte conta",
       set(g.municipios_candidatos(item("2000011", "SP", "Rio Claro e Araraquara"), {"unidade": ""}, caixas)) == {"354390", "350320"})
checar("município sem contorno conhecido: nenhum candidato", g.municipios_candidatos(item("2000012", "SP", "Cidade Nova"), {"unidade": "3599992000012"}, caixas) == [])
checar("ponto dentro do município: confirmado", g.conferir(hosp, cad, None, caixas) == ("sim", ""))
fora = dict(cad, lat=-23.50, lon=-46.60)  # dentro do estado de SP, mas em outra cidade
ok, motivo = g.conferir(hosp, fora, None, caixas)
checar("ponto no estado certo mas na CIDADE errada: rejeitado (o que o retângulo do estado não pegava)", ok == "não" and "fora do município (Rio Claro)" in motivo)
checar("ponto no município do NOME da planilha, mas o código do CNES é de outro: aceito (basta um dos dois)",
       g.conferir(item("2000013", "SP", "Araraquara"), dict(cad, unidade="3543902000013", lat=-20.0, lon=-47.95), None, caixas)[0] == "sim")
checar("sem candidato conhecido: vale só o retângulo do estado (não rejeita por falta de contorno)",
       g.conferir(item("2000014", "SP", "Cidade Nova"), dict(cad, unidade="3599992000014"), None, caixas)[0] == "sim")
checar("sem contornos (sem internet): como antes, só o retângulo do estado", g.conferir(hosp, fora, None, None)[0] == "sim")
checar("a margem de ~3 km nas bordas é tolerada", g.conferir(hosp, dict(cad, lat=-22.46, lon=-47.55), None, caixas)[0] == "sim"
       and g.conferir(hosp, dict(cad, lat=-22.60, lon=-47.55), None, caixas)[0] == "não")
via_montar = {l["cnes"]: l for l in g.montar([hosp], {"2000010": dict(cad, lat=-23.50, lon=-46.60, nome="Santa Casa", endereco="", cep="", telefone="")}, None, caixas)}
caixa_teste = (-22.45, -22.30, -47.60, -47.50)
checar("distância ao contorno: dentro = 0; 0,1 grau ao sul = ~11 km; o motivo mostra os km",
       g._km_fora(-22.40, -47.55, [caixa_teste]) == 0 and 10 < g._km_fora(-22.55, -47.55, [caixa_teste]) < 12
       and "km do contorno" in g.conferir(hosp, dict(cad, lat=-22.55, lon=-47.55), None, caixas)[1])
checar("onde_cai: o município do ponto, do menor para o maior retângulo; fora de tudo = vazio",
       g.onde_cai(-22.40, -47.55, caixas, "SP") == ["Rio Claro"] and g.onde_cai(-10.0, -40.0, caixas, "SP") == [])
checar("o motivo diz onde o ponto cai (pista para conferir)", "o ponto cai em" in g.conferir(item("2000020", "SP", "Araraquara"), dict(cad, unidade="3503202000020", lat=-22.40, lon=-47.55), None, caixas)[1]
       or "o ponto não cai" in g.conferir(item("2000020", "SP", "Araraquara"), dict(cad, unidade="3503202000020", lat=-22.40, lon=-47.55), None, caixas)[1])
checar("montar usa os contornos: sem ponto e com o motivo", via_montar["2000010"]["no_mapa"] == "não" and via_montar["2000010"]["lat"] == "")

checar("todo estado tem retângulo e código IBGE (27)", len(g.CAIXA_UF) == 27 and len(g.UF_POR_CODIGO) == 27 and set(g.UF_POR_CODIGO.values()) == set(g.CAIXA_UF))
if falhas:
    print("\nFALHARAM:", *falhas, sep="\n  - ")
    sys.exit(1)
print("\nTodas as checagens das coordenadas dos hospitais habilitados passaram.")
