import contextlib
import io
import os
import sqlite3
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "etl"))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
import cruzar_hospitais_oncologia as c  # noqa: E402

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


# ---------- a lista oficial guardada no projeto ----------
oficiais = c.ler_oficiais()
cnes = [o["cnes"] for o in oficiais]
checar("lista oficial de SP: 88 estabelecimentos, CNES de 7 dígitos, sem repetir",
       len(oficiais) == 88 and all(x.isdigit() and len(x) == 7 for x in cnes) and len(set(cnes)) == 88)
checar("tipos conhecidos (61 UNACON, 14 CACON, 8 hospitais gerais com cirurgia, 5 serviços de radioterapia)",
       sorted((t, sum(1 for o in oficiais if o["tipo"] == t)) for t in {o["tipo"] for o in oficiais})
       == [("CACON", 14), ("Hospital geral com cirurgia oncológica", 8), ("Serviço isolado de radioterapia", 5), ("UNACON", 61)])
por_cnes = {o["cnes"]: o for o in oficiais}
checar("CNES conferidos no banco do autor (18/10/2026) batem com a lista do Ministério",
       all(x in por_cnes for x in ("6123740", "2077531", "2080125", "2080273", "2083086", "2079798", "2082187", "2090236",
                                   "7400926", "2082888")))
checar("Rio Claro: Santa Casa é UNACON (CNES 2082888)",
       por_cnes["2082888"]["municipio"] == "Rio Claro" and por_cnes["2082888"]["tipo"] == "UNACON")
checar("CNES curtos mantêm os zeros da frente (0008923, 0009369)", "0008923" in por_cnes and "0009369" in por_cnes)
checar("o catálogo do Apoio não guarda CNES fora da lista oficial", c.conferir_catalogo(oficiais) == [])
checar("o catálogo detecta CNES que não existe na lista (teste do próprio teste)",
       len(c.conferir_catalogo([o for o in oficiais if o["cnes"] != "2082888"])) == 1)

# ---------- CNES e banco sintéticos ----------
with tempfile.TemporaryDirectory() as pasta:
    pasta_cnes = os.path.join(pasta, "cnes")
    os.makedirs(pasta_cnes)
    with open(os.path.join(pasta_cnes, "tbEstabelecimento202610.csv"), "w", encoding="utf-8") as f:
        f.write("CO_CNES;NO_FANTASIA;NO_LOGRADOURO;NU_ENDERECO;NO_BAIRRO;CO_CEP;NU_TELEFONE;NU_LATITUDE;NU_LONGITUDE;CO_MOTIVO_DESAB\n")
        f.write("2082888;SANTA CASA DE RIO CLARO;RUA 2;297;CENTRO;13500000;1935357000;-22,40;-47,56;\n")
        f.write("2081458;SANTA CASA DE LIMEIRA;AV X;1;Y;13480000;19344661006122;-22,40;-47,56;\n")
        f.write("2079321;HOSPITAL GPACI;RUA Z;1;Y;18000000;1521016555;-3,10;-60,00;\n")
        f.write("0008923;CENTRO HOSPITALAR DE SANTO ANDRE;AV TESTE;10;CENTRO;09000000;1144330000;;;1\n")
        f.write("9999999;OUTRO LUGAR;RUA X;1;Y;1;1;;;\n")
    banco = os.path.join(pasta, "teste.db")
    con = sqlite3.connect(banco)
    con.execute("CREATE TABLE internacoes (cnes TEXT, municipio_hospital TEXT)")
    con.execute("CREATE TABLE municipios_localizacao (codigo6 TEXT, nome TEXT, latitude REAL, longitude REAL)")
    con.execute("INSERT INTO municipios_localizacao VALUES ('354390', 'Rio Claro', -22.373, -47.580)")
    con.execute("INSERT INTO municipios_localizacao VALUES ('354780', 'Santo André', -23.66, -46.53)")
    con.execute("CREATE TABLE hospitais (cnes TEXT, nome TEXT)")
    con.executemany("INSERT INTO internacoes VALUES (?, ?)", [("2082888", "354390")] * 5 + [("8923", "354780")] * 2
                    + [("5550874", "354390")] * 300)
    con.execute("INSERT INTO hospitais VALUES ('2082888', 'SANTA CASA DE RIO CLARO')")
    con.commit()
    con.close()

    pequeno = [o for o in oficiais if o["cnes"] in ("2082888", "0008923", "2090236", "2081458", "2079321")]
    linhas, aviso = c.cruzar(pequeno, banco, pasta_cnes)
    por = {l["cnes"]: l for l in linhas}
    checar("cruzamento: sem aviso e internações do banco por CNES", aviso == "" and por["2082888"]["internacoes_cancer"] == 5
           and por["2090236"]["internacoes_cancer"] == 0)
    checar("cruzamento: CNES curto sem zeros no banco conta (8923 = 0008923)", por["0008923"]["internacoes_cancer"] == 2)
    checar("cruzamento: endereço, telefone e coordenada do CNES",
           por["2082888"]["no_cnes"] and por["2082888"]["telefone"] == "(19) 3535-7000"
           and por["2082888"]["lat"] == -22.40 and "Rua 2, 297" in por["2082888"]["endereco"])
    checar("cruzamento: cadastro desabilitado e sem coordenada é apontado, hospital ausente do arquivo também",
           por["0008923"]["ativo_no_cnes"] is False and por["0008923"]["lat"] is None and not por["2090236"]["no_cnes"])
    fora = c.maiores_fora_da_lista(banco, {o["cnes"] for o in oficiais})
    checar("coordenada: ok perto do município, fora de SP apontada, sem coordenada marcada",
           por["2082888"]["coordenada"] == "ok" and por["2079321"]["coordenada"] == "fora de SP"
           and por["0008923"]["coordenada"] == "sem")
    checar("telefone do CNES com número colado: mostra o primeiro e o resto à parte",
           por["2081458"]["telefone"] == "(19) 3446-6100 (+ 6122)")
    checar("hospital fora da lista com muitas internações aparece", fora and fora[0][0] == "5550874" and fora[0][2] == 300)
    antes = os.path.getmtime(banco)
    saida = os.path.join(pasta, "saida", "cruzado.csv")
    with contextlib.redirect_stdout(io.StringIO()) as relatorio:
        codigo = c.main(["--salvar"], banco=banco, pasta_cnes=pasta_cnes, saida=saida)
    texto = relatorio.getvalue()
    checar("relatório traz a lista, o cadastro desabilitado e o hospital fora da lista",
           "88 estabelecimentos" in texto and "DESABILITADO" in texto and "5550874" in texto and "todos os CNES do catálogo" in texto
           and "COORDENADA SUSPEITA" in texto and "Internações por câncer no SIH em hospitais da lista oficial: 7 de 307" in texto)
    checar("main roda, grava o CSV e não altera o banco", codigo == 0 and os.path.exists(saida) and os.path.getmtime(banco) == antes)
    # sem banco e sem CNES: nada quebra
    linhas2, aviso2 = c.cruzar(pequeno, os.path.join(pasta, "nao_existe.db"), os.path.join(pasta, "nao_existe"))
    checar("sem banco e sem arquivo do CNES: segue com aviso, sem quebrar",
           len(linhas2) == 5 and "não encontrado" in aviso2 and all(l["internacoes_cancer"] is None for l in linhas2))

print("Todas as checagens passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
