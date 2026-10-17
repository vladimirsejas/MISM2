import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request

# =====================================
# BAIXAR A POPULAÇÃO DE MULHERES POR MUNICÍPIO (IBGE, Censo 2022) -- rodar no computador do autor
#
# Por que: sem a população não existe taxa por 100 mil mulheres nem ranking proporcional entre cidades (a pergunta que a Lia não
# soube responder no teste com pessoa). Fonte oficial: API de agregados do IBGE, tabela 9514 do Censo 2022 (população residente
# por sexo e idade), variável 93, municípios de SP. Os códigos de sexo e idade NÃO ficam fixos no script: ele lê os metadados da
# tabela e escolhe as categorias pelo nome ("Mulheres" e "Total"), então não depende de código decorado.
#
# Grava a tabela `populacao_mulheres` (codigo_ibge, municipio, ano, populacao, fonte) no banco; não mexe em mais nada.
#
# Uso (da pasta do projeto):
#   py etl\baixar_populacao.py                 baixa e grava
#   py etl\baixar_populacao.py --reconhecer    só mostra as classificações da tabela (não grava)
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
AGREGADO, VARIAVEL, PERIODO, UF_SP = "9514", "93", "2022", "35"
RIO_CLARO = "3543907"
FONTE = "IBGE, Censo 2022, tabela 9514 (população residente, mulheres)"


def obter_json(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": "EscudoFeminino/1.0 (trabalho academico)"})
    with urllib.request.urlopen(pedido, timeout=120) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def escolher_categorias(meta):
    """'2[5]|286[113635]|287[6653]': Sexo = Mulheres; qualquer outra classificação = Total. Se não achar, diz o que existe."""
    partes = []
    for classificacao in meta["classificacoes"]:
        categorias = classificacao["categorias"]
        quer = "mulheres" if "sexo" in classificacao["nome"].lower() else "total"
        achadas = [c for c in categorias if c["nome"].strip().lower() == quer]
        if not achadas:
            existentes = [c["nome"] for c in categorias][:15]
            raise ValueError(f"classificação '{classificacao['nome']}': não achei a categoria '{quer}'. Existem: {existentes}")
        partes.append(f"{classificacao['id']}[{achadas[0]['id']}]")
    return "|".join(partes)


def extrair(dados, periodo=PERIODO):
    """[(codigo_ibge, município, população)] da resposta da API; ignora valores que não são número ('-', '...')."""
    linhas = []
    for variavel in dados:
        for resultado in variavel["resultados"]:
            for serie in resultado["series"]:
                try:
                    populacao = int(serie["serie"].get(periodo))
                except (TypeError, ValueError):
                    continue
                local = serie["localidade"]
                linhas.append((str(local["id"]), local["nome"].rsplit(" - ", 1)[0], populacao))
    return linhas


def gravar(linhas, banco=BANCO):
    conn = sqlite3.connect(banco)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS populacao_mulheres (
            codigo_ibge TEXT, municipio TEXT, ano INTEGER, populacao INTEGER, fonte TEXT, PRIMARY KEY (codigo_ibge, ano))""")
        conn.executemany("INSERT OR REPLACE INTO populacao_mulheres VALUES (?, ?, ?, ?, ?)",
                         [(c, n, int(PERIODO), p, FONTE) for c, n, p in linhas])
        conn.commit()
    finally:
        conn.close()


def main(obter=obter_json, banco=BANCO, so_reconhecer=None):
    if so_reconhecer is None:
        so_reconhecer = "--reconhecer" in sys.argv
    print(f"POPULAÇÃO DE MULHERES POR MUNICÍPIO (IBGE, Censo {PERIODO}, tabela {AGREGADO})")
    meta = obter(f"{BASE}/{AGREGADO}/metadados")
    print("Classificações da tabela: " + "; ".join(
        f"{c['nome']} ({len(c['categorias'])} categorias)" for c in meta["classificacoes"]))
    classificacao = escolher_categorias(meta)
    print(f"Categorias escolhidas pelo nome: {classificacao}")
    if so_reconhecer:
        print("(modo --reconhecer: nada foi baixado nem gravado)")
        return None
    consulta = f"localidades=N6[N3[{UF_SP}]]&classificacao={classificacao}"
    url = f"{BASE}/{AGREGADO}/periodos/{PERIODO}/variaveis/{VARIAVEL}?" + urllib.parse.quote(consulta, safe="[]|=&,")
    linhas = extrair(obter(url))
    if len(linhas) < 600:
        raise SystemExit(f"Só {len(linhas)} municípios vieram (SP tem 645). Não gravei nada; cole esta mensagem no chat.")
    rio = [p for c, _, p in linhas if c == RIO_CLARO]
    if not rio or not 50_000 < rio[0] < 200_000:
        raise SystemExit(f"Rio Claro ({RIO_CLARO}) veio como {rio}: fora do esperado (50 a 200 mil mulheres). Não gravei nada.")
    gravar(linhas, banco)
    print(f"OK: {len(linhas)} municípios gravados em populacao_mulheres. Rio Claro: {rio[0]:,} mulheres.".replace(",", "."))
    print(f"Total de mulheres em SP: {sum(p for _, _, p in linhas):,}.".replace(",", "."))
    return linhas


if __name__ == "__main__":
    main()
