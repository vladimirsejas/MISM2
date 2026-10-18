"""Diagnóstico SÓ DE LEITURA de UMA unidade do CNES (18/10/2026): o que o cadastro registra para ela, linha a linha.

Mostra as linhas CRUAS da tabela que liga unidade e serviço (rlEstabServClass, com TODAS as colunas), o nome que
cada código recebe nos dicionários e o texto que a página monta. Serve para saber se uma unidade aparece numa busca
porque o CNES a cadastrou assim ou porque a junção das tabelas está errada. Só imprime códigos de serviço e nomes
de estabelecimento (dado público); não lê o arquivo de profissionais.

    py etl\\diagnosticar_unidade_cnes.py "UBS Dr Mario Fittipaldi"
"""
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "etl"))
import diagnosticar_busca_cnes as base  # noqa: E402
import unidades_saude as us  # noqa: E402


def titulo(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def ler(caminho, enc=None, **kw):
    enc = enc or us._codificacao(caminho)
    return pd.read_csv(caminho, sep=us._separador(caminho, enc), encoding=enc, dtype=str, keep_default_na=False, **kw)


def main():
    if len(sys.argv) < 2:
        print('Uso: py etl\\diagnosticar_unidade_cnes.py "parte do nome da unidade"')
        return 1
    busca = us._chave(sys.argv[1]).replace("_", " ")
    caminho = us.achar_arquivo()
    if not caminho:
        print("Sem tbEstabelecimento em banco\\cnes.")
        return 1
    pasta = os.path.dirname(caminho)
    mes = os.path.basename(caminho)[-10:-4]
    us._medicos_cnes = lambda *a, **k: ({}, "")
    df = us.carregar_unidades()
    achadas = df[df["nome"].map(lambda n: busca in us._chave(n).replace("_", " "))]
    print(f"Unidades de Rio Claro cujo nome contém '{sys.argv[1]}': {len(achadas)}")
    if achadas.empty:
        return 1
    bruto, ach = base.ler_unidades_cruas(caminho)
    unidade_de = {us.so_digitos(c).zfill(7): us.so_digitos(u) for u, c in zip(bruto[ach["unidade"]], bruto[ach["cnes"]])}

    rel = os.path.join(pasta, f"rlEstabServClass{mes}.csv")
    cla = os.path.join(pasta, f"tbClassificacaoServico{mes}.csv")
    ser = os.path.join(pasta, f"tbServicoEspecializado{mes}.csv")
    titulo("Cabeçalho das tabelas de serviço (todas as colunas)")
    for rotulo, arq, enc in (("rlEstabServClass", rel, "latin-1"), ("tbClassificacaoServico", cla, None), ("tbServicoEspecializado", ser, None)):
        print(f"{rotulo}: {list(ler(arq, enc, nrows=0).columns)}")
    dic_c = ler(cla)
    dic_s = ler(ser)

    for r in achadas.head(3).itertuples():
        u = unidade_de.get(r.cnes)
        titulo(f"{r.nome} | CNES {r.cnes} | CO_UNIDADE {u} | {r.tipo} | {r.natureza}")
        linhas = []
        for p in pd.read_csv(rel, sep=us._separador(rel, "latin-1"), encoding="latin-1", dtype=str, chunksize=500_000, keep_default_na=False):
            linhas.append(p.loc[p["CO_UNIDADE"].map(us.so_digitos) == u])
        reg = pd.concat(linhas, ignore_index=True)
        print(f"Linhas desta unidade em rlEstabServClass: {len(reg)}")
        if reg.empty:
            print("  (nenhuma: o CNES não registra nenhum serviço especializado para esta unidade)")
        else:
            with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40):
                print(reg.head(25).to_string(index=False))
            print("\nComo cada linha vira nome (serviço -> classificação):")
            for _, x in reg.head(25).iterrows():
                s, c = us.so_digitos(x["CO_SERVICO"]), us.so_digitos(x["CO_CLASSIFICACAO"])
                ns = dic_s[dic_s["CO_SERVICO_ESPECIALIZADO"].map(us.so_digitos) == s]["DS_SERVICO_ESPECIALIZADO"].tolist()
                nc = dic_c[(dic_c["CO_SERVICO_ESPECIALIZADO"].map(us.so_digitos) == s) & (dic_c["CO_CLASSIFICACAO_SERVICO"].map(us.so_digitos) == c)]["DS_CLASSIFICACAO_SERVICO"].tolist()
                so_codigo = dic_c[dic_c["CO_CLASSIFICACAO_SERVICO"].map(us.so_digitos) == c]["DS_CLASSIFICACAO_SERVICO"].nunique()
                print(f"   serviço {s} = {ns} | classificação {c} = {nc}   (o código de classificação {c} existe com {so_codigo} nome(s) diferente(s) no dicionário)")
        print("\nTexto que a página monta para esta unidade:")
        print("  ", str(r.servicos)[:900] or "(vazio)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
