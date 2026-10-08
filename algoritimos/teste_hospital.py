import sqlite3

import inteligencia as ti

# =====================================
# TESTE DO PERFIL POR HOSPITAL (inteligencia.py, 10/2026)
#
# Banco falso com números conferíveis à mão.
#   Hospital A (CNES 2090236, Barretos, tem nome na tabela), 26 internações:
#     MAMA: 10 de Barretos (2 dias, eletivo), 6 de Jaú (4 dias, urgência, 1 óbito),
#           4 de MG (6 dias, urgência, 1 óbito)
#     COLO: 5 de Barretos (2 dias, eletivo), 1 de GO (6 dias, eletivo)
#     -> dias 84 (média 3,23), urgência 10 de 26, de fora 5 (19,2%: MG 4, GO 1)
#   Hospital B (CNES 2077590, São Paulo, sem nome na tabela), 4 internações de
#     moradoras de São Paulo, 1 dia; 2 de urgência e 2 sem o caráter informado.
#   Estado (A + B): 30 internações, 88 dias, urgência 12 de 28 com caráter.
# =====================================


def banco():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE municipios (codigo_ibge INTEGER, origem TEXT, nome TEXT, uf TEXT)")
    c.executemany("INSERT INTO municipios VALUES (?,?,?,?)", [
        (3505500, "BARRETOS", "Barretos", "SP"), (3525300, "JAU", "Jaú", "SP"), (3550308, "SAO_PAULO", "São Paulo", "SP")])
    c.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, codigo_ibge INTEGER, ano INT, "
              "mes INT, obito INT, valor_total REAL, dias_permanencia INT, uf_residencia TEXT, "
              "municipio_hospital TEXT, cnes TEXT, car_int TEXT)")
    c.execute("CREATE TABLE hospitais (cnes TEXT PRIMARY KEY, nome TEXT NOT NULL, fonte TEXT, consultado_em TEXT)")
    c.execute("INSERT INTO hospitais VALUES ('2090236', 'FUNDACAO PIO XII BARRETOS', 'teste', '2026-10-08')")
    return c


def add(c, n, tipo, municipio, codigo, uf, hospital, cnes, dias, car, obitos=0, ano=2024):
    for i in range(n):
        c.execute("INSERT INTO internacoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tipo, "SP", municipio, codigo, ano, 1 + i % 12, 1 if i < obitos else 0, 100.0, dias, uf,
                   hospital, cnes, car))


def hospital_x(ano_extra):
    """Hospital X (CNES 3333333, Barretos): 2024 tem 24 internações, 2 por mês
    (12 da cidade, 8 de Jaú, 4 de MG). `ano_extra` diz o que existe em 2023:
    'x3' = 3 internações dele nos meses 1 a 3 (a fonte só tem 3 meses de 2023);
    'outro' = só um outro hospital, com os 12 meses (X ainda não aparecia)."""
    c = banco()
    add(c, 12, "MAMA", "BARRETOS", 3505500, "SP", "350550", "3333333", 2, "01")
    add(c, 8, "MAMA", "JAU", 3525300, "SP", "350550", "3333333", 2, "01")
    add(c, 4, "MAMA", "OUTRO_ESTADO", 3106200, "MG", "350550", "3333333", 2, "01")
    if ano_extra == "x3":
        add(c, 3, "MAMA", "BARRETOS", 3505500, "SP", "350550", "3333333", 2, "01", ano=2023)
    else:
        add(c, 12, "MAMA", "SAO_PAULO", 3550308, "SP", "355030", "2077590", 2, "01", ano=2023)
    c.commit()
    return c


def aprox(a, b, tol=0.05):
    return abs(a - b) <= tol


