import os
import sqlite3
import sys
import unicodedata

# =====================================
# HOSPITAIS QUE MAIS INTERNAM CÂNCER, POR CIDADE (só lê o banco)
#
# Para descobrir o CNES REAL de um hospital sem depender de lista de terceiros: pega o município do HOSPITAL
# (`internacoes.municipio_hospital`, código IBGE de 6 dígitos), conta as internações por CNES e mostra o nome
# oficial da tabela `hospitais` (criada por etl\\criar_tabela_hospitais.py). Abre o banco em modo somente leitura.
#
# Uso:  py etl\\listar_hospitais_por_cidade.py                  (cidades padrão)
#       py etl\\listar_hospitais_por_cidade.py Barretos Jaú     (só estas)
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
CIDADES_PADRAO = ["Barretos", "Jaú", "Campinas", "Ribeirão Preto", "Botucatu", "Piracicaba", "Rio Claro", "São José dos Campos",
                  "Sorocaba", "Santos", "São José do Rio Preto", "Bauru", "Marília", "Presidente Prudente", "Araçatuba",
                  "Araraquara", "São Carlos", "Franca", "Limeira", "Jales"]
POR_CIDADE = 5


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto).lower()) if not unicodedata.combining(c)).strip()


def listar(banco, cidades, por_cidade=POR_CIDADE):
    """{cidade pedida: [(cnes, nome ou None, internações)]} ou None se o nome não está em municipios_localizacao."""
    conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    try:
        codigos = {sem_acento(n): c for n, c in conexao.execute("SELECT nome, codigo6 FROM municipios_localizacao")}
        tem_nomes = bool(conexao.execute("SELECT name FROM sqlite_master WHERE name='hospitais'").fetchone())
        saida = {}
        for cidade in cidades:
            codigo = codigos.get(sem_acento(cidade))
            if codigo is None:
                saida[cidade] = None
                continue
            linhas = conexao.execute(
                "SELECT cnes, COUNT(*) FROM internacoes WHERE municipio_hospital = ? AND cnes IS NOT NULL "
                "GROUP BY cnes ORDER BY COUNT(*) DESC LIMIT ?", (codigo, por_cidade)).fetchall()
            nomes = {}
            if tem_nomes and linhas:
                nomes = dict(conexao.execute(
                    f"SELECT cnes, nome FROM hospitais WHERE cnes IN ({','.join('?' * len(linhas))})", [c for c, _ in linhas]))
            saida[cidade] = [(c, nomes.get(c), n) for c, n in linhas]
        return saida
    finally:
        conexao.close()


def main(argv=None, banco=BANCO):
    cidades = (argv if argv is not None else sys.argv[1:]) or CIDADES_PADRAO
    if not os.path.exists(banco):
        print(f"Banco não encontrado em {banco}.")
        return 1
    try:
        resultado = listar(banco, cidades)
    except sqlite3.Error as e:
        print(f"Não consegui ler o banco: {e}. A tabela municipios_localizacao e as colunas cnes/municipio_hospital precisam existir.")
        return 1
    for cidade, linhas in resultado.items():
        print(f"\n{cidade}")
        if linhas is None:
            print("   (nome não encontrado em municipios_localizacao; confira a grafia)")
        elif not linhas:
            print("   (nenhuma internação por câncer com hospital nesta cidade)")
        for cnes, nome, n in linhas or []:
            print(f"   {cnes}  {n:>7} internações  {nome or '(nome ainda não está na tabela hospitais)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
