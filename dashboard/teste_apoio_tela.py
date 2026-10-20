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
checar("A. boas-vindas separa prevenção, exame alterado, diagnóstico e outras situações",
       all(botao(at, f"bv_ap_{c}") is not None
           for c in ("prevencao", "alterado", "diagnostico", "ajuda")))
_txt_abertura = " ".join(m.value for m in at.markdown)
checar("A. emergência (190, 180, 192) à vista na primeira tela, fora de qualquer menu",
       "apoio-emergencia" in _txt_abertura and all(n in _txt_abertura for n in ("190", "180", "192")))
checar("A. antes de escolher a situação não abre cartões de nenhum câncer (nada de mama por padrão)",
       'class="escudo-cartao' not in _txt_abertura and botao(at, "ir_carretas_mama") is None)
checar("A. faixa 'Você está em' mostra onde a mulher está", "Você está em" in _txt_abertura)
checar("A. contadores internos não ocupam a entrada de quem procura atendimento",
       not any(m.label in ("Caminhos de orientação", "Informações cadastradas", "Pedem confirmação")
               for m in at.metric))
checar("A. mesma Lia na lateral (rosto + nome)",
       any("lia-nome" in m.value for m in at.sidebar.markdown) and any("lia-rosto" in m.value for m in at.sidebar.markdown))
for entrada, caminho, etapa in (("prevencao", "ajuda", "nao_fiz"), ("alterado", "ajuda", "alterado"),
                                ("diagnostico", "ajuda", "diagnostico_cancer"), ("ajuda", "ajuda", None)):
    at = abrir()
    botao(at, f"bv_ap_{entrada}").click().run()
    checar(f"A. entrada {entrada} do centro", not erros(at)
           and at.session_state["ap_caminho"] == caminho
           and at.session_state["ap_etapa"] == etapa
           and at.session_state["ap_aba"] == apoio.LAMINAS["caminho"]
           and botao(at, f"bv_ap_{entrada}") is None)
checar("A. 'Não sei' deixa as seis etapas sem nenhuma presumida", at.session_state["ap_etapa"] is None)

at = abrir()
botao(at, "nav_apoio_sobre").click().run()
checar("A. os contadores e informações de confirmação continuam disponíveis em 'Sobre estas informações'",
       not erros(at) and {m.label for m in at.metric} ==
       {"Caminhos de orientação", "Informações cadastradas", "Pedem confirmação"})

at = abrir()
botao(at, "bv_ap_diagnostico").click().run()
conteudo = " ".join(str(x.value) for x in at.markdown)
checar("A. diagnóstico confirmado abre diagrama com a etapa atual e a regulação", not erros(at)
       and all(t in conteudo for t in ("Diagnóstico confirmado", "Você está aqui", "Regulação do SUS",
                                      "Como acompanho a vaga?")))
checar("A. jornada do diagnóstico exibe quatro etapas numeradas e conectores visíveis",
       all(f'class="apoio-jornada-numero" aria-hidden="true">{n}' in conteudo for n in (1, 2, 3, 4))
       and conteudo.count('class="apoio-jornada-conector" aria-hidden="true">↓') == 3)
checar("A. a segunda etapa é marcada como próximo passo",
       "<strong>Próximo passo:</strong>" in conteudo)
ids_retomada = ["nao_achei_nome", "lista_regulacao", "como_chegar_cross"]
if apoio.CIDADE.casefold() == "rio claro":
    ids_retomada.append("rc_unidades")
checar("A. bloco de retomada contém os cartões do catálogo e seus links oficiais",
       "Se a resposta demorar ou o encaminhamento não chegar" in conteudo
       and all(apoio.POR_ID[i]["titulo"] in conteudo and apoio.POR_ID[i]["link"] in conteudo
               for i in ids_retomada))

# ---------- A2. Trocar a aba não substitui a fala da Lia ----------
at = abrir()
botao(at, "bv_ap_diagnostico").click().run()
fala_diagnostico = at.session_state["ap_lia"]["atual"].fala
botao(at, "nav_apoio_carretas").click().run()
aviso_contexto = any("Esta resposta é sobre" in str(i.value)
                     and "Você está em Carretas" in str(i.value) for i in at.info)
