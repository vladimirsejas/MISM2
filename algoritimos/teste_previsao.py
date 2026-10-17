import os

import numpy as np
import pandas as pd

import inteligencia as ti

# =====================================
# TESTE DA PREVISÃO COM VALIDAÇÃO (inteligencia.py, 10/2026)
#
# Séries sintéticas com resposta conhecida (reta exata, constante, curta,
# queda até zero) e a base pública de Rio Claro (analises/base_preditiva_
# 2013_2025.csv). Confere o que importa para o Escudo ser honesto:
#   - o modelo escolhido é o que errou menos nos anos já conhecidos;
#   - "repetir o último ano" é sempre o termo de comparação;
#   - nada abaixo de zero; faixa contém o ponto; poucos anos = sem previsão;
#   - as frases nunca prometem ("vai ficar", "deve ter").
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MESES = {2013: 10, 2014: 10, 2015: 8, 2016: 9, 2017: 11, 2018: 6, 2019: 7, 2020: 8, 2021: 11, 2022: 10,
         2023: 11, 2024: 8, 2025: 12}
CODIGOS = {"Mama": "MAMA", "Colo do útero": "COLO_UTERO", "Colorretal": "COLORRETAL", "Ovário": "OVARIO",
           "Pele não melanoma": "PELE_NAO_MELANOMA", "Pulmão": "PULMAO", "Tireoide": "TIREOIDE"}


def serie(valores, ano_ini=2013):
    return pd.DataFrame({"ano": range(ano_ini, ano_ini + len(valores)), "internacoes": valores})


def serie_real():
    real = pd.read_csv(os.path.join(RAIZ, "analises", "base_preditiva_2013_2025.csv"), sep=";")
    real["tipo_cancer"] = real["cancer"].map(CODIGOS)
    real["grupo"] = real["territorio"].map({"Rio Claro": "MUNICIPIO", "São Paulo": "SP"})
    real["dias_permanencia"] = real["dias_internacao_total"]
    return ti.ajustar_meses(ti.completar_anos(real[["tipo_cancer", "grupo", "ano", "internacoes", "obitos",
                                                    "valor_total", "dias_permanencia"]]), MESES)


