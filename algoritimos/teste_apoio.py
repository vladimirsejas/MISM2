import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import apoio  # noqa: E402
from lia import INICIO  # noqa: E402

# =====================================
# TESTE DO APOIO À MULHER (algoritimos/apoio.py)
#
# Catálogo: todo item tem fonte, link oficial (https), caminho e
# lâmina válidos, ids únicos. Lia: percorre a árvore inteira a partir
# do início (todos os botões, até não sobrar botão novo) e confere
# que cada resposta tem fala, expressão válida, destino numa lâmina
# e termina com "Começar de novo"; item a confirmar deixa a Lia
# cautelosa; nenhuma fala promete vaga nem dá conduta médica.
# Uso: py algoritimos\teste_apoio.py
# =====================================

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


# ---------- catálogo ----------
ids = [i["id"] for i in apoio.ITENS]
checar("ids únicos", len(ids) == len(set(ids)))
checar("todo item tem fonte e link https", all(i["fonte"] and i["link"].startswith("https://") for i in apoio.ITENS))
checar("todo item está num caminho válido (sem caminho só fora da lâmina dos caminhos)",
       all(i["caminho"] in apoio.NOME_CAMINHO or (i["caminho"] is None and i["lamina"] != "caminho")
           for i in apoio.ITENS))
checar("todo item de Barretos está num tema da lâmina",
       all(i["grupo"] in apoio.GRUPOS_BARRETOS for i in apoio.itens(lamina="barretos")))
checar("Barretos tem hospitais de referência e carretas",
       apoio.itens(lamina="barretos") and all(any(i["grupo"] == g for i in apoio.ITENS)
                                              for g in ("Hospitais de referência", "Carretas e unidades móveis")))
checar("toda lâmina de item existe", all(i["lamina"] in apoio.LAMINAS and i["lamina"] != "sobre"
                                         for i in apoio.ITENS))
checar("todo item de lâmina com temas/regiões está num deles",
       all(i["grupo"] in apoio.GRUPOS[lam] for lam in apoio.GRUPOS for i in apoio.itens(lamina=lam)))
checar("todo 'também em' aponta para um tema/região que existe",
       all(g in apoio.GRUPOS.get(lam, ()) for i in apoio.ITENS for lam, g in i["tambem"]))
checar("todo tema/região tem pelo menos um item", all(sum(map(len, apoio.do_grupo(lam, g)))
                                                       for lam in apoio.GRUPOS for g in apoio.GRUPOS[lam]))
checar("Hospitais no Estado: pelo menos 20 hospitais", len(apoio.itens(lamina="hospitais")) >= 20)
checar("proteção à mulher (em Preciso de ajuda): pelo menos 8 canais", len(apoio.itens(caminho="ajuda")) >= 8)
checar("as 8 portas combinadas com o autor", list(apoio.NOME_CAMINHO) == [
    "mama", "colo", "diagnostico", "regulacao", "tratamento", "rede", "direitos", "ajuda"])
checar("Preciso de ajuda: 6 pontos do caminho, com violência", len(apoio.ETAPAS) == 6
       and "violencia" in apoio.NOME_ETAPA)
checar("todo ponto do caminho aponta para portas e itens que existem",
       all(set(portas) <= set(apoio.NOME_CAMINHO) and all(i in apoio.POR_ID for i in ids)
           for _, _, _, portas, ids in apoio.ETAPAS) and all(apoio.itens_da_etapa(e) for e in apoio.NOME_ETAPA))
checar("todo 'tambem_caminhos' aponta para uma porta que existe",
       all(c in apoio.NOME_CAMINHO and c != i["caminho"] for i in apoio.ITENS for c in i["tambem_caminhos"]))
checar("diagnóstico explica mamografia e preventivo alterados",
       {"mamografia_alterada", "preventivo_alterado"} <= {i["id"] for i in apoio.itens(caminho="diagnostico")})
checar("regulação diz o que fazer se o nome não aparecer", "nao_achei_nome" in apoio.POR_ID
       and apoio.POR_ID["nao_achei_nome"]["caminho"] == "regulacao")
checar("fluxo da rede aponta para portas que existem", all(p in apoio.NOME_CAMINHO for _, _, p in apoio.FLUXO_REDE))
checar("caminho Seus direitos com TFD e reconstrução da mama",
       {"tfd", "reconstrucao_mamaria"} <= {i["id"] for i in apoio.itens(caminho="direitos")})
checar("todo caminho tem pelo menos um item", all(apoio.itens(caminho=c) for c in apoio.NOME_CAMINHO))
checar("Rio Claro tem lâmina com itens", len(apoio.itens(lamina="rio_claro")) >= 4)
checar("Cadu de Rio Claro aparece como serviço de apoio à mulher",
       "rc_cadu_agendamento" in apoio.POR_ID
       and "0800 019 0505" in apoio.POR_ID["rc_cadu_agendamento"]["contato"]
       and apoio.POR_ID["rc_cadu_agendamento"]["link"].startswith("https://")
       and apoio.POR_ID["rc_cadu_agendamento"]["conferido"] == "09/10/2026")
