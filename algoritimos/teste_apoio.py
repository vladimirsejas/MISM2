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


def textos(valor):
    """Reúne textos aninhados de estruturas do guia para verificar conteúdo visível."""
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return sum((textos(v) for v in valor.values()), [])
    if isinstance(valor, (list, tuple)):
        return sum((textos(v) for v in valor), [])
    return []


# ---------- catálogo ----------
ids = [i["id"] for i in apoio.ITENS]
checar("ids únicos", len(ids) == len(set(ids)))
checar("todo item tem fonte e link https", all(i["fonte"] and i["link"].startswith("https://") for i in apoio.ITENS))

# ---------- ausência de itinerário histórico das carretas ----------
textos_guia = textos(apoio.ITENS) + textos(apoio.INTRO_LAMINA) + textos(apoio.ETAPAS)
textos_guia.extend([apoio.saudacao().fala])
textos_guia.extend(apoio.responder_caminho(c).fala for c in apoio.NOME_CAMINHO)
historicos = ("fevereiro de 2025", "esteve em rio claro", "araçoiaba", "bertioga", "serrana",
              "avare", "itapura", "eldorado", "piquete", "bananal")
normalizado = " ".join(textos_guia).casefold()
checar("nenhum itinerário antigo aparece nos textos do guia ou da Lia",
       not any(t in normalizado for t in historicos))
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "dashboard", "pages", "apoio.py"), encoding="utf-8") as arquivo:
    texto_tela = arquivo.read().casefold()
checar("a página Apoio não apresenta a carreta histórica de Rio Claro",
       not any(t in texto_tela for t in historicos))
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
# 10/2026: as 8 portas combinadas com o autor ganharam a porta "Outros cânceres" (intestino, ovário, pele, pulmão, tireoide e
# corpo do útero), depois de o autor achar que o Apoio girava em torno do câncer de mama. As 8 de antes continuam, na ordem.
# 20/10/2026 (autor): "Regulação" saiu dos assuntos (técnico demais; a paciente não opera a regulação: o conteúdo mora em "Fui
# encaminhada") e "Tratamento" e "Rede oncológica" viraram um assunto só, "Tratamento pelo SUS".
checar("os assuntos, na ordem: sem Regulação, Tratamento unido à Rede oncológica e Diagnóstico unido a 'Meu exame deu alterado'",
       list(apoio.NOME_CAMINHO) == ["mama", "colo", "outros", "tratamento", "direitos", "ajuda"]
       and not {"regulacao", "rede", "diagnostico"} & set(apoio.NOME_CAMINHO))
checar("nenhum cartão ficou num assunto que não existe mais", all(i["caminho"] is None or i["caminho"] in apoio.NOME_CAMINHO for i in apoio.ITENS))  # None = só mora numa área
checar("Preciso de ajuda: 6 pontos do caminho, com violência", len(apoio.ETAPAS) == 6
       and "violencia" in apoio.NOME_ETAPA)
checar("todo ponto do caminho aponta para portas e itens que existem",
       all(set(portas) <= set(apoio.NOME_CAMINHO) and all(i in apoio.POR_ID for i in ids)
           for _, _, _, portas, ids in apoio.ETAPAS) and all(apoio.itens_da_etapa(e) for e in apoio.NOME_ETAPA))
checar("todo 'tambem_caminhos' aponta para uma porta que existe",
       all(c in apoio.NOME_CAMINHO and c != i["caminho"] for i in apoio.ITENS for c in i["tambem_caminhos"]))
checar("cartões técnicos de BI-RADS e colposcopia saíram (autor, 19/10/2026)",
       not {"mamografia_alterada", "preventivo_alterado"} & {i["id"] for i in apoio.itens()})
checar("prazo legal de 30 dias explicita hipótese principal e pedido médico fundamentado",
       "principal hipótese diagnóstica" in apoio.POR_ID["lei_30_dias"]["resumo"]
       and "pedido médico fundamentado" in apoio.POR_ID["lei_30_dias"]["resumo"]
       and "principal hipótese" in next(x[2] for x in apoio.ETAPAS if x[0] == "alterado"))
checar("diagnóstico recente tem um próximo passo prático sem indicar hospital por conta própria",
       "quem está responsável pelo encaminhamento" in next(x[2] for x in apoio.ETAPAS if x[0] == "diagnostico_cancer")
       and "60 dias" in next(x[2] for x in apoio.ETAPAS if x[0] == "diagnostico_cancer"))
checar("o que fazer se o nome não aparecer na fila continua no guia (assunto Tratamento) e na situação 'Fui encaminhada'",
       apoio.POR_ID["nao_achei_nome"]["caminho"] == "tratamento"
       and "nao_achei_nome" in next(x[4] for x in apoio.ETAPAS if x[0] == "encaminhada"))
