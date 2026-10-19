import csv
import json
import os
import sys
import tempfile

# =====================================
# TESTE DE ACEITAÇÃO DA PÁGINA "HOSPITAIS DE CÂNCER" (dashboard/pages/hospitais_cancer.py)
#
# Abre a página DE VERDADE (Streamlit AppTest) com dados sintéticos e clica:
#   A. com posições: Estado de SP, cidade, os 3 mais próximos, mapa, cartões, filtros de tipo e busca;
#   B. o hospital cuja posição não passou aparece na lista SEM ponto e diz o motivo;
#   C. visão Brasil: filtro por estado e a nota de que o SIH só enxerga hospitais de SP;
#   D. só a lista (sem posições) e sem nenhum arquivo: avisa o que fazer, sem quebrar.
# Uso (da pasta do projeto):  py dashboard\teste_hospitais_cancer_tela.py
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PAGINA = os.path.join(RAIZ, "dashboard", "pages", "hospitais_cancer.py")
falhas = []
GEO_CAMPOS = ["cnes", "uf", "municipio", "nome", "nome_ministerio", "tipo", "habilitacao", "endereco", "cep", "telefone", "lat", "lon", "no_mapa", "motivo"]
LINHAS = [
    ("2090236", "SP", "Barretos", "Hospital de Amor", "CACON", "CACON", "Rua A, 1", "(17) 3321-6600", "-20.557000", "-48.568000", "sim", ""),
    ("2082888", "SP", "Rio Claro", "Santa Casa de Rio Claro", "UNACON", "UNACON", "Rua Dois, 297", "(19) 3535-7000", "-22.411000", "-47.561000", "sim", ""),
    ("2079798", "SP", "Campinas", "HC da Unicamp", "CACON", "CACON", "Rua B, 2", "(19) 3521-7000", "-22.829000", "-47.060000", "sim", ""),
    ("2058391", "SP", "São Paulo", "Hospital Albert Einstein", "Serviço isolado de radioterapia", "Radioterapia", "Av. C, 3", "(11) 2151-1233", "-23.600000", "-46.715000", "sim", ""),
    ("2025507", "SP", "Marília", "HC da Famema", "UNACON", "UNACON", "", "", "", "", "não", "a coordenada fica a 44 km do centro do município"),
    ("2269821", "RJ", "Rio de Janeiro", "INCA", "CACON", "CACON", "Praça D, 4", "(21) 3207-1000", "-22.911000", "-43.190000", "sim", ""),
    ("2147777", "RS", "Porto Alegre", "Hospital de Clínicas de Porto Alegre", "UNACON", "UNACON", "", "", "-30.040000", "-51.200000", "sim", ""),
]


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def abrir():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(PAGINA, default_timeout=60)
    at.run()
    return at


def texto(at):
    return (" ".join(str(m.value) for m in at.markdown) + " " + " ".join(str(w.value) for w in at.warning) + " "
            + " ".join(str(i.value) for i in at.info) + " " + " ".join(str(c.value) for c in at.caption))


def esquecer():
    import streamlit as st
    st.cache_data.clear()
    sys.modules.pop("hospitais_oncologia", None)  # o módulo lê a pasta na importação


def cartoes(at):
    return texto(at).count('class="hc-cartao"')