checar("A2. trocar para Carretas preserva a fala de diagnóstico e informa a diferença de contexto",
       not erros(at) and at.session_state["ap_lia"]["atual"].fala == fala_diagnostico and aviso_contexto)
checar("A2. a nova fala só é solicitada por um botão explícito",
       botao(at, "lia_falar_sobre_aba") is not None
       and botao(at, "lia_falar_sobre_aba").label == "Falar sobre Carretas")
botao(at, "lia_falar_sobre_aba").click().run()
checar("A2. após pedir, Lia responde sobre Carretas e o aviso desaparece",
       not erros(at) and at.session_state["ap_lia"]["atual"].destino.get("aba") == apoio.LAMINAS["carretas"]
       and not any("Esta resposta é sobre" in str(i.value) for i in at.info)
       and botao(at, "lia_falar_sobre_aba") is None)

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
checar("C. sem saber o ponto: a tela não assume que a mulher ainda não fez exame",
       not erros(at2) and at2.session_state["ap_etapa"] is None
       and "Escolha uma situação acima" in " ".join(str(x.value) for x in at2.info))
next(b for b in botoes_lia(at2) if b.label == "Meu exame deu alterado").click().run()
checar("C. Preciso de ajuda → 'Meu exame deu alterado' leva primeiro à unidade de saúde do bairro (não à lei)",
       not erros(at2) and at2.session_state["ap_etapa"] == "alterado"
       and any("USF" in b.label and "UBS" in b.label for b in botoes_lia(at2))
       and not any("30 dias" in b.label for b in botoes_lia(at2)))
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
    if lam == "carretas":
        continue  # a lâmina Carretas não tem mais cartões por grupo: mostra o quadro com os links oficiais (conferido no bloco D acima)
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
# a porta para o mapa de hospitais habilitados mora na área "Hospitais no Estado" (e só nela); os cartões continuam os mesmos
at.session_state["ap_aba"] = apoio.LAMINAS["hospitais"]
at.run()
tudo = " ".join(m.value for m in at.markdown) + " " + " ".join(str(l.label) for l in getattr(at, "page_link", []) if hasattr(l, "label"))
checar("D. a área Hospitais no Estado tem a porta para o mapa de hospitais habilitados", not erros(at) and "hospitais_cancer" in tudo)
at.session_state["ap_aba"] = apoio.LAMINAS["rio_claro"]
at.run()
checar("D. a porta do mapa NÃO aparece nas outras áreas (uma casa só)", "hospitais_cancer" not in " ".join(m.value for m in at.markdown))
at.session_state["ap_aba"] = apoio.LAMINAS["carretas"]
at.run()
texto = " ".join(m.value for m in at.markdown)
checar("D. lâmina Carretas direciona aos itinerários oficiais e preserva as orientações essenciais",
       not erros(at) and "Consulte o itinerário atualizado das carretas" in texto
       and apoio.URL_CARRETAS_SP_POR_TODAS in texto
       and apoio.URL_CARRETAS_POUPATEMPO in texto
       and "O que levar" in texto and "senhas limitadas" in texto
       and "Araçoiaba da Serra" not in texto)