checar("o passo da vaga explica que quem pede é a equipe de saúde (a paciente não opera a regulação)",
       any("a unidade de saúde pede a vaga" in o for _, o, _ in apoio.FLUXO_REDE))
checar("fluxo do caminho na rede aponta para assuntos, situações ou áreas que existem",
       all(p in apoio.NOME_CAMINHO or p == "hospitais" or (p.startswith("etapa:") and p[6:] in apoio.NOME_ETAPA)
           for _, _, p in apoio.FLUXO_REDE))
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

# ---------- vocabulário da usuária: "lâmina" é termo interno (autor, 10/2026), ela lê "área" ----------
_lidos = [apoio.saudacao().fala, apoio.responder_sobre().fala]
for _c in apoio.NOME_CAMINHO:
    _lidos.append(apoio.responder_caminho(_c).fala)
    _lidos += [t for t, _ in apoio.responder_caminho(_c).botoes]
for _i in apoio.POR_ID:
    _lidos.append(apoio.responder_item(_i).fala)
for _l in ("hospitais", "carretas", "rio_claro", "barretos"):
    _lidos.append(apoio.responder_lamina(_l).fala)
checar("nenhum texto lido pela usuária (cartões, botões, falas da Lia) usa a palavra 'lâmina'",
       not any("lâmina" in t.lower() or "lamina" in t.lower() for t in _lidos))

# ---------- a Lia: árvore inteira ----------
inicio = apoio.responder(INICIO)
checar("saudação diz onde a pessoa está", apoio.CIDADE in inicio.fala and inicio.expressao == "acolhedora")
checar("saudação oferece todas as portas", all(any(a == apoio.caminho(c) for _, a in inicio.botoes)
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
fala_carretas = apoio.frase_carretas()
checar("carretas: a Lia aponta para o itinerário do SP Por Todas e do Poupatempo",
       apoio.URL_CARRETAS_SP_POR_TODAS in fala_carretas
       and apoio.URL_CARRETAS_POUPATEMPO in fala_carretas)
checar("carretas: a Lia não reproduz cidades nem datas de uma rota que pode vencer",
       "Araçoiaba da Serra" not in fala_carretas and "24/09" not in fala_carretas)
checar("carretas: o grupo estadual não mistura a ação histórica do Hospital de Amor",
       [i["id"] for i in apoio.itens(lamina="carretas")] == ["carretas_estado"])
checar("Rio Claro: não mostra o registro antigo da carreta do Hospital de Amor",
       all(i["id"] != "rc_carreta_hospital_de_amor" for i in apoio.itens(lamina="rio_claro")))

# ---------- auditoria de usabilidade (20/10/2026) ----------
for id_ in ("santa_casa_piracicaba", "fornecedores_cana", "santa_casa_limeira"):
    checar(f"{id_}: o botão avisa que o link é o boletim da região (PDF), não a página do hospital",
           "boletim" in apoio.rotulo_do_link(apoio.POR_ID[id_]).lower() and "PDF" in apoio.responder_item(id_).fala)
checar("os outros cartões continuam com 'Abrir a página oficial'",
       all(apoio.rotulo_do_link(i) == "Abrir a página oficial" for i in apoio.ITENS if i["id"] not in apoio.ROTULO_LINK))
termos = [t for t, _ in apoio.GLOSSARIO]
checar("glossário explica as palavras que a usuária não conhece (UBS, regulação, UNACON, RRAS, TFD...)",
       all(any(k in t for t in termos) for k in ("UBS", "Regulação", "UNACON", "RRAS", "TFD", "Rede oncológica")))
checar("glossário: nenhuma explicação vazia e a região de Rio Claro bate com o catálogo",
       all(len(e) > 20 for _, e in apoio.GLOSSARIO) and any(apoio.REGIAO in e for _, e in apoio.GLOSSARIO))
visivel = " ".join(r.fala + " ".join(b[0] for b in r.botoes) for r in (
    [apoio.saudacao()] + [apoio.responder_caminho(c) for c in apoio.NOME_CAMINHO]
    + [apoio.responder_etapa(e) for e in apoio.NOME_ETAPA]))
botoes_lia = " ".join(b[0].lower() for r in [apoio.saudacao()] + [apoio.responder_etapa(e) for e in apoio.NOME_ETAPA] for b in r.botoes)
checar("Lia: sem a metáfora interna ('Porta X', 'esta porta', 'uma porta'); 'porta de entrada' é expressão comum e fica",
       "porta " not in botoes_lia and not any(t in visivel.lower() for t in ("esta porta", "uma porta", "as portas", "nas portas")))
curto = apoio.onde_mora(apoio.POR_ID["colo_utero"]), apoio.onde_mora(apoio.POR_ID["icesp"])
checar("onde_mora diz 'no assunto' ou 'na área', já com a preposição", curto[0].startswith("no assunto")
       and curto[1].startswith("na área"))

print()
print("Todas as checagens do apoio passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
