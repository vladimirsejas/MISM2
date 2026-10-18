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

    titulo("3. Quem FAZ o serviço (TP_CARACTERISTICA = 1) e quem o tem POR TERCEIRO (= 2)")
    bruto, ach = base.ler_unidades_cruas(caminho)
    cnes_de = {us.so_digitos(u): us.so_digitos(c).zfill(7) for u, c in zip(bruto[ach["unidade"]], bruto[ach["cnes"]])}
    unidade_de = {v: k for k, v in cnes_de.items()}
    nome_de_cnes = dict(zip(df["cnes"], df["nome"]))
    rel = os.path.join(pasta, f"rlEstabServClass{mes}.csv")
    cla = os.path.join(pasta, f"tbClassificacaoServico{mes}.csv")
    ser = os.path.join(pasta, f"tbServicoEspecializado{mes}.csv")
    cc = pd.read_csv(cla, sep=us._separador(cla, us._codificacao(cla)), encoding=us._codificacao(cla), dtype=str, keep_default_na=False)
    cs = pd.read_csv(ser, sep=us._separador(ser, us._codificacao(ser)), encoding=us._codificacao(ser), dtype=str, keep_default_na=False)
    nome_classe = {(us.so_digitos(r["CO_SERVICO_ESPECIALIZADO"]), us.so_digitos(r["CO_CLASSIFICACAO_SERVICO"])): r["DS_CLASSIFICACAO_SERVICO"].strip()
                   for _, r in cc.iterrows()}
    nome_serv = {us.so_digitos(r["CO_SERVICO_ESPECIALIZADO"]): r["DS_SERVICO_ESPECIALIZADO"].strip() for _, r in cs.iterrows()}
    todas = set(unidade_de.values())
    proprio, terceiro, provedores = {}, {}, {}
    colunas = ["CO_UNIDADE", "CO_SERVICO", "CO_CLASSIFICACAO", "TP_CARACTERISTICA", "CO_CNPJCPF"]
    for p in pd.read_csv(rel, sep=us._separador(rel, "latin-1"), encoding="latin-1", dtype=str, usecols=colunas,
                         chunksize=500_000, keep_default_na=False):
        p = p.loc[p["CO_UNIDADE"].map(us.so_digitos).isin(todas)]
        for u, sv, cl, car, quem in zip(p["CO_UNIDADE"], p["CO_SERVICO"], p["CO_CLASSIFICACAO"], p["TP_CARACTERISTICA"], p["CO_CNPJCPF"]):
            u, sv, cl = us.so_digitos(u), us.so_digitos(sv), us.so_digitos(cl)
            rot = (nome_serv.get(sv, ""), nome_classe.get((sv, cl), ""))
            if alvo not in norm(rot[0]) and alvo not in norm(rot[1]):
                continue
            if us.so_digitos(car) == "2":
                terceiro.setdefault(u, set()).add(rot[1] or rot[0])
                provedores[us.so_digitos(quem).zfill(7)] = provedores.get(us.so_digitos(quem).zfill(7), 0) + 1
            else:
                proprio.setdefault(u, set()).add(rot[1] or rot[0])
    so_terceiro = set(terceiro) - set(proprio)
    print(f"Unidades que FAZEM (próprio): {len(proprio)} | só por terceiro: {len(so_terceiro)}")
    cnes_da = {v: k for k, v in unidade_de.items()}
    por_grupo = df.set_index("cnes")["grupo"].astype(str).to_dict()
    print("\nQuem FAZ, com o que registrou:")
    for u in sorted(proprio, key=lambda x: nome_de_cnes.get(unidade_de and next((c for c, uu in unidade_de.items() if uu == x), ""), "")):
        c = next((c for c, uu in unidade_de.items() if uu == u), "")
        print(f"   - {nome_de_cnes.get(c, u)} [{por_grupo.get(c, '?')}] -> {', '.join(sorted(proprio[u]))}")
    print(f"\nQuem aparece SÓ POR TERCEIRO ({len(so_terceiro)} unidades). Por grupo:",
          {k: int(v) for k, v in pd.Series([por_grupo.get(next((c for c, uu in unidade_de.items() if uu == u), ""), "?") for u in so_terceiro]).value_counts().items()})
    print("\nQuem é o 'terceiro' (CO_CNPJCPF) e em quantos registros aparece; se for o CNES de uma unidade de Rio Claro, o nome:")
    for cod, q in sorted(provedores.items(), key=lambda x: -x[1])[:15]:
        print(f"   {cod}  {q:3d} registros  -> {nome_de_cnes.get(cod, '(não é uma unidade de Rio Claro no cadastro)')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
