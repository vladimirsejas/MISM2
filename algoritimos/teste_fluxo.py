import sqlite3

import pandas as pd

import inteligencia as ti

# =====================================
# TESTE DO FLUXO DE PACIENTES (inteligencia.py, 10/2026)
#
# Banco falso com números pequenos, conferíveis à mão:
#   MAMA 2024 (12 meses): 100 moradoras de Rio Claro atendidas em Rio Claro,
#     10 de Rio Claro atendidas em Campinas, 20 de Campinas em Campinas, e
#     30 de outros estados: MG 18 + GO 6 em Barretos, MG 4 em São Paulo,
#     PA 2 em Rio Claro.
#   MAMA 2023 (só 6 meses na fonte): 40 de Rio Claro em Rio Claro e 2 de MG
#     em Barretos.
#   COLO 2024: 10 de Campinas em Campinas e 5 de MG em Barretos.
# =====================================


def banco():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE municipios (codigo_ibge INTEGER, origem TEXT, nome TEXT, uf TEXT)")
    c.executemany("INSERT INTO municipios VALUES (?,?,?,?)", [
        (3543907, "RIO_CLARO", "Rio Claro", "SP"), (3509502, "CAMPINAS", "Campinas", "SP"),
        (3505500, "BARRETOS", "Barretos", "SP"), (3550308, "SAO_PAULO", "São Paulo", "SP")])
    c.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, ano INT, mes INT, "
              "obito INT, valor_total REAL, dias_permanencia INT, uf_residencia TEXT, "
              "municipio_hospital TEXT, cnes TEXT, car_int TEXT)")
    return c


