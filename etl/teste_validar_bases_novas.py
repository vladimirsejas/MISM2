import io
import os
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validar_bases_novas as v  # noqa: E402

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def banco(raca_trocada=False, com_tudo=True):
    pasta = tempfile.mkdtemp()
    caminho = os.path.join(pasta, "t.db")
    c = sqlite3.connect(caminho)
    if com_tudo:
        c.execute("CREATE TABLE populacao_mulheres (codigo_ibge TEXT, municipio TEXT, ano INTEGER, populacao INTEGER, fonte TEXT)")
        c.execute("INSERT INTO populacao_mulheres VALUES ('3543907', 'Rio Claro', 2022, 106123, 't')")
        c.execute("CREATE TABLE municipios_localizacao (codigo_ibge TEXT, codigo6 TEXT, nome TEXT, uf TEXT, latitude REAL, longitude REAL, fonte TEXT)")
        c.execute("INSERT INTO municipios_localizacao VALUES ('3543907','354390','Rio Claro','SP',-22.4,-47.5,'t')")
        c.execute("""CREATE TABLE oncologia_ambulatorial (modalidade TEXT, ano INTEGER, mes INTEGER, codigo_residencia TEXT, tipo_cancer TEXT,
                     faixa TEXT, estadiamento TEXT, raca_cor TEXT, apacs INTEGER, pacientes INTEGER)""")
        parda, amarela = ("04", "03") if raca_trocada else ("03", "04")
        c.executemany("INSERT INTO oncologia_ambulatorial VALUES ('QUIMIO', 2023, 1, ?, 'MAMA', '50 a 69', '2', ?, ?, 1)",
                      [("354390", parda, 80), ("354390", amarela, 5), ("355030", "01", 100)])
        c.execute("CREATE TABLE obitos_sim (ano INTEGER, codigo_residencia TEXT, tipo_cancer TEXT, faixa TEXT, local_obito TEXT, raca_cor TEXT, obitos INTEGER)")
        c.executemany("INSERT INTO obitos_sim VALUES (2022, ?, 'MAMA', '50 a 69', ?, ?, ?)",
                      [("354390", "1", "4", 30), ("354390", "3", "3", 10), ("355030", "1", "1", 60)])
    c.commit()
    c.close()
    return caminho


def rodar(caminho):
    saida = io.StringIO()
    with redirect_stdout(saida):
        codigo = v.main(caminho)
    return codigo, saida.getvalue()


codigo, texto = rodar(banco())
checar("a conferência roda, mostra Rio Claro e os totais de cada base", codigo == 0 and "106.123" in texto and "QUIMIO" in texto
       and "óbitos de mulheres" in texto and "Rio Claro (óbitos por ano): 2022:40" in texto)
checar("raça/cor: parda maior que amarela passa sem alerta", "ok: parda" in texto and "ATENÇÃO" not in texto)
checar("diz onde os óbitos ocorreram (hospital x casa) com a tradução do código do SIM", "hospital" in texto and "casa" in texto)
codigo, texto = rodar(banco(raca_trocada=True))
checar("raça/cor trocada no SIA dispara o alerta", "ATENÇÃO" in texto and "trocado" in texto)
codigo, texto = rodar(banco(com_tudo=False))
checar("banco sem as tabelas: diz qual comando rodar, sem quebrar", codigo == 0 and "tabela ausente" in texto and "--so sia" in texto)
antes = os.path.getsize(banco(com_tudo=False))
codigo, _ = rodar("/caminho/que/nao/existe.db")
checar("banco inexistente: avisa e sai com código 1, sem criar arquivo", codigo == 1 and not os.path.exists("/caminho/que/nao/existe.db"))

# o banco nunca é alterado pela conferência (aberta só para leitura)
caminho = banco()
tempo_antes = os.path.getmtime(caminho)
rodar(caminho)
checar("a conferência só lê: o arquivo do banco não é modificado", os.path.getmtime(caminho) == tempo_antes)
print()
if falhas:
    raise SystemExit(1)
print("Todas as checagens da conferência das bases novas passaram.")
