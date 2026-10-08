import os
import sqlite3
import tempfile

import pandas as pd

from inteligencia import (
    anos_fora_do_padrao,
    anos_incompletos,
    confiabilidade,
    ficha_cancer,
    ano_atipico_no_estado,
    carregar_serie,
    completar_anos,
    escolher_uma_fonte,
    formatar_numero,
    leitura_evolucao,
    leitura_ponta_projecao,
    nome_doenca,
    ponta_fora_da_tendencia,
    projetar,
    radar_futuro,
    resumo_doencas,
    ritmo_estadual_na_escala,
    serie_doenca,
    tendencia_no_periodo,
    testar_projecao,
)

# =====================================
# TESTE DA INTELIGÊNCIA CENTRAL
#
# Séries sintéticas com números fáceis de conferir de cabeça, um
# banco sqlite temporário (para a regra de "uma fonte por cidade")
# e a base pública real analises/base_preditiva_2013_2025.csv.
# Não precisa do banco do Windows.
# =====================================

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CSV_REAL = os.path.join(DIRETORIO_ATUAL, "..", "analises", "base_preditiva_2013_2025.csv")

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def serie(valores_municipio, valores_estado=None, cancer="MAMA", ano_inicial=2013):
    linhas = []
    for i, v in enumerate(valores_municipio):
        linhas.append((cancer, "MUNICIPIO", ano_inicial + i, v, 0, 100.0 * v, 3 * v))
    for i, v in enumerate(valores_estado or []):
        linhas.append((cancer, "SP", ano_inicial + i, v, 0, 100.0 * v, 3 * v))
    return completar_anos(pd.DataFrame(linhas, columns=[
        "tipo_cancer", "grupo", "ano", "internacoes", "obitos", "valor_total", "dias_permanencia"]))


# ---- A. nomes ----
checar("A. 'COLO_UTERO' -> 'Colo do útero'", nome_doenca("COLO_UTERO") == "Colo do útero")
checar("A. 'PELE_NAO_MELANOMA' -> 'Pele não melanoma'", nome_doenca("PELE_NAO_MELANOMA") == "Pele não melanoma")
checar("A. nome já bonito continua igual", nome_doenca("Pulmão") == "Pulmão")
checar("A. código desconhecido não some", nome_doenca("NOVO_CANCER") == "Novo cancer")
checar("A. 1234567 -> '1.234.567'", formatar_numero(1234567) == "1.234.567")

# ---- B. ano sem internação vira zero ----
s = completar_anos(pd.DataFrame([
    ("MAMA", "MUNICIPIO", 2013, 5, 0, 1.0, 1), ("MAMA", "MUNICIPIO", 2016, 5, 0, 1.0, 1)],
    columns=["tipo_cancer", "grupo", "ano", "internacoes", "obitos", "valor_total", "dias_permanencia"]))
checar("B. 2014 e 2015 entram com zero", s[s["ano"].isin([2014, 2015])]["internacoes"].tolist() == [0, 0])

# ---- C. anos fora do padrão ----
estavel = [50, 52, 49, 51, 50, 53, 48, 50, 52, 49, 51, 50, 52]
checar("C. série estável: nenhum ano marcado",
       anos_fora_do_padrao(serie_doenca(serie(estavel), "MAMA")).empty)

# As pontas não podem ser avaliadas por uma reta ajustada aos outros
# anos, porque isso extrapola para fora do intervalo observado.
pontas = [90] + [50] * 11 + [90]
fora_pontas = anos_fora_do_padrao(serie_doenca(serie(pontas), "MAMA"))
checar("C. primeiro e último ano não são marcados por extrapolação",
       fora_pontas.empty)
ponta = ponta_fora_da_tendencia(serie_doenca(serie(pontas), "MAMA"))
checar("C. ponta: último ano muito acima da tendência dos anteriores é marcado",
       ponta["fora"] and ponta["direcao"] == "acima" and ponta["ano"] == 2025)