def main():
    c = banco()
    add(c, 10, "MAMA", "BARRETOS", 3505500, "SP", "350550", "2090236", 2, "01")
    add(c, 6, "MAMA", "JAU", 3525300, "SP", "350550", "2090236", 4, "02", obitos=1)
    add(c, 4, "MAMA", "OUTRO_ESTADO", 3106200, "MG", "350550", "2090236", 6, "02", obitos=1)
    add(c, 5, "COLO_UTERO", "BARRETOS", 3505500, "SP", "350550", "2090236", 2, "01")
    add(c, 1, "COLO_UTERO", "OUTRO_ESTADO", 5208707, "GO", "350550", "2090236", 6, "01")
    add(c, 2, "MAMA", "SAO_PAULO", 3550308, "SP", "355030", "2077590", 1, "02")
    add(c, 2, "MAMA", "SAO_PAULO", 3550308, "SP", "355030", "2077590", 1, None)
    c.commit()

    dados = ti.carregar_hospitais(c)
    assert dados is not None

    # ---- a lista: nome da tabela ou 'CNES ...', do que mais interna ao que menos ----
    lista = ti.lista_hospitais(dados)
    assert list(lista["cnes"]) == ["2090236", "2077590"]
    assert list(lista["hospital"]) == ["FUNDACAO PIO XII BARRETOS", "CNES 2077590"]
    assert list(lista["municipio"]) == ["Barretos", "São Paulo"] and list(lista["internacoes"]) == [26, 4]
    print("[OK] lista: 26 e 4 internações; o sem nome na tabela aparece como 'CNES 2077590'")

    # ---- a ficha do hospital A ----
    a = ti.ficha_hospital(dados, "2090236")
    assert a["internacoes"] == 26 and a["obitos"] == 2 and a["tem_nome"] is True
    assert a["procedencia"] == {"cidade": 15, "outra_cidade": 6, "fora": 5, "sem_info": 0}
    assert aprox(a["pct_fora"], 19.23)
    assert a["ufs"] == [("Minas Gerais", 4), ("Goiás", 1)]
    assert list(a["cancer"]["tipo_cancer"]) == ["MAMA", "COLO_UTERO"] and list(a["cancer"]["internacoes"]) == [20, 6]
    assert aprox(a["cancer"].iloc[0]["pct"], 76.92)
    assert aprox(a["permanencia"], 84 / 26) and aprox(a["pct_urgencia"], 100 * 10 / 26)
    print("[OK] hospital A: 15 da cidade, 6 de outras cidades, 5 de fora (MG 4, GO 1); mama 76,9%; urgência 38,5%; 3,2 dias")

    # ---- referência do Estado: urgência só conta quem tem o caráter informado ----
    est = a["estado"]
    assert est["internacoes"] == 30 and aprox(est["permanencia"], 88 / 30)
    assert aprox(est["pct_urgencia"], 100 * 12 / 28)
    b = ti.ficha_hospital(dados, "2077590")
    assert b["internacoes"] == 4 and aprox(b["pct_urgencia"], 100.0) and b["tem_nome"] is False
    assert b["procedencia"]["cidade"] == 4 and b["ufs"] == []
    assert ti.ficha_hospital(dados, "9999999") is None
    print("[OK] Estado: urgência 12 de 28 (os 2 sem caráter não entram); hospital B 100% de urgência entre os informados")

    # ---- frases: descrevem, não ranqueiam nem explicam ----
    texto = " ".join(ti.leitura_hospital(a))
    junto = texto.lower()
    assert "fundacao pio xii barretos (barretos) registrou 26 internações" in junto
    assert "minas gerais (4)" in junto and "câncer com mais internações é mama" in junto
    assert "não serve para comparar hospitais nem medir qualidade" in junto and "internações, não pessoas" in junto
    for proibido in ("porque", "devido", "por causa", "em razão", "r$", "melhor hospital", "pior"):
        assert proibido not in junto, proibido
    assert "leia com cautela" in junto and "leia com cautela" in " ".join(ti.leitura_hospital(b)).lower()  # < 100
    grande = " ".join(ti.leitura_hospital(dict(a, internacoes=500))).lower()
    assert "leia com cautela" not in grande
    print("[OK] frases: citam os números, avisam que não mede qualidade e pedem cautela com poucas internações")

    # ---- por ano: ano com meses ausentes vai para a escala de 12 meses ----
    x = ti.ficha_hospital(ti.carregar_hospitais(hospital_x("x3")), "3333333")
    por_ano = x["por_ano"].set_index("ano")
    assert list(por_ano.index) == [2023, 2024]
    assert (por_ano.loc[2023, "registrado"], por_ano.loc[2023, "meses"]) == (3, 3)
    assert aprox(por_ano.loc[2023, "ajustado"], 12.0) and aprox(por_ano.loc[2023, "cidade"], 12.0)
    assert aprox(por_ano.loc[2024, "ajustado"], 24.0) and aprox(por_ano.loc[2024, "cidade"], 12.0)
    assert aprox(por_ano.loc[2024, "outra_cidade"], 8.0) and aprox(por_ano.loc[2024, "fora"], 4.0)
    assert aprox(por_ano.loc[2023, "fora"], 0.0)
    texto_anos = " ".join(ti.leitura_hospital_anos(x)).lower()
    assert "12 internações em 2023 e 24 em 2024" in texto_anos and "ponto mais alto foi 24 em 2024" in texto_anos
    assert "0,0% em 2023 e 16,7% em 2024" in texto_anos
    assert "anos com meses ausentes na fonte (2023)" in texto_anos and "média dos meses disponíveis" in texto_anos
    print("[OK] por ano: 2023 (3 meses na fonte) vai de 3 para 12 internações; 2024 tem 24 (12 + 8 + 4); parcela de fora 0% -> 16,7%")

    # ---- hospital que só aparece depois: ano sem registro não vira queda nem zero explicado ----
    y = ti.ficha_hospital(ti.carregar_hospitais(hospital_x("outro")), "3333333")
    por_ano = y["por_ano"].set_index("ano")
    assert por_ano.loc[2023, "registrado"] == 0 and aprox(por_ano.loc[2024, "ajustado"], 24.0)
    texto_y = " ".join(ti.leitura_hospital_anos(y)).lower()
    assert "primeiro ano com internações registradas foi 2024" in texto_y or "só há um ano" in texto_y
    assert "anos com meses ausentes" not in texto_y  # 2023 tem os 12 meses
    for proibido in ("porque", "devido", "por causa", "em razão", "r$", "abriu", "fechou"):
        assert proibido not in texto_anos + texto_y, proibido
    print("[OK] hospital sem internações em 2023: o ano aparece com zero registrado, sem inventar causa")

    # ---- banco antigo, sem a coluna do código IBGE, ou sem nenhum hospital ----
    sem_codigo = sqlite3.connect(":memory:")
    sem_codigo.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, uf_residencia TEXT, "
                       "municipio_hospital TEXT, cnes TEXT)")
    assert ti.carregar_hospitais(sem_codigo) is None
    antigo = sqlite3.connect(":memory:")
    antigo.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, ano INT)")
    assert ti.carregar_hospitais(antigo) is None
    assert ti.carregar_hospitais(sqlite3.connect(":memory:")) is None
    vazio = banco()
    assert ti.carregar_hospitais(vazio) is None
    sem_tabela = sqlite3.connect(":memory:")
    sem_tabela.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, codigo_ibge INTEGER, "
                       "ano INT, mes INT, obito INT, valor_total REAL, dias_permanencia INT, uf_residencia TEXT, "
                       "municipio_hospital TEXT, cnes TEXT, car_int TEXT)")
    sem_tabela.execute("INSERT INTO internacoes VALUES ('MAMA','SP','BARRETOS',3505500,2024,1,0,1,2,'SP','350550','2090236','01')")
    d = ti.carregar_hospitais(sem_tabela)
    assert list(ti.lista_hospitais(d)["hospital"]) == ["CNES 2090236"]
    print("[OK] banco antigo, sem código IBGE ou vazio: None; sem a tabela de nomes: mostra o número do CNES")

    print("\nTodas as checagens do perfil por hospital passaram.")


if __name__ == "__main__":
    main()