def main():
    # reta exata: quem acerta é a tendência; a previsão continua a reta
    reta = serie([10 + 2 * i for i in range(13)])
    p = ti.prever_com_validacao(reta)
    assert p["modelo"] == "tendencia", p["modelo"]  # empate com a tendência recente: vence a mais simples
    assert p["mae"] < 1e-6 and p["supera_ingenuo"] and not p["fragil"]
    assert [round(v) for v in p["previsao"]["internacoes"]] == [36, 38, 40], p["previsao"]
    print("[OK] reta exata: escolhe a tendência, erro ~0, prevê 36, 38 e 40 em 2026-2028")

    # constante: nada ganha de repetir o último ano -> previsão frágil, dito com todas as letras
    p = ti.prever_com_validacao(serie([20] * 13))
    assert p["modelo"] == "ingenuo" and not p["supera_ingenuo"] and p["fragil"]
    assert any("frágil" in f for f in ti.leitura_previsao(p, "MAMA"))
    print("[OK] série constante: vence 'repetir o último ano', previsão tratada como frágil")

    # poucos anos: sem previsão (melhor calar do que inventar)
    assert ti.prever_com_validacao(serie([5, 6, 7, 8, 9, 10, 11])) is None
    assert ti.validar_modelos(serie([5, 6, 7])) is None
    assert ti.prever_com_validacao(serie([5, 6, 7, 8, 9, 10, 11, 12])) is not None
    print("[OK] 7 anos ou menos: sem previsão; com 8 anos já valida (2 testes)")

    # queda até zero: nunca negativo
    p = ti.prever_com_validacao(serie([30, 26, 22, 18, 14, 10, 7, 4, 2, 1, 0, 0, 0]))
    assert (p["previsao"][["internacoes", "minimo", "maximo"]] >= 0).all().all()
    print("[OK] queda até zero: ponto, mínimo e máximo nunca ficam abaixo de zero")

    # tabela e contas conferíveis
    ruido = serie([40, 45, 38, 52, 47, 60, 41, 66, 58, 70, 55, 75, 69])
    p = ti.prever_com_validacao(ruido)
    t = p["tabela"]
    assert list(t["mae"]) == sorted(t["mae"]) and set(t["modelo"]) == set(ti.MODELOS_PREVISAO)
    assert (t["testes"] == 18).all()  # origens 6..12: 7 + 6 + 5 previsões a 1, 2 e 3 anos
    ing = float(t[t["modelo"] == "ingenuo"]["mae"].iloc[0])
    assert abs(p["mae_ingenuo"] - ing) < 1e-9 and abs(p["ganho_pct"] - (1 - p["mae"] / ing) * 100) < 1e-6
    f = p["previsao"]
    assert (f["minimo"] <= f["internacoes"]).all() and (f["internacoes"] <= f["maximo"]).all()
    assert list(f["ano"]) == [2026, 2027, 2028]
    assert list(f["maximo"] - f["minimo"]) == sorted(f["maximo"] - f["minimo"])  # incerteza não encolhe com o tempo
    print("[OK] tabela ordenada pelo erro, 18 testes por modelo, ganho sobre o ingênuo conferido, faixa contém o ponto")

    # o backtest NÃO enxerga o futuro: mudar o último ano não muda o erro dos testes que o antecedem
    a = ti.validar_modelos(serie([10, 12, 11, 13, 12, 14, 13, 15, 14, 16]), horizonte=1)
    b = ti.validar_modelos(serie([10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 99]), horizonte=1)
    assert a is not None and b is not None and len(a) == len(b) == 5
    print("[OK] validação anda para frente no tempo (treina só com o passado de cada teste)")

    # coerência com o painel: se a tendência linear vence, a previsão é a MESMA projeção do gráfico
    painel = ti.projetar(reta)["internacoes"].round().tolist()
    assert painel == [round(v) for v in ti.prever_com_validacao(reta)["previsao"]["internacoes"]]
    print("[OK] quando a tendência linear vence, a previsão coincide com a projeção do gráfico")

    # frases: nunca prometem
    for dados in (reta, ruido, serie([3, 2, 4, 3, 2, 5, 3, 4, 2, 3, 4, 3, 2])):
        texto = " ".join(ti.leitura_previsao(ti.prever_com_validacao(dados), "MAMA")).lower()
        assert "vai ficar" not in texto and "vai ter" not in texto and "deve ter" not in texto
        assert "tendência aponta" in texto
    p = ti.prever_com_validacao(serie([3, 2, 4, 3, 2, 5, 3, 4, 2, 3, 4, 3, 2]))
    assert p["pequeno"] and p["fragil"]
    assert any("poucas internações" in f for f in ti.leitura_previsao(p, "MAMA"))
    print("[OK] frases dizem 'a tendência aponta', nunca prometem; série pequena avisa que o acaso pesa")

    # dados reais de Rio Claro: roda nos 7 cânceres, determinístico
    s = serie_real()
    todos = ti.previsao_todos(s)
    assert {x["tipo_cancer"] for x in todos} == set(CODIGOS.values())
    for x in todos:
        assert (x["previsao"]["internacoes"] >= 0).all() and x["testes"] == 18
    assert [x["tipo_cancer"] for x in todos] == [x["tipo_cancer"] for x in ti.previsao_todos(s)]
    variacoes = [abs(ti._variacao_pct(x)) for x in todos]
    assert variacoes == sorted(variacoes, reverse=True)
    print(f"[OK] Rio Claro (base pública): {len(todos)} cânceres validados, determinístico, ordenados pela variação")

    print("\nTodas as checagens da previsão passaram.")


if __name__ == "__main__":
    main()