pequenos = [0, 0, 1, 0, 1, 1, 0, 2, 1, 1, 2, 1, 6]
checar("C. ponta com números pequenos: não arrisca (None), como pediu o teste das pontas",
       ponta_fora_da_tendencia(serie_doenca(serie(pequenos), "MAMA")) is None)
checar("C. ponta estável: não é marcada",
       not ponta_fora_da_tendencia(serie_doenca(serie(estavel), "MAMA"))["fora"])
checar("C. sem contradição aparente, sem frase de ponta",
       leitura_ponta_projecao(serie_doenca(serie(estavel), "MAMA")) is None)

pico = estavel.copy(); pico[8] = 90  # 2021
fora = anos_fora_do_padrao(serie_doenca(serie(pico), "MAMA"))
checar("C. pico marcado no ano certo e como 'acima'",
       fora["ano"].tolist() == [2021] and fora["direcao"].iloc[0] == "acima")

crescente = [10 + 5 * i for i in range(13)]
checar("C. crescimento regular não é 'fora do padrão'",
       anos_fora_do_padrao(serie_doenca(serie(crescente), "MAMA")).empty)

pequena = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1]  # 1 -> 3: "+200%", mas são 2 internações
checar("C. cidade pequena: 1 -> 3 NÃO é marcado (diferença mínima)",
       anos_fora_do_padrao(serie_doenca(serie(pequena), "MAMA")).empty)

agudos = [3, 4, 2, 4, 7, 2, 3, 3, 1, 4, 3, 12, 5]  # caso real do print (ovário, 2024)
fora = anos_fora_do_padrao(serie_doenca(serie(agudos), "MAMA"))
checar("C. pico de cidade pequena marcado e com aviso de números pequenos",
       fora["ano"].tolist() == [2024] and bool(fora["numeros_pequenos"].iloc[0]))

# ---- D. Estado na escala da cidade ----
s = serie([10] * 13, [1000 + 100 * i for i in range(13)])
estado = ritmo_estadual_na_escala(s, "MAMA")
checar("D. linha do Estado tem o mesmo total que a cidade",
       abs(estado["internacoes"].sum() - 130) < 1e-6)
checar("D. linha do Estado mantém o formato (sobe)",
       estado["internacoes"].iloc[-1] > estado["internacoes"].iloc[0])

# ---- E. leitura ----
frases = leitura_evolucao(serie(crescente, [1000] * 13), "MAMA")
checar("E. cita o crescimento", any("cresceram" in f for f in frases))
checar("E. compara com o Estado (mais rápido)", any("mais rápido" in f for f in frases))
frases = leitura_evolucao(serie(agudos), "MAMA")
checar("E. avisa números pequenos", any("Números pequenos" in f for f in frases))

# ---- F. projeção ----
proj = projetar(serie_doenca(serie(crescente), "MAMA"))
checar("F. reta perfeita projeta exato (2026 = 75)", abs(proj["internacoes"].iloc[0] - 75) < 1e-6)
proj = projetar(serie_doenca(serie([5, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0]), "MAMA"))
checar("F. projeção e faixa nunca negativas", (proj[["internacoes", "minimo"]] >= 0).all().all())
teste = testar_projecao(serie_doenca(serie(crescente), "MAMA"))
checar("F. teste de acerto: reta perfeita erra zero", teste["erro_tendencia"] < 1e-6)

# ---- G. uma fonte por cidade (evita contar Rio Claro em dobro) ----
linhas = pd.DataFrame({"tipo_cancer": ["MAMA", "MAMA"], "origem": ["RIO_CLARO", "SP"], "internacoes": [10, 10]})
checar("G. cidade nas duas fontes: usa só a estadual",
       escolher_uma_fonte(linhas)["origem"].tolist() == ["SP"])
checar("G. cidade só no arquivo próprio: usa ele",
       escolher_uma_fonte(linhas[linhas["origem"] == "RIO_CLARO"])["origem"].tolist() == ["RIO_CLARO"])