at.session_state["ap_aba"] = apoio.LAMINAS["rio_claro"]
at.run()
texto = " ".join(m.value for m in at.markdown)
checar("D. Rio Claro omite a ação passada e direciona ao itinerário oficial atual",
       not erros(at) and "Ação passada do Hospital de Amor" not in texto
       and "cidades e datas das Carretas da Mamografia do Estado" in texto
       and apoio.URL_CARRETAS_SP_POR_TODAS in texto
       and apoio.URL_CARRETAS_POUPATEMPO in texto)

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
           and "não guarda as perguntas" in lateral(at))
    checar("F. sem Gemini configurado a busca usa apenas o catálogo", "indisponível nesta sessão" in lateral(at)
           and "catálogo conferido" in lateral(at)
           and not any(t.key == "caixa_ap_gemini_ativo" for t in at.toggle))

    perguntar_no_apoio(at, "como funciona a carreta da mamografia?")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. pergunta escrita: a Lia mostra o item do guia (carretas), com a pergunta, o selo 'nenhuma IA' e o painel na lâmina certa",
           not erros(at) and atual.tipo in ("itens", "palpites") and "carretas_estado" in atual.candidatos
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

    # cobertura por tipo de câncer (10/2026): quem pergunta de outro câncer não recebe mamografia
    perguntar_no_apoio(at, "Tenho câncer no intestino. Onde procuro ajuda?")
    atual = at.session_state["ap_lia"]["atual"]
    rotulos = " ".join(b.label for b in botoes_lia(at)).lower()
    # "onde procuro ajuda?" pede o CAMINHO: abre a jornada do exame de intestino (18/10/2026); a pergunta geral abre o cartão do câncer
    checar("F. câncer de intestino: a Lia abre o conteúdo do intestino, a página vai para Outros cânceres e nada de mamografia",
           not erros(at) and {"cancer_intestino", "jornada_exame_intestino"} & set(atual.candidatos)
           and at.session_state["ap_caminho"] == "outros"
           and ("Rastreamento ou sintomas?" in lateral(at) or "Sinais que merecem avaliação" in lateral(at))
           and "mamogra" not in rotulos and atual.tipo_cancer == "colorretal")
    perguntar_no_apoio(at, "e os sinais?")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. 'e os sinais?' segue o câncer em foco (só memória da sessão)",
           not erros(at) and "Continuando sobre o câncer de intestino" in atual.fala and atual.tipo_cancer == "colorretal")
    perguntar_no_apoio(at, "e o de pulmão?")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. mudou de assunto: 'e o de pulmão?' abre o pulmão e deixa o intestino",
           not erros(at) and "cancer_pulmao" in atual.candidatos and atual.tipo_cancer == "pulmao"
           and not {"cancer_intestino", "jornada_exame_intestino"} & set(atual.candidatos))
    perguntar_no_apoio(at, "Estou com uma ferida que não cicatriza.")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. ferida que não cicatriza: texto fixo de sintoma e botão para os sinais do câncer de pele, sem diagnosticar",
           not erros(at) and atual.tipo == "sintoma" and "Eu não faço diagnóstico" in atual.fala
           and any("pele" in b.label.lower() for b in botoes_lia(at)))
    perguntar_no_apoio(at, "Qual a diferença entre câncer do colo do útero e câncer do endométrio?")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. colo do útero x endométrio: a Lia mostra os dois cânceres e não escolhe um",
           not erros(at) and atual.tipo == "palpites" and len([b for b in botoes_lia(at) if b.label.startswith("Ver ")]) == 2)

    # "o que você sabe responder?" (autor, 18/10/2026): a Lia explica o que o guia cobre, em texto fixo
    checar("F. a caixa avisa, sem mexer no resto, a pergunta que mostra o que a Lia sabe", "o que você sabe responder?" in lateral(at))
    perguntar_no_apoio(at, "o que você sabe responder?")
    atual = at.session_state["ap_lia"]["atual"]
    checar("F. 'o que você sabe responder?': a Lia lista os assuntos, diz o que não faz e oferece as portas em botões",
           not erros(at) and atual.tipo == "sobre_a_lia" and "O que eu não faço" in lateral(at)
           and "intestino" in lateral(at) and len(botoes_lia(at)) >= len(apoio.NOME_CAMINHO)
           and "Nenhuma IA" in lateral(at))
    botoes_lia(at)[0].click().run()   # clicar numa porta continua funcionando depois dessa resposta
    checar("F. depois da explicação, clicar numa porta leva a ela, sem erro", not erros(at)
           and at.session_state["ap_lia"]["atual"].destino.get("caminho") in apoio.NOME_CAMINHO)

    # cartão com mais links (autor, 18/10/2026): o botão do INCA e as páginas de serviço aparecem no cartão da porta Outros cânceres
    at.session_state["ap_aba"] = apoio.LAMINAS["caminho"]
    at.session_state["ap_caminho"] = "outros"
    at.run()
    html_porta = " ".join(m.value for m in at.markdown)
    checar("F. porta Outros cânceres: cada cartão mostra o botão do INCA e as 4 páginas de serviço ao lado, sem erro",
           not erros(at) and html_porta.count("Abrir a página oficial") >= 7
           and html_porta.count("Unidades de saúde de Rio Claro: onde começar") >= 6
           and html_porta.count("Agendar consulta pelo Cadu") >= 6 and "saude-rioclaro.org.br/enderecos" in html_porta)

    antes = at.session_state["ap_lia"]["atual"]
    perguntar_no_apoio(at, "   ")
    checar("F. enviar vazio não faz nada e não quebra", not erros(at) and at.session_state["ap_lia"]["atual"] is antes)

    perguntar_no_apoio(at, "qual a previsão do tempo")
    checar("F. fora do assunto: diz que não achou e mostra as portas de novo", not erros(at) and at.session_state["ap_lia"]["atual"].tipo == "nada"
           and len(botoes_lia(at)) >= 8)

    botao_assunto = next((b for b in at.sidebar.button if b.key == "assunto_caminho_mama"), None)
    checar("F. assunto de prevenção oferece botão no grupo dinâmico", botao_assunto is not None)
    if botao_assunto:
        botao_assunto.click().run()
    resposta_assunto = at.session_state["ap_lia"]["atual"]
    checar("F. atalho usa pergunta-modelo e mostra resposta do guia sem IA",
           not erros(at) and at.session_state["caixa_ap_texto"] == "Quero orientação sobre câncer de mama."
           and resposta_assunto.destino.get("caminho") == "mama" and bool(resposta_assunto.botoes))

    at.button(key="lia_discreto_voltar_ap").click().run()
    checar("F. '← Voltar' continua funcionando depois de perguntas", not erros(at))

    # O Gemini (simulado) só é chamado após consentimento explícito; o texto continua sendo do guia.
    recebidos = []
    classificador_falso = {"resultado": {"intencao": "mama"}, "erro": False}
    original = apoio_busca.obter_classificador

    def classificar_falso(p, o, contexto=None, com_cancer=True):
        recebidos.append(p)
        if classificador_falso["erro"]:
            raise RuntimeError("falha simulada do classificador")
        return classificador_falso["resultado"]

    apoio_busca.obter_classificador = lambda: classificar_falso
    try:
        at = abrir()
        checar("F. Gemini configurado aparece desligado por padrão com aviso de privacidade",
               not at.session_state["caixa_ap_gemini_ativo"] and at.toggle(key="caixa_ap_gemini_ativo") is not None
               and "somente para escolher o assunto" in lateral(at)
               and "A IA não escreve a resposta" in lateral(at)
               and "Não envie nomes, telefones" in lateral(at))
        perguntar_no_apoio(at, "xyzzy plugh")
        checar("F. pergunta usa só a busca local quando Gemini está desligado", recebidos == []
               and at.session_state["ap_lia"]["atual"].origem != "gemini")
        at.toggle(key="caixa_ap_gemini_ativo").set_value(True).run()
        checar("F. ligar a opção mantém visível a informação do envio ao Google", "somente para escolher o assunto" in lateral(at))
        perguntar_no_apoio(at, "xyzzy plugh")
        atual = at.session_state["ap_lia"]["atual"]
        checar("F. com consentimento, Gemini escolhe a porta; o texto continua sendo o do guia",
               not erros(at) and atual.origem == "gemini" and recebidos == ["xyzzy plugh"] and apoio.responder(apoio.caminho("mama")).fala in atual.fala
               and "não da IA" in lateral(at) and at.session_state["caixa_ap_ia"] == 1)
        classificador_falso["resultado"] = {"intencao": "destino_inexistente"}
        perguntar_no_apoio(at, "xyzzy retorno inválido")
        checar("F. retorno inválido do Gemini conta como chamada", at.session_state["caixa_ap_ia"] == 2
               and at.session_state["ap_lia"]["atual"].tipo == "nada")
        classificador_falso["resultado"] = {"intencao": "nenhuma"}
        perguntar_no_apoio(at, "xyzzy nenhuma")
        checar("F. resposta nenhuma do Gemini conta como chamada", at.session_state["caixa_ap_ia"] == 3)
        classificador_falso["erro"] = True
        perguntar_no_apoio(at, "xyzzy erro")
        checar("F. erro do Gemini também conta como chamada", at.session_state["caixa_ap_ia"] == 4
               and not erros(at))
        classificador_falso["erro"] = False
        classificador_falso["resultado"] = {"intencao": "nenhuma"}
        at.session_state["caixa_ap_ia"] = 39
        perguntar_no_apoio(at, "xyzzy chamada quarenta")
        chamadas_ate_quarenta = len(recebidos)
        checar("F. 40a classificação incrementa o contador até o limite", at.session_state["caixa_ap_ia"] == 40
               and chamadas_ate_quarenta == 5)
        perguntar_no_apoio(at, "xyzzy plugh dois")
        checar("F. 41a tentativa não chama Gemini e avisa que a busca local continua",
               len(recebidos) == chamadas_ate_quarenta and at.session_state["caixa_ap_ia"] == 40
               and at.session_state["ap_lia"]["atual"].tipo == "nada"
               and any("Limite de 40 classificações" in str(i.value) for i in at.info))
    finally:
        apoio_busca.obter_classificador = original
