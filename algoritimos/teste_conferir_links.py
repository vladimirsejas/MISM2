import sys

import conferir_links as c

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


checar("mesmo endereço (http/https, www e barra no fim não contam) é OK",
       c.classificar("http://www.gov.br/inca/x/", 200, "https://gov.br/inca/x", None) == "OK")
checar("terminar em outra página é REDIRECIONOU", c.classificar("https://gov.br/inca/tipos/intestino", 200,
                                                                "https://gov.br/inca/cartilhas", None) == "REDIRECIONOU")
checar("404 e erro de rede são ERRO", c.classificar("https://a.br/x", 404, "https://a.br/x", "HTTP 404") == "ERRO"
       and c.classificar("https://a.br/x", None, "https://a.br/x", "URLError") == "ERRO")

mapa = {"https://a.br/ok": (200, "https://a.br/ok", None), "https://a.br/velho": (200, "https://a.br/geral", None),
        "https://a.br/sumiu": (404, "https://a.br/sumiu", "HTTP 404")}
consultas = []


def falso(url):
    consultas.append(url)
    return mapa[url]


itens = [{"id": "a", "link": "https://a.br/ok"}, {"id": "b", "link": "https://a.br/velho"},
         {"id": "c", "link": "https://a.br/sumiu"}, {"id": "d", "link": "https://a.br/ok"}]
r = c.conferir(abrir_url=falso, pausa=0, itens=itens)
checar("classifica cada cartão", [x[1] for x in r] == ["OK", "REDIRECIONOU", "ERRO", "OK"])
checar("link repetido é consultado uma vez só", consultas.count("https://a.br/ok") == 1)
checar("filtra por id", [x[0] for x in c.conferir(ids={"b"}, abrir_url=falso, pausa=0, itens=itens)] == ["b"])
checar("página que abre com certificado não verificável é AVISO (não ERRO)",
       c.classificar("https://a.br/x", 200, "https://a.br/x", "CERTIFICADO não verificável (a página abre)") == "AVISO")
checar("abrir() nunca levanta exceção (endereço inválido vira ERRO)", c.abrir("http://localhost:1/nada")[2] is not None)
print("Todas as checagens passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