misto = pd.DataFrame({"tipo_cancer": ["MAMA", "MAMA", "OVARIO"],
                      "origem": ["RIO_CLARO", "SP", "RIO_CLARO"], "internacoes": [10, 10, 4]})
escolhido = escolher_uma_fonte(misto)
checar("G. escolha é por câncer: ovário só da pasta da cidade não some",
       sorted(zip(escolhido["tipo_cancer"], escolhido["origem"])) == [("MAMA", "SP"), ("OVARIO", "RIO_CLARO")])

caminho = os.path.join(tempfile.mkdtemp(), "teste.db")
conn = sqlite3.connect(caminho)
conn.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, ano INTEGER, "
             "obito INTEGER, valor_total REAL, dias_permanencia INTEGER)")
registros = []
for ano in range(2013, 2019):
    registros += [("MAMA", "RIO_CLARO", "RIO_CLARO", ano, 0, 100.0, 2)] * 4  # arquivo de Rio Claro
    registros += [("MAMA", "SP", "RIO_CLARO", ano, 0, 100.0, 2)] * 4         # as mesmas, no estadual
    registros += [("MAMA", "SP", "LIMEIRA", ano, 0, 100.0, 2)] * 6
conn.executemany("INSERT INTO internacoes VALUES (?,?,?,?,?,?,?)", registros)
s = carregar_serie(conn, "RIO_CLARO")
conn.close()
checar("G. banco: Rio Claro conta 4 por ano, não 8",
       serie_doenca(s, "MAMA")["internacoes"].tolist() == [4] * 6)
checar("G. banco: Estado soma todas as cidades do arquivo estadual (10 por ano)",
       serie_doenca(s, "MAMA", "SP")["internacoes"].tolist() == [10] * 6)

# ---- H. base pública real ----
if os.path.exists(CSV_REAL):
    real = pd.read_csv(CSV_REAL, sep=";")
    codigos = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL",
               "Ovário": "OVARIO", "Pele não melanoma": "PELE_NAO_MELANOMA",
               "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}
    real["tipo_cancer"] = real["cancer"].map(codigos)
    real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
    real["dias_permanencia"] = real["dias_internacao_total"]
    s = completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                             "valor_total", "dias_permanencia"]])
    resumo = resumo_doencas(s)
    checar("H. base real: Mama é o maior volume em Rio Claro (670)",
           resumo.iloc[0]["doenca"] == "Mama" and resumo.iloc[0]["internacoes"] == 670)
    fora, total = ano_atipico_no_estado(s, 2025)
    # anos_fora_do_padrao continua sem testar as pontas; o último ano
    # do Estado é avaliado por ponta_fora_da_tendencia (um passo,
    # números grandes): o salto simultâneo de 2025 volta a aparecer.
    checar("H. base real: 2025 fora do padrão no Estado na maioria dos cânceres (checagem da ponta)",
           total == 7 and fora >= 4)
    mama = serie_doenca(s, "MAMA")
    checar("H. base real: mama explica por que 2028 aparece abaixo de 2025 sem ser queda",
           "sem que isso signifique queda" in (leitura_ponta_projecao(mama) or ""))
    checar("H. base real: a projeção sai da reta, que em 2025 fica abaixo do observado",
           tendencia_no_periodo(mama)["internacoes"].iloc[-1] < mama["internacoes"].iloc[-1])
else:
    print("(pulado) H. base real não encontrada em " + CSV_REAL)

# ---- I. ficha, confiabilidade, investigação, planejamento ----
from inteligencia import (anos_fora_todos, cancer_de, comparar_faixas, confiabilidade,
                          destaques_cancer, evidencias_planejamento, ficha_cancer,
                          leitura_faixas, pressao_projetada, quando_aparece)

