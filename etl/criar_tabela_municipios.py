import os
import json
import re
import sqlite3
import unicodedata
import gzip
from urllib.request import Request, urlopen

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios"


def normalizar_origem(nome, codigo_ibge):
    texto = unicodedata.normalize("NFKD", nome)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    texto = re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")
    return texto or f"MUNICIPIO_{codigo_ibge}"


def carregar_municipios_ibge():
    requisicao = Request(
        URL_IBGE,
        headers={"Accept-Encoding": "identity"},
    )
    with urlopen(requisicao, timeout=30) as resposta:
        conteudo = resposta.read()
        if resposta.headers.get("Content-Encoding", "").lower() == "gzip":
            conteudo = gzip.decompress(conteudo)
        dados = json.loads(conteudo.decode("utf-8"))

    return [
        {
            "codigo_ibge": int(item["id"]),
            "origem": normalizar_origem(item["nome"], int(item["id"])),
            "nome": item["nome"],
            "uf": "SP",
        }
        for item in dados
    ]


def atualizar():
    municipios = carregar_municipios_ibge()
    conexao = sqlite3.connect(BANCO)
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS municipios (
            codigo_ibge INTEGER PRIMARY KEY,
            origem TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            uf TEXT NOT NULL
        )
    """)

    for municipio in municipios:
        cursor.execute("""
            INSERT INTO municipios (codigo_ibge, origem, nome, uf)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(codigo_ibge) DO UPDATE SET
                origem = excluded.origem,
                nome = excluded.nome,
                uf = excluded.uf
        """, (
            municipio["codigo_ibge"],
            municipio["origem"],
            municipio["nome"],
            municipio["uf"],
        ))

    conexao.commit()

    total = cursor.execute(
        "SELECT COUNT(*) FROM municipios WHERE uf = 'SP'"
    ).fetchone()[0]

    print(f"Municípios de SP cadastrados: {total}")
    print("São Paulo:", cursor.execute(
        "SELECT codigo_ibge, origem, nome, uf FROM municipios "
        "WHERE codigo_ibge = 3550308"
    ).fetchone())
    print("Rio Claro:", cursor.execute(
        "SELECT codigo_ibge, origem, nome, uf FROM municipios "
        "WHERE codigo_ibge = 3543907"
    ).fetchone())

    conexao.close()


if __name__ == "__main__":
    atualizar()
