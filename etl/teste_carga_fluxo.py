import os
import sqlite3
import tempfile

import carga_todas_bases as carga

# =====================================
# TESTE: A CARGA GUARDA O FLUXO DE PACIENTES (10/2026)
#
# De onde a paciente vem (UF de residência) e onde foi atendida (município
# do hospital, CNES, caráter da internação). Roda carregar() de verdade, com
# CSVs e banco temporários:
#   1. arquivo com MUNIC_MOV, CNES e CAR_INT: as colunas novas saem certas
#      (UF pelo código, hospital com 6 dígitos, CNES com 7, caráter com 2);
#   2. arquivo sem essas colunas: carga normal, colunas novas vazias, com aviso;
#   3. UM código de município inválido no meio de centenas: não pode derrubar
#      o arquivo (antes, o .map virava decimal e nenhum código achava o catálogo);
#   4. nada que identifique alguém (CEP, nascimento, nº da AIH) vai para o banco.
# =====================================

CABECALHO = "ANO_CMPT;MES_CMPT;IDADE;DIAS_PERM;MORTE;VAL_TOT;MUNIC_RES;MUNIC_MOV;CNES;CAR_INT;CEP;NASC;N_AIH\n"
CABECALHO_SEM_FLUXO = "ANO_CMPT;MES_CMPT;IDADE;DIAS_PERM;MORTE;VAL_TOT;MUNIC_RES\n"


def escrever(base, pasta, texto):
    os.makedirs(os.path.join(base, pasta))
    with open(os.path.join(base, pasta, "dados.csv"), "w", encoding="latin1") as arquivo:
        arquivo.write(texto)


def banco_com_catalogo(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.execute("CREATE TABLE municipios (codigo_ibge INTEGER, origem TEXT, nome TEXT, uf TEXT)")
    conexao.execute("INSERT INTO municipios VALUES (3543907, 'RIO_CLARO', 'Rio Claro', 'SP')")
    conexao.execute("INSERT INTO municipios VALUES (3509502, 'CAMPINAS', 'Campinas', 'SP')")
    conexao.execute("CREATE TABLE internacoes (tipo_cancer TEXT, municipio TEXT)")
    conexao.commit()
    conexao.close()


def linhas(caminho, sql):
    conexao = sqlite3.connect(caminho)
    try:
        return conexao.execute(sql).fetchall()
    finally:
        conexao.close()


def main():
    # ---- 1 e 4: colunas do fluxo preenchidas ----
    temporario = tempfile.mkdtemp()
    base, banco = os.path.join(temporario, "dados"), os.path.join(temporario, "teste.db")
    banco_com_catalogo(banco)
    escrever(base, "cancer_mama_sp",
             CABECALHO
             + "2024;1;50;3;0;100.0;354390;354390;2082888;1;13500000;19700101;1111\n"   # Rio Claro, tratada em Rio Claro
             + "2024;2;60;4;0;100.0;354390;350950;2079798;02;13500001;19600101;2222\n"  # Rio Claro, tratada em Campinas
             + "2024;3;55;5;1;100.0;310620;350550;2090236;1;30000000;19650101;3333\n"   # Belo Horizonte (MG), tratada em Barretos
             + "2024;4;45;2;0;100.0;3509502;3543907;2082888.0;1;13000000;19750101;4444\n")  # Campinas (7 dígitos) em Rio Claro
    carga.BASE_DADOS, carga.BANCO = base, banco
    carga.carregar()

    colunas = [linha[1] for linha in linhas(banco, "PRAGMA table_info(internacoes)")]
    for coluna in ("uf_residencia", "municipio_hospital", "cnes", "car_int"):
        assert coluna in colunas, (coluna, colunas)
    for proibida in ("cep", "nasc", "n_aih", "CEP", "NASC", "N_AIH"):
        assert proibida not in colunas, f"{proibida} não pode ir para o banco"
    dados = linhas(banco, "SELECT municipio, uf_residencia, municipio_hospital, cnes, car_int "
                          "FROM internacoes ORDER BY mes")
    assert dados == [
        ("RIO_CLARO", "SP", "354390", "2082888", "01"),
        ("RIO_CLARO", "SP", "350950", "2079798", "02"),
        ("OUTRO_ESTADO", "MG", "350550", "2090236", "01"),
        ("CAMPINAS", "SP", "354390", "2082888", "01"),
    ], dados
    print("[OK] UF pelo código, hospital com 6 dígitos, CNES com 7, caráter com 2; MG entra como OUTRO_ESTADO")
    print("[OK] CEP, nascimento e número da AIH não vão para o banco")

    # ---- 2: sem as colunas do fluxo ----
    temporario2 = tempfile.mkdtemp()
    base2, banco2 = os.path.join(temporario2, "dados"), os.path.join(temporario2, "teste.db")
    banco_com_catalogo(banco2)
    escrever(base2, "cancer_mama_sp", CABECALHO_SEM_FLUXO + "2024;1;50;3;0;100.0;354390\n" * 3)
    carga.BASE_DADOS, carga.BANCO = base2, banco2
    carga.carregar()
    dados2 = linhas(banco2, "SELECT uf_residencia, municipio_hospital, cnes, car_int FROM internacoes")
    assert dados2 == [("SP", None, None, None)] * 3, dados2
    print("[OK] arquivo sem MUNIC_MOV/CNES/CAR_INT: carga normal, colunas do hospital vazias (com aviso)")

    # ---- 3: um código inválido no meio ----
    temporario3 = tempfile.mkdtemp()
    base3, banco3 = os.path.join(temporario3, "dados"), os.path.join(temporario3, "teste.db")
    banco_com_catalogo(banco3)
    escrever(base3, "cancer_mama_sp",
             CABECALHO_SEM_FLUXO + "2024;1;50;3;0;100.0;354390\n" * 300 + "2024;1;50;3;0;100.0;abc\n")
    carga.BASE_DADOS, carga.BANCO = base3, banco3
    carga.carregar()
    total, codigos = linhas(banco3, "SELECT COUNT(*), COUNT(DISTINCT codigo_ibge) FROM internacoes")[0]
    assert total == 300 and codigos == 1, (total, codigos)
    assert linhas(banco3, "SELECT typeof(codigo_ibge) FROM internacoes LIMIT 1") == [("integer",)]
    print("[OK] um código inválido entre 301 registros fica de fora, e os outros 300 entram (códigos continuam inteiros)")

    print("\nTodas as checagens da carga do fluxo passaram.")


if __name__ == "__main__":
    main()