checar("I. 'câncer colorretal' sem 'de'; 'câncer de mama' com", cancer_de("COLORRETAL") == "câncer colorretal"
       and cancer_de("MAMA") == "câncer de mama")

dois = pd.concat([
    serie([10] * 13, [1000] * 13, cancer="MAMA"),
    serie([10] * 13, [1000] * 13, cancer="OVARIO"),
], ignore_index=True)
dois.loc[dois["tipo_cancer"] == "OVARIO", "valor_total"] *= 3  # ovário: mesma quantidade, valor 3x
f = ficha_cancer(dois, "OVARIO")
checar("I. ficha: 50% das internações e 75% do valor registrado", abs(f["pct_internacoes"] - 50) < 1e-6
       and abs(f["pct_valor"] - 75) < 1e-6)
checar("I. destaque: 'pesa mais no valor' quando valor% > internações%",
       any("Pesa mais no valor" in d for d in destaques_cancer(dois, "OVARIO")))
checar("I. destaque não aparece para quem não pesa mais no valor",
       not any("Pesa mais no valor" in d for d in destaques_cancer(dois, "MAMA")))

avisos = dict((t[:20], n) for n, t in confiabilidade(serie(agudos), "MAMA", duplicados=["MAMA"]))
textos = " ".join(t for _, t in confiabilidade(serie(agudos), "MAMA", duplicados=["MAMA"]))
checar("I. confiabilidade avisa duplicidade, números pequenos e falta de população",
       "duplicidade" in textos and "Números pequenos" in textos and "população" in textos)
checar("I. série grande e sem duplicidade: sem aviso de números pequenos",
       "Números pequenos" not in " ".join(t for _, t in confiabilidade(serie(crescente), "MAMA")))

varios = pd.concat([serie(pico, cancer="MAMA"), serie(agudos, cancer="OVARIO")], ignore_index=True)
todos = anos_fora_todos(varios)
checar("I. investigação junta os anos fora do padrão de todos os cânceres",
       sorted(zip(todos["doenca"], todos["ano"])) == [("Mama", 2021), ("Ovário", 2024)])

aparece = quando_aparece(serie([0, 0, 3, 4, 0, 5, 6, 7, 8, 9, 10, 11, 12]))
linha = aparece.iloc[0]
checar("I. quando aparece: primeiro ano 2015, pico 2025, 10 de 13 anos",
       linha["primeiro_ano"] == 2015 and linha["ano_de_pico"] == 2025 and linha["anos_com_internacao"] == "10 de 13")

from inteligencia import leitura_aparece, tabela_aparece_para_tela
tela = tabela_aparece_para_tela(aparece, 2013)
checar("I. tabela 'cresce mais rápido': uma coluna 'Observação' só quando algum câncer foge do normal, e só preenchida para ele",
       list(tela.columns) == ["Câncer", "Crescimento por ano", "Ano com mais internações", "Internações naquele ano",
                              "Observação"]
       and tela.iloc[0]["Observação"] == "só em 10 de 13 anos, desde 2015")
sempre = pd.concat([serie([5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17], cancer="MAMA"),
                    serie([9, 9, 9, 8, 8, 8, 7, 7, 7, 6, 6, 6, 5], cancer="OVARIO")], ignore_index=True)
ap2 = quando_aparece(sempre)
tela2 = tabela_aparece_para_tela(ap2)
checar("I. tabela: se todos aparecem sempre, some a coluna de observação; mais rápido em cima",
       list(tela2.columns) == ["Câncer", "Crescimento por ano", "Ano com mais internações", "Internações naquele ano"]
       and tela2.iloc[0]["Câncer"] == "Mama" and tela2.iloc[0]["Crescimento por ano"].startswith("+"))
txt = " ".join(leitura_aparece(ap2, {2018: 6}, 2025, 2013)).lower()
checar("I. leitura: mais rápido, queda, pico recente e aviso de meses estimados; sem causa nem R$",
       "mama é o que mais cresce" in txt and "com tendência de queda: ovário" in txt
       and "todos os cânceres tiveram internações em todos os anos do período." in txt and "estimado para 12 meses" in txt
       and "não é previsão" in txt and not any(p in txt for p in ("porque", "devido", "r$")))
