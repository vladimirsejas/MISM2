import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baixar_populacao as bp  # noqa: E402

# Teste do ETL de população com a API do IBGE simulada (a nuvem não alcança o IBGE).

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


META = {"classificacoes": [
    {"id": "2", "nome": "Sexo", "categorias": [{"id": "4", "nome": "Homens"}, {"id": "5", "nome": "Mulheres"}, {"id": "6794", "nome": "Total"}]},
    {"id": "286", "nome": "Forma de declaração da idade", "categorias": [{"id": "113635", "nome": "Total"}, {"id": "113636", "nome": "Data de nascimento"}]},
    {"id": "287", "nome": "Idade", "categorias": [{"id": "6653", "nome": "Total"}, {"id": "93070", "nome": "0 a 4 anos"}]}]}


def dados(n=650):
    series = [{"localidade": {"id": str(3500000 + i), "nome": f"Cidade {i} - SP"}, "serie": {"2022": str(1000 + i)}} for i in range(n)]
    series.append({"localidade": {"id": bp.RIO_CLARO, "nome": "Rio Claro - SP"}, "serie": {"2022": "106123"}})
    series.append({"localidade": {"id": "3599999", "nome": "Sem dado - SP"}, "serie": {"2022": "-"}})
    return [{"resultados": [{"series": series}]}]


def falso(resposta_dados):
    chamadas = []

    def obter(url):
        chamadas.append(url)
        return META if url.endswith("/metadados") else resposta_dados
    obter.chamadas = chamadas
    return obter


def main():
    checar("categorias escolhidas pelo nome: Sexo=Mulheres e as demais =Total (sem código decorado)",
           bp.escolher_categorias(META) == "2[5]|286[113635]|287[6653]")
    try:
        bp.escolher_categorias({"classificacoes": [{"id": "2", "nome": "Sexo", "categorias": [{"id": "4", "nome": "Homens"}]}]})
        checar("categoria que não existe dá erro claro, com as que existem", False)
    except ValueError as erro:
        checar("categoria que não existe dá erro claro, com as que existem", "Homens" in str(erro) and "mulheres" in str(erro))
    linhas = bp.extrair(dados())
    checar("extrair: lê código, nome sem ' - SP' e população; ignora valor '-' (sem dado)",
           (bp.RIO_CLARO, "Rio Claro", 106123) in linhas and not any(c == "3599999" for c, _, _ in linhas) and len(linhas) == 651)
    with tempfile.TemporaryDirectory() as pasta:
        banco = os.path.join(pasta, "t.db")
        obter = falso(dados())
        bp.main(obter, banco, so_reconhecer=False)
        conn = sqlite3.connect(banco)
        total, rio = conn.execute("SELECT COUNT(*), SUM(CASE WHEN codigo_ibge=? THEN populacao END) FROM populacao_mulheres", (bp.RIO_CLARO,)).fetchone()
        conn.close()
        checar("grava a tabela populacao_mulheres com os municípios e a população de Rio Claro", total == 651 and rio == 106123)
        checar("a consulta pede só municípios de SP, variável 93 e as categorias escolhidas",
               "N6[N3[35]]" in obter.chamadas[-1] and "variaveis/93" in obter.chamadas[-1] and "2[5]" in obter.chamadas[-1])
        bp.main(falso(dados()), banco, so_reconhecer=False)
        conn = sqlite3.connect(banco)
        checar("rodar de novo não duplica (substitui)", conn.execute("SELECT COUNT(*) FROM populacao_mulheres").fetchone()[0] == 651)
        conn.close()
        banco2 = os.path.join(pasta, "r.db")
        bp.main(falso(dados()), banco2, so_reconhecer=True)
        checar("--reconhecer não grava nada", not os.path.exists(banco2))
        try:
            bp.main(falso(dados(10)), os.path.join(pasta, "x.db"), so_reconhecer=False)
            checar("poucos municípios: não grava e avisa", False)
        except SystemExit as erro:
            checar("poucos municípios: não grava e avisa", "Só 11 municípios" in str(erro) and not os.path.exists(os.path.join(pasta, "x.db")))
        ruim = dados()
        ruim[0]["resultados"][0]["series"][-2]["serie"]["2022"] = "5"
        try:
            bp.main(falso(ruim), os.path.join(pasta, "y.db"), so_reconhecer=False)
            checar("Rio Claro fora do esperado: não grava e avisa", False)
        except SystemExit as erro:
            checar("Rio Claro fora do esperado: não grava e avisa", "fora do esperado" in str(erro))
    print()
    if falhas:
        print(f"{len(falhas)} checagem(ns) falharam.")
        raise SystemExit(1)
    print("Todas as checagens da população passaram.")


if __name__ == "__main__":
    main()
