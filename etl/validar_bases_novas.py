import os
import sqlite3
import sys

# =====================================
# CONFERÊNCIA DAS BASES NOVAS (população, centros, SIA, SIM, CNES) -- só LÊ o banco, não baixa nada, roda em segundos
#
# Mostra, em texto curto, o que entrou em cada tabela e confere o que dá para conferir sem a fonte: se os códigos de raça/cor parecem
# trocados (parda deve ser maior que amarela), se há anos faltando, quanto Rio Claro tem. Cole a saída no chat.
# Uso:  py etl\validar_bases_novas.py
# =====================================

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
RIO_CLARO6 = "354390"
RACA_SIA = {"01": "branca", "02": "preta", "03": "parda", "04": "amarela", "05": "indígena", "99": "sem informação"}
RACA_SIM = {"1": "branca", "2": "preta", "3": "amarela", "4": "parda", "5": "indígena", "": "sem informação", "sem_info": "sem informação"}
LOCAL_SIM = {"1": "hospital", "2": "outro serviço de saúde", "3": "casa", "4": "via pública", "5": "outro", "9": "ignorado", "sem_info": "ignorado"}


def tem(conn, tabela):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone() is not None


def linhas(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def pct(parte, total):
    return f"{parte / total * 100:.1f}%" if total else "-"


def titulo(texto):
    print("\n" + "=" * 70 + f"\n{texto}\n" + "=" * 70)


def conferir_raca(conn, tabela, coluna_valor, nomes, parda, amarela):
    dist = dict(linhas(conn, f"SELECT {coluna_valor.split(',')[0]}, SUM({coluna_valor.split(',')[1]}) FROM {tabela} GROUP BY 1"))
    total = sum(dist.values())
    print("  raça/cor (estado): " + ", ".join(f"{nomes.get(str(k).strip(), 'código ' + str(k))} {pct(v, total)}" for k, v in
                                              sorted(dist.items(), key=lambda kv: -kv[1])[:7]))
    p, a = dist.get(parda, 0), dist.get(amarela, 0)
    if p < a:
        print(f"  ATENÇÃO: o código {parda} (parda) é MENOR que o {amarela} (amarela). Mapeamento de raça/cor provavelmente trocado.")
    else:
        print(f"  ok: parda ({pct(p, total)}) maior que amarela ({pct(a, total)}), como esperado em SP.")


def main(banco=BANCO):
    if not os.path.exists(banco):
        print(f"Banco não encontrado: {banco}")
        return 1
    conn = sqlite3.connect(f"file:{banco}?mode=ro", uri=True, timeout=60)
    try:
        titulo("POPULAÇÃO DE MULHERES (IBGE)")
        if tem(conn, "populacao_mulheres"):
            n, total = linhas(conn, "SELECT COUNT(*), SUM(populacao) FROM populacao_mulheres")[0]
            rio = linhas(conn, "SELECT populacao FROM populacao_mulheres WHERE substr(CAST(codigo_ibge AS TEXT),1,6)=?", (RIO_CLARO6,))
            print(f"  {n} municípios; {total:,} mulheres no total; Rio Claro: {rio[0][0]:,}".replace(",", ".") if rio else f"  {n} municípios; Rio Claro ausente!")
        else:
            print("  tabela ausente (rode: py -3.12 etl\\carregar_tudo_pysus.py --so populacao)")

        titulo("CENTRO DOS MUNICÍPIOS")
        if tem(conn, "municipios_localizacao"):
            print(f"  {linhas(conn, 'SELECT COUNT(*) FROM municipios_localizacao')[0][0]} municípios com latitude/longitude")
        else:
            print("  tabela ausente (rode: py -3.12 etl\\carregar_tudo_pysus.py --so geo)")

        titulo("QUIMIO E RADIO AMBULATORIAIS (SIA)")
        if tem(conn, "oncologia_ambulatorial"):
            for mod, ano_min, ano_max, anos, apacs in linhas(conn, "SELECT modalidade, MIN(ano), MAX(ano), COUNT(DISTINCT ano), SUM(apacs) "
                                                                    "FROM oncologia_ambulatorial GROUP BY modalidade"):
                print(f"  {mod}: {ano_min}-{ano_max} ({anos} anos), {apacs:,} APACs de mulheres".replace(",", "."))
            anos = {r[0] for r in linhas(conn, "SELECT DISTINCT ano FROM oncologia_ambulatorial")}
            falta = [a for a in range(2013, 2026) if a not in anos]
            print("  anos que NÃO entraram: " + (", ".join(map(str, falta)) if falta else "nenhum"))
            print("  por câncer: " + ", ".join(f"{c}={n:,}".replace(",", ".") for c, n in
                                               linhas(conn, "SELECT tipo_cancer, SUM(apacs) FROM oncologia_ambulatorial GROUP BY 1 ORDER BY 2 DESC")))
            rio = linhas(conn, "SELECT modalidade, ano, SUM(apacs) FROM oncologia_ambulatorial WHERE substr(codigo_residencia,1,6)=? "
                               "GROUP BY 1,2 ORDER BY 1,2", (RIO_CLARO6,))
            por_mod = {}
            for m, a, n in rio:
                por_mod.setdefault(m, []).append(f"{a}:{n}")
            for m, itens in por_mod.items():
                print(f"  Rio Claro {m} (APACs por ano): " + " ".join(itens))
            conferir_raca(conn, "oncologia_ambulatorial", "raca_cor,apacs", RACA_SIA, "03", "04")
            est = linhas(conn, "SELECT estadiamento, SUM(apacs) FROM oncologia_ambulatorial GROUP BY 1 ORDER BY 2 DESC LIMIT 8")
            print("  estadiamento (código=APACs): " + ", ".join(f"{e or 'vazio'}={n:,}".replace(",", ".") for e, n in est))
            faixas = linhas(conn, "SELECT faixa, SUM(apacs) FROM oncologia_ambulatorial GROUP BY 1 ORDER BY 2 DESC")
            print("  faixa etária: " + ", ".join(f"{f}={n:,}".replace(",", ".") for f, n in faixas))
        else:
            print("  tabela ausente (rode: py -3.12 etl\\carregar_tudo_pysus.py --so sia)")

        titulo("MORTALIDADE REAL (SIM)")
        if tem(conn, "obitos_sim"):
            anos = linhas(conn, "SELECT ano, SUM(obitos) FROM obitos_sim GROUP BY ano ORDER BY ano")
            print("  óbitos de mulheres pelos 7 cânceres, por ano: " + " ".join(f"{a}:{n:,}".replace(",", ".") for a, n in anos))
            so_sp = linhas(conn, "SELECT ano, SUM(obitos) FROM obitos_sim WHERE substr(codigo_residencia,1,2)='35' GROUP BY ano ORDER BY ano")
            print("  só moradoras de SP (a base de comparação entre anos; o DOSP de 2013-2024 também tem moradoras de outros estados): "
                  + " ".join(f"{a}:{n:,}".replace(",", ".") for a, n in so_sp))
            falta = [a for a in range(2013, 2025) if a not in {x for x, _ in anos}]   # 2025 em diante o SIM só existe como Mortalidade_Geral (outro formato)
            print("  anos que NÃO entraram: " + (", ".join(map(str, falta)) if falta else "nenhum"))
            if tem(conn, "obitos_sim_fonte"):   # de qual arquivo veio cada ano e quantos meses têm óbito
                fontes = linhas(conn, "SELECT ano, arquivo, meses FROM obitos_sim_fonte ORDER BY ano")
                print("  fonte por ano: " + ", ".join(f"{a}:{arq}{'' if m is None or m >= 12 else f' ({m} meses)'}" for a, arq, m in fontes))
            print("  por câncer: " + ", ".join(f"{c}={n:,}".replace(",", ".") for c, n in
                                               linhas(conn, "SELECT tipo_cancer, SUM(obitos) FROM obitos_sim GROUP BY 1 ORDER BY 2 DESC")))
            loc = dict(linhas(conn, "SELECT local_obito, SUM(obitos) FROM obitos_sim GROUP BY 1"))
            tot = sum(loc.values())
            print("  onde ocorreram: " + ", ".join(f"{LOCAL_SIM.get(str(k), 'código ' + str(k))} {pct(v, tot)}" for k, v in
                                                   sorted(loc.items(), key=lambda kv: -kv[1])))
            rio = linhas(conn, "SELECT ano, SUM(obitos) FROM obitos_sim WHERE substr(codigo_residencia,1,6)=? GROUP BY ano ORDER BY ano", (RIO_CLARO6,))
            print("  Rio Claro (óbitos por ano): " + " ".join(f"{a}:{n}" for a, n in rio))
            conferir_raca(conn, "obitos_sim", "raca_cor,obitos", RACA_SIM, "4", "3")
            if tem(conn, "internacoes"):
                sih = linhas(conn, "SELECT ano, SUM(obito) FROM internacoes WHERE origem='SP' AND municipio='RIO_CLARO' GROUP BY ano ORDER BY ano")
                print("  para comparar, óbitos NA INTERNAÇÃO (SIH) de Rio Claro por ano: " + " ".join(f"{a}:{n}" for a, n in sih))
        else:
            print("  tabela ausente (rode: py -3.12 etl\\carregar_tudo_pysus.py --so sim)")

        titulo("CAPACIDADE (CNES)")
        for tabela, rotulo in (("cnes_equipamentos", "equipamentos"), ("cnes_leitos", "leitos")):
            if tem(conn, tabela):
                n, a0, a1 = linhas(conn, f"SELECT COUNT(*), MIN(ano), MAX(ano) FROM {tabela}")[0]
                print(f"  {rotulo}: {n} linhas, anos {a0}-{a1}")
            else:
                print(f"  {rotulo}: tabela ausente (rode: py -3.12 etl\\carregar_tudo_pysus.py --so cnes)")
    finally:
        conn.close()
    print("\nCole TUDO isto no chat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