checar("I. leitura: o 'ponto mais alto' conta a partir do último ano dos dados (2024 ou 2025), com plural certo",
       "em 1 de 2 cânceres o ano com mais internações foi 2024 ou 2025" in txt)
raro_txt = " ".join(leitura_aparece(quando_aparece(serie([0, 0, 3, 4, 0, 5, 6, 7, 8, 9, 10, 11, 12])), None, 2025, 2013)).lower()
checar("I. leitura: câncer que só começou depois leva 'desde 2015'; sem 'desde' quando sempre existiu",
       "teve internações em 10 dos 13 anos, desde 2015" in raro_txt
       and "desde 2013" not in " ".join(leitura_aparece(ap2, None, 2025, 2013)).lower())
checar("I. leitura: nenhum câncer com pico recente não vira 'em 0 de n'",
       "nenhum câncer teve o ano com mais internações em 2024 ou 2025" in " ".join(
           leitura_aparece(quando_aparece(serie([20, 18, 16, 14, 12, 10, 9, 8, 7, 6, 5, 4, 3])), None, 2025, 2013)).lower())

faixas = pd.DataFrame([
    ("MAMA", ano, faixa, n) for ano in range(2013, 2025)
    for faixa, n in (("até 39 anos", 10), ("40 a 49", 10), ("50 a 69", 10 if ano < 2019 else 30), ("70 ou mais", 10))
], columns=["tipo_cancer", "ano", "faixa", "internacoes"])
tabela, periodos = comparar_faixas(faixas, "MAMA")
checar("I. faixas: dois períodos e 50-69 sobe de 25% para 50%",
       periodos == ["2013–2018", "2019–2024"]
       and abs(tabela[(tabela["faixa"] == "50 a 69") & (tabela["periodo"] == "2019–2024")]["pct"].iloc[0] - 50) < 1e-6)
checar("I. leitura das faixas cita a faixa que mais mudou", "50 a 69" in leitura_faixas(tabela, periodos)[0])

pressao = pressao_projetada(serie(crescente, [1000] * 13), "MAMA")
checar("I. pressão projetada: internações, dias e valor registrado em 2028",
       set(pressao) == {"internacoes", "dias_permanencia", "valor_total"}
       and pressao["internacoes"]["ano"] == 2028 and abs(pressao["internacoes"]["previsto"] - 85) < 1e-6)
ev = evidencias_planejamento(pd.concat([serie(crescente, [1000] * 13, cancer="MAMA"),
                                        serie(estavel, [1000] * 13, cancer="OVARIO")], ignore_index=True))
checar("I. planejamento: quem cresce vem primeiro, com sinal de crescimento e linha de ação do INCA",
       ev[0]["tipo_cancer"] == "MAMA" and any("crescem" in s for s in ev[0]["sinais"])
       and "mamografia" in ev[0]["linha_de_acao"])
checar("I. planejamento: nenhuma evidência traz valor de orçamento",
       not any("orçamento" in s.lower() for e in ev for s in e["sinais"]))

# ---- R. radar do futuro ----
cresce_liso = [40 + 4 * i for i in range(13)]           # cresce firme, reta perfeita
estado_lento = [1000 + 20 * i for i in range(13)]        # Estado cresce ~1,6% ao ano
estavel_r = [50, 52, 49, 51, 50, 53, 48, 50, 52, 49, 51, 50, 52]
pouco = [2, 3, 2, 4, 3, 4, 5, 4, 6, 5, 6, 7, 7]          # cresce, mas com poucas internações
base_r = pd.concat([serie(cresce_liso, estado_lento, "MAMA"), serie(estavel_r, [1000] * 13, "OVARIO"),
                    serie(pouco, [500 + 10 * i for i in range(13)], "TIREOIDE")], ignore_index=True)