checar("Barretos tem lâmina com itens", len(apoio.itens(lamina="barretos")) >= 3)
outras = {"Campinas", "Ribeirão Preto", "São José do Rio Preto"}
checar("outras cidades entram só nos caminhos e na lista de hospitais (sem lâmina própria)",
       all(i["lamina"] in ("caminho", "hospitais") for i in apoio.ITENS if i["onde"] in outras)
       and any(i["onde"] in outras for i in apoio.ITENS)
       and any(i["onde"].startswith("Piracicaba") for i in apoio.ITENS))
checar("texto sem seta ASCII (->)", not any("->" in str(v) for i in apoio.ITENS for v in i.values()))

# ---------- a Lia: árvore inteira ----------
inicio = apoio.responder(INICIO)
checar("saudação diz onde a pessoa está", apoio.CIDADE in inicio.fala and inicio.expressao == "acolhedora")
checar("saudação oferece as 8 portas", all(any(a == apoio.caminho(c) for _, a in inicio.botoes)
                                              for c in apoio.NOME_CAMINHO))

vistos, fila, respostas = set(), deque([INICIO]), 0
problemas = []
while fila:
    acao = fila.popleft()
    chave = tuple(sorted(acao.items()))
    if chave in vistos:
        continue
    vistos.add(chave)
    r = apoio.responder(acao)
    respostas += 1
    if not r.fala or r.expressao not in ("acolhedora", "explicando", "atenta", "cautelosa", "pensativa"):
        problemas.append(f"fala/expressão: {acao}")
    if not r.destino or r.destino.get("aba") not in apoio.LAMINAS.values():
        problemas.append(f"destino: {acao}")
    if acao is not INICIO and (not r.botoes or r.botoes[-1] != ("Começar de novo", INICIO)):
        problemas.append(f"sem começar de novo: {acao}")
    for proibida in ("vai conseguir", "vaga garantida", "garantimos", "tome ", "você tem câncer"):
        if proibida in r.fala.lower():
            problemas.append(f"fala proibida '{proibida}': {acao}")
    if acao.get("tipo") == "apoio_item":
        i = apoio.POR_ID[acao["id"]]
        if (i["confirmar"] is not None) != (r.expressao == "cautelosa"):
            problemas.append(f"expressão x confirmar: {acao}")
        data_item = i.get("conferido", apoio.CONFERIDO)
        if i["link"] not in r.fala or not any(data_item in n for n in r.numeros):
            problemas.append(f"item sem link/data específica: {acao}")
    for _, a in r.botoes:
        fila.append(a)
checar(f"árvore inteira sem problemas ({respostas} respostas)", not problemas)
for p in problemas[:10]:
    print("   ", p)
itens_alcancados = {dict(k)["id"] for k in vistos if dict(k).get("tipo") == "apoio_item"}
checar("todo item é alcançável pelos botões", itens_alcancados == set(ids))
checar("botão desconhecido volta à saudação", apoio.responder({"tipo": "apoio_item", "id": "nao_existe"}).fala
       == inicio.fala)

# ---------- itinerário das carretas ----------
from datetime import date  # noqa: E402
dia = date(2026, 9, 24)
agora = {c["cidade"] for c in apoio.carretas(dia) if c["situacao"] == "agora"}
checar("carretas em 24/09/2026: as 8 em andamento", agora == {
    "Eldorado", "Piquete", "Araçoiaba da Serra", "Bertioga", "Serrana", "Barra do Turvo", "Itapura", "Avaré"})
checar("carretas: Bananal e Paraisópolis já passaram; Apiaí sem data",
       {c["cidade"]: c["situacao"] for c in apoio.carretas(dia)}["Bananal"] == "encerrada"
       and {c["cidade"]: c["situacao"] for c in apoio.carretas(dia)}["Apiaí"] == "sem_data")
checar("carretas: em 01/09 Bananal aparece como em breve",
       {c["cidade"]: c["situacao"] for c in apoio.carretas(date(2026, 9, 1))}["Bananal"] == "em_breve")
checar("carretas: a Lia diz onde a carreta está hoje", "Araçoiaba da Serra" in apoio.frase_carretas(dia))
checar("carretas: itinerário vencido manda ver o novo no Poupatempo",
       apoio.itinerario_vencido(date(2026, 10, 10)) and "Poupatempo" in apoio.frase_carretas(date(2026, 10, 10)))
checar("carretas: toda fonte do itinerário existe", all(c["fonte"] in apoio.FONTES_ITINERARIO
                                                         for c in apoio.ITINERARIO))

print()
print("Todas as checagens do apoio passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
