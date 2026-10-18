import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listar_hospitais_por_cidade as m

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


with tempfile.TemporaryDirectory() as pasta:
    banco = os.path.join(pasta, "t.db")
    c = sqlite3.connect(banco)
    c.execute("CREATE TABLE municipios_localizacao (codigo_ibge TEXT, codigo6 TEXT, nome TEXT, uf TEXT, latitude REAL, longitude REAL, fonte TEXT)")
    c.executemany("INSERT INTO municipios_localizacao VALUES (?,?,?,?,?,?,?)",
                  [("3505500", "350550", "Barretos", "SP", 0, 0, "t"), ("3525300", "352530", "Jaú", "SP", 0, 0, "t")])
    c.execute("CREATE TABLE internacoes (cnes TEXT, municipio_hospital TEXT)")
    c.executemany("INSERT INTO internacoes VALUES (?,?)", [("111", "350550")] * 5 + [("222", "350550")] * 2 + [("333", "352530")] * 3 + [(None, "350550")])
    c.execute("CREATE TABLE hospitais (cnes TEXT PRIMARY KEY, nome TEXT, fonte TEXT, consultado_em TEXT)")
    c.execute("INSERT INTO hospitais VALUES ('111','HOSPITAL A','t','x')")
    c.commit()
    c.close()
    r = m.listar(banco, ["Barretos", "jau", "Atlântida"])
    checar("ordena por internações e traz o nome oficial", r["Barretos"][0] == ("111", "HOSPITAL A", 5) and r["Barretos"][1] == ("222", None, 2))
    checar("ignora CNES vazio e separa por município do hospital", len(r["Barretos"]) == 2 and r["jau"] == [("333", None, 3)])
    checar("acento e maiúscula não atrapalham; cidade desconhecida vira None", r["Atlântida"] is None)
    antes = os.path.getmtime(banco)
    m.main(["Barretos"], banco=banco)
    checar("só lê: o banco não é alterado", os.path.getmtime(banco) == antes)
    try:
        sqlite3.connect(f"file:{banco}?mode=ro", uri=True).execute("INSERT INTO hospitais VALUES ('9','x','x','x')")
        escreveu = True
    except sqlite3.OperationalError:
        escreveu = False
    checar("o modo somente leitura realmente impede gravação", not escreveu)
    checar("banco inexistente: mensagem e código 1, sem quebrar", m.main(["Barretos"], banco=os.path.join(pasta, "nao.db")) == 1)
print("Todas as checagens passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
