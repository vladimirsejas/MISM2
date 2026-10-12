import os
import sys
import time
from collections import deque

# =====================================
# TESTE DE ACEITAÇÃO DA LÂMINA DE APOIO (dashboard/pages/apoio.py)
#
# Abre a página DE VERDADE (Streamlit AppTest) e clica como a pessoa:
#   A. boas-vindas: cada caminho do centro leva à lâmina e ao caminho;
#   B. Lia na lateral: todos os botões, até não sobrar botão novo; em
#      cada clique a tela não quebra e a lâmina é a do destino;
#   C. "← Voltar" e "Começar de novo";
#   D. as 4 lâminas abrem, e cada caminho da lâmina "Encontre um
#      caminho" mostra os cartões dele.
# Não precisa de banco (a página não lê o banco).
# Uso (da pasta do projeto):  py dashboard\teste_apoio_tela.py
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))

import apoio  # noqa: E402
from html import escape as _html_esc  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def abrir():
    at = AppTest.from_file(os.path.join(RAIZ, "dashboard", "pages", "apoio.py"), default_timeout=60)
    at.run()
    return at


def erros(at):
    return [str(e.value) for e in at.exception]


def botao(at, key):
    return next((b for b in at.button if b.key == key), None)


def botoes_lia(at):
    return [b for b in at.sidebar.button if b.key and b.key.startswith("lia_ap_")]


inicio = time.time()

# ---------- A. boas-vindas ----------
at = abrir()
checar("A. abre sem erro", not erros(at))
checar("A. boas-vindas no centro com as 3 entradas principais",
       all(botao(at, f"bv_ap_{c}") is not None for c in ("prevencao", "diagnostico", "ajuda")))
checar("A. mesma Lia na lateral (rosto + nome)",
       any("lia-nome" in m.value for m in at.sidebar.markdown) and any("lia-rosto" in m.value for m in at.sidebar.markdown))
for entrada, caminho in (("prevencao", "mama"), ("diagnostico", "diagnostico"), ("ajuda", "ajuda")):
    at = abrir()
    botao(at, f"bv_ap_{entrada}").click().run()
    checar(f"A. entrada {entrada} do centro", not erros(at)
           and at.session_state["ap_caminho"] == caminho
           and at.session_state["ap_aba"] == apoio.LAMINAS["caminho"]
           and botao(at, f"bv_ap_{entrada}") is None)

# ---------- B. Lia: todos os botões ----------
at = abrir()
botao(at, "bv_fechar_apoio").click().run()
vistos, fila, cliques, problemas = set(), deque([()]), 0, []
while fila:
    caminho_de_cliques = fila.popleft()
    at = abrir()
    botao(at, "bv_fechar_apoio").click().run()
    for rotulo in caminho_de_cliques:
        b = next(b for b in botoes_lia(at) if b.label == rotulo)
        b.click().run()
        cliques += 1
    if erros(at):
        problemas.append(f"erro em {caminho_de_cliques}: {erros(at)[:1]}")
        continue
    destino = at.session_state["ap_lia"]["atual"].destino or {}
    if caminho_de_cliques and destino.get("aba") != at.session_state["ap_aba"]:
        problemas.append(f"lâmina errada em {caminho_de_cliques}")
    for b in botoes_lia(at):
        if b.label not in vistos:
            vistos.add(b.label)
            fila.append(caminho_de_cliques + (b.label,))
checar(f"B. Lia: {len(vistos)} botões diferentes, {cliques} cliques, sem erro", not problemas)
for p in problemas[:10]:
    print("   ", p)
titulos = {i["titulo"] for i in apoio.ITENS}
checar("B. todo item do catálogo tem botão na Lia", titulos <= vistos)

# ---------- C. voltar e começar de novo ----------
at = abrir()
botao(at, "bv_fechar_apoio").click().run()
next(b for b in botoes_lia(at) if b.label == "Câncer de mama").click().run()
fala_mama = at.session_state["ap_lia"]["atual"].fala
next(b for b in botoes_lia(at) if b.label.startswith("Próximo passo")).click().run()
checar("C. próximo passo de Câncer de mama leva a Diagnóstico", at.session_state["ap_caminho"] == "diagnostico")
botao(at, "lia_discreto_voltar_ap").click().run()
checar("C. voltar devolve a fala anterior", at.session_state["ap_lia"]["atual"].fala == fala_mama
       and at.session_state["ap_caminho"] == "mama")