radar = {r["tipo_cancer"]: r for r in radar_futuro(base_r)}
checar("R. cresce firme, confiável e mais rápido que o Estado: alerta", radar["MAMA"]["nivel"] == "alerta")
checar("R. série estável: estável, sem sinal", radar["OVARIO"]["nivel"] == "estavel" and not radar["OVARIO"]["sinais"])
checar("R. poucas internações nunca viram alerta (no máximo observar, com cuidado escrito)",
       radar["TIREOIDE"]["nivel"] != "alerta" and any("poucas internações" in c for c in radar["TIREOIDE"]["cuidados"]))
checar("R. alerta vem antes de estável na ordem", [r["nivel"] for r in radar_futuro(base_r)][0] == "alerta")
checar("R. nenhum sinal fala em orçamento ou R$",
       not any("R$" in t or "orçamento" in t for r in radar.values() for t in r["sinais"] + r["cuidados"]))
checar("R. futuro comparado com o nível da tendência (não com o último ano)",
       abs(radar["MAMA"]["internacoes_hoje"] - cresce_liso[-1]) < 0.5 and radar["MAMA"]["internacoes_a_mais"] > 0)

# ---- M. anos com meses que a fonte não oferece ----
def banco_com_meses(meses_2018=6, com_coluna_mes=True):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE internacoes (tipo_cancer, origem, municipio, ano, " + ("mes, " if com_coluna_mes else "")
                 + "obito, valor_total, dias_permanencia)")
    linhas = []
    for ano in range(2013, 2025):
        for mes in range(1, 13):
            if ano == 2018 and mes > meses_2018:
                continue  # o DATASUS não oferece estes meses
            linhas += [("MAMA", "SP", "RIO_CLARO", ano, mes, 0, 100.0, 2)] * 5
            linhas += [("MAMA", "SP", "OUTRA", ano, mes, 1, 100.0, 2)] * 95
    if not com_coluna_mes:
        linhas = [l[:4] + l[5:] for l in linhas]
    conn.executemany("INSERT INTO internacoes VALUES (" + ",".join("?" * len(linhas[0])) + ")", linhas)
    return conn

sm = carregar_serie(banco_com_meses(), "RIO_CLARO", "SP")
mama = serie_doenca(sm, "MAMA")
checar("M. 2018 com 6 de 12 meses: vale a média mensal x 12 (60), não 30",
       mama.loc[mama["ano"] == 2018, "internacoes"].iloc[0] == 60
       and mama.loc[mama["ano"] == 2018, "internacoes_reg"].iloc[0] == 30)
checar("M. com o ajuste, 2018 não vira 'ano fora do padrão' (a queda era falta de meses)",
       anos_fora_do_padrao(mama).empty)
checar("M. totais do período continuam os REGISTRADOS", resumo_doencas(sm).iloc[0]["internacoes"] == 5 * 12 * 11 + 5 * 6
       and ficha_cancer(sm, "MAMA")["internacoes"] == 690)
checar("M. anos incompletos identificados (pelo Estado)", anos_incompletos(sm) == {2018: 6})
checar("M. confiabilidade avisa os meses que a fonte não oferece",
       any("DATASUS não oferece" in t and "2018 (6 de 12)" in t for _, t in confiabilidade(sm, "MAMA")))
sv = carregar_serie(banco_com_meses(com_coluna_mes=False), "RIO_CLARO", "SP")
checar("M. banco antigo (sem coluna mes): sem ajuste e pede para recarregar",
       serie_doenca(sv, "MAMA").loc[lambda d: d["ano"] == 2018, "internacoes"].iloc[0] == 30
       and any("sem o mês" in t for _, t in confiabilidade(sv, "MAMA")))

print()
if falhas:
    print(f"{len(falhas)} checagem(ns) falharam.")
    raise SystemExit(1)
print("Todas as checagens passaram.")
