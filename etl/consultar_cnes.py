"""Consulta SÓ DE LEITURA no cadastro do CNES (banco\\cnes\\tbEstabelecimento*.csv): o que o SEU arquivo diz de um estabelecimento.

Serve para conferir uma pista (um CNES que apareceu num texto, uma troca de cadastro) contra o arquivo real antes de usar.
Só dado público do estabelecimento; nunca profissionais.

    py etl\\consultar_cnes.py 2655519 9841903          (por código do CNES)
    py etl\\consultar_cnes.py --nome "Santa Casa" --uf MT   (por parte do nome; --uf filtra pelo estado)
"""
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "etl"))
import cruzar_hospitais_oncologia as c  # noqa: E402
import gerar_hospitais_oncologia_geo as g  # noqa: E402
import unidades_saude as us  # noqa: E402

LIMITE = 15


def consultar(pasta, codigos=(), nome="", uf=""):
    """Lista de dicts (um por estabelecimento achado). Por código, por parte do nome (sem acento), ou os dois."""
    caminho = us.achar_arquivo(pasta)
    if caminho is None:
        return [], "Arquivo tbEstabelecimento*.csv não encontrado em banco\\cnes."
    cod = us._codificacao(caminho)
    sep = us._separador(caminho, cod)
    achados = us._mapear_colunas(list(pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, nrows=0).columns))
    if "cnes" not in achados:
        return [], "O arquivo não tem a coluna do CNES."
    usar = list(dict.fromkeys(achados.values()))
    quero = {us.so_digitos(x).zfill(7) for x in codigos}
    texto = g._norm(nome)
    saida = []
    for pedaco in pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, usecols=usar, chunksize=us.TAMANHO_PEDACO, keep_default_na=False, low_memory=False):
        def col(campo):
            return pedaco[achados[campo]].astype(str).str.strip() if campo in achados else pd.Series("", index=pedaco.index)
        cnes = col("cnes").map(us.so_digitos).str.zfill(7)
        mask = cnes.isin(quero) if quero else pd.Series(False, index=pedaco.index)
        if texto:
            nomes = (col("nome") + " " + col("razao")).map(g._norm)
            casa = nomes.str.contains(texto, regex=False)
            if uf and "unidade" in achados:
                casa &= col("unidade").str[:2].map(lambda p: g.UF_POR_CODIGO.get(p) == uf.upper())
            mask = mask | casa if quero else casa
        for i in pedaco.index[mask]:
            lat = pd.to_numeric(col("lat")[i].replace(",", "."), errors="coerce")
            lon = pd.to_numeric(col("lon")[i].replace(",", "."), errors="coerce")
            motivo = us.so_digitos(col("desabilitado")[i]).lstrip("0") if "desabilitado" in achados else ""
            unidade = us.so_digitos(col("unidade")[i]) if "unidade" in achados else ""
            saida.append({"cnes": cnes[i], "unidade": unidade, "uf": g.UF_POR_CODIGO.get(unidade[:2], "?"), "municipio6": unidade[:6],
                          "nome": us.nome_legivel(col("nome")[i]), "razao": us.nome_legivel(col("razao")[i]),
                          "ativo": motivo == "", "motivo_desab": motivo,
                          "endereco": us.endereco_legivel(col("logradouro")[i], col("numero")[i], col("bairro")[i]),
                          "cep": us.cep_legivel(col("cep")[i]), "telefone": c.telefone_do_cnes(col("telefone")[i]),
                          "lat": None if pd.isna(lat) else float(lat), "lon": None if pd.isna(lon) else float(lon)})
    saida.sort(key=lambda r: (not r["ativo"], r["uf"], r["nome"]))
    return saida, ""


def main(argv=None, pasta=us.PASTA_CNES):
    args = list(sys.argv[1:] if argv is None else argv)
    nome = uf = ""
    if "--nome" in args:
        i = args.index("--nome")
        nome = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if "--uf" in args:
        i = args.index("--uf")
        uf = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if not args and not nome:
        print(__doc__)
        return 1
    achados, aviso = consultar(pasta, args, nome, uf)
    if aviso:
        print(aviso)
        return 1
    if not achados:
        print("Nada no seu CNES para essa consulta.")
        return 0
    print(f"{len(achados)} estabelecimento(s) no seu CNES" + (f" (mostrando {LIMITE})" if len(achados) > LIMITE else "") + ":")
    for r in achados[:LIMITE]:
        print(f"\nCNES {r['cnes']} | {r['nome']} ({r['razao']})")
        print(f"   {'ATIVO' if r['ativo'] else 'DESABILITADO (motivo ' + r['motivo_desab'] + ')'} | estado {r['uf']} | município (código de 6 dígitos) {r['municipio6']} | CO_UNIDADE {r['unidade']}")
        print(f"   {r['endereco']} | CEP {r['cep']} | telefone {r['telefone'] or '(sem)'}")
        if r["lat"] is not None and r["lon"] is not None:
            print(f"   onde o CNES diz que fica: https://www.google.com/maps?q={r['lat']:.6f},{r['lon']:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
