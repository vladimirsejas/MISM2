"""Testes da avaliação aninhada e da ausência de vazamento temporal."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import inteligencia as ti
import teste_previsao as tp
from avaliacao_aninhada import avaliar_janela, resumo_por_serie, teste_sinais_pareado


def test_janelas_reproduzem_totais_de_referencia():
    real = tp.serie_real()
    referencias = {8: (70, 25, 19, 26), 10: (42, 7, 14, 21)}
    for janela, esperado in referencias.items():
        r = avaliar_janela(real, janela)
        obtido = (
            len(r),
            int((r.diferenca_erro < -1e-9).sum()),
            int((r.diferenca_erro.abs() <= 1e-9).sum()),
            int((r.diferenca_erro > 1e-9).sum()),
        )
        assert obtido == esperado


def test_futuro_nao_altera_modelo_ou_previsao():
    real = tp.serie_real()
    total = 0
    for grupo in sorted(real.grupo.dropna().unique()):
        for cancer in sorted(real.tipo_cancer.dropna().unique()):
            d = real[(real.grupo == grupo) & (real.tipo_cancer == cancer)].sort_values("ano")
            y = d.internacoes.to_numpy(float)
            anos = d.ano.astype(int).to_numpy()
            for corte in range(8, len(y)):
                passado = pd.DataFrame({"ano": anos[:corte], "internacoes": y[:corte]})
                base = ti.prever_com_validacao(passado, horizonte=1)
                alterado = y.copy()
                alterado[corte:] = alterado[corte:] * 1000 + 12345
                futuro_alterado = pd.DataFrame({
                    "ano": anos[:corte], "internacoes": alterado[:corte]
                })
                depois = ti.prever_com_validacao(futuro_alterado, horizonte=1)
                assert base["modelo"] == depois["modelo"]
                assert np.isclose(base["previsao"].internacoes.iloc[0],
                                  depois["previsao"].internacoes.iloc[0],
                                  rtol=0, atol=1e-9)
                total += 1
    assert total == 70


def test_controle_positivo_alteracao_do_passado_muda_previsao():
    real = tp.serie_real()
    d = real[(real.grupo == "MUNICIPIO") &
             (real.tipo_cancer == sorted(real.tipo_cancer.unique())[0])].sort_values("ano")
    y = d.internacoes.to_numpy(float)
    anos = d.ano.astype(int).to_numpy()
    base = ti.prever_com_validacao(pd.DataFrame({
        "ano": anos[:10], "internacoes": y[:10]
    }), horizonte=1)
    alterado = y[:10].copy()
    alterado[9] += 50
    depois = ti.prever_com_validacao(pd.DataFrame({
        "ano": anos[:10], "internacoes": alterado
    }), horizonte=1)
    assert not np.isclose(base["previsao"].internacoes.iloc[0],
                          depois["previsao"].internacoes.iloc[0],
                          rtol=0, atol=1e-9)


def test_empates_sao_excluidos_do_teste_de_sinais():
    exemplo = pd.DataFrame({"diferenca_mae": [-2.0, 0.0, 1.0, 0.0]})
    resultado = teste_sinais_pareado(exemplo)
    assert resultado == {
        "series_vitorias": 1, "series_empates": 2, "series_derrotas": 1,
        "pares_no_teste": 2, "p_bilateral_exato": 1.0,
    }


def test_resumo_por_serie_nao_trata_anos_como_series_independentes():
    exemplo = pd.DataFrame({
        "grupo": ["MUNICIPIO"] * 3, "cancer": ["MAMA"] * 3,
        "ano_alvo": [2021, 2022, 2023],
        "erro_escolhido": [4.0, 5.0, 6.0],
        "erro_ingenuo": [5.0, 5.0, 5.0],
    })
    resumo = resumo_por_serie(exemplo)
    assert len(resumo) == 1
    assert resumo.iloc[0].n_anos == 3
    assert resumo.iloc[0].resultado == "empate"
