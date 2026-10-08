import pandas as pd

import inteligencia as ti

# =====================================
# TESTE DE COMPARAR CIDADES SEM POPULAÇÃO (inteligencia.py, 10/2026)
#
# Duas cidades com números conferíveis à mão (13 anos, 2013-2025):
#   RIO:  mama 10 internações/ano (1 óbito/ano, 3 dias cada) e colo 5/ano (0 óbitos, 2 dias).
#   CAMP: mama 20/ano (4 óbitos/ano, 4 dias) e colo 20/ano (2 óbitos/ano, 3 dias), colo crescendo.
# =====================================


def serie_da_cidade(spec):
    linhas = []
    for cancer, por_ano in spec.items():
        for i, (n, obitos, dias_cada) in enumerate(por_ano):
            linhas.append((cancer, "MUNICIPIO", 2013 + i, n, obitos, 100.0 * n, dias_cada * n))
    return ti.completar_anos(pd.DataFrame(linhas, columns=[
        "tipo_cancer", "grupo", "ano", "internacoes", "obitos", "valor_total", "dias_permanencia"]))


def aprox(a, b, tol=0.05):
    return abs(a - b) <= tol


def main():
    rio = serie_da_cidade({"MAMA": [(10, 1, 3)] * 13, "COLO_UTERO": [(5, 0, 2)] * 13})
    camp = serie_da_cidade({"MAMA": [(20, 4, 4)] * 13,
                            "COLO_UTERO": [(10 + 2 * i, 2, 3) for i in range(13)]})

    a, b = ti.perfil_cidade(rio), ti.perfil_cidade(camp)
    assert a["internacoes"] == 195 and a["principal"] == "Mama" and aprox(a["pct_principal"], 66.67)
    assert aprox(a["letalidade"], 100 * 13 / 195) and aprox(a["permanencia"], (13 * 30 + 13 * 10) / 195)
    assert aprox(a["ritmo"], 0.0) and not a["poucos_casos"]
    assert b["principal"] == "Mama" or b["principal"] == "Colo do útero"
    assert b["ritmo"] > 0, b["ritmo"]  # o colo de Campinas cresce
    print("[OK] perfil: Rio 195 internações, mama 66,7%, letalidade 6,7%, permanência 2,7 dias, ritmo 0")

    tabela = ti.tabela_comparacao(a, b, "Rio Claro", "Campinas")
    assert list(tabela.columns) == ["Indicador", "Rio Claro", "Campinas"]
    assert tabela.iloc[1]["Rio Claro"] == "6,7%" and tabela.iloc[0]["Rio Claro"] == "Mama (66,7%)"
    assert "não compara tamanhos" in tabela.iloc[-1]["Indicador"]
    print("[OK] tabela: uma linha por indicador, uma coluna por cidade; o número absoluto avisa que não compara tamanhos")

    mix = ti.mix_comparacao(a, b, "Rio Claro", "Campinas")
    assert len(mix) == 4 and abs(mix[mix["cidade"] == "Rio Claro"]["pct"].sum() - 100) < 1e-6
    assert abs(mix[mix["cidade"] == "Campinas"]["pct"].sum() - 100) < 1e-6
    print("[OK] parcela de cada câncer soma 100% em cada cidade")

    texto = " ".join(ti.leitura_comparacao(a, b, "Rio Claro", "Campinas")).lower()
    assert "letalidade hospitalar é maior em campinas" in texto, texto
    assert "permanência média é maior em campinas" in texto
    assert "o tamanho não é comparável" in texto and "não explica o motivo" in texto
    assert not any(p in texto for p in ("porque", "devido", "por causa", "r$")), texto
    print("[OK] leitura: aponta onde a letalidade e a permanência são maiores, avisa que tamanho não compara, sem causa")

    parecida = ti.leitura_comparacao(a, a, "A", "B")
    assert "letalidade hospitalar é parecida" in " ".join(parecida).lower()
    print("[OK] cidades iguais: 'parecida', sem inventar diferença")

    pequena = ti.perfil_cidade(serie_da_cidade({"MAMA": [(1, 0, 2)] * 13}))
    assert pequena["poucos_casos"]
    assert "poucas internações por ano" in " ".join(ti.leitura_comparacao(pequena, a, "Pequena", "Rio Claro"))
    print("[OK] cidade com poucas internações por ano leva o aviso de acaso")

    assert ti.perfil_cidade(rio.iloc[0:0]) is None
    porte = {"A": 100, "B": 120, "C": 1000, "D": 90, "OUTRA": 0}
    assert ti.cidades_parecidas(porte, "A", 2) == ["D", "B"], ti.cidades_parecidas(porte, "A", 2)
    assert ti.cidades_parecidas(porte, "Z") == [] and "A" not in ti.cidades_parecidas(porte, "A")
    print("[OK] cidade de porte parecido: D (90) e B (120) para A (100); nunca a própria nem as vazias")

    print("\nTodas as checagens de comparar cidades passaram.")


if __name__ == "__main__":
    main()