at2 = abrir()
botao(at2, "bv_ap_ajuda").click().run()
next(b for b in botoes_lia(at2) if b.label == "Meu exame deu alteração").click().run()
checar("C. Preciso de ajuda → 'Meu exame deu alteração' leva a Diagnóstico",
       not erros(at2) and at2.session_state["ap_etapa"] == "alterado"
       and any(b.label == "Porta Diagnóstico" for b in botoes_lia(at2)))
botao(at, "lia_discreto_inicio_ap").click().run()
checar("C. começar de novo volta à saudação", apoio.CIDADE in at.session_state["ap_lia"]["atual"].fala
       and not erros(at))

# ---------- D. lâminas e caminhos ----------
at = abrir()
botao(at, "bv_fechar_apoio").click().run()
for nome in apoio.LAMINAS.values():
    at.session_state["ap_aba"] = nome
    at.run()
    checar(f"D. lâmina {nome} abre sem erro", not erros(at))
at.session_state["ap_aba"] = apoio.LAMINAS["caminho"]
for c in apoio.NOME_CAMINHO:
    if c == "ajuda":
        continue
    at.session_state["ap_caminho"] = c
    at.run()
    texto = " ".join(m.value for m in at.markdown)
    esperados = [i["titulo"] for i in apoio.itens(caminho=c, lamina="caminho")]
    checar(f"D. porta {c} mostra seus {len(esperados)} cartões",
           not erros(at) and all(_html_esc(t) in texto for t in esperados))
at.session_state["ap_caminho"] = "rede"
at.run()
checar("D. porta Rede oncológica desenha o caminho em 6 passos",
       not erros(at) and sum('class="apoio-fluxo"' in m.value for m in at.markdown) == len(apoio.FLUXO_REDE))
at.session_state["ap_caminho"] = "ajuda"
for e in apoio.NOME_ETAPA:
    at.session_state["ap_etapa"] = e
    at.run()
    texto = " ".join(m.value for m in at.markdown)
    esperados = [i["titulo"] for i in apoio.itens_da_etapa(e)]
    checar(f"D. Preciso de ajuda, '{apoio.NOME_ETAPA[e]}': {len(esperados)} cartões",
           not erros(at) and all(_html_esc(t) in texto for t in esperados))

import html as _html
for lam in apoio.GRUPOS:
    at.session_state["ap_aba"] = apoio.LAMINAS[lam]
    for g in apoio.GRUPOS[lam]:
        at.session_state[f"ap_grupo_{lam}"] = g
        at.run()
        texto = " ".join(m.value for m in at.markdown)
        casa, visitas = apoio.do_grupo(lam, g)
        checar(f"D. {apoio.LAMINAS[lam]}, {g}: {len(casa)} + {len(visitas)} cartões, só os dele",
               not erros(at) and all(_html.escape(i["titulo"]) in texto for i in casa + visitas)
               and not any(_html.escape(i["titulo"]) in texto for i in apoio.itens(lamina=lam) if i["grupo"] != g
                           and (lam, g) not in i["tambem"]))
checar("D. cartões com o botão Abrir a página oficial", "apoio-botao" in texto)
at.session_state["ap_aba"] = apoio.LAMINAS["carretas"]
at.run()
texto = " ".join(m.value for m in at.markdown)
checar("D. lâmina Carretas mostra onde a carreta está agora",
       not erros(at) and "Onde a carreta da mamografia está agora?" in texto
       and ("carreta-grade" in texto or "escudo-alerta" in texto))

# ---------- E. botão Início (volta ao painel, na aba Panorama) ----------
at = abrir()
checar("E. botão Início no topo e na lateral",
       botao(at, "inicio_topo") is not None and any(b.key == "inicio_lateral" for b in at.sidebar.button))
at.session_state["aba"] = "Evolução"  # o painel tinha ficado noutra aba
botao(at, "inicio_topo").click().run()
checar("E. Início marca o Panorama no painel", not erros(at) and at.session_state["aba"] == "Panorama")

print(f"\n({time.time() - inicio:.0f} s)")
print("Todas as checagens da lâmina de apoio passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
