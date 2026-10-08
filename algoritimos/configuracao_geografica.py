import os
import sqlite3


RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")

MUNICIPIO_PADRAO = "RIO_CLARO"
UF_REFERENCIA = "SP"


def _conectar():
    return sqlite3.connect(BANCO)


def _buscar_origem_por_codigo_ibge(codigo_ibge):

    conexao = _conectar()

    try:
        linha = conexao.execute(
            "SELECT origem FROM municipios WHERE codigo_ibge = ?",
            (codigo_ibge,)
        ).fetchone()

        return linha[0] if linha else None

    except sqlite3.OperationalError:
        # tabela municipios ainda não existe -- bancos criados antes
        # dessa camada territorial continuam funcionando normalmente
        return None

    finally:
        conexao.close()


def obter_municipio():
    """
    Retorna o identificador interno do município selecionado -- o
    mesmo valor usado na coluna internacoes.origem (ex.: 'RIO_CLARO').

    Configurável via variável de ambiente ESCUDO_MUNICIPIO com esse
    identificador OU com o código IBGE do município (ex.: '3543907'),
    resolvido automaticamente pela tabela municipios. Se o código
    IBGE não for encontrado no catálogo, cai no município padrão.
    """

    valor = os.getenv("ESCUDO_MUNICIPIO", MUNICIPIO_PADRAO).strip()

    if valor.isdigit():
        origem = _buscar_origem_por_codigo_ibge(int(valor))
        return (origem or MUNICIPIO_PADRAO).upper()

    return valor.upper()


def _buscar_metadados_municipio(origem=None):

    origem = origem or obter_municipio()

    conexao = _conectar()

    try:
        return conexao.execute(
            "SELECT codigo_ibge, nome, uf FROM municipios WHERE origem = ?",
            (origem,)
        ).fetchone()

    except sqlite3.OperationalError:
        return None

    finally:
        conexao.close()


def obter_codigo_ibge():
    """Código IBGE do município selecionado, ou None se não cadastrado."""

    linha = _buscar_metadados_municipio()

    return linha[0] if linha else None


def obter_nome_municipio():
    """
    Nome do município para apresentação (ex.: 'Rio Claro'). Se ainda
    não estiver cadastrado em `municipios`, deriva um nome legível a
    partir do identificador interno como fallback.
    """

    linha = _buscar_metadados_municipio()

    if linha:
        return linha[1]

    return obter_municipio().replace("_", " ").title()


def obter_uf():
    """UF do município selecionado, ou UF_REFERENCIA como fallback."""

    linha = _buscar_metadados_municipio()

    return linha[2] if linha else UF_REFERENCIA


def listar_municipios_disponiveis():
    """
    Municípios que existem tanto no catálogo `municipios` quanto com
    dados já carregados em `internacoes` -- ou seja, os que podem
    realmente ser selecionados hoje. Vem do banco, nunca de uma lista
    fixa no código.
    """

    conexao = _conectar()

    try:
        linhas = conexao.execute("""
            SELECT DISTINCT
                m.codigo_ibge, m.origem, m.nome, m.uf
            FROM municipios AS m
            INNER JOIN internacoes AS i
                ON i.municipio = m.origem
            WHERE m.uf = ?
            ORDER BY m.nome
        """, (UF_REFERENCIA,)).fetchall()

        return [
            {
                "codigo_ibge": linha[0],
                "origem": linha[1],
                "nome": linha[2],
                "uf": linha[3]
            }
            for linha in linhas
        ]

    except sqlite3.OperationalError:
        return []

    finally:
        conexao.close()
