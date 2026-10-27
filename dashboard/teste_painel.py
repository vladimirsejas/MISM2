import json
import os
import sys
import time
from collections import deque

import pandas as pd
import streamlit

# =====================================
# TESTE DE ACEITAÇÃO DO PAINEL (combinado com o autor, 09/2026)
#
# Abre o painel DE VERDADE (dashboard/app.py, via Streamlit AppTest)
# e clica, como a pessoa clicaria:
#   A. boas-vindas -> "Prefiro explorar sozinha" -> cada caminho da
#      Lia -> cada câncer -> cada ação -> próximos passos ... até não
#      sobrar botão novo. Em cada clique: a tela não quebra, a Lia
#      responde, e o painel vai para a aba e o câncer da resposta.
#   B. "← Voltar" devolve a fala anterior; "Começar de novo" volta ao
#      início.
#   C. Passeio pelo Escudo: as 6 paradas, anterior, terminar.
#   D. As 5 abas abrem com todas as camadas ligadas.
# Usa a base pública do repositório (analises/base_preditiva_2013_
# 2025.csv) com os meses que o DATASUS oferece (docs/FONTE_DOS_DADOS.md)
# -- não precisa do banco.
#
# Uso (da pasta do projeto):  py dashboard\teste_painel.py
# Leva alguns minutos (são centenas de cliques).
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "dashboard"))

# O app abre uma conexão com o banco mesmo aqui (os dados vêm do CSV); sem banco\ a pasta
# pode não existir (CI, máquina nova) e o sqlite3 não cria pasta.
os.makedirs(os.path.join(RAIZ, "banco"), exist_ok=True)

import configuracao_geografica  # noqa: E402
import conversa  # noqa: E402
import inteligencia  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

MESES_NA_FONTE = {2013: 10, 2014: 10, 2015: 8, 2016: 9, 2017: 11, 2018: 6, 2019: 7, 2020: 8,
                  2021: 11, 2022: 10, 2023: 11, 2024: 8, 2025: 12}
CODIGOS = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL", "Ovário": "OVARIO",
           "Pele não melanoma": "PELE_NAO_MELANOMA", "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def preparar_dados():
    """O painel lê do banco; aqui ele lê a base pública (sem banco)."""
    real = pd.read_csv(os.path.join(RAIZ, "analises", "base_preditiva_2013_2025.csv"), sep=";")
    real["tipo_cancer"] = real["cancer"].map(CODIGOS)
    real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
    real["dias_permanencia"] = real["dias_internacao_total"]
    serie = inteligencia.ajustar_meses(
        inteligencia.completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                                          "valor_total", "dias_permanencia"]]), MESES_NA_FONTE)
    faixas = pd.DataFrame([(c, a, f, 5 + a % 3) for c in CODIGOS.values() for a in range(2013, 2026)
                           for f in ("até 39 anos", "40 a 49", "50 a 69", "70 ou mais")],
                          columns=["tipo_cancer", "ano", "faixa", "internacoes"])
    configuracao_geografica.listar_municipios_disponiveis = lambda: [
        {"origem": "RIO_CLARO", "nome": "Rio Claro", "codigo_ibge": 3543907, "uf": "SP"}]
    configuracao_geografica.obter_municipio = lambda: "RIO_CLARO"
    inteligencia.carregar_serie = lambda conn, o, uf="SP": serie.copy()
    inteligencia.carregar_faixas = lambda conn, o, uf="SP": faixas.copy()
    inteligencia.canceres_com_duplicidade = lambda conn, o: []
    conversa.registrar_pergunta = lambda *a: None


def fluxo_falso():
    """Fluxo de mulheres de outros estados (MG, GO e PA) atendidas em Barretos e São Paulo."""
    linhas = [(c, ano, uf, hosp, "2090236", n, 0, 3 * n)
              for c in CODIGOS.values() for ano in range(2013, 2026)
              for uf, hosp, n in (("MG", "350550", 6), ("GO", "350550", 3), ("PA", "355030", 1))]
    fora = pd.DataFrame(linhas, columns=["tipo_cancer", "ano", "uf_residencia", "municipio_hospital", "cnes",
                                         "internacoes", "obitos", "dias_permanencia"])
    total = pd.DataFrame([(c, ano, 100, 300) for c in CODIGOS.values() for ano in range(2013, 2026)],
                         columns=["tipo_cancer", "ano", "internacoes", "dias_permanencia"])
    return {"fora": fora, "total": total, "nomes": {"350550": "Barretos", "355030": "São Paulo"},
            "meses": MESES_NA_FONTE}


def abrir():
    at = AppTest.from_file(os.path.join(RAIZ, "dashboard", "app.py"), default_timeout=120)
    at.run()
    return at


def erros(at):
    return [str(e.value) for e in at.exception]


def botoes_da_lia(at):
    """Próximos passos no balão da Lia (sem Voltar/Começar de novo)."""
    return [b for b in at.main.button if (b.key or "").startswith("lia_") and "discreto" not in (b.key or "")]


def clicar(at, rotulo):
    alvo = [b for b in botoes_da_lia(at) if b.label == rotulo]
    if not alvo:
        return False
    alvo[0].click().run()
    return True


def ir_ao_inicio(at):
    at.button(key="lia_discreto_inicio").click().run()


