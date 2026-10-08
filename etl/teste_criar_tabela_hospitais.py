import os
import sqlite3
import tempfile

import criar_tabela_hospitais as hosp

# =====================================
# TESTE: TABELA DE HOSPITAIS (CNES -> nome), 10/2026
#
# Usa uma consulta falsa (sem internet). Confere:
#   1. grava o nome só dos CNES do banco, com 7 dígitos;
#   2. CNES sem resposta fica de fora e é listado como falha;
#   3. rodar de novo consulta SÓ o que faltava e não troca nome já gravado;
#   4. não mexe em `internacoes`;
#   5. banco sem a coluna cnes: erro claro (rodar a carga).
# =====================================


def banco_com(cnes_lista):
    pasta = tempfile.mkdtemp()
    caminho = os.path.join(pasta, "teste.db")
    con = sqlite3.connect(caminho)
    con.execute("CREATE TABLE internacoes (tipo_cancer TEXT, cnes TEXT)")
    con.executemany("INSERT INTO internacoes VALUES ('MAMA', ?)", [(c,) for c in cnes_lista])
    con.commit()
    con.close()
    return caminho


def linhas(caminho, sql):
    con = sqlite3.connect(caminho)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def main():
    # CNES 9601 vem sem zeros (como número); 2090236 aparece 3 vezes; um vazio e um nulo não contam
    caminho = banco_com(["2090236", "2090236", "2090236", "2077590", "9601", "0009601", "", None, "1111111"])
    respostas = {"2090236": "FUNDACAO PIO XII BARRETOS", "2077590": "IBCC", "0009601": "HOSPITAL PIO XII"}
    perguntados = []

    def falsa(cnes):
        perguntados.append(cnes)
        nome = respostas.get(cnes)
        return (nome, None) if nome else (None, "HTTP 404")

    r = hosp.atualizar(caminho, consultar=falsa, pausa=0)
    assert r["total"] == 4 and r["gravados"] == 3 and r["ja_tinha"] == 0, r
    assert r["falhas"] == [("1111111", "HTTP 404")], r["falhas"]
    assert sorted(perguntados) == ["0009601", "1111111", "2077590", "2090236"], perguntados
    assert dict(linhas(caminho, "SELECT cnes, nome FROM hospitais")) == {
        "2090236": "FUNDACAO PIO XII BARRETOS", "2077590": "IBCC", "0009601": "HOSPITAL PIO XII"}
    print("[OK] grava o nome dos CNES do banco (7 dígitos, 9601 e 0009601 viram um só); o sem resposta vira falha")

    # ---- segunda rodada: só o que faltou; nome já gravado não é trocado ----
    respostas["1111111"] = "HOSPITAL NOVO"
    respostas["2090236"] = "NOME DIFERENTE QUE NAO PODE ENTRAR"
    perguntados.clear()
    r = hosp.atualizar(caminho, consultar=falsa, pausa=0)
    assert perguntados == ["1111111"], perguntados
    assert r["gravados"] == 1 and r["ja_tinha"] == 3 and r["falhas"] == [], r
    nomes = dict(linhas(caminho, "SELECT cnes, nome FROM hospitais"))
    assert nomes["1111111"] == "HOSPITAL NOVO" and nomes["2090236"] == "FUNDACAO PIO XII BARRETOS"
    print("[OK] segunda rodada consulta só o que faltava e não troca nome já gravado")

    # ---- internacoes intacta ----
    assert linhas(caminho, "SELECT COUNT(*) FROM internacoes") == [(9,)]
    print("[OK] a tabela internacoes não é alterada")

    # ---- banco antigo, sem cnes ----
    pasta = tempfile.mkdtemp()
    antigo = os.path.join(pasta, "antigo.db")
    con = sqlite3.connect(antigo)
    con.execute("CREATE TABLE internacoes (tipo_cancer TEXT)")
    con.commit()
    con.close()
    try:
        hosp.atualizar(antigo, consultar=falsa, pausa=0)
        raise AssertionError("devia recusar banco sem a coluna cnes")
    except RuntimeError as erro:
        assert "carga" in str(erro)
    print("[OK] banco sem a coluna cnes: erro claro mandando rodar a carga")

    print("\nTodas as checagens da tabela de hospitais passaram.")


if __name__ == "__main__":
    main()
