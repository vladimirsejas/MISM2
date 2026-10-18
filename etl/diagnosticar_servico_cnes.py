"""Diagnóstico SÓ DE LEITURA de UM serviço do CNES em Rio Claro (18/10/2026).

Responde: quantas unidades têm esse serviço no cadastro, de que tipo e natureza elas são, QUAIS
classificações cada uma registrou de fato (o serviço "guarda-chuva" tem várias), e se a lista "o que existe
na cidade" e a busca da página contam a mesma coisa. Não muda nada; só imprime contagens e nomes de
estabelecimento (dado público). Não lê o arquivo de profissionais.

    py etl\\diagnosticar_servico_cnes.py
    py etl\\diagnosticar_servico_cnes.py "ULTRASSONOGRAFIA"
"""
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
sys.path.insert(0, os.path.join(RAIZ, "etl"))
import diagnosticar_busca_cnes as base  # noqa: E402
import onde_atendida as oa  # noqa: E402
import unidades_saude as us  # noqa: E402


def norm(t):
    return us._chave(t).replace("_", " ")


def titulo(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def main():
    termo = sys.argv[1] if len(sys.argv) > 1 else "DIAGNOSTICO POR IMAGEM"
    alvo = norm(termo)
    caminho = us.achar_arquivo()
    if not caminho:
        print("Sem tbEstabelecimento em banco\\cnes.")
        return 1
    pasta = os.path.dirname(caminho)
    mes = os.path.basename(caminho)[-10:-4]
    print(f"Serviço procurado: '{termo}'  (cadastro de {mes})")

    us._medicos_cnes = lambda *a, **k: ({}, "")  # não precisamos do arquivo de 881 MB aqui
    df = us.carregar_unidades()
    if df.empty:
        print("Sem unidades."); return 1
    tem = df[df["servicos"].astype(str).map(norm).str.contains(alvo, regex=False)]

    titulo("1. Quantas unidades têm esse serviço no cadastro (texto montado pela página)")
    print(f"Unidades ativas de Rio Claro: {len(df)} | com '{termo}': {len(tem)}")
    print("Por grupo:", {k: int(v) for k, v in tem["grupo"].astype(str).value_counts().items()})
    print("Por natureza:", {k: int(v) for k, v in tem["natureza"].astype(str).value_counts().items()})

    titulo("2. A lista 'o que existe na cidade' e a busca contam o mesmo?")
    lista = oa.unificar(df, [])
    _, servicos_op = oa.opcoes_de_busca(lista)
    print("Na lista:", [(rot, q) for rot, t, q in servicos_op if alvo in norm(t)][:5])
    for rot, t, q in servicos_op:
        if alvo in norm(t):
            achadas = oa.filtrar(lista, None, busca=t, so_publicos=False)
            print(f"  busca por '{t}' (sem filtro): {len(achadas)} lugares | por grupo: "
                  f"{ {k: int(v) for k, v in achadas['grupo'].astype(str).value_counts().items()} }")
            print(f"  ... na página aparecem {min(len(achadas), 12)} de cada vez ('Mostrar mais' traz o resto)")
            break

    titulo("3. O que cada unidade REGISTROU de fato (serviço -> classificação)")
    bruto, ach = base.ler_unidades_cruas(caminho)
    cnes_de = {us.so_digitos(u): us.so_digitos(c).zfill(7) for u, c in zip(bruto[ach["unidade"]], bruto[ach["cnes"]])}
    unidade_de = {v: k for k, v in cnes_de.items()}
    rel = os.path.join(pasta, f"rlEstabServClass{mes}.csv")
    cla = os.path.join(pasta, f"tbClassificacaoServico{mes}.csv")
    ser = os.path.join(pasta, f"tbServicoEspecializado{mes}.csv")
    cc = pd.read_csv(cla, sep=us._separador(cla, us._codificacao(cla)), encoding=us._codificacao(cla), dtype=str, keep_default_na=False)
    cs = pd.read_csv(ser, sep=us._separador(ser, us._codificacao(ser)), encoding=us._codificacao(ser), dtype=str, keep_default_na=False)
    nome_classe = {(us.so_digitos(r["CO_SERVICO_ESPECIALIZADO"]), us.so_digitos(r["CO_CLASSIFICACAO_SERVICO"])): r["DS_CLASSIFICACAO_SERVICO"].strip()
                   for _, r in cc.iterrows()}
    nome_serv = {us.so_digitos(r["CO_SERVICO_ESPECIALIZADO"]): r["DS_SERVICO_ESPECIALIZADO"].strip() for _, r in cs.iterrows()}
    unidades = set(unidade_de.get(c) for c in tem["cnes"]) - {None}
    registros = {}
    for p in pd.read_csv(rel, sep=us._separador(rel, "latin-1"), encoding="latin-1", dtype=str, usecols=["CO_UNIDADE", "CO_SERVICO", "CO_CLASSIFICACAO"],
                         chunksize=500_000, keep_default_na=False):
        p = p.loc[p["CO_UNIDADE"].map(us.so_digitos).isin(unidades)]
        for u, s, c in zip(p["CO_UNIDADE"], p["CO_SERVICO"], p["CO_CLASSIFICACAO"]):
            u, s, c = us.so_digitos(u), us.so_digitos(s), us.so_digitos(c)
            registros.setdefault(u, set()).add((nome_serv.get(s, f"serviço {s}"), nome_classe.get((s, c), f"classificação {c}")))
    contagem = {}
    for u, regs in registros.items():
        for sv, cl in regs:
            if alvo in norm(sv):
                contagem[cl] = contagem.get(cl, 0) + 1
    print(f"Classificações registradas dentro de '{termo}', em quantas unidades (as {len(tem)} acima):")
    for cl, q in sorted(contagem.items(), key=lambda x: -x[1])[:20]:
        print(f"   {q:3d}  {cl}")

    titulo("4. As UBS / postos (grupo 'basica') que aparecem para esse serviço, com o que registraram")
    ubs = tem[tem["grupo"].astype(str) == "basica"]
    print(f"{len(ubs)} unidade(s) de posto/UBS.")
    for r in ubs.head(40).itertuples():
        regs = sorted(cl for sv, cl in registros.get(unidade_de.get(r.cnes), set()) if alvo in norm(sv))
        print(f"   - {r.nome} [{r.natureza}] -> registrou: {', '.join(regs) if regs else '(nenhuma classificação deste serviço)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
