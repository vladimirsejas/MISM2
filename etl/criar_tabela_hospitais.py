import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import date

# =====================================
# TABELA DE HOSPITAIS (CNES -> nome)
#
# O SIH/SUS traz só o NÚMERO do CNES do hospital; o arquivo de
# estabelecimentos do CNES também não tem o nome. O nome vem da API de
# dados abertos do Ministério da Saúde (conferida em 08/10/2026: devolve
# nome_fantasia e nome_razao_social para o número do CNES).
#
# Lê os CNES que já estão em `internacoes`, consulta só os que ainda não
# estão na tabela `hospitais` e grava aos poucos (se der erro no meio,
# o que já veio fica; é só rodar de novo). Não apaga nem troca nome já
# gravado e não mexe em `internacoes`.
#
# Rodar depois da carga:  py etl\criar_tabela_hospitais.py
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos/{cnes}"
TENTATIVAS = 3
ESPERA = 2          # segundos; dobra a cada tentativa
PAUSA = 0.15        # entre consultas, para não sobrecarregar a API
GRAVAR_A_CADA = 25


def consultar_nome(cnes):
    """Nome do estabelecimento pela API. Devolve (nome, erro): um dos dois é None."""
    pedido = urllib.request.Request(URL.format(cnes=cnes), headers={"Accept": "application/json"})
    espera = ESPERA
    erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as resposta:
                dados = json.loads(resposta.read().decode("utf-8", errors="replace"))
            if isinstance(dados, dict):
                nome = dados.get("nome_fantasia") or dados.get("nome_razao_social")
                if nome and str(nome).strip():
                    return " ".join(str(nome).split()), None
            return None, "a API respondeu sem nome"
        except urllib.error.HTTPError as e:
            erro = f"HTTP {e.code}"
            if e.code in (400, 404):  # não existe: repetir não adianta
                return None, erro
        except Exception as e:
            erro = f"{type(e).__name__}: {e}"
        if tentativa < TENTATIVAS:
            time.sleep(espera)
            espera *= 2
    return None, erro


def cnes_do_banco(conexao):
    linhas = conexao.execute(
        "SELECT cnes, COUNT(*) FROM internacoes WHERE cnes IS NOT NULL AND TRIM(cnes) <> '' "
        "GROUP BY cnes ORDER BY COUNT(*) DESC").fetchall()
    juntos = {}  # "9601" e "0009601" são o mesmo hospital
    for c, n in linhas:
        codigo = str(c).strip().zfill(7)
        juntos[codigo] = juntos.get(codigo, 0) + n
    return sorted(juntos.items(), key=lambda item: -item[1])


def garantir_tabela(conexao):
    conexao.execute("CREATE TABLE IF NOT EXISTS hospitais ("
                    "cnes TEXT PRIMARY KEY, nome TEXT NOT NULL, fonte TEXT, consultado_em TEXT)")
    conexao.commit()


def atualizar(banco=None, consultar=None, pausa=None):
    """Consulta os CNES que faltam e grava. `consultar` existe para os testes.
    Devolve {'ja_tinha', 'gravados', 'falhas': [(cnes, erro)], 'total'}."""
    banco = banco or BANCO
    consultar = consultar or consultar_nome
    pausa = PAUSA if pausa is None else pausa
    conexao = sqlite3.connect(banco)
    try:
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(internacoes)")}
        if "cnes" not in colunas:
            raise RuntimeError("o banco não tem a coluna cnes: rode a carga de novo (py etl\\carga_todas_bases.py)")
        garantir_tabela(conexao)
        todos = cnes_do_banco(conexao)
        existentes = {linha[0] for linha in conexao.execute("SELECT cnes FROM hospitais")}
        faltam = [(c, n) for c, n in todos if c not in existentes]
        resultado = {"total": len(todos), "ja_tinha": len(todos) - len(faltam), "gravados": 0, "falhas": []}
        hoje = date.today().isoformat()
        for i, (cnes, n) in enumerate(faltam, 1):
            nome, erro = consultar(cnes)
            if nome:
                conexao.execute("INSERT OR IGNORE INTO hospitais (cnes, nome, fonte, consultado_em) VALUES (?,?,?,?)",
                                (cnes, nome, "API de dados abertos do Ministério da Saúde", hoje))
                resultado["gravados"] += 1
            else:
                resultado["falhas"].append((cnes, erro or "sem nome"))
            if i % GRAVAR_A_CADA == 0:
                conexao.commit()
                print(f"  {i} de {len(faltam)} consultados...")
            if pausa:
                time.sleep(pausa)
        conexao.commit()
        return resultado
    finally:
        conexao.close()


def main():
    if not os.path.isfile(BANCO):
        print(f"Não encontrei o banco em {BANCO}. Rode a carga primeiro (py etl\\carga_todas_bases.py).")
        return 1
    print("TABELA DE HOSPITAIS (CNES -> nome)\n")
    try:
        r = atualizar()
    except RuntimeError as erro:
        print("ERRO:", erro)
        return 1
    print(f"\nCNES no banco: {r['total']} | já tinham nome: {r['ja_tinha']} | gravados agora: {r['gravados']} "
          f"| sem nome: {len(r['falhas'])}")
    for cnes, erro in r["falhas"][:20]:
        print(f"  CNES {cnes}: {erro}")
    if r["falhas"]:
        print("\nOs que ficaram sem nome aparecem no painel só com o número. Rode de novo para tentar outra vez.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