finally:
    sqlite3.connect = sqlite_original

# ---------- G. Atalhos dinâmicos: caminhos, etapas e lâminas, sem IA ----------
assuntos_teste = [
    ("caminho", id, rotulo, f"Quero orientação sobre {rotulo.lower()}.")
    for id, rotulo, _, _ in apoio.CAMINHOS
    if id in {"mama", "colo", "outros", "diagnostico", "regulacao", "tratamento", "rede", "direitos"}
]
assuntos_teste += [
    ("etapa", id, rotulo, f"Minha situação é: {rotulo.lower()}.")
    for id, rotulo, _, _, _ in apoio.ETAPAS
    if id in {"nao_fiz", "alterado", "diagnostico_cancer", "encaminhada", "em_tratamento", "violencia"}
]
assuntos_teste += [
    ("lamina", id, apoio.LAMINAS[id], f"Quero consultar {apoio.LAMINAS[id].lower()}.")
    for id in ("hospitais", "rio_claro", "barretos", "carretas")
]

chamadas_assuntos = []
original_classificador_assuntos = apoio_busca.obter_classificador
apoio_busca.obter_classificador = lambda: (lambda *a, **k: chamadas_assuntos.append(a[0]) or {"intencao": "mama"})
try:
    at = abrir()
    at.toggle(key="caixa_ap_gemini_ativo").set_value(True).run()
    for tipo, id, rotulo, pergunta_modelo in assuntos_teste:
        botao_assunto = next((b for b in at.sidebar.button if b.key == f"assunto_{tipo}_{id}"), None)
        if botao_assunto:
            botao_assunto.click().run()
        resposta = at.session_state["ap_lia"]["atual"]
        destino = resposta.destino or {}
        if tipo == "caminho":
            destino_valido = destino.get("aba") == apoio.LAMINAS["caminho"] and destino.get("caminho") == id
        elif tipo == "etapa":
            destino_valido = destino.get("aba") == apoio.LAMINAS["caminho"] and destino.get("etapa") == id
        else:
            destino_valido = destino.get("aba") == apoio.LAMINAS[id]
        checar(f"G. assunto {rotulo} responde com destino válido, botões e pergunta-modelo", botao_assunto is not None
               and not erros(at) and destino_valido and bool(resposta.botoes)
               and at.session_state["caixa_ap_texto"] == pergunta_modelo
               and getattr(resposta, "pergunta", None) == pergunta_modelo)
    botao_urgencia = next((b for b in at.sidebar.button if b.key == "assunto_urgencia_agora"), None)
    if botao_urgencia:
        botao_urgencia.click().run()
    resposta_urgencia = at.session_state["ap_lia"]["atual"]
    checar("G. perigo imediato usa orientação fixa 190/180 sem chamar Gemini", botao_urgencia is not None
           and not erros(at) and "190" in resposta_urgencia.fala and "180" in resposta_urgencia.fala
           and chamadas_assuntos == [])
finally:
    apoio_busca.obter_classificador = original_classificador_assuntos

checar("F. a página do Apoio não abriu banco de dados em nenhum momento (perguntas não são gravadas)", abriu_banco == [])

print(f"\n({time.time() - inicio:.0f} s)")
print("Todas as checagens da lâmina de apoio passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