def main():
    with tempfile.TemporaryDirectory() as pasta, tempfile.TemporaryDirectory() as so_lista, tempfile.TemporaryDirectory() as nada:
        with open(os.path.join(pasta, "hospitais_oncologia_br_geo.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(GEO_CAMPOS)
            for cn, uf, mu, no, ti, ha, en, te, la, lo, nm, mo in LINHAS:
                w.writerow([cn, uf, mu, no, no, ti, ha, en, "", te, la, lo, nm, mo])
        with open(os.path.join(pasta, "centros.csv"), "w", encoding="utf-8") as f:
            f.write("nome,latitude,longitude\nRio Claro,-22.373,-47.580\nPiracicaba,-22.725,-47.649\nBarretos,-20.557,-48.568\n")
        with open(os.path.join(so_lista, "hospitais_oncologia_br.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["cnes", "uf", "municipio", "regiao_de_saude", "nome_ministerio", "codigo_habilitacao", "habilitacao", "tipo"])
            w.writerow(["2082888", "SP", "Rio Claro", "RRAS 14", "Santa Casa de Rio Claro", "17.06", "UNACON", "UNACON"])
        os.environ["ESCUDO_CENTROS_CSV"] = os.path.join(pasta, "centros.csv")

        # A. com posições
        os.environ["ESCUDO_HOSPITAIS_PASTA"] = pasta
        esquecer()
        at = abrir()
        t = texto(at)
        checar("A. abre sem exceção, com título, aviso 'habilitado não é vaga' e o alerta de risco",
               not at.exception and "Hospitais habilitados em" in t and "Habilitado não é vaga" in t and "190" in t)
        checar("A. começa no Estado de SP (5 estabelecimentos) com o selo de escopo", cartoes(at) == 5 and "Todo o Estado de São Paulo" in t)
        checar("A. escolhe a cidade (Rio Claro) e mostra os 3 hospitais mais próximos em linha reta, a Santa Casa primeiro",
               t.count("em linha reta") >= 3 and t.index("Santa Casa de Rio Claro") < t.index("HC da Unicamp") and "Não é rota nem tempo de viagem" in t)
        grade = t[t.index('class="hc-grade"'):]
        ordem = [grade.index(n) for n in ("Santa Casa de Rio Claro", "HC da Unicamp", "Hospital Albert Einstein", "Hospital de Amor", "HC da Famema")]
        checar("A. os cartões de baixo seguem a cidade escolhida: do mais perto ao mais longe, com km, e sem posição por último",
               ordem == sorted(ordem) and "em linha reta da sua cidade" in grade and grade.count("em linha reta da sua cidade") == 4
               and "Do mais perto ao mais longe de Rio Claro" in t)
        checar("A. avisa que quem decide é a regulação, não a proximidade", "quem decide para onde você vai é a regulação" in t)
        checar("A. a leitura diz o que está no mapa e o que está só na lista", "4 aparecem no mapa" in t and "1 está só na lista" in t)
        checar("B. o hospital sem posição confirmada aparece na lista SEM ponto e diz o motivo",
               "HC da Famema" in t and "Sem ponto no mapa: a coordenada fica a 44 km" in t)
        checar("A. cartão tem Como chegar (Google Maps) e Ligar com DDD",
               "google.com/maps/dir" in t and 'href="tel:+551935357000"' in t)
        checar("A. o mapa foi desenhado e a legenda mostra os tipos", len(at.get("deck_gl_json_chart")) == 1 and "UNACON" in t and "sua cidade" in t)
        mapa = json.loads(at.get("deck_gl_json_chart")[0].proto.json)
        tipos_camada = [c["@@type"] for c in mapa["layers"]]
        checar("A. mapa: pontos + 'sua cidade' + nomes escritos (poucos hospitais), com nome no balão ao passar o mouse",
               tipos_camada.count("ScatterplotLayer") == 2 and "TextLayer" in tipos_camada and "{nome}" in at.get("deck_gl_json_chart")[0].proto.tooltip)
        nomes_no_mapa = {d["nome"] for c in mapa["layers"] if c["@@type"] == "ScatterplotLayer" for d in c["data"]}
        checar("A. mapa: só tem ponto quem tem posição confirmada (o HC da Famema não entra) e cada ponto leva o nome do hospital",
               "Santa Casa de Rio Claro" in nomes_no_mapa and "HC da Famema" not in nomes_no_mapa and "Sua cidade" in nomes_no_mapa)

        checar("A. a página explica UNACON e CACON ali mesmo, com a diferença e o aviso de que o tipo não diz qual é melhor",
               "O que significam UNACON e CACON" in t and "Unidade de Assistência de Alta Complexidade em Oncologia" in t
               and "Centro de Assistência de Alta Complexidade em Oncologia" in t and "não diz qual hospital é melhor" in t)

        next(m for m in at.multiselect if m.key == "hc_tipos").set_value(["CACON"]).run()
        checar("A. filtro de tipo: só CACON (2 no SP)", cartoes(at) == 2 and not at.exception)
        next(m for m in at.multiselect if m.key == "hc_tipos").set_value([]).run()
        next(i for i in at.text_input if i.key == "hc_busca").set_value("barretos").run()
        checar("A. busca pelo município: Barretos", cartoes(at) == 1 and "Hospital de Amor" in texto(at))
        next(i for i in at.text_input if i.key == "hc_busca").set_value("zzzzz").run()
        checar("A. busca sem resultado: mensagem, sem quebrar", any("Nenhum estabelecimento" in str(i.value) for i in at.info) and not at.exception)
        next(i for i in at.text_input if i.key == "hc_busca").set_value("").run()

        # C. Brasil
        next(r for r in at.radio if r.key == "hc_escopo").set_value("br").run()
        t = texto(at)
        checar("C. visão Brasil: 7 estabelecimentos, selo 'Brasil' e a nota de que o SIH só enxerga hospitais de SP",
               cartoes(at) == 7 and "🌎 Brasil" in t and "não quem sai de São Paulo" in t and not at.exception)
        next(m for m in at.multiselect if m.key == "hc_ufs").set_value(["RJ"]).run()
        checar("C. filtro por estado: RJ mostra só o INCA", cartoes(at) == 1 and "INCA" in texto(at))
        next(m for m in at.multiselect if m.key == "hc_ufs").set_value([]).run()
        checar("C. na visão Brasil a escolha de cidade some (só vale para SP)", not any(s.key == "hc_cidade" for s in at.selectbox))

        # E. muitos pontos: o nome fica no balão; escrito ao lado só com poucos hospitais na tela
        with tempfile.TemporaryDirectory() as muitos:
            with open(os.path.join(muitos, "hospitais_oncologia_br_geo.csv"), "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(GEO_CAMPOS)
                for i in range(60):
                    w.writerow([f"{3000000 + i}", "SP", "Rio Claro", f"Hospital Numero {i}", f"Hospital Numero {i}", "UNACON", "UNACON", "", "", "",
                                f"{-22.30 - i * 0.004}", f"{-47.50 - i * 0.004}", "sim", ""])
            os.environ["ESCUDO_HOSPITAIS_PASTA"] = muitos
            esquecer()
            at = abrir()
            mapa = json.loads(at.get("deck_gl_json_chart")[0].proto.json)
            checar("E. com 60 hospitais na tela o mapa não escreve os nomes (só o balão), para não atropelar",
                   not at.exception and "TextLayer" not in [c["@@type"] for c in mapa["layers"]] and "Passe o mouse" in texto(at))
            next(i for i in at.text_input if i.key == "hc_busca").set_value("numero 7").run()
            mapa = json.loads(at.get("deck_gl_json_chart")[0].proto.json)
            checar("E. filtrando para poucos, os nomes passam a ser escritos ao lado dos pontos",
                   "TextLayer" in [c["@@type"] for c in mapa["layers"]] and "aparecem escritos ao lado" in texto(at))

        # D. só a lista, sem posições
        os.environ["ESCUDO_HOSPITAIS_PASTA"] = so_lista
        esquecer()
        at = abrir()
        t = texto(at)
        checar("D. só a lista oficial: mostra o hospital, avisa que o mapa precisa das posições e diz o comando",
               not at.exception and "Santa Casa de Rio Claro" in t and "gerar_hospitais_oncologia_geo" in t and len(at.get("deck_gl_json_chart")) == 0)
        os.environ["ESCUDO_HOSPITAIS_PASTA"] = nada
        esquecer()
        at = abrir()
        checar("D. sem nenhum arquivo: avisa como criar a lista, sem quebrar", not at.exception and any("gerar_lista_hospitais_oncologia" in str(w.value) for w in at.warning))

    if falhas:
        print("\nFALHARAM:", *falhas, sep="\n  - ")
        sys.exit(1)
    print("\nTodas as checagens da página Hospitais de câncer passaram.")


if __name__ == "__main__":
    main()
