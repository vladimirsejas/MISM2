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
    c.execute("CREATE TABLE hospitais (cnes TEXT PRIMARY KEY, nome TEXT NOT NULL, fonte TEXT, consultado_em TEXT)")
    c.execute("INSERT INTO hospitais VALUES ('2090236', 'FUNDACAO PIO XII BARRETOS', 'teste', '2026-10-08')")
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

    # ---- hospitais: nome da tabela `hospitais`; sem nome, o número do CNES ----
    hosp = ti.hospitais_fluxo(fluxo, "MAMA")
    assert list(hosp["cnes"]) == ["2090236", "2071234", "2082888"], list(hosp["cnes"])
    assert list(hosp["hospital"]) == ["FUNDACAO PIO XII BARRETOS", "CNES 2071234", "CNES 2082888"]
    assert list(hosp["tem_nome"]) == [True, False, False]
    assert list(hosp["municipio"]) == ["Barretos", "São Paulo", "Rio Claro"]
    assert list(hosp["internacoes"]) == [26, 4, 2] and aprox(hosp.iloc[0]["pct"], 81.25)
    todos_h = ti.hospitais_fluxo(fluxo)
    assert (todos_h.iloc[0]["internacoes"], todos_h.iloc[0]["cnes"]) == (31, "2090236")
    assert len(ti.hospitais_fluxo(fluxo, "MAMA", n=2)) == 2
    texto_h = " ".join(ti.leitura_hospitais(fluxo, hosp, "MAMA")).lower()
    assert "fundacao pio xii barretos (barretos)" in texto_h and "3 hospitais" in texto_h
    assert "py etl\\criar_tabela_hospitais.py" in texto_h and "internações, não pessoas" in texto_h
    for proibido in ("porque", "devido", "por causa", "em razão", "r$"):
        assert proibido not in texto_h, proibido
    sem_tabela = dict(fluxo, hospitais={})
    assert not ti.hospitais_fluxo(sem_tabela, "MAMA")["tem_nome"].any()
    sem_cnes = dict(fluxo, fora=fluxo["fora"].assign(cnes=None))
    assert ti.hospitais_fluxo(sem_cnes).empty and "CNES" in ti.leitura_hospitais(sem_cnes, ti.hospitais_fluxo(sem_cnes))[0]
    print("[OK] hospitais: nome da tabela ou 'CNES 0000000'; município certo; 81,3% no primeiro; sem tabela/CNES não quebra")

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

    # ---- tabela completa e pesquisável (10/2026) ----
    tab = ti.tabela_fluxo(fluxo)
    assert len(tab) == 6 and int(tab["internacoes"].sum()) == 37, tab
    assert set(tab["cancer"]) == {ti.nome_doenca("MAMA"), ti.nome_doenca("COLO_UTERO")}
    assert "FUNDACAO PIO XII BARRETOS" in set(tab["hospital"]) and "CNES 2082888" in set(tab["hospital"])
    assert set(tab["municipio"]) == {"Barretos", "São Paulo", "Rio Claro"}
    barretos = ti.filtrar_tabela_fluxo(tab, busca="barretos")
    assert len(barretos) == 4 and int(barretos["internacoes"].sum()) == 31
    for jeito in ("sao paulo", "SÃO PAULO", "  São   Paulo "):
        achou = ti.filtrar_tabela_fluxo(tab, busca=jeito)
        assert len(achou) == 1 and int(achou["internacoes"].sum()) == 4, jeito  # sem acento nem maiúscula
    assert int(ti.filtrar_tabela_fluxo(tab, busca="minas barretos")["internacoes"].sum()) == 25  # todas as palavras
    assert ti.filtrar_tabela_fluxo(tab, busca="2082888")["internacoes"].sum() == 2  # CNES também acha
    assert ti.filtrar_tabela_fluxo(tab, busca="zzz").empty
    assert int(ti.filtrar_tabela_fluxo(tab, cancers=[ti.nome_doenca("COLO_UTERO")])["internacoes"].sum()) == 5
    assert int(ti.filtrar_tabela_fluxo(tab, estados=["Goiás"])["internacoes"].sum()) == 6
    assert int(ti.filtrar_tabela_fluxo(tab, anos=(2024, 2024))["internacoes"].sum()) == 35
    soma = ti.agrupar_tabela_fluxo(tab)
    assert len(soma) == 5 and int(soma.iloc[0]["internacoes"]) == 20 and int(soma["internacoes"].sum()) == 37
    assert "ano" not in soma.columns and len(ti.agrupar_tabela_fluxo(tab, por_ano=True)) == 6
    assert ti.agrupar_tabela_fluxo(tab.iloc[0:0]).empty
    print("[OK] tabela completa: 6 linhas = 37 internações; busca sem acento/maiúscula, várias palavras, CNES, filtros e soma")

    parcelas = ti.parcela_fora_por_cancer(fluxo)
    assert list(parcelas["doenca"]) == [ti.nome_doenca("COLO_UTERO"), ti.nome_doenca("MAMA")]
    assert aprox(parcelas.iloc[0]["pct_fora"], 33.33) and aprox(parcelas.iloc[1]["pct_fora"], 15.84)
    em_2024 = ti.parcela_fora_por_cancer(fluxo, (2024, 2024))
    assert aprox(em_2024[em_2024["doenca"] == ti.nome_doenca("MAMA")].iloc[0]["pct_fora"], 18.75)  # 30 de 160
    leitura_t = ti.leitura_tabela_fluxo(tab, parcelas, False) + ti.leitura_tabela_fluxo(barretos, parcelas, True)
    junto_t = " ".join(leitura_t).lower()
    assert "37 internações" in junto_t and "com os filtros escolhidos, são 31 internações" in junto_t
    assert "fundacao pio xii barretos" in junto_t and "internações, não pessoas" in junto_t
    assert "33,3%" in junto_t and "15,8%" in junto_t
    assert ti.leitura_tabela_fluxo(tab.iloc[0:0], parcelas, True)[0].startswith("Nenhuma internação de fora")
    for proibido in ("porque", "devido", "por causa", "em razão", "r$"):
        assert proibido not in junto_t, proibido
    print("[OK] parcela de fora por câncer no período (colo 33,3%; mama 15,8%, ou 18,8% só em 2024) e frases sem causa")

    # ---- a cidade ----
    info = ti.fluxo_da_cidade(c, "RIO_CLARO", 3543907)
    assert info["atendimentos"] == 142 and info["da_cidade"] == 140
    assert info["outras_cidades"] == 0 and info["outros_estados"] == 2
    assert info["moradoras"] == 150 and info["moradoras_na_cidade"] == 140 and info["moradoras_fora"] == 10
    assert info["destinos"] == [("Campinas", 10)]
    print("[OK] Rio Claro: 142 atendimentos (140 moradoras, 2 de outros estados); 10 moradoras atendidas em Campinas")

    # ---- de que cidades vêm as mulheres de fora atendidas na cidade (pedido do autor, 22/10/2026) ----
    v = banco()
    v.executemany("INSERT INTO municipios VALUES (?,?,?,?)", [
        (3547502, "SANTA_GERTRUDES", "Santa Gertrudes", "SP"), (3523107, "ITIRAPINA", "Itirapina", "SP"),
        (3520004, "IPEUNA", "Ipeúna", "SP"), (3503505, "ARARAS", "Araras", "SP")])  # CORDEIROPOLIS fica de fora do catálogo
    for municipio, n in (("RIO_CLARO", 20), ("SANTA_GERTRUDES", 14), ("ITIRAPINA", 6), ("IPEUNA", 5),
                         ("ANALANDIA", 3), ("CORUMBATAI", 2), ("ARARAS", 1), ("CORDEIROPOLIS", 1)):
        add(v, n, 2024, todos, "MAMA", municipio, "SP", "354390", "2082888")
    add(v, 4, 2024, todos, "MAMA", "RIO_CLARO", "SP", "350950", "2079798")      # moradora atendida fora: não conta como "de fora"
    add(v, 9, 2024, todos, "MAMA", "SANTA_GERTRUDES", "SP", "350950", "2079798")  # hospital de Campinas: não é de Rio Claro
    v.commit()
    cv = ti.fluxo_da_cidade(v, "RIO_CLARO", 3543907)
    assert cv["atendimentos"] == 52 and cv["da_cidade"] == 20 and cv["outras_cidades"] == 32 and cv["outros_estados"] == 0
    nomes_o = [o["nome"] for o in cv["origens"]]
    assert nomes_o == ["Santa Gertrudes", "Itirapina", "Ipeúna", "Analandia", "Corumbatai", "Araras", "Cordeiropolis"], nomes_o
    assert [o["internacoes"] for o in cv["origens"]] == [14, 6, 5, 3, 2, 1, 1]
    assert sum(o["internacoes"] for o in cv["origens"]) == cv["outras_cidades"]  # as barras fecham com o número do painel
    assert cv["origens"][0]["codigo6"] == "354750" and cv["origens"][3]["codigo6"] is None  # sem catálogo: nome da chave, sem código
    principais, resto_n, resto_c = ti.agrupar_origens(cv["origens"])
    assert principais == [("Santa Gertrudes", 14), ("Itirapina", 6), ("Ipeúna", 5)] and (resto_n, resto_c) == (7, 4)
    assert sum(n for _, n in principais) + resto_n == cv["outras_cidades"]
    todas_pequenas, r0, r1 = ti.agrupar_origens([{"nome": "A", "internacoes": 2}, {"nome": "B", "internacoes": 1}])
    assert todas_pequenas == [("A", 2), ("B", 1)] and (r0, r1) == (0, 0)  # nenhuma chega ao mínimo: mostra todas
    assert ti.agrupar_origens([]) == ([], 0, 0) and ti.agrupar_origens(None) == ([], 0, 0)
    # polo com dezenas de cidades (Barretos): só as 15 maiores aparecem, o resto vira um bloco e a soma fecha
    muitas = [{"nome": f"Cidade {i:02d}", "internacoes": 100 - i} for i in range(30)]
    p15, r_n, r_c = ti.agrupar_origens(muitas)
    assert len(p15) == ti.MAXIMO_DE_CIDADES == 15 and r_c == 15 and p15[0] == ("Cidade 00", 100)
    assert sum(n for _, n in p15) + r_n == sum(o["internacoes"] for o in muitas)
    pequenas = [{"nome": f"P{i}", "internacoes": 2} for i in range(20)]  # nenhuma chega a 5 e são muitas: também há teto
    p_p, rp_n, rp_c = ti.agrupar_origens(pequenas)
    assert len(p_p) == 15 and rp_c == 5 and rp_n == 10
    texto_o = " ".join(ti.leitura_cidade_visao(cv, "Rio Claro", "aqui"))
    assert "vêm de 7 cidades" in texto_o and "Santa Gertrudes (14, 43,8%)" in texto_o and "Itirapina (6, 18,8%)" in texto_o
    assert "residência da mulher" in texto_o and "não explica por quê" in texto_o
    assert "internações, não pessoas" in texto_o and "só enxerga hospitais de sp" in texto_o.lower()
    for proibido in ("porque", "devido", "por causa", "em razão", "r$"):
        assert proibido not in texto_o.lower(), proibido
    sem_origem = dict(cv, origens=[])
    assert "vêm de" not in " ".join(ti.leitura_cidade_visao(sem_origem, "Rio Claro", "aqui"))  # sem a lista, a leitura de antes
    sem_chave = {k: x for k, x in cv.items() if k != "origens"}
    assert "vêm de" not in " ".join(ti.leitura_cidade_visao(sem_chave, "Rio Claro", "aqui"))  # info antiga (sem 'origens')
    # vale para QUALQUER cidade, não só Rio Claro: Barretos (hospital de referência) recebe de outras cidades e de outros estados
    w = banco()
    w.executemany("INSERT INTO municipios VALUES (?,?,?,?)", [(3543402, "RIBEIRAO_PRETO", "Ribeirão Preto", "SP")])
    for municipio, uf, n in (("BARRETOS", "SP", 10), ("RIBEIRAO_PRETO", "SP", 30), ("COLINA", "SP", 8), ("OUTRO_ESTADO", "MG", 18),
                             ("OUTRO_ESTADO", "GO", 6), ("RIO_CLARO", "SP", 2)):
        add(w, n, 2024, todos, "MAMA", municipio, uf, "350550", "2090236")
    add(w, 7, 2024, todos, "MAMA", "BARRETOS", "SP", "354390", "2082888")  # moradora de Barretos atendida em Rio Claro
    w.commit()
    cb = ti.fluxo_da_cidade(w, "BARRETOS", 3505500)
    assert cb["atendimentos"] == 74 and cb["da_cidade"] == 10 and cb["outras_cidades"] == 40 and cb["outros_estados"] == 24
    assert [(o["nome"], o["internacoes"]) for o in cb["origens"]] == [("Ribeirão Preto", 30), ("Colina", 8), ("Rio Claro", 2)], cb["origens"]
    assert "Barretos" not in [o["nome"] for o in cb["origens"]] and sum(o["internacoes"] for o in cb["origens"]) == cb["outras_cidades"]
    assert "Ribeirão Preto (30, 75,0%)" in " ".join(ti.leitura_cidade_visao(cb, "Barretos", "aqui"))
    assert [o["nome"] for o in ti.fluxo_da_cidade(w, "RIO_CLARO", 3543907)["origens"]] == ["Barretos"]  # a mesma base, outra cidade
    sem_tabela = sqlite3.connect(":memory:")  # banco sem a tabela `municipios`: nomes vêm da chave
    sem_tabela.execute("CREATE TABLE internacoes (tipo_cancer TEXT, origem TEXT, municipio TEXT, ano INT, mes INT, "
                       "obito INT, valor_total REAL, dias_permanencia INT, uf_residencia TEXT, "
                       "municipio_hospital TEXT, cnes TEXT, car_int TEXT)")
    add(sem_tabela, 7, 2024, todos, "MAMA", "SANTA_GERTRUDES", "SP", "354390", "2082888")
    sem_tabela.commit()
    assert [(o["nome"], o["internacoes"]) for o in ti.fluxo_da_cidade(sem_tabela, "RIO_CLARO", 3543907)["origens"]] == [("Santa Gertrudes", 7)]
    print("[OK] cidades de origem: 7 cidades somam as 32 internações de fora; <5 viram 'outras'; leitura cita as 3 maiores sem causa")

    # ---- posição das cidades de origem (mapa) ----
    import localizacao as loc
    tabela_pos = pd.DataFrame({"nome": ["Rio Claro", "Santa Gertrudes", "Itirapina", "Ipeúna"],
                               "latitude": [-22.373, -22.459, -22.253, -22.434], "longitude": [-47.580, -47.527, -47.822, -47.716]})
    tabela_pos["chave"] = tabela_pos["nome"].map(loc.ent.normalizar)
    centro_o, pts_o, sem_o = loc.pontos_origens(principais + [("Cidade fantasma", 3)], tabela_pos, "Rio Claro")
    assert centro_o == (-22.373, -47.580)
    assert list(pts_o["nome"]) == ["Santa Gertrudes", "Itirapina", "Ipeúna"] and list(pts_o["internacoes"]) == [14, 6, 5]
    assert sem_o == 3  # a cidade que não está na tabela não ganha ponto inventado: só é contada
    sem_tab = loc.pontos_origens(principais, loc.carregar_localizacao(sqlite3.connect(":memory:")), "Rio Claro")
    assert sem_tab[0] is None and sem_tab[1].empty and sem_tab[2] == 25  # sem a tabela: nenhum ponto, tudo "sem posição"
    assert loc.pontos_origens(principais, None, "Rio Claro")[0] is None
    assert loc.pontos_origens(principais, tabela_pos, "Cidade Sem Posição")[0] is None  # sem o centro da cidade, sem mapa
    print("[OK] mapa das cidades de origem: ponto só para quem está na tabela; sem tabela ou sem centro não desenha nada")

    # ---- textos: descrevem, não explicam ----
    textos = (ti.leitura_fluxo(mama, ev.reset_index()) + ti.leitura_fluxo(todos_c, None)
              + ti.leitura_cidade(info, "Rio Claro"))
    junto = " ".join(textos).lower()
    for proibido in ("porque", "devido", "por causa", "em razão", "r$"):
        assert proibido not in junto, proibido
    assert "internações, não pessoas" in junto and "só enxerga hospitais de sp" in junto
    assert "minas gerais" in junto and "barretos" in junto and "campinas (10)" in junto
    assert "diferença: -8 (mais saíram do que entraram)" in junto, junto
    assert "2 internações de mulheres de fora da cidade foram atendidas" in junto
    assert "10 internações de moradoras foram em hospitais de outras cidades" in junto
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


# --- sem o dado de onde as moradoras são atendidas: a leitura diz que não existe ---
def _teste_sem_destino():
    info = {"atendimentos": 10, "da_cidade": 4, "outras_cidades": 6, "outros_estados": 0, "moradoras": 0,
            "moradoras_na_cidade": 0, "moradoras_fora": 0, "destinos": [], "moradoras_sem_hospital": 7}
    texto = " ".join(leitura_cidade(info, "Teste"))
    assert "Não há como dizer onde as moradoras de Teste foram atendidas" in texto, texto
    info["moradoras_sem_hospital"] = 0
    assert "não existe o dado" in " ".join(leitura_cidade(info, "Teste"))


try:
    _teste_sem_destino()
    print("OK sem destino das moradoras")
except NameError:
    from inteligencia import leitura_cidade
    _teste_sem_destino()
    print("OK sem destino das moradoras")