def add(c, n, ano, meses, tipo, municipio, uf, hospital, cnes, dias=2):
    for i in range(n):
        c.execute("INSERT INTO internacoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (tipo, "SP", municipio, ano, meses[i % len(meses)], 0, 100.0, dias, uf, hospital, cnes, "01"))


def aprox(a, b, tol=0.05):
    return abs(a - b) <= tol


def main():
    c = banco()
    todos, seis = list(range(1, 13)), list(range(1, 7))
    add(c, 100, 2024, todos, "MAMA", "RIO_CLARO", "SP", "354390", "2082888")
    add(c, 10, 2024, todos, "MAMA", "RIO_CLARO", "SP", "350950", "2079798")
    add(c, 20, 2024, todos, "MAMA", "CAMPINAS", "SP", "350950", "2079798")
    add(c, 18, 2024, todos, "MAMA", "OUTRO_ESTADO", "MG", "350550", "2090236", dias=3)
    add(c, 6, 2024, todos, "MAMA", "OUTRO_ESTADO", "GO", "350550", "2090236", dias=3)
    add(c, 4, 2024, todos, "MAMA", "OUTRO_ESTADO", "MG", "355030", "2071234", dias=3)
    add(c, 2, 2024, todos, "MAMA", "OUTRO_ESTADO", "PA", "354390", "2082888", dias=3)
    add(c, 40, 2023, seis, "MAMA", "RIO_CLARO", "SP", "354390", "2082888")
    add(c, 2, 2023, seis, "MAMA", "OUTRO_ESTADO", "MG", "350550", "2090236", dias=3)
    add(c, 10, 2024, todos, "COLO_UTERO", "CAMPINAS", "SP", "350950", "2079798")
    add(c, 5, 2024, todos, "COLO_UTERO", "OUTRO_ESTADO", "MG", "350550", "2090236", dias=3)
    c.commit()

    fluxo = ti.carregar_fluxo(c)
    assert fluxo is not None

    # ---- totais ----
    todos_c = ti.resumo_fluxo(fluxo)
    assert (todos_c["internacoes_fora"], todos_c["internacoes_total"]) == (37, 217), todos_c
    assert aprox(todos_c["pct_fora"], 100 * 37 / 217)
    mama = ti.resumo_fluxo(fluxo, "MAMA")
    assert (mama["internacoes_fora"], mama["internacoes_total"]) == (32, 202)
    assert aprox(mama["pct_fora"], 15.84) and mama["dias_fora"] == 96 and mama["dias_total"] == 436
    assert aprox(mama["pct_dias_fora"], 22.02) and aprox(mama["permanencia_fora"], 3.0)
    print("[OK] totais: 37 de 217 (todos) e 32 de 202 (mama); dias de leito 96 de 436")

    # ---- de onde vêm e para onde vão ----
    ufs = mama["ufs"]
    assert list(ufs["uf"]) == ["MG", "GO", "PA"] and list(ufs["internacoes"]) == [24, 6, 2]
    assert ufs.iloc[0]["estado"] == "Minas Gerais" and aprox(ufs.iloc[0]["pct"], 75.0)
    dest = mama["destinos"]
    assert list(dest["municipio"]) == ["Barretos", "São Paulo", "Rio Claro"]
    assert list(dest["internacoes"]) == [26, 4, 2]
    conc = mama["concentracao"]
    assert conc["destino"] == "Barretos" and aprox(conc["pct"], 81.25) and conc["n_para_90"] == 2
    print("[OK] origem (MG 24, GO 6, PA 2) e destino (Barretos 26, São Paulo 4, Rio Claro 2); 90% em 2 municípios")

    # ---- evolução: a parcela compara os mesmos meses; o absoluto vai para 12 meses ----
    ev = ti.evolucao_fluxo(fluxo, "MAMA").set_index("ano")
    assert (ev.loc[2023, "fora"], ev.loc[2023, "total"]) == (2, 42) and ev.loc[2023, "meses"] == 6
    assert aprox(ev.loc[2023, "pct_fora"], 4.76) and aprox(ev.loc[2023, "fora_ajustado"], 4.0)
    assert (ev.loc[2024, "fora"], ev.loc[2024, "total"]) == (30, 160) and aprox(ev.loc[2024, "pct_fora"], 18.75)
    print("[OK] evolução: 2023 (6 meses) 4,8% e absoluto ajustado 4; 2024 18,8%")

    # ---- ligações do gráfico ----
    lig = ti.ligacoes_fluxo(fluxo, "MAMA", n_ufs=2, n_destinos=2)
    assert lig["valor"].sum() == 32
    par = {(r.origem, r.destino): r.valor for r in lig.itertuples()}
    assert par[("Minas Gerais", "Barretos")] == 20 and par[("Minas Gerais", "São Paulo")] == 4
    assert par[("Goiás", "Barretos")] == 6
    assert par[("Outros estados", "Outros municípios de SP")] == 2
    print("[OK] ligações do gráfico somam 32; o que passa do limite vira 'Outros'")

    # ---- pontos do mapa ----
    pontos, sem_pos = ti.pontos_mapa_fluxo(mama)
    assert list(pontos["uf"]) == ["MG", "GO", "PA"] and list(pontos["internacoes"]) == [24, 6, 2] and sem_pos == 0
    assert all(-35 < la < 6 and -75 < lo < -33 for la, lo in zip(pontos["lat"], pontos["lon"]))
    estranho = dict(mama, ufs=pd.DataFrame({"uf": ["MG", "XX"], "estado": ["Minas Gerais", "XX"],
                                            "internacoes": [5, 3], "pct": [62.5, 37.5]}))
    pontos, sem_pos = ti.pontos_mapa_fluxo(estranho)
    assert list(pontos["uf"]) == ["MG"] and sem_pos == 3
    print("[OK] mapa: uma bolha por estado de origem; sigla desconhecida fica de fora e é contada")

    # ---- por câncer ----
    pc = ti.por_cancer_fluxo(fluxo)
    assert list(pc["tipo_cancer"]) == ["COLO_UTERO", "MAMA"]  # maior parcela primeiro
    assert aprox(pc.iloc[0]["pct_fora"], 33.33) and pc.iloc[0]["destino_principal"] == "Barretos"
    print("[OK] por câncer: colo 33,3% de fora; mama 15,8%")

    # ---- a cidade ----
    info = ti.fluxo_da_cidade(c, "RIO_CLARO", 3543907)
    assert info["atendimentos"] == 142 and info["da_cidade"] == 140
    assert info["outras_cidades"] == 0 and info["outros_estados"] == 2
    assert info["moradoras"] == 150 and info["moradoras_na_cidade"] == 140 and info["moradoras_fora"] == 10
    assert info["destinos"] == [("Campinas", 10)]
    print("[OK] Rio Claro: 142 atendimentos (140 moradoras, 2 de outros estados); 10 moradoras atendidas em Campinas")

    # ---- textos: descrevem, não explicam ----
    textos = (ti.leitura_fluxo(mama, ev.reset_index()) + ti.leitura_fluxo(todos_c, None)
              + ti.leitura_cidade(info, "Rio Claro"))
    junto = " ".join(textos).lower()
    for proibido in ("porque", "devido", "por causa", "em razão", "r$"):
        assert proibido not in junto, proibido
    assert "internações, não pessoas" in junto and "só enxerga hospitais de sp" in junto
    assert "minas gerais" in junto and "barretos" in junto and "campinas (10)" in junto
    assert "saldo da cidade: -8" in junto, junto
    print("[OK] frases: citam os números, avisam que contam internações e nunca atribuem causa")

    # ---- banco antigo (sem as colunas do fluxo) e banco sem ninguém de fora ----
    antigo = sqlite3.connect(":memory:")
    antigo.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, ano INT)")
    assert ti.carregar_fluxo(antigo) is None
    assert ti.fluxo_da_cidade(antigo, "RIO_CLARO", 3543907) is None
    sem_fora = banco()
    add(sem_fora, 5, 2024, todos, "MAMA", "RIO_CLARO", "SP", "354390", "2082888")
    sem_fora.commit()
    assert ti.carregar_fluxo(sem_fora) is None
    vazio = sqlite3.connect(":memory:")  # nem a tabela existe
    assert ti.carregar_fluxo(vazio) is None and ti.fluxo_da_cidade(vazio, "X", 1) is None
    print("[OK] banco antigo, sem mulheres de fora ou sem tabela: devolve None (o painel avisa, não quebra)")

    print("\nTodas as checagens do fluxo passaram.")


if __name__ == "__main__":
    main()
