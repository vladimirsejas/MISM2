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

# ---------- F. Pergunte à Lia no Apoio (caixa de texto na lateral) ----------
import sqlite3  # noqa: E402
import apoio_busca  # noqa: E402


def perguntar_no_apoio(at, texto):
    at.text_input(key="caixa_ap_texto").set_value(texto)
    botao(at, "caixa_ap_enviar").click().run()


def lateral(at):
    return " ".join(str(c.value) for c in at.sidebar.caption) + " " + " ".join(str(m.value) for m in at.sidebar.markdown)


abriu_banco = []
sqlite_original = sqlite3.connect
sqlite3.connect = lambda *a, **k: (abriu_banco.append(a), sqlite_original(*a, **k))[1]
try:
    at = abrir()
    at.button(key="bv_ap_ajuda").click().run() if botao(at, "bv_ap_ajuda") is not None else None
    checar("F. a caixa 'Pergunte à Lia' está na lateral do Apoio, junto da Lia, e avisa que as perguntas não são guardadas",
           not erros(at) and at.text_input(key="caixa_ap_texto") is not None and "Pergunte à Lia" in lateral(at)
           and "não são guardadas" in lateral(at))
    checar("F. sem chave do Gemini a caixa diz que a IA está desligada e que o texto é do guia", "desligada" in lateral(at))

    perguntar_no_apoio(at, "como funciona a carreta da mamografia?")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. pergunta escrita: a Lia mostra o item do guia (carretas), com a pergunta, o selo 'nenhuma IA' e o painel na lâmina certa",
           not erros(at) and atual.tipo in ("itens", "palpites") and ("carretas_estado" in atual.candidatos or "rc_carreta_hospital_de_amor" in atual.candidatos)
           and "Você perguntou" in lateral(at) and "Nenhuma IA escreveu" in lateral(at))
    if atual.tipo == "palpites":
        botoes = botoes_lia(at)
        botoes[0].click().run()
        atual = at.session_state["ap_lia"]["atual"]
    checar("F. o cartão do item aparece com o aviso de conferência e o botão da página oficial",
           not erros(at) and apoio.AVISO in lateral(at) + " ".join(str(m.value) for m in at.markdown) and "Abrir a página oficial" in lateral(at))

    perguntar_no_apoio(at, "meu marido me bate")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. segurança: 190 e 180, o canal Ligue 180 em botão, e a página vai para 'Preciso de ajuda'",
           not erros(at) and atual.tipo == "risco" and "190" in atual.fala and "180" in atual.fala
           and any("Ligue 180" in b.label for b in botoes_lia(at)) and at.session_state["ap_caminho"] == "ajuda")

    perguntar_no_apoio(at, "senti um caroço no peito")
    checar("F. sintoma pessoal: texto fixo sem diagnóstico", "Eu não faço diagnóstico" in at.session_state["ap_lia"]["atual"].fala)

    antes = at.session_state["ap_lia"]["atual"]
    perguntar_no_apoio(at, "   ")
    checar("F. enviar vazio não faz nada e não quebra", not erros(at) and at.session_state["ap_lia"]["atual"] is antes)

    perguntar_no_apoio(at, "qual a previsão do tempo")
    checar("F. fora do assunto: diz que não achou e mostra as portas de novo", not erros(at) and at.session_state["ap_lia"]["atual"].tipo == "nada"
           and len(botoes_lia(at)) >= 8)

    at.button(key="caixa_ap_exemplo_0").click().run()
    checar("F. botão de exemplo ('Onde faço mamografia pelo SUS?') responde sem digitar",
           not erros(at) and at.session_state["ap_lia"]["atual"].tipo in ("itens", "palpites"))

    at.button(key="lia_discreto_voltar_ap").click().run()
    checar("F. '← Voltar' continua funcionando depois de perguntas", not erros(at))

    # com o Gemini (simulado): só ajuda a entender; o texto continua sendo do guia
    recebidos = []
    original = apoio_busca.obter_classificador
    apoio_busca.obter_classificador = lambda: (lambda p, o, contexto=None, com_cancer=True: recebidos.append(p) or {"intencao": "mama"})
    try:
        at = abrir()
        checar("F. com o Gemini ligado a caixa diz que a IA ajuda a entender", "ajuda a entender" in lateral(at))
        perguntar_no_apoio(at, "xyzzy plugh")
        atual = at.session_state["ap_lia"]["atual"]
        checar("F. Gemini escolheu a porta: o texto é o do guia e o selo diz que não é da IA",
               not erros(at) and atual.origem == "gemini" and recebidos == ["xyzzy plugh"] and apoio.responder(apoio.caminho("mama")).fala in atual.fala
               and "não da IA" in lateral(at))
        at.session_state["caixa_ap_ia"] = 40
        perguntar_no_apoio(at, "xyzzy plugh dois")
        checar("F. passou do limite de perguntas com IA na sessão: segue só com a busca", recebidos == ["xyzzy plugh"]
               and at.session_state["ap_lia"]["atual"].tipo == "nada")
    finally:
        apoio_busca.obter_classificador = original
finally:
    sqlite3.connect = sqlite_original
checar("F. a página do Apoio não abriu banco de dados em nenhum momento (perguntas não são gravadas)", abriu_banco == [])

print(f"\n({time.time() - inicio:.0f} s)")
print("Todas as checagens da lâmina de apoio passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
