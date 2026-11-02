"""Avaliação temporal aninhada das previsões do MISM2.

Janela principal: 8 anos de passado. Sensibilidade: 10 anos.
A série é preparada pela mesma função usada nos testes do projeto.
Não altera a lógica de previsão nem o painel.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import inteligencia as ti
import teste_previsao as tp

JANELAS = {"principal_8_anos": 8, "sensibilidade_10_anos": 10}
GRUPOS_ESPERADOS = {"MUNICIPIO", "SP"}


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def commit_atual() -> str:
    """SHA do checkout; vazio/indisponível fora de um clone Git."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=RAIZ, text=True,
            stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("GITHUB_SHA", "nao_disponivel")


def avaliar_janela(real: pd.DataFrame, passado_minimo: int) -> pd.DataFrame:
    linhas = []
    for grupo in sorted(real["grupo"].dropna().unique()):
        for cancer in sorted(real["tipo_cancer"].dropna().unique()):
            d = real[(real["grupo"] == grupo) &
                     (real["tipo_cancer"] == cancer)].sort_values("ano")
            y = d["internacoes"].to_numpy(dtype=float)
            anos = d["ano"].astype(int).to_numpy()
            for corte in range(passado_minimo, len(y)):
                passado = pd.DataFrame({
                    "ano": anos[:corte],
                    "internacoes": y[:corte],
                })
                p = ti.prever_com_validacao(passado, horizonte=1)
                if p is None:
                    continue
                previsto = float(p["previsao"]["internacoes"].iloc[0])
                erro_escolhido = abs(float(y[corte]) - previsto)
                erro_ingenuo = abs(float(y[corte]) - float(y[corte - 1]))
                linhas.append({
                    "grupo": grupo, "cancer": cancer,
                    "ano_alvo": int(anos[corte]), "modelo": p["modelo"],
                    "valor_real": float(y[corte]), "previsao": previsto,
                    "erro_escolhido": erro_escolhido,
                    "erro_ingenuo": erro_ingenuo,
                    "diferenca_erro": erro_escolhido - erro_ingenuo,
                })
    return pd.DataFrame(linhas)


def resumo_por_serie(resultados: pd.DataFrame) -> pd.DataFrame:
    """Uma comparação pareada por série; anos repetidos não viram n independente."""
    if resultados.empty:
        return pd.DataFrame(columns=["grupo", "cancer", "n_anos", "mae_escolhido",
                                     "mae_ingenuo", "diferenca_mae", "resultado"])
    s = resultados.groupby(["grupo", "cancer"], as_index=False).agg(
        n_anos=("ano_alvo", "count"),
        mae_escolhido=("erro_escolhido", "mean"),
        mae_ingenuo=("erro_ingenuo", "mean"),
    )
    s["diferenca_mae"] = s["mae_escolhido"] - s["mae_ingenuo"]
    s["resultado"] = np.select(
        [s["diferenca_mae"] < -1e-9, s["diferenca_mae"] > 1e-9],
        ["vitoria", "derrota"], default="empate"
    )
    return s


def teste_sinais_pareado(serie: pd.DataFrame) -> dict:
    """Teste binomial bilateral exato; empates são excluídos do denominador."""
    v = int((serie["diferenca_mae"] < -1e-9).sum())
    d = int((serie["diferenca_mae"] > 1e-9).sum())
    n = v + d
    if n == 0:
        p = None
    else:
        k = min(v, d)
        cauda = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
        p = min(1.0, 2 * cauda)
    return {"series_vitorias": v, "series_empates": int(len(serie) - n),
            "series_derrotas": d, "pares_no_teste": n,
            "p_bilateral_exato": p}



