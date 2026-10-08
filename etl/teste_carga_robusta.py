import os
import sqlite3
import tempfile

import carga_todas_bases as carga

# =====================================
# TESTE: UM ARQUIVO COM PROBLEMA NÃO DERRUBA A CARGA
#
# Em 24/09/2026 o banco do autor ficou só com colo do útero: a carga
# antiga apagava a tabela no 1º arquivo e parava no 2º que desse erro.
# Este teste roda carregar() de verdade, com CSVs e banco temporários:
#   - colorretal com coluna faltando fica de fora, com o motivo, e os
#     outros cânceres entram mesmo assim;
#   - o banco anterior é copiado antes da troca;
#   - poucos códigos de município fora do catálogo ficam de fora com
#     aviso; se nenhum arquivo servir, o banco antigo fica intacto.
# =====================================

BOM = "ANO_CMPT;MES_CMPT;IDADE;DIAS_PERM;MORTE;VAL_TOT;MUNIC_RES\n"


def escrever(base, pasta, texto):
    os.makedirs(os.path.join(base, pasta))
    with open(os.path.join(base, pasta, "dados.csv"), "w", encoding="latin1") as arquivo:
        arquivo.write(texto)


def banco_com_catalogo(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.execute("CREATE TABLE municipios (codigo_ibge INTEGER, origem TEXT, nome TEXT, uf TEXT)")
    conexao.execute("INSERT INTO municipios VALUES (3543907, 'RIO_CLARO', 'Rio Claro', 'SP')")
    conexao.execute("CREATE TABLE internacoes (tipo_cancer TEXT, municipio TEXT)")
    conexao.execute("INSERT INTO internacoes VALUES ('ANTIGO', 'RIO_CLARO')")
    conexao.commit()
    conexao.close()


def tipos(caminho):
    conexao = sqlite3.connect(caminho)
    try:
        return dict(conexao.execute("SELECT tipo_cancer, COUNT(*) FROM internacoes GROUP BY tipo_cancer").fetchall())
    finally:
        conexao.close()


def main():
    temporario = tempfile.mkdtemp()
    base = os.path.join(temporario, "dados")
    banco = os.path.join(temporario, "teste.db")
    banco_com_catalogo(banco)

    escrever(base, "cancer_colo_utero_sp", BOM + "2024;1;50;3;0;100.0;354390\n" * 3)
    escrever(base, "cancer_colorretal_sp", "ANO_CMPT;IDADE;MUNIC_RES\n2024;60;354390\n")  # faltam colunas
    # mama: 200 registros de Rio Claro e 1 com código fora do catálogo (0,5%)
    escrever(base, "cancer_mama_sp", BOM + "2024;2;55;4;0;200.0;354390\n" * 200 + "2024;2;55;4;0;200.0;359999\n")
    # base com muitas moradoras de outros estados (MG): não derruba o arquivo e todas entram (atendimento em SP)
    escrever(base, "cancer_pulmao_sp", BOM + "2024;3;70;5;1;300.0;354390\n" * 5 + "2024;3;70;5;1;300.0;310620\n" * 5)

    carga.BASE_DADOS, carga.BANCO = base, banco
    carga.carregar()

    contagem = tipos(banco)
    assert contagem == {"COLO_UTERO": 3, "MAMA": 200, "PULMAO": 10}, contagem
    print("[OK] colorretal com problema fica de fora; colo do útero, mama e pulmão entram (o 2º arquivo não derruba o resto)")
    print("[OK] metade de moradoras de outro estado não derruba o arquivo de pulmão: elas entram como OUTRO_ESTADO")
    assert tipos(banco[:-3] + "_antes_da_carga.db") == {"ANTIGO": 1}
    print("[OK] o banco anterior foi copiado antes da troca")
    print("[OK] 1 código fora do catálogo em 201 registros fica de fora com aviso")
    conexao = sqlite3.connect(banco)
    situacoes = dict(conexao.execute("SELECT tipo_cancer, situacao FROM carga_resultado").fetchall())
    motivo = conexao.execute("SELECT motivo FROM carga_resultado WHERE tipo_cancer = 'COLORRETAL'").fetchone()[0]
    conexao.close()
    assert situacoes["COLO_UTERO"] == "carregado" and situacoes["COLORRETAL"] == "de fora", situacoes
    assert situacoes["OVARIO"] == "sem pasta" and "faltam as colunas" in motivo, (situacoes, motivo)
    print("[OK] o resultado da carga fica gravado no banco (carga_resultado), com o motivo de cada um")

    # nenhum arquivo serve: o banco não muda
    temporario2 = tempfile.mkdtemp()
    base2 = os.path.join(temporario2, "dados")
    banco2 = os.path.join(temporario2, "teste.db")
    banco_com_catalogo(banco2)
    escrever(base2, "cancer_mama_sp", "ANO_CMPT;MUNIC_RES\n2024;354390\n")
    carga.BASE_DADOS, carga.BANCO = base2, banco2
    try:
        carga.carregar()
    except RuntimeError as erro:
        assert "NÃO foi alterado" in str(erro), erro
    else:
        raise AssertionError("sem nenhum arquivo bom a carga deveria parar")
    assert tipos(banco2) == {"ANTIGO": 1}
    print("[OK] sem nenhum arquivo bom, o banco antigo fica intacto")

    print("\nTodas as checagens da carga robusta passaram.")


if __name__ == "__main__":
    main()