def main():
    preparar_dados()
    inicio = time.time()
    at = abrir()
    checar("abre sem erro", not erros(at))
    at.button(key="bv_fechar").click().run()
    checar("'Prefiro explorar sozinha' fecha as boas-vindas e mostra os caminhos", len(botoes_da_lia(at)) >= 6)

    # ---- A. a árvore inteira, clicando ----
    vistos, fila, problemas, cliques = set(), deque([()]), [], 0
    while fila:
        caminho = fila.popleft()
        ir_ao_inicio(at)
        chegou = all(clicar(at, rotulo) for rotulo in caminho)
        cliques += len(caminho) + 1
        if not chegou:
            problemas.append(f"{' > '.join(caminho)}: botão sumiu no caminho")
            continue
        atual = at.session_state["lia"]["atual"]
        if caminho:
            destino = atual.destino or {}
            if erros(at):
                problemas.append(f"{' > '.join(caminho)}: erro {erros(at)[0][:120]}")
            if not atual.fala.strip():
                problemas.append(f"{' > '.join(caminho)}: Lia sem fala")
            if destino.get("aba") and at.session_state["aba"] != destino["aba"]:
                problemas.append(f"{' > '.join(caminho)}: painel em {at.session_state['aba']}, esperado {destino['aba']}")
            if destino.get("cancer") and at.session_state["doenca"] != destino["cancer"]:
                problemas.append(f"{' > '.join(caminho)}: câncer {at.session_state['doenca']}, esperado {destino['cancer']}")
        for b in botoes_da_lia(at):
            chave = (atual.fala[:80], b.label)
            if chave not in vistos and len(caminho) < 4:
                vistos.add(chave)
                fila.append(caminho + (b.label,))
    checar(f"A. árvore inteira clicada ({len(vistos)} botões, {cliques} cliques): "
           + ("sem problemas" if not problemas else "; ".join(problemas[:5])), not problemas)
    ja_clicados = {rotulo for _, rotulo in vistos}
    for nome in CODIGOS:
        checar(f"A. o câncer '{nome}' foi alcançado pelos botões", nome in ja_clicados)

    # ---- A2. TODO câncer x TODA ação, pelo caminho de cliques mais curto ----
    # (a árvore é funda: alguns pares só aparecem com 5-6 cliques)
    from lia import ACOES_CANCER, INICIO, Contexto, responder
    ctx = Contexto(serie=inteligencia.carregar_serie(None, "RIO_CLARO"), cidade="Rio Claro",
                   faixas=inteligencia.carregar_faixas(None, "RIO_CLARO"))
    rotas, vistos_a2, fila_a2 = {}, set(), deque([(INICIO, ())])
    while fila_a2:
        acao, rota = fila_a2.popleft()
        if acao.get("tipo") == "cancer" and acao.get("acao") != "menu":
            rotas.setdefault((acao["cancer"], acao["acao"]), rota)
        for rotulo, proxima in responder(ctx, acao).botoes:
            chave = str(sorted(proxima.items()))
            if proxima.get("tipo") != "inicio" and chave not in vistos_a2:
                vistos_a2.add(chave)
                fila_a2.append((proxima, rota + (rotulo,)))
    esperados = {(c, a) for c in CODIGOS.values() for _, a in ACOES_CANCER}
    checar(f"A2. todos os {len(esperados)} pares câncer x ação têm caminho de cliques",
           esperados <= set(rotas))
    problemas_a2 = []
    for (cancer, acao), rota in sorted(rotas.items()):
        ir_ao_inicio(at)
        if not all(clicar(at, rotulo) for rotulo in rota):
            problemas_a2.append(f"{cancer}/{acao}: botão sumiu")
            continue
        atual = at.session_state["lia"]["atual"]
        destino = atual.destino or {}
        if erros(at) or not atual.fala.strip() or at.session_state["doenca"] != cancer \
                or (destino.get("aba") and at.session_state["aba"] != destino["aba"]):
            problemas_a2.append(f"{cancer}/{acao} ({' > '.join(rota)})")
    checar(f"A2. os {len(rotas)} pares câncer x ação clicados no painel: "
           + ("sem problemas" if not problemas_a2 else "; ".join(problemas_a2[:5])), not problemas_a2)

    # ---- B. voltar e começar de novo ----
    ir_ao_inicio(at)
    clicar(at, "O que mais aparece?")
    fala_antes = at.session_state["lia"]["atual"].fala
    clicar(at, botoes_da_lia(at)[0].label)
    at.button(key="lia_discreto_voltar").click().run()
    checar("B. '← Voltar' devolve a fala anterior", at.session_state["lia"]["atual"].fala == fala_antes)
    ir_ao_inicio(at)
    checar("B. 'Começar de novo' volta à saudação", "Olá" in at.session_state["lia"]["atual"].fala)

    # ---- C. passeio ----
    from passeio import PARADAS
    at.button(key="pbtn_seguir_comecar").click().run()
    abas = []
    for i in range(len(PARADAS)):
        abas.append(at.session_state["aba"])
        checar(f"C. passeio, parada {i + 1}: sem erro", not erros(at) and at.session_state["passeio"] == i)
        if i < len(PARADAS) - 1:
            at.button(key="pbtn_seguir").click().run()
    checar(f"C. passeio leva o painel por {abas}", abas == ["Panorama", "Evolução", "Rede hospitalar", "Evolução",
                                                           "Planejamento", "Método"])
    at.button(key="pbtn_anterior").click().run()
    checar("C. passeio: '← anterior' volta uma parada", at.session_state["passeio"] == len(PARADAS) - 2)
    at.button(key="pbtn_sair").click().run()
    checar("C. passeio: 'sair' fecha e a Lia continua lá", at.session_state.get("passeio") is None
           and at.session_state["lia"]["atual"].fala.strip())

    # ---- D. as 5 abas, com as camadas ligadas ----
    for aba in ["Panorama", "Evolução", "Rede hospitalar", "Investigar", "Planejamento", "Método"]:
        at.session_state["aba"] = aba
        for camada in ("ver_estado", "ver_fora", "ver_projecao"):
            at.session_state[camada] = True
        at.run()
        checar(f"D. aba {aba} abre sem erro", not erros(at))

    # ---- D2. botão Início: de qualquer aba volta ao Panorama ----
    for aba in ["Evolução", "Rede hospitalar", "Investigar", "Planejamento", "Método"]:
        at.session_state["aba"] = aba
        at.run()
        at.button(key="inicio_painel").click().run()
        checar(f"D2. 'Início' na aba {aba} volta ao Panorama",
               not erros(at) and at.session_state["aba"] == "Panorama")

    # ---- E. banco atualizado com o painel aberto: o cache não pode segurar os dados velhos ----
    at = abrir()
    antes = list(next(r for r in at.radio if r.label == "Câncer em foco").options)
    serie_original = inteligencia.carregar_serie
    so_mama = serie_original(None, "RIO_CLARO")
    so_mama = so_mama[so_mama["tipo_cancer"] == "MAMA"]
    inteligencia.carregar_serie = lambda conn, o, uf="SP": so_mama.copy()
    try:
        at.run()  # banco não mudou: continua o cache (os 7)
        igual = list(next(r for r in at.radio if r.label == "Câncer em foco").options) == antes
        banco_app = configuracao_geografica.BANCO  # o banco que o painel de fato abre (o do Parquet ou o legado)
        if os.path.exists(banco_app):
            os.utime(banco_app, (time.time() + 60, time.time() + 60))  # "nova carga"
        at.run()
        depois = list(next(r for r in at.radio if r.label == "Câncer em foco").options)
        checar("E. banco sem mudança: o cache continua valendo", igual and len(antes) == 7)
        checar("E. banco mudou: o painel lê de novo, sem reiniciar", not erros(at) and depois == ["Mama"])
    finally:
        inteligencia.carregar_serie = serie_original

    # ---- F. fluxo de mulheres de outros estados (aba Rede hospitalar) ----
    # Sem dados de fluxo (banco só com a carga antiga) a seção avisa e não quebra: é o que as abas
    # do cenário D já mostraram, com o banco vazio. Aqui, com dados de fluxo:
    fluxo_original, cidade_original = inteligencia.carregar_fluxo, inteligencia.fluxo_da_cidade
    inteligencia.carregar_fluxo = lambda conn, uf="SP": fluxo_falso()
    inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": {
        "atendimentos": 142, "da_cidade": 140, "outras_cidades": 0, "outros_estados": 2, "moradoras": 150,
        "moradoras_na_cidade": 140, "moradoras_fora": 10, "destinos": [("Campinas", 10)]}
    try:
        at = abrir()
        at.session_state["aba"] = "Rede hospitalar"
        at.run()
        textos = " ".join(str(m.value) for m in at.markdown)
        rotulos = {m.label: m.value for m in at.metric}
        checar("F. fluxo: a aba Rede hospitalar abre sem erro", not erros(at))
        checar("F. fluxo: perguntas do fluxo e da cidade aparecem",
               "De onde vêm as mulheres de outros estados atendidas em São Paulo?" in textos
               and "Quem é atendida nos hospitais de Rio Claro" in textos)
        checar("F. fluxo: números (3 estados de origem; 2 de outros estados em Rio Claro)",
               rotulos.get("Estados de origem") == "3"
               and "Internações de fora de SP" in rotulos)
        checar("F. fluxo da cidade: escolhe-se o que ver; a 1ª visão são as moradoras atendidas fora",
               "O que você quer ver?" in [r.label for r in at.radio]
               and rotulos.get("Internações de moradoras") == "150" and rotulos.get("Na própria cidade") == "140"
               and rotulos.get("Em outras cidades de SP") == "10" and "Campinas" in " ".join(
                   str(d.value) for d in at.dataframe))
        at.session_state["fluxo_visao"] = "Mulheres de fora da cidade atendidas na cidade"
        at.run()
        rot2 = {m.label: m.value for m in at.metric}
        checar("F. fluxo da cidade: 2ª visão mostra as mulheres de fora atendidas na cidade",
               not erros(at) and rot2.get("Internações nos hospitais") == "142" and rot2.get("Moradoras de Rio Claro") == "140"
               and rot2.get("De outros estados") == "2")
        # De quais cidades vêm as mulheres de fora (22/10/2026): os números reais de Rio Claro, conferidos no banco do autor
        origens_reais = [("Santa Gertrudes", 143), ("Itirapina", 59), ("Ipeúna", 56), ("Analândia", 28), ("Corumbataí", 18),
                         ("Pirassununga", 10), ("Araras", 10), ("Leme", 5), ("Conchal", 3), ("Limeira", 2)]
        inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": {
            "atendimentos": 1842, "da_cidade": 1508, "outras_cidades": 334, "outros_estados": 0, "moradoras": 1668,
            "moradoras_na_cidade": 1508, "moradoras_fora": 160, "destinos": [("Barretos", 100)],
            "origens": [{"nome": n, "codigo6": None, "internacoes": v} for n, v in origens_reais]}
        at_o = abrir()
        at_o.session_state["aba"] = "Rede hospitalar"
        at_o.session_state["fluxo_visao"] = "Mulheres de fora da cidade atendidas na cidade"
        at_o.run()
        texto_o = " ".join(str(m.value) for m in at_o.markdown)
        graficos_o = [g for g in at_o.get("plotly_chart") if "Santa Gertrudes" in str(g.proto.spec)]
        checar("F. cidades de origem: a visão 'mulheres de fora' mostra a pergunta, o gráfico e a leitura, sem erro",
               not erros(at_o) and "De quais cidades de SP vêm as mulheres de fora?" in texto_o and len(graficos_o) == 1
               and "Santa Gertrudes (143, 42,8%)" in texto_o and "vêm de 10 cidades" in texto_o)
        spec_o = str(graficos_o[0].proto.spec) if graficos_o else ""
        checar("F. cidades de origem: as cidades menores viram uma barra só (até 3 cada), e as barras fecham em 334",
               "Outras 2 cidades" in spec_o and "3 cada)" in spec_o  # (o JSON do gráfico escapa o acento de "até") and "Conchal" not in spec_o and "Limeira" not in spec_o
               and "Itirapina" in spec_o and "residência da mulher" in texto_o
               and "As 2 cidades menores (até 3 internações cada) aparecem juntas." in texto_o and "não entram no mapa" not in texto_o
               and 143 + 59 + 56 + 28 + 18 + 10 + 10 + 5 + (3 + 2) == 334)
        checar("F. cidades de origem: a leitura descreve e não atribui causa",
               all(p not in texto_o.lower() for p in ("porque", "devido", "por causa", "em razão", "r$")))
        # Mapa das cidades vizinhas (22/10/2026): com a posição das cidades (tabela do IBGE) o mapa é o padrão e as barras
        # ficam a um clique; sem a tabela só as barras aparecem (é o caso das checagens acima).
        import localizacao as loc_mod
        posicoes_f = {"Rio Claro": (-22.373, -47.580), "Santa Gertrudes": (-22.457, -47.527), "Itirapina": (-22.253, -47.822),
                      "Ipeúna": (-22.432, -47.716), "Analândia": (-22.129, -47.662), "Corumbataí": (-22.221, -47.622),
                      "Pirassununga": (-21.996, -47.425), "Araras": (-22.357, -47.384), "Leme": (-22.181, -47.390),
                      "Conchal": (-22.336, -47.173), "Limeira": (-22.565, -47.402)}
        tabela_pos_f = pd.DataFrame({"nome": list(posicoes_f), "latitude": [v[0] for v in posicoes_f.values()],
                                     "longitude": [v[1] for v in posicoes_f.values()]})
        tabela_pos_f["chave"] = tabela_pos_f["nome"].map(loc_mod.ent.normalizar)
        loc_original = loc_mod.carregar_localizacao
        loc_mod.carregar_localizacao = lambda conn: tabela_pos_f[["nome", "chave", "latitude", "longitude"]]
        try:
            at_m = abrir()
            at_m.session_state["aba"] = "Rede hospitalar"
            at_m.session_state["fluxo_visao"] = "Mulheres de fora da cidade atendidas na cidade"
            at_m.run()
            texto_m = " ".join(str(m.value) for m in at_m.markdown)
            mapas = [g for g in at_m.get("plotly_chart") if "diamond" in str(g.proto.spec) and "Santa Gertrudes" in str(g.proto.spec)]
            spec_m = str(mapas[0].proto.spec) if mapas else ""
            checar("F. mapa das cidades: com a posição das cidades, o mapa é o padrão e há o seletor 'Ver como'",
                   not erros(at_m) and "Ver como" in [r.label for r in at_m.radio] and len(mapas) == 1
                   and at_m.session_state["fluxo_origens_forma"] == "Mapa" and "centro da cidade" in texto_m)
            checar("F. mapa das cidades: Rio Claro é o losango, as cidades com 5 ou mais aparecem e as pequenas não",
                   "Rio Claro" in spec_m and "Santa Gertrudes" in spec_m and "143" in spec_m and "Leme" in spec_m
                   and "Conchal" not in spec_m and "Limeira" not in spec_m
                   and "As 2 cidades menores (até 3 internações cada) aparecem juntas nas barras e não entram no mapa." in texto_m)
            at_m.session_state["fluxo_origens_forma"] = "Barras"
            at_m.run()
            barras = [g for g in at_m.get("plotly_chart") if "Outras 2 cidades" in str(g.proto.spec)]
            checar("F. mapa das cidades: 'Barras' troca o mapa pelas barras (uma informação, uma casa só)",
                   not erros(at_m) and len(barras) == 1
                   and not [g for g in at_m.get("plotly_chart") if "diamond" in str(g.proto.spec) and "Santa Gertrudes" in str(g.proto.spec)])
            # a cidade dos hospitais fora da tabela: sem centro não há mapa, só as barras (nunca um ponto inventado)
            tabela_sem_rc = tabela_pos_f[tabela_pos_f["nome"] != "Rio Claro"]
            loc_mod.carregar_localizacao = lambda conn: tabela_sem_rc[["nome", "chave", "latitude", "longitude"]]
            at_s = abrir()
            at_s.session_state["aba"] = "Rede hospitalar"
            at_s.session_state["fluxo_visao"] = "Mulheres de fora da cidade atendidas na cidade"
            at_s.run()
            checar("F. mapa das cidades: sem o centro da cidade na tabela, só as barras (sem seletor, sem erro)",
                   not erros(at_s) and "Ver como" not in [r.label for r in at_s.radio]
                   and len([g for g in at_s.get("plotly_chart") if "Outras 2 cidades" in str(g.proto.spec)]) == 1)
        finally:
            loc_mod.carregar_localizacao = loc_original
        # info antiga (sem a lista) e visão das moradoras: seguem abrindo, sem o gráfico novo
        inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": {
            "atendimentos": 142, "da_cidade": 140, "outras_cidades": 0, "outros_estados": 2, "moradoras": 150,
            "moradoras_na_cidade": 140, "moradoras_fora": 10, "destinos": [("Campinas", 10)]}
        at_v = abrir()
        at_v.session_state["aba"] = "Rede hospitalar"
        at_v.session_state["fluxo_visao"] = "Mulheres de fora da cidade atendidas na cidade"
        at_v.run()
        checar("F. cidades de origem: sem a lista (banco/info antiga) a visão abre normal e sem o gráfico",
               not erros(at_v) and "De quais cidades de SP vêm as mulheres de fora?" not in " ".join(str(m.value) for m in at_v.markdown))
        at.session_state["fluxo_visao"] = "Moradoras atendidas em cidades de fora"
        at.run()
        checar("F. anos fora do padrão: o bloco solto e confuso saiu da aba Investigar (a informação mora na Evolução)",
               not erros(at) and "saiu do padrão em Rio Claro" not in textos
               and "Direção" not in textos and "Números pequenos" not in textos)
        checar("F. fluxo: cada bloco diz se é do Estado ou da cidade",
               textos.count("Todo o Estado de São Paulo") >= 3 and "📍 Rio Claro" in textos
               and "não muda quando você troca de cidade" in textos)
        checar("F. fluxo: a leitura cita Minas Gerais, Barretos e o aviso de que conta internações",
               "Minas Gerais" in textos and "Barretos" in textos and "internações, não pessoas" in textos)

        # tabela completa e pesquisável (10/2026): substituiu a de 7 linhas (uma por câncer)
        def tabela_do_fluxo(app):
            achadas = [d.value for d in app.dataframe if {"Estado de origem", "Hospital"} <= set(d.value.columns)]
            return achadas[0] if len(achadas) == 1 else None
        tab_f = tabela_do_fluxo(at)
        checar("F. fluxo: a tabela completa tem filtros de câncer, estado e anos, e a caixa de busca",
               tab_f is not None and at.multiselect(key="fluxo_tab_cancer") is not None
               and at.multiselect(key="fluxo_tab_estado") is not None
               and at.select_slider(key="fluxo_tab_anos") is not None and at.text_input(key="fluxo_tab_busca") is not None)
        checar("F. fluxo: a tabela mostra TUDO (21 linhas = 7 cânceres x 3 estados; 910 internações), não 7 linhas",
               tab_f is not None and len(tab_f) == 21 and int(tab_f["Internações"].sum()) == 910
               and "Parcela de fora" not in set(tab_f.columns))
        at.text_input(key="fluxo_tab_busca").set_value("goias").run()  # sem acento acha Goiás
        tab_busca = tabela_do_fluxo(at)
        checar("F. fluxo: buscar 'goias' (sem acento) deixa só Goiás: 7 linhas, 273 internações, e a leitura acompanha",
               not erros(at) and tab_busca is not None and len(tab_busca) == 7
               and set(tab_busca["Estado de origem"]) == {"Goiás"} and int(tab_busca["Internações"].sum()) == 273
               and "Com os filtros escolhidos, são 273 internações" in " ".join(str(m.value) for m in at.markdown))
        at.text_input(key="fluxo_tab_busca").set_value("palavra que não existe").run()
        checar("F. fluxo: busca sem resultado avisa e não quebra",
               not erros(at) and tabela_do_fluxo(at) is None
               and any("Nenhuma internação de fora com esses filtros" in str(i.value) for i in at.info))
        at.text_input(key="fluxo_tab_busca").set_value("").run()

        # hospitais habilitados no mapa de estados (10/2026): chave ligada por padrão, desligável; sem arquivo de posições, avisa
        import csv
        import tempfile
        import hospitais_oncologia as hosp_onco
        carregar_original = hosp_onco.carregar
        campos = ["cnes", "uf", "municipio", "nome", "nome_ministerio", "tipo", "habilitacao", "endereco", "cep", "telefone", "lat", "lon", "no_mapa", "motivo"]
        hospitais = [("2090236", "SP", "Barretos", "Hospital de Amor", "CACON", -20.557, -48.567, "sim"),
                     ("2082888", "SP", "Rio Claro", "Santa Casa de Rio Claro", "UNACON", -22.409, -47.560, "sim"),
                     ("1", "AM", "Manaus", "Centro de Oncologia de Manaus", "UNACON", -3.119, -60.021, "sim"),
                     ("2", "MT", "Cuiabá", "Hospital sem posição", "UNACON", "", "", "não")]
        with tempfile.TemporaryDirectory() as pasta_h:
            with open(os.path.join(pasta_h, "hospitais_oncologia_br_geo.csv"), "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(campos)
                for cn, uf, mu, no, ti, la, lo, nm in hospitais:
                    w.writerow([cn, uf, mu, no, no, ti, ti, "", "", "", la, lo, nm, "" if nm == "sim" else "cadastro desabilitado"])
            hosp_onco.carregar = lambda: carregar_original(pasta_h)
            st_cache = __import__("streamlit").cache_data
            try:
                st_cache.clear()
                at = abrir()
                at.session_state["aba"] = "Rede hospitalar"
                at.run()
                textos = " ".join(str(m.value) for m in at.markdown)
                liga = [x for x in at.toggle if "hospitais habilitados em oncologia" in x.label]
                tracos = json.dumps([json.loads(g.proto.spec) for g in at.get("plotly_chart")])
                checar("F. hospitais no mapa de estados: a chave aparece ligada e os tipos entram como pontos",
                       not erros(at) and len(liga) == 1 and liga[0].value is True and '"name": "UNACON"' in tracos and '"name": "CACON"' in tracos)
                checar("F. hospitais no mapa: só os 3 com posição (o sem posição não entra) e os nomes ficam no balão",
                       "Hospital de Amor" in tracos and "Centro de Oncologia de Manaus" in tracos and "Hospital sem posição" not in tracos)
                checar("F. hospitais no mapa: a leitura conta (3: 2 em SP, 1 fora), lembra que não é vaga e que não explica o motivo",
                       "3 hospitais habilitados em oncologia" in textos and "2 em SP e 1 em outros estados" in textos
                       and "não explica por que vêm" in textos and "Habilitado não quer dizer vaga" in textos)
                liga[0].set_value(False).run()
                tracos = json.dumps([json.loads(g.proto.spec) for g in at.get("plotly_chart")])
                textos = " ".join(str(m.value) for m in at.markdown)
                checar("F. hospitais no mapa: desligando a chave, os pontos e a frase somem e o resto do mapa continua",
                       not erros(at) and "Hospital de Amor" not in tracos and "hospitais habilitados em oncologia pelo" not in textos
                       and "Minas Gerais" in textos)
                hosp_onco.carregar = lambda: carregar_original(pasta_h + "_nao_existe")
                st_cache.clear()
                at = abrir()
                at.session_state["aba"] = "Rede hospitalar"
                at.run()
                legendas = " ".join(str(c.value) for c in at.caption)
                checar("F. hospitais no mapa: sem arquivo de posições a seção avisa o comando e não quebra",
                       not erros(at) and "gerar_hospitais_oncologia_geo" in legendas and not [x for x in at.toggle if "hospitais habilitados" in x.label])
            finally:
                hosp_onco.carregar = carregar_original
                st_cache.clear()
    finally:
        inteligencia.carregar_fluxo, inteligencia.fluxo_da_cidade = fluxo_original, cidade_original

    # ---- G. comparar cidades (aba Investigar): com uma cidade só avisa; com duas compara ----
    at = abrir()
    at.session_state["aba"] = "Investigar"
    at.run()
    textos = " ".join(str(m.value) for m in at.markdown)
    info = " ".join(str(i.value) for i in at.info)
    checar("G. uma cidade só no banco: a comparação avisa e não quebra",
           not erros(at) and "Só há uma cidade com dados no banco" in info
           and "Como Rio Claro se compara com outra cidade?" in textos)
    lista_original = configuracao_geografica.listar_municipios_disponiveis
    porte_original = inteligencia.porte_das_cidades
    configuracao_geografica.listar_municipios_disponiveis = lambda: [
        {"origem": "RIO_CLARO", "nome": "Rio Claro", "codigo_ibge": 3543907, "uf": "SP"},
        {"origem": "CAMPINAS", "nome": "Campinas", "codigo_ibge": 3509502, "uf": "SP"}]
    inteligencia.porte_das_cidades = lambda conn, uf="SP": {"RIO_CLARO": 1668, "CAMPINAS": 3656}
    try:
        at = abrir()
        at.session_state["aba"] = "Investigar"
        at.run()
        textos = " ".join(str(m.value) for m in at.markdown)
        caixas = {s.label: list(s.options) for s in at.selectbox}
        checar("G. duas cidades: abre sem erro e oferece Campinas para comparar",
               not erros(at) and caixas.get("Comparar Rio Claro com") == ["Campinas"])
        checar("G. duas cidades: mostra a comparação e a leitura",
               "O que a comparação mostra" in textos and "não é comparável" in textos
               and any("Letalidade hospitalar" in str(c) for c in at.dataframe[-1].value.columns.tolist() + at.dataframe[-1].value["Indicador"].tolist())
               if at.dataframe else False)
    finally:
        configuracao_geografica.listar_municipios_disponiveis = lista_original
        inteligencia.porte_das_cidades = porte_original

    # ---- H. ficha de um hospital (aba Rede hospitalar): escolher o câncer muda a lista e a ficha ----
    def hospitais_falsos():
        linhas, ufs = [], []
        for cnes, cidade, mun, n_mama, n_colo in (("2090236", "350550", "BARRETOS", 20, 6), ("2077590", "355030", "SAO_PAULO", 8, 0)):
            for tipo, n in (("MAMA", n_mama), ("COLO_UTERO", n_colo)):
                if not n:
                    continue
                for ano in range(2013, 2026):
                    if cnes == "2077590" and ano == 2015:
                        continue  # ano sem registro: o gráfico marca com x e explica
                    for proc, parte in (("cidade", n), ("outra_cidade", n // 2), ("fora", n // 4)):
                        linhas.append((cnes, tipo, ano, cidade, proc, parte, 0, 3 * parte, parte // 2, parte))
                ufs.append((cnes, tipo, "MG", 4 * n))
        base = pd.DataFrame(linhas, columns=["cnes", "tipo_cancer", "ano", "municipio_hospital", "procedencia",
                                             "internacoes", "obitos", "dias_permanencia", "urgencia", "com_carater"])
        return {"base": base, "ufs": pd.DataFrame(ufs, columns=["cnes", "tipo_cancer", "uf_residencia", "internacoes"]),
                "nomes": {"350550": "Barretos", "355030": "São Paulo"},
                "hospitais": {"2090236": "FUNDACAO PIO XII BARRETOS"}, "meses": MESES_NA_FONTE}

    # o bloco do hospital mora dentro do fluxo: sem fluxo (banco antigo) ele nem aparece
    # a tabela do fluxo ("Em quais cânceres a parcela de fora é maior?") também tem coluna "Câncer"
    TABELA_CANCERES_HOSPITAL = {"Câncer", "Internações", "Parcela"}
    hospitais_original, fluxo_original = inteligencia.carregar_hospitais, inteligencia.carregar_fluxo
    cidade_original = inteligencia.fluxo_da_cidade
    inteligencia.carregar_hospitais = lambda conn, uf="SP": hospitais_falsos()
    inteligencia.carregar_fluxo = lambda conn, uf="SP": fluxo_falso()
    inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": None
    streamlit.cache_data.clear()  # a carga do hospital e do fluxo ficam em cache entre cenários
    try:
        at = abrir()
        at.session_state["aba"] = "Rede hospitalar"
        at.run()
        textos = " ".join(str(m.value) for m in at.markdown)
        caixas = {s.label: list(s.options) for s in at.selectbox}
        checar("H. hospital: abre sem erro e oferece o seletor de câncer e o de hospital",
               not erros(at) and "Câncer" in caixas and "Todos os cânceres" in caixas["Câncer"]
               and "Escolha um hospital (pode digitar o nome)" in caixas)
        checar("H. hospital (todos os cânceres): lista pelo nome ou pelo CNES, com gráfico por ano e tabela de cânceres",
               caixas["Escolha um hospital (pode digitar o nome)"][0].startswith("FUNDACAO PIO XII BARRETOS")
               and any(o.startswith("CNES 2077590") for o in caixas["Escolha um hospital (pode digitar o nome)"])
               and "Quantas internações FUNDACAO PIO XII BARRETOS registrou em cada ano?" in textos
               and any(set(d.value.columns) == TABELA_CANCERES_HOSPITAL for d in at.dataframe))
        at.selectbox(key="hospital_cancer").select("Colo do útero").run()
        textos = " ".join(str(m.value) for m in at.markdown)
        caixas = {s.label: list(s.options) for s in at.selectbox}
        checar("H. hospital (colo do útero): só entra quem internou colo, a ficha vale só para ele e some a tabela de cânceres",
               not erros(at) and len(caixas["Escolha um hospital (pode digitar o nome)"]) == 1
               and "câncer de colo do útero" in textos and "colo do útero" in textos.lower()
               and not any(set(d.value.columns) == TABELA_CANCERES_HOSPITAL for d in at.dataframe))
        # hospital sem registro em 2015: o ano vazio é explicado (x no gráfico + leitura + caixa "por que")
        at.selectbox(key="hospital_cancer").select("Todos os cânceres").run()
        rotulo_sp = next(o for o in at.selectbox(key="hospital_perfil_todos").options if o.startswith("CNES 2077590"))
        at.selectbox(key="hospital_perfil_todos").select(rotulo_sp).run()
        textos = " ".join(str(m.value) for m in at.markdown)
        rotulos_exp = [e.label for e in at.expander]
        checar("H. hospital com um ano sem registro: a leitura diz o ano, a fonte e que o banco não guarda o motivo",
               not erros(at) and "Sem nenhuma internação registrada em 2015" in textos
               and "o banco não guarda o motivo da ausência" in textos
               and "Por que alguns anos ficam sem barra?" in rotulos_exp)
        at.selectbox(key="hospital_perfil_todos").select(
            next(o for o in at.selectbox(key="hospital_perfil_todos").options if o.startswith("FUNDACAO"))).run()
        checar("H. hospital sem lacunas: a caixa 'por que alguns anos ficam sem barra' não aparece",
               not erros(at) and "Por que alguns anos ficam sem barra?" not in [e.label for e in at.expander])

        # ---- ficha mais completa para gestor e pesquisador (22/10/2026): CNES, anos, estados de origem, CSV e atalho para a tabela ----
        textos = " ".join(str(m.value) for m in at.markdown)
        legendas = " ".join(str(c.value) for c in at.caption)
        graficos_e = [g for g in at.get("plotly_chart") if "Minas Gerais" in str(g.proto.spec)]
        baixar = [b for b in at.get("download_button") if "por ano" in str(b.proto.label)]
        checar("H. ficha: mostra o CNES, o filtro de anos, o gráfico dos estados de origem e o CSV por ano",
               not erros(at) and "CNES 2090236 · Barretos" in legendas and at.select_slider(key="hospital_anos") is not None
               and "De quais estados vêm as mulheres de fora de FUNDACAO PIO XII BARRETOS?" in textos
               and len(graficos_e) >= 1 and len(baixar) == 1
               and "vindas de 1 estado: Minas Gerais" in textos and "residência da mulher" in textos)
        # o período vale para tudo e a escolha do hospital NÃO pula (fica guardada pelo CNES)
        at.selectbox(key="hospital_perfil_todos").select(
            next(o for o in at.selectbox(key="hospital_perfil_todos").options if o.startswith("CNES 2077590"))).run()
        at.select_slider(key="hospital_anos").set_value((2016, 2020)).run()
        textos = " ".join(str(m.value) for m in at.markdown)
        legendas = " ".join(str(c.value) for c in at.caption)
        caixa_h = next(s for s in at.selectbox if s.label == "Escolha um hospital (pode digitar o nome)")
        checar("H. período: o título mostra os anos e o hospital escolhido continua o mesmo (guardado pelo CNES)",
               not erros(at) and at.session_state["hospital_cnes"] == "2077590" and "2016–2020" in textos
               and "CNES 2077590" in legendas and caixa_h.value.startswith("CNES 2077590"))
        at.select_slider(key="hospital_anos").set_value((2013, 2025)).run()
        checar("H. período: voltar ao período inteiro mantém o hospital e a ficha",
               not erros(at) and "CNES 2077590" in " ".join(str(c.value) for c in at.caption))
        # atalho para a tabela completa: filtra "Quem vem de fora..." para este hospital (CNES), este câncer e estes anos
        at.selectbox(key="hospital_perfil_todos").select(
            next(o for o in at.selectbox(key="hospital_perfil_todos").options if o.startswith("FUNDACAO"))).run()
        at.selectbox(key="hospital_cancer").select("Colo do útero").run()
        at.button(key="hospital_ver_na_tabela").click().run()
        legendas = " ".join(str(c.value) for c in at.caption)
        tabela_f = [d.value for d in at.dataframe if {"Estado de origem", "Hospital"} <= set(d.value.columns)]
        checar("H. atalho: filtra a tabela completa para este hospital e este câncer, e avisa que ela está filtrada",
               not erros(at) and at.session_state["fluxo_tab_busca"] == "2090236"
               and at.text_input(key="fluxo_tab_busca").value == "2090236"
               and at.multiselect(key="fluxo_tab_cancer").value == ["Colo do útero"]
               and "está filtrada para este hospital" in legendas
               and len(tabela_f) == 1 and set(tabela_f[0]["Câncer"]) == {"Colo do útero"})
    finally:
        inteligencia.carregar_hospitais, inteligencia.carregar_fluxo = hospitais_original, fluxo_original
        inteligencia.fluxo_da_cidade = cidade_original
        streamlit.cache_data.clear()

    # ---- J. previsão com validação (aba Evolução, projeção ligada) ----
    at = abrir()
    at.session_state["aba"] = "Evolução"
    at.session_state["ver_projecao"] = True
    at.run()
    rotulos = [e.label for e in at.expander]
    checar("J. com a projeção ligada, a aba Evolução mostra como o modelo de previsão foi escolhido",
           not erros(at) and "Como o Escudo escolheu o modelo de previsão (aprendizado de máquina simples)" in rotulos)
    tabelas = [d.value for d in at.dataframe if "Modelo" in d.value.columns]
    checar("J. a tabela compara os 5 modelos, com o escolhido marcado, e a leitura diz 'tendência aponta'",
           tabelas and len(tabelas[-1]) == 5 and (tabelas[-1]["Escolhido"] == "✔").sum() == 1
           and "tendência aponta" in " ".join(str(m.value) for m in at.markdown))
    at.session_state["ver_projecao"] = False
    at.run()
    checar("J. com a projeção desligada o bloco não aparece",
           "Como o Escudo escolheu o modelo de previsão (aprendizado de máquina simples)" not in [e.label for e in at.expander])

    # ---- I. Pergunte à Lia: a caixa de texto no painel real ----
    import assistente
    gravadas = []
    conversa.registrar_pergunta = lambda banco, assunto: gravadas.append(assunto)
    obter_ia_original = assistente.obter_ia

    def perguntar_na_caixa(at, texto):
        at.text_input(key="caixa_texto").set_value(texto)
        at.button(key="caixa_enviar").click().run()

    def textos_da_lateral(at):
        return " ".join(str(c.value) for c in at.main.caption) + " " + " ".join(str(m.value) for m in at.main.markdown)

    try:
        at = abrir()
        at.button(key="bv_fechar").click().run()
        checar("I. a caixa 'Pergunte à Lia' fica no centro, logo abaixo da Lia, e o painel abre sem erro",
               not erros(at) and at.text_input(key="caixa_texto") is not None and "Pergunte à Lia" in textos_da_lateral(at))
        checar("I. sem chave do Gemini a caixa avisa que está sem IA de linguagem",
               "IA de linguagem desligada" in textos_da_lateral(at))

        perguntar_na_caixa(at, "o câncer de mama está aumentando?")
        atual = at.session_state["lia"]["atual"]
        lateral = textos_da_lateral(at)
        checar("I. pergunta escrita: a Lia responde (evolução da mama) e o painel vai ao gráfico dela",
               not erros(at) and (atual.intencao, atual.cancer) == ("evolucao", "MAMA") and at.session_state["aba"] == "Evolução"
               and at.session_state["doenca"] == "MAMA")
        checar("I. a resposta mostra o que foi perguntado, o selo (sem IA) e a fonte dos dados",
               "Você perguntou: “o câncer de mama está aumentando?”" in lateral and "sem IA" in lateral and "SIH/SUS" in lateral)
        checar("I. só o ASSUNTO entendido é contado; o texto da pergunta nunca é guardado",
               gravadas == ["evolucao"] and all("mama" not in str(g) for g in gravadas))

        perguntar_na_caixa(at, "e no estado?")
        atual = at.session_state["lia"]["atual"]
        checar("I. contexto: 'e no estado?' continua na mama e liga a comparação com o Estado no gráfico",
               not erros(at) and (atual.intencao, atual.cancer) == ("estado", "MAMA") and at.session_state["ver_estado"] is True)

        perguntar_na_caixa(at, "e o de pulmão?")
        atual = at.session_state["lia"]["atual"]
        checar("I. contexto: 'e o de pulmão?' mantém o assunto e troca o câncer (o painel acompanha)",
               (atual.intencao, atual.cancer) == ("estado", "PULMAO") and at.session_state["doenca"] == "PULMAO")

        perguntar_na_caixa(at, "me explica isso melhor")
        atual = at.session_state["lia"]["atual"]
        checar("I. conversa: 'me explica isso melhor' retoma a resposta anterior (estado, pulmão) com explicação simples e os números",
               not erros(at) and (atual.intencao, atual.cancer, atual.origem) == ("estado", "PULMAO", "explicar")
               and "Vou explicar de outro jeito" in atual.fala and "Para ler os números" in atual.fala)
        perguntar_na_caixa(at, "está aumentando e o que posso esperar para frente?")
        atual = at.session_state["lia"]["atual"]
        checar("I. conversa: pedido composto responde os dois assuntos (evolução e previsão) e o painel vai ao gráfico",
               not erros(at) and (atual.origem, atual.intencao) == ("composta", "evolucao") and "dois pedidos" in atual.selo
               and at.session_state["aba"] == "Evolução")

        at.button(key="lia_discreto_inicio").click().run()
        checar("I. 'Começar de novo' esquece o contexto da caixa", "lia_memoria" not in at.session_state)

        perguntar_na_caixa(at, "o que são APACs?")
        atual = at.session_state["lia"]["atual"]
        checar("I. glossário: 'o que são APACs?' é explicado (texto fixo, sem IA) e não muda a aba",
               not erros(at) and atual.intencao == "glossario" and "Autorização de Procedimento Ambulatorial" in atual.fala
               and "Texto fixo" in textos_da_lateral(at))
        perguntar_na_caixa(at, "qual o preço da diária de internação?")
        atual = at.session_state["lia"]["atual"]
        checar("I. glossário: o preço da diária é explicado (o Escudo não calcula), sem devolver o total de valores",
               not erros(at) and atual.intencao == "glossario" and "não calcula nem informa o preço da diária" in atual.fala)
        at.button(key="lia_discreto_inicio").click().run()

        perguntar_na_caixa(at, "me explica o negócio dos números do hospital das moças")
        atual = at.session_state["lia"]["atual"]
        botoes = botoes_da_lia(at)
        checar("I. pergunta obscura: a Lia não chuta; oferece palpites em botões", atual.tipo in ("palpites", "fora") and len(botoes) >= 1)
        if atual.tipo == "palpites":
            botoes[0].click().run()
            checar("I. clicar num palpite responde o assunto escolhido", not erros(at) and at.session_state["lia"]["atual"].tipo == "intencao")

        gravadas.clear()
        perguntar_na_caixa(at, "meu marido me bate")
        atual = at.session_state["lia"]["atual"]
        checar("I. segurança: relato de violência mostra 190 e 180, leva ao Apoio e NÃO é gravado",
               not erros(at) and "190" in atual.fala and "180" in atual.fala and len(atual.links) == 1 and gravadas == [])
        perguntar_na_caixa(at, "senti um caroço no peito")
        checar("I. sintoma pessoal: texto fixo sem diagnóstico e também não é gravado",
               "Eu não faço diagnóstico" in at.session_state["lia"]["atual"].fala and gravadas == [])

        antes = at.session_state["lia"]["atual"]
        perguntar_na_caixa(at, "   ")
        checar("I. enviar vazio não faz nada e não quebra", not erros(at) and at.session_state["lia"]["atual"] is antes)

        at.button(key="caixa_exemplo_0").click().run()
        checar("I. botão de exemplo ('Qual câncer mais interna?') responde sem digitar",
               not erros(at) and at.session_state["lia"]["atual"].intencao == "mais_aparece")

        # ---- com o Gemini (simulado) ----
        recebidos = []

        def explicar_falso(pergunta, base, perfil):
            recebidos.append((pergunta, perfil))
            return "Em Rio Claro, a tendência aponta para o aumento das internações por câncer de mama; veja os números abaixo."

        assistente.obter_ia = lambda: assistente.IA(explicar=explicar_falso, classificar=lambda p, o: None, ligada=True)
        at = abrir()
        at.button(key="bv_fechar").click().run()
        checar("I. com o Gemini ligado a caixa diz que ele está ligado", "Gemini) ligada" in textos_da_lateral(at))
        at.radio(key="caixa_linguagem").set_value("Simples").run()
        perguntar_na_caixa(at, "o câncer de mama está aumentando?")
        atual = at.session_state["lia"]["atual"]
        rotulos_expanders = [e.label for e in at.main.expander]
        checar("I. IA redigiu: selo do Gemini, base calculada guardada e perfil 'Simples' enviado",
               not erros(at) and atual.usou_ia and "Redigido pela IA" in textos_da_lateral(at)
               and "O que o Escudo calculou (base da resposta)" in rotulos_expanders and recebidos[-1][1] == "SIMPLES")

        assistente.obter_ia = lambda: assistente.IA(explicar=lambda p, b, pf: (_ for _ in ()).throw(ConnectionError("sem rede")),
                                                    classificar=lambda p, o: None, ligada=True)
        perguntar_na_caixa(at, "o câncer de mama está aumentando?")
        checar("I. Gemini fora do ar: a resposta direta aparece, sem erro na tela",
               not erros(at) and not at.session_state["lia"]["atual"].usou_ia and at.session_state["lia"]["atual"].fala.strip())

        assistente.obter_ia = lambda: assistente.IA(explicar=explicar_falso, classificar=lambda p, o: None, ligada=True)
        at.session_state["lia_perguntas_ia"] = 40
        perguntar_na_caixa(at, "o câncer de mama está aumentando?")
        checar("I. passou do limite de perguntas com IA na sessão: segue sem Gemini, e avisa",
               not erros(at) and not at.session_state["lia"]["atual"].usou_ia and "IA de linguagem desligada" in textos_da_lateral(at))
    finally:
        assistente.obter_ia = obter_ia_original
        conversa.registrar_pergunta = lambda *a: None

    # ---- J. gráfico de idade (pedido da Secretaria da Mulher): escolher cidade e câncer dentro do gráfico ----
    lista_original = configuracao_geografica.listar_municipios_disponiveis
    faixas_original = inteligencia.carregar_faixas
    colunas_faixas = ["tipo_cancer", "ano", "faixa", "internacoes"]
    faixas_rio_claro = pd.DataFrame([(c, a_, f, 5 + a_ % 3) for c in CODIGOS.values() for a_ in range(2013, 2026)
                                     for f in ("até 39 anos", "40 a 49", "50 a 69", "70 ou mais")], columns=colunas_faixas)
    faixas_campinas = pd.DataFrame([("COLO_UTERO", 2025, f, 7) for f in ("até 39 anos", "40 a 49", "50 a 69", "70 ou mais")],
                                   columns=colunas_faixas)
    configuracao_geografica.listar_municipios_disponiveis = lambda: [
        {"origem": "RIO_CLARO", "nome": "Rio Claro", "codigo_ibge": 3543907, "uf": "SP"},
        {"origem": "CAMPINAS", "nome": "Campinas", "codigo_ibge": 3509502, "uf": "SP"}]
    inteligencia.carregar_faixas = lambda conn, o, uf="SP": faixas_rio_claro.copy() if o == "RIO_CLARO" else faixas_campinas.copy()
    try:
        streamlit.cache_data.clear()
        at = abrir()
        at.session_state["aba"] = "Investigar"
        at.run()
        caixas = {s.label: s for s in at.selectbox}
        textos = " ".join(str(m.value) for m in at.markdown)
        checar("J. idade: cidade e câncer se escolhem dentro do gráfico (começam iguais ao topo)",
               not erros(at) and "Cidade (onde as mulheres moram)" in caixas and "Câncer deste gráfico" in caixas
               and caixas["Cidade (onde as mulheres moram)"].value == "RIO_CLARO"
               and list(caixas["Câncer deste gráfico"].options)[0] == "Todos os cânceres acompanhados" and len(caixas["Câncer deste gráfico"].options) == 8)
        checar("J. idade: a pergunta diz de quem são os números (selo da cidade escolhida)",
               "A idade das mulheres internadas por câncer de mama mudou?" in textos and "📍 Rio Claro" in textos)
        caixas["Câncer deste gráfico"].select("TODOS").run()
        textos = " ".join(str(m.value) for m in at.markdown)
        checar("J. idade: 'Todos os cânceres acompanhados' soma os sete e muda o título",
               not erros(at) and "pelos cânceres acompanhados" in textos
               and "não prova que a idade de cada mulher mudou" in textos)
        {s.label: s for s in at.selectbox}["Cidade (onde as mulheres moram)"].select("CAMPINAS").run()
        caixas = {s.label: s for s in at.selectbox}
        textos = " ".join(str(m.value) for m in at.markdown)
        checar("J. idade: trocar de cidade troca os dados e as opções de câncer (só o que a cidade tem)",
               not erros(at) and list(caixas["Câncer deste gráfico"].options) == ["Todos os cânceres acompanhados", "Colo do útero"] and "📍 Campinas" in textos
               and "Só há idade registrada em 2025" in " ".join(str(m.value) for m in at.markdown))
        inteligencia.carregar_faixas = lambda conn, o, uf="SP": faixas_campinas.iloc[0:0].copy()
        streamlit.cache_data.clear()
        at = abrir()
        at.session_state["aba"] = "Investigar"
        at.session_state["faixas_origem"] = "CAMPINAS"
        at.session_state["faixas_origem_topo"] = "RIO_CLARO"
        at.run()
        info = " ".join(str(i.value) for i in at.info)
        checar("J. idade: cidade sem registro avisa 'este dado não existe', sem gráfico e sem zero inventado",
               not erros(at) and "Este dado não existe para Campinas" in info)
    finally:
        configuracao_geografica.listar_municipios_disponiveis = lista_original
        inteligencia.carregar_faixas = faixas_original
        streamlit.cache_data.clear()

    # ---- K. divisão da aba Investigar (20/10/2026): cada pergunta mora numa aba só, e a orientação diz qual ----
    hospitais_original_k, fluxo_original_k = inteligencia.carregar_hospitais, inteligencia.carregar_fluxo
    cidade_original_k = inteligencia.fluxo_da_cidade
    inteligencia.carregar_hospitais = lambda conn, uf="SP": hospitais_falsos()
    inteligencia.carregar_fluxo = lambda conn, uf="SP": fluxo_falso()
    inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": None
    streamlit.cache_data.clear()
    textos_aba = {}
    try:
        for nome_aba in ("Rede hospitalar", "Investigar"):
            at = abrir()
            at.session_state["aba"] = nome_aba
            at.run()
            textos_aba[nome_aba] = (" ".join(str(m.value) for m in at.markdown), erros(at))
    finally:
        inteligencia.carregar_hospitais, inteligencia.carregar_fluxo = hospitais_original_k, fluxo_original_k
        inteligencia.fluxo_da_cidade = cidade_original_k
        streamlit.cache_data.clear()
    rede, inv = textos_aba["Rede hospitalar"][0], textos_aba["Investigar"][0]
    checar("K. as 6 abas existem na ordem: Panorama, Evolução, Rede hospitalar, Investigar, Planejamento, Método",
           [r for r in at.radio if r.label == "Navegação"][0].options == ["Panorama", "Evolução", "Rede hospitalar", "Investigar", "Planejamento", "Método"])
    checar("K. Rede hospitalar abre sem erro, tem a orientação 'Nesta aba' e as perguntas de fluxo e hospital",
           not textos_aba["Rede hospitalar"][1] and "Nesta aba:" in rede
           and "De onde vêm as mulheres de outros estados" in rede and "Como é o atendimento em um hospital específico?" in rede)
    checar("K. Investigar abre sem erro, tem a orientação e as perguntas da cidade escolhida",
           not textos_aba["Investigar"][1] and "Nesta aba:" in inv
           and "Qual câncer cresce mais rápido" in inv and "A idade das mulheres internadas" in inv
           and "se compara com outra cidade" in inv)
    checar("K. nenhuma pergunta aparece nas duas abas (cada informação tem uma casa só)",
           "De onde vêm as mulheres de outros estados" not in inv and "Como é o atendimento em um hospital" not in inv
           and "Qual câncer cresce mais rápido" not in rede and "A idade das mulheres internadas" not in rede
           and "se compara com outra cidade" not in rede)
    checar("K. a faixa 'Você está em' nomeia a aba nova", "Rede hospitalar · onde as mulheres são atendidas" in rede)

    # ---- L. internações de um ano, mês a mês (Secretaria da Mulher): 2026 parcial, residência x hospital, sem dado != zero ----
    anos_original, periodo_original = inteligencia.anos_com_dados, inteligencia.internacoes_do_periodo
    chamadas_l = []

    def periodo_falso(conn, origem, codigo, ano, perspectiva="moradoras", cancer=None, uf="SP"):
        chamadas_l.append((ano, perspectiva, cancer))
        if ano == 2030:
            return {"ano": 2030, "perspectiva": perspectiva, "cancer": cancer, "meses": {m: None for m in range(1, 13)},
                    "na_fonte": [], "sem_dado": list(range(1, 13)), "total": 0, "por_cancer": {}, "ultimo_mes": None}
        na_fonte = [1, 3, 4, 5, 6, 7] if ano == 2026 else list(range(1, 13))
        base = 10 if perspectiva == "moradoras" else 25
        meses = {m: (base if m in na_fonte else None) for m in range(1, 13)}
        return {"ano": ano, "perspectiva": perspectiva, "cancer": cancer, "meses": meses, "na_fonte": na_fonte,
                "sem_dado": [m for m in range(1, 13) if m not in na_fonte], "total": base * len(na_fonte),
                "por_cancer": {"MAMA": base * len(na_fonte)}, "ultimo_mes": max(na_fonte)}

    inteligencia.anos_com_dados = lambda conn, uf="SP": [2024, 2025, 2026]
    inteligencia.internacoes_do_periodo = periodo_falso
    try:
        streamlit.cache_data.clear()
        at = abrir()
        at.session_state["aba"] = "Evolução"
        at.run()
        caixas = {s.label: s for s in at.selectbox}
        textos = " ".join(str(m.value) for m in at.markdown)
        metricas = {m.label: m.value for m in at.metric}
        checar("L. abre sem erro, com ano (o mais recente de início), 'Quem contar' e câncer",
               not erros(at) and caixas["Ano das internações"].value == 2026 and "Quem contar" in caixas
               and "Câncer das internações" in caixas)
        checar("L. 2026 parcial: 6 de 12 meses, último mês julho e o total é o REGISTRADO (60)",
               metricas.get("Meses que a fonte tem") == "6 de 12" and metricas.get("Último mês publicado") == "julho"
               and metricas.get("Internações registradas em 2026") == "60")
        leitura_txt = " ".join(str(m.value) for m in at.markdown)
        checar("L. a leitura diz que mês sem dado não é zero e que 2026 está incompleto",
               "não é zero" in leitura_txt and "incompleto" in leitura_txt)
        caixas["Quem contar"].select("hospitais").run()
        metricas = {m.label: m.value for m in at.metric}
        checar("L. trocar para 'hospitais da cidade' recalcula (6 meses x 25 = 150) e passa a perspectiva certa",
               not erros(at) and metricas.get("Internações registradas em 2026") == "150" and chamadas_l[-1][1] == "hospitais")
        {s.label: s for s in at.selectbox}["Ano das internações"].select(2025).run()
        metricas = {m.label: m.value for m in at.metric}
        textos = " ".join(str(m.value) for m in at.markdown)
        checar("L. 2025 (completo): 12 de 12 meses e sem aviso de ano incompleto",
               metricas.get("Meses que a fonte tem") == "12 de 12" and "2025 está incompleto" not in textos)
        # Estado velho/inválido numa caixa não pode derrubar a tela ("list.index(x): x not in list", 22/10/2026).
        at = abrir()
        at.session_state["aba"] = "Evolução"
        at.session_state["ip_quem"] = "valor_que_nao_existe"
        at.run()
        checar("L. valor inválido guardado em 'Quem contar' volta ao padrão, sem erro",
               not erros(at) and {s.label: s for s in at.selectbox}["Quem contar"].value == "moradoras")
    finally:
        inteligencia.anos_com_dados, inteligencia.internacoes_do_periodo = anos_original, periodo_original
        streamlit.cache_data.clear()
    inteligencia.anos_com_dados = lambda conn, uf="SP": []
    try:
        streamlit.cache_data.clear()
        at = abrir()
        at.session_state["aba"] = "Evolução"
        at.run()
        checar("L. sem anos no banco: avisa 'este dado não existe', sem erro e sem gráfico",
               not erros(at) and "Este dado não existe: o painel não conseguiu ler os anos" in " ".join(str(i.value) for i in at.info))
    finally:
        inteligencia.anos_com_dados = anos_original
        streamlit.cache_data.clear()

    # ---- M. seletor de município (autor, 22/10/2026): fica colado nos dados que ele muda e a escolha sobrevive à troca de aba ----
    # Duas cidades; o fluxo e o fluxo da cidade são os de teste (cenário F). Na Rede hospitalar o seletor mora logo acima do bloco da
    # cidade (os gráficos de cima são do Estado); nas outras abas, no começo dos dados. É desenhado em TODA aba, uma vez só.
    lista_original, fluxo_orig_m, cidade_orig_m = (configuracao_geografica.listar_municipios_disponiveis, inteligencia.carregar_fluxo,
                                                   inteligencia.fluxo_da_cidade)
    configuracao_geografica.listar_municipios_disponiveis = lambda: [
        {"origem": "RIO_CLARO", "nome": "Rio Claro", "codigo_ibge": 3543907, "uf": "SP"},
        {"origem": "CAMPINAS", "nome": "Campinas", "codigo_ibge": 3509502, "uf": "SP"}]
    inteligencia.carregar_fluxo = lambda conn, uf="SP": fluxo_falso()
    inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": {
        "atendimentos": 142, "da_cidade": 140, "outras_cidades": 0, "outros_estados": 2, "moradoras": 150,
        "moradoras_na_cidade": 140, "moradoras_fora": 10, "destinos": [("Campinas", 10)]}
    streamlit.cache_data.clear()  # a lista de cidades e o fluxo ficam em cache: nada de dado velho
    try:
        def seletores_da_cidade(app):
            return [c for c in app.selectbox if c.key == "municipio_painel"]

        def posicao(app, trecho):
            achados = [i for i, m in enumerate(app.markdown) if trecho in str(m.value)]
            return achados[0] if achados else None

        at = abrir()
        at.session_state["aba"] = "Rede hospitalar"
        at.run()
        p_tabela, p_dica, p_cidade = (posicao(at, "Quem vem de fora, de qual câncer e para qual hospital?"),
                                      posicao(at, "A cidade escolhida muda só o bloco abaixo"),
                                      posicao(at, "Quem é atendida nos hospitais de Rio Claro"))
        checar("M. Rede hospitalar: o seletor da cidade aparece UMA vez, depois dos gráficos do Estado e logo antes do bloco da cidade",
               not erros(at) and len(seletores_da_cidade(at)) == 1 and None not in (p_tabela, p_dica, p_cidade)
               and p_tabela < p_dica < p_cidade)
        at.selectbox(key="municipio_painel").select("Campinas").run()
        checar("M. Rede hospitalar: trocar a cidade no seletor atualiza o bloco da cidade e o resto do painel",
               not erros(at) and at.session_state["municipio_painel"] == "Campinas"
               and posicao(at, "Quem é atendida nos hospitais de Campinas") is not None
               and "Câncer em mulheres de <em>Campinas</em>" in " ".join(str(m.value) for m in at.markdown))
        percurso_ok = True
        for aba_m in ("Panorama", "Evolução", "Rede hospitalar", "Investigar", "Planejamento", "Método", "Rede hospitalar", "Panorama"):
            at.session_state["aba"] = aba_m
            at.run()
            percurso_ok = percurso_ok and not erros(at) and len(seletores_da_cidade(at)) == 1 \
                and at.session_state["municipio_painel"] == "Campinas"
        checar("M. a cidade escolhida SOBREVIVE a uma volta por todas as abas (o seletor muda de lugar, nunca some nem duplica)",
               percurso_ok)
        at.session_state["aba"] = "Panorama"
        at.run()
        p_dica_p, p_numeros = posicao(at, "A cidade escolhida vale para os gráficos marcados com"), posicao(at, "internações</span>")
        checar("M. nas abas da cidade (Panorama) o seletor fica no começo dos dados, antes dos números",
               not erros(at) and p_dica_p is not None and (p_numeros is None or p_dica_p < p_numeros)
               and posicao(at, "A cidade escolhida muda só o bloco abaixo") is None)
        # banco sem o fluxo: o bloco da cidade não existe, e o seletor continua à mão no fim da aba
        inteligencia.carregar_fluxo = lambda conn, uf="SP": None
        streamlit.cache_data.clear()
        at = abrir()
        at.session_state["aba"] = "Rede hospitalar"
        at.run()
        checar("M. Rede hospitalar sem o fluxo no banco: o seletor continua à mão (uma vez, sem erro)",
               not erros(at) and len(seletores_da_cidade(at)) == 1)
    finally:
        configuracao_geografica.listar_municipios_disponiveis = lista_original
        inteligencia.carregar_fluxo, inteligencia.fluxo_da_cidade = fluxo_orig_m, cidade_orig_m
        streamlit.cache_data.clear()

    print(f"\n({time.time() - inicio:.0f} s)")
    if falhas:
        print(f"{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("Todas as checagens do painel passaram.")


if __name__ == "__main__":
    main()