def analises_complementares(real: pd.DataFrame, saida: Path) -> None:
    """Gera tabelas descritivas, bootstrap por série e figuras solicitadas."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figdir = saida / "figuras"
    figdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261102)
    tabelas = []

    for janela in (8, 10):
        r = avaliar_janela(real, janela)
        serie = resumo_por_serie(r)
        nome = f"janela_{janela}"
        print(f"\nANÁLISES COMPLEMENTARES — {janela} ANOS")

        # Bootstrap por série: cada reamostragem sorteia 7 séries com reposição.
        for grupo, sub in serie.groupby("grupo"):
            razoes = []
            for _ in range(10000):
                amostra = sub.iloc[rng.integers(0, len(sub), len(sub))]
                den = amostra["mae_ingenuo"].mean()
                if den > 0:
                    razoes.append(amostra["mae_escolhido"].mean() / den)
            med = float(np.median(razoes))
            li, ls = np.quantile(razoes, [0.025, 0.975])
            print(f"Bootstrap {grupo} (7 séries): mediana={med:.4f}; IC95%=[{li:.4f}, {ls:.4f}]")
        
        # Subperíodos e porte da série, com resultados agregados e contagens.
        r = r.merge(serie[["grupo", "cancer", "mae_escolhido"]].rename(
            columns={"mae_escolhido": "media_serie"}), on=["grupo", "cancer"], how="left")
        r["subperiodo"] = np.where(r["ano_alvo"].between(2021, 2022), "2021-2022", "2023-2025")
        r["porte_serie"] = np.where(r["media_serie"] < 20, "média abaixo de 20", "média igual/acima de 20")
        for dimensao in ("subperiodo", "porte_serie"):
            tab = r.groupby(["grupo", dimensao], as_index=False).agg(
                n=("ano_alvo", "count"), mae_escolhido=("erro_escolhido", "mean"),
                mae_ingenuo=("erro_ingenuo", "mean"))
            print(f"\n{dimensao}:")
            print(tab.to_string(index=False))
            tab.insert(0, "janela", janela)
            tab.to_csv(saida / f"{nome}_{dimensao}.csv", index=False)

        # Frequência de seleção e erro de cada modelo fixo nas mesmas origens.
        fixas = []
        for grupo in sorted(real.grupo.dropna().unique()):
            for cancer in sorted(real.tipo_cancer.dropna().unique()):
                d = real[(real.grupo == grupo) & (real.tipo_cancer == cancer)].sort_values("ano")
                anos = d.ano.astype(int).to_numpy()
                y = d.internacoes.to_numpy(float)
                for corte in range(janela, len(y)):
                    passado_anos, passado_y = anos[:corte], y[:corte]
                    escolhido = ti.prever_com_validacao(
                        pd.DataFrame({"ano": passado_anos, "internacoes": passado_y}), horizonte=1)
                    if escolhido is None:
                        continue
                    alvo = float(y[corte])
                    linha = {"grupo": grupo, "cancer": cancer, "ano_alvo": int(anos[corte]),
                             "modelo_escolhido": escolhido["modelo"]}
                    for modelo, func in ti._PREVISORES.items():
                        previsto = float(np.clip(func(passado_anos, passado_y, 1)[0], 0, None))
                        linha[f"erro_{modelo}"] = abs(alvo - previsto)
                    fixas.append(linha)
        fd = pd.DataFrame(fixas)
        linhas = []
        for grupo, sub in fd.groupby("grupo"):
            for modelo in ti.MODELOS_PREVISAO:
                linhas.append({"grupo": grupo, "modelo": modelo,
                               "vezes_escolhido": int((sub.modelo_escolhido == modelo).sum()),
                               "mae_modelo_fixo": float(sub[f"erro_{modelo}"].mean()),
                               "n": len(sub)})
        fm = pd.DataFrame(linhas)
        print("\nModelos escolhidos e erros dos modelos fixos:")
        print(fm.to_string(index=False))
        fm.to_csv(saida / f"{nome}_modelos_fixos.csv", index=False)

        # Gráficos por território: dispersão log-log e razão por série.
        ss = resumo_por_serie(avaliar_janela(real, janela))
        for grupo, sub in ss.groupby("grupo"):
            fig, ax = plt.subplots(figsize=(7, 6))
            positivos = np.r_[sub.mae_escolhido[sub.mae_escolhido > 0],
                              sub.mae_ingenuo[sub.mae_ingenuo > 0]]
            eps = max(float(positivos.min()) * 0.5, 1e-6) if len(positivos) else 1e-6
            x = sub.mae_ingenuo.clip(lower=eps)
            yv = sub.mae_escolhido.clip(lower=eps)
            limite = max(float(x.max()), float(yv.max()), eps) * 1.15
            ax.scatter(x, yv)
            ax.plot([eps, limite], [eps, limite], linestyle="--", label="Diagonal de igualdade")
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_xlim(left=eps); ax.set_ylim(bottom=eps)
            ax.set_xlabel("MAE do método ingênuo")
            ax.set_ylabel("MAE do modelo escolhido")
            ax.set_title(f"Erros por série — {grupo} — janela {janela} anos")
            ax.legend()
            fig.tight_layout()
            base = figdir / f"{nome}_{grupo}_dispersao"
            fig.savefig(base.with_suffix(".png"), dpi=300)
            fig.savefig(base.with_suffix(".svg"))
            plt.close(fig)

            ordem = sub.assign(razao=sub.mae_escolhido / sub.mae_ingenuo.replace(0, np.nan)).sort_values("razao")
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.bar(ordem.cancer, ordem.razao)
            ax.axhline(1, linestyle="--", label="Igualdade")
            ax.set_ylabel("Razão MAE escolhido / MAE ingênuo")
            ax.set_xlabel("Tipo de câncer")
            ax.set_title(f"Razão dos erros por série — {grupo} — janela {janela} anos")
            ax.tick_params(axis="x", rotation=35)
            ax.legend()
            fig.tight_layout()
            base = figdir / f"{nome}_{grupo}_razao"
            fig.savefig(base.with_suffix(".png"), dpi=300)
            fig.savefig(base.with_suffix(".svg"))
            plt.close(fig)


def executar(saida: Path | None = None) -> dict:
    saida = saida or (RAIZ / "analises" / "avaliacao_aninhada")
    saida.mkdir(parents=True, exist_ok=True)
    base = RAIZ / "analises" / "base_preditiva_2013_2025.csv"
    real = tp.serie_real()
    if set(real["grupo"].dropna().unique()) != GRUPOS_ESPERADOS:
        raise AssertionError(f"Grupos inesperados na base: {sorted(real['grupo'].dropna().unique())}")

    esperado = {
        8: (70, 25, 19, 26),
        10: (42, 7, 14, 21),
    }
    relatorio = {}
    for nome, janela in JANELAS.items():
        r = avaliar_janela(real, janela)
        serie = resumo_por_serie(r)
        v = int((r["diferenca_erro"] < -1e-9).sum())
        e = int((r["diferenca_erro"].abs() <= 1e-9).sum())
        d = int((r["diferenca_erro"] > 1e-9).sum())
        obtido = (len(r), v, e, d)
        if obtido != esperado[janela]:
            raise AssertionError(
                f"Janela {janela}: esperado {esperado[janela]}, obtido {obtido}. "
                "Interrompido para investigar divergência."
            )
        r.to_csv(saida / f"{nome}_previsoes.csv", index=False, float_format="%.10g")
        serie.to_csv(saida / f"{nome}_por_serie.csv", index=False, float_format="%.10g")
        por_grupo = {}
        for grupo, sub in r.groupby("grupo"):
            por_grupo[grupo] = {
                "n_previsoes": int(len(sub)),
                "mae_escolhido": float(sub["erro_escolhido"].mean()),
                "mae_ingenuo": float(sub["erro_ingenuo"].mean()),
                "vitorias": int((sub["diferenca_erro"] < -1e-9).sum()),
                "empates": int((sub["diferenca_erro"].abs() <= 1e-9).sum()),
                "derrotas": int((sub["diferenca_erro"] > 1e-9).sum()),
                "teste_sinais_por_serie": teste_sinais_pareado(
                    serie[serie["grupo"] == grupo]),
            }
        relatorio[nome] = {
            "passado_minimo_anos": janela,
            "anos_alvo": sorted(int(x) for x in r["ano_alvo"].unique()),
            "n_previsoes": len(r), "vitorias": v, "empates": e, "derrotas": d,
            "mae_escolhido_geral": float(r["erro_escolhido"].mean()),
            "mae_ingenuo_geral": float(r["erro_ingenuo"].mean()),
            "por_grupo": por_grupo,
            "teste_sinais_por_serie": teste_sinais_pareado(serie),
        }

    analises_complementares(real, saida)

    metadados = {
        "commit": commit_atual(),
        "sha256_base_csv": sha256_arquivo(base),
        "arquivo_base": str(base.relative_to(RAIZ)),
        "regra_janela_principal": 8,
        "regra_sensibilidade": 10,
        "horizonte_anos": 1,
        "selecao_modelo": "prever_com_validacao recebe exclusivamente os anos anteriores ao alvo",
        "ajuste_meses": "tp.serie_real aplica completar_anos e ajustar_meses com o mapa de meses declarado em teste_previsao.py",
        "tolerancia_empate": 1e-9,
        "nota": "As duas janelas foram examinadas antes da definição da janela principal; 8 anos é a análise principal por corresponder ao mínimo declarado pelo projeto.",
    }
    (saida / "metadados.json").write_text(
        json.dumps({"metadados": metadados, "resultados": relatorio},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("AVALIAÇÃO ANINHADA — MISM2")
    for nome, x in relatorio.items():
        print(f"{nome}: {x['n_previsoes']} previsões; "
              f"{x['vitorias']} vitórias, {x['empates']} empates, {x['derrotas']} derrotas")
        for grupo, g in x["por_grupo"].items():
            print(f"  {grupo}: MAE escolhido={g['mae_escolhido']:.2f}; "
                  f"ingênuo={g['mae_ingenuo']:.2f}; "
                  f"vitórias/empates/derrotas={g['vitorias']}/{g['empates']}/{g['derrotas']}")
    print(f"Arquivos gravados em: {saida}")
    return relatorio


if __name__ == "__main__":
    executar()
