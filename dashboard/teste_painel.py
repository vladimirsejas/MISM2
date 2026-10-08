import os
import sys
import time
from collections import deque

import pandas as pd

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
    return [b for b in at.sidebar.button if (b.key or "").startswith("lia_") and "discreto" not in (b.key or "")]


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
    checar(f"C. passeio leva o painel por {abas}", abas == ["Panorama", "Evolução", "Investigar", "Evolução",
                                                           "Planejamento", "Método"])
    at.button(key="pbtn_anterior").click().run()
    checar("C. passeio: '← anterior' volta uma parada", at.session_state["passeio"] == len(PARADAS) - 2)
    at.button(key="pbtn_sair").click().run()
    checar("C. passeio: 'sair' fecha e a Lia continua lá", at.session_state.get("passeio") is None
           and at.session_state["lia"]["atual"].fala.strip())

    # ---- D. as 5 abas, com as camadas ligadas ----
    for aba in ["Panorama", "Evolução", "Investigar", "Planejamento", "Método"]:
        at.session_state["aba"] = aba
        for camada in ("ver_estado", "ver_fora", "ver_projecao"):
            at.session_state[camada] = True
        at.run()
        checar(f"D. aba {aba} abre sem erro", not erros(at))

    # ---- D2. botão Início: de qualquer aba volta ao Panorama ----
    for aba in ["Evolução", "Investigar", "Planejamento", "Método"]:
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
        banco_app = os.path.join(RAIZ, "banco", "escudo_feminino.db")
        if os.path.exists(banco_app):
            os.utime(banco_app, (time.time() + 60, time.time() + 60))  # "nova carga"
        at.run()
        depois = list(next(r for r in at.radio if r.label == "Câncer em foco").options)
        checar("E. banco sem mudança: o cache continua valendo", igual and len(antes) == 7)
        checar("E. banco mudou: o painel lê de novo, sem reiniciar", not erros(at) and depois == ["Mama"])
    finally:
        inteligencia.carregar_serie = serie_original

    # ---- F. fluxo de mulheres de outros estados (aba Investigar) ----
    # Sem dados de fluxo (banco só com a carga antiga) a seção avisa e não quebra: é o que as abas
    # do cenário D já mostraram, com o banco vazio. Aqui, com dados de fluxo:
    fluxo_original, cidade_original = inteligencia.carregar_fluxo, inteligencia.fluxo_da_cidade
    inteligencia.carregar_fluxo = lambda conn, uf="SP": fluxo_falso()
    inteligencia.fluxo_da_cidade = lambda conn, o, cod, uf="SP": {
        "atendimentos": 142, "da_cidade": 140, "outras_cidades": 0, "outros_estados": 2, "moradoras": 150,
        "moradoras_na_cidade": 140, "moradoras_fora": 10, "destinos": [("Campinas", 10)]}
    try:
        at = abrir()
        at.session_state["aba"] = "Investigar"
        at.run()
        textos = " ".join(str(m.value) for m in at.markdown)
        rotulos = {m.label: m.value for m in at.metric}
        checar("F. fluxo: a aba Investigar abre sem erro", not erros(at))
        checar("F. fluxo: perguntas do fluxo e da cidade aparecem",
               "De onde vêm as mulheres de outros estados atendidas em São Paulo?" in textos
               and "Quem é atendida nos hospitais de Rio Claro" in textos)
        checar("F. fluxo: números (3 estados de origem; 2 de outros estados em Rio Claro)",
               rotulos.get("Estados de origem") == "3" and rotulos.get("De outros estados") == "2"
               and "Internações de fora de SP" in rotulos)
        checar("F. fluxo: cada bloco diz se é do Estado ou da cidade",
               textos.count("Todo o Estado de São Paulo") >= 3 and "📍 Rio Claro" in textos
               and "não muda quando você troca de cidade" in textos)
        checar("F. fluxo: a leitura cita Minas Gerais, Barretos e o aviso de que conta internações",
               "Minas Gerais" in textos and "Barretos" in textos and "internações, não pessoas" in textos)
    finally:
        inteligencia.carregar_fluxo, inteligencia.fluxo_da_cidade = fluxo_original, cidade_original

    print(f"\n({time.time() - inicio:.0f} s)")
    if falhas:
        print(f"{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("Todas as checagens do painel passaram.")


if __name__ == "__main__":
    main()
