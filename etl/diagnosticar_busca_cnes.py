"""Diagnóstico SÓ DE LEITURA da busca "Exames e especialistas" (18/10/2026).

Não muda nada: lê o CNES de banco\\cnes e mostra, para Rio Claro, onde os dados de serviços e de médicos
existem, como as tabelas se ligam e o que cada regra da busca deixa passar ou corta. Imprime apenas
contagens e nomes de estabelecimento (dado público); nunca código, nome ou registro de profissional.

    py etl\\diagnosticar_busca_cnes.py
"""
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "algoritimos"))
import onde_atendida as oa  # noqa: E402
import unidades_saude as us  # noqa: E402

CODIGO_RIO_CLARO = "354390"


def titulo(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def ler_unidades_cruas(caminho):
    cod = us._codificacao(caminho)
    sep = us._separador(caminho, cod)
    cols = list(pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, nrows=0).columns)
    ach = us._mapear_colunas(cols)
    print(f"Colunas do tbEstabelecimento ({len(cols)}): {', '.join(cols)}")
    print("Reconhecidas pelo Escudo:", {k: v for k, v in ach.items()})
    campo = "municipio_local" if "municipio_local" in ach else ("municipio_gestor" if "municipio_gestor" in ach else None)
    if campo is None:
        print("ATENÇÃO: nenhuma coluna de município reconhecida; o painel não consegue saber quais unidades são da cidade.")
        raise SystemExit(1)
    print(f"Critério de município usado pelo painel: {campo} ({ach[campo]})"
          + ("  <-- é o GESTOR, não o endereço" if campo == "municipio_gestor" else ""))
    usar = list(dict.fromkeys(ach.values()))
    saida = []
    for p in pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, usecols=usar, chunksize=100_000, keep_default_na=False):
        m = p[ach[campo]].map(us.so_digitos).str[:6] == CODIGO_RIO_CLARO
        saida.append(p.loc[m])
    bruto = pd.concat(saida, ignore_index=True)
    return bruto, ach


def main():
    caminho = us.achar_arquivo()
    if not caminho:
        print("Sem tbEstabelecimento em banco\\cnes.")
        return 1
    pasta = os.path.dirname(caminho)
    mes = os.path.basename(caminho)[-10:-4]
    print(f"Arquivo: {os.path.basename(caminho)}  (mês {mes})")

    # ---------- 1. as unidades de Rio Claro ----------
    titulo("1. Unidades de Rio Claro no cadastro (tbEstabelecimento)")
    bruto, ach = ler_unidades_cruas(caminho)
    if "unidade" not in ach:
        print("ATENÇÃO: não achei a coluna CO_UNIDADE; sem ela nada se liga. Colunas:", list(bruto.columns))
        return 1
    ativo = (bruto[ach["desabilitado"]].map(us.so_digitos).str.lstrip("0") == "") if "desabilitado" in ach else pd.Series(True, index=bruto.index)
    nat = bruto[ach["natureza"]].map(us.classificar_natureza) if "natureza" in ach else pd.Series("desconhecida", index=bruto.index)
    print(f"Total {len(bruto)} | ativas {int(ativo.sum())} | desabilitadas {int((~ativo).sum())}")
    print("Ativas por natureza:", {k: int(v) for k, v in nat[ativo].value_counts().items()})
    ex = bruto[ach["unidade"]].head(3).tolist()
    print("Exemplos de CO_UNIDADE no cadastro (tamanho):", [(x, len(x)) for x in ex])
    unidades = {us.so_digitos(u) for u in bruto.loc[ativo, ach["unidade"]]}
    nome_de = {us.so_digitos(u): us.nome_legivel(n) for u, n in zip(bruto[ach["unidade"]], bruto[ach["nome"]])}
    nat_de = {us.so_digitos(u): n for u, n in zip(bruto[ach["unidade"]], nat)}

    # ---------- 2. quantas aparecem em cada tabela relacionada ----------
    titulo("2. Quantas unidades ativas aparecem em cada tabela (a CHAVE CO_UNIDADE confere?)")
    rel = os.path.join(pasta, f"rlEstabServClass{mes}.csv")
    carga = os.path.join(pasta, f"tbCargaHorariaSus{mes}.csv")
    prof = os.path.join(pasta, f"rlEstabEquipeProf{mes}.csv")
    achou = {}
    for rotulo, arq, enc in (("serviços (rlEstabServClass)", rel, "latin-1"), ("equipes (rlEstabEquipeProf)", prof, "latin-1")):
        if not os.path.isfile(arq):
            print(f"  {rotulo}: arquivo não está na pasta"); continue
        vistos = set()
        for p in pd.read_csv(arq, sep=us._separador(arq, enc), encoding=enc, dtype=str, usecols=["CO_UNIDADE"], chunksize=500_000, keep_default_na=False):
            vistos |= set(p["CO_UNIDADE"].map(us.so_digitos)) & unidades
        achou[rotulo] = vistos
        print(f"  {rotulo}: {len(vistos)} de {len(unidades)} unidades")

    # ---------- 3. carga horária: o arquivo dos profissionais ----------
    titulo("3. Profissionais por unidade (tbCargaHorariaSus) - só contagens")
    if not os.path.isfile(carga):
        print("tbCargaHorariaSus não está na pasta."); return 1
    cod_c = "latin-1"  # o arquivo é grande e tem bytes fora de UTF-8 depois do começo
    sep_c = us._separador(carga, cod_c)
    cols_c = {us._chave(c): c for c in pd.read_csv(carga, sep=sep_c, encoding=cod_c, dtype=str, nrows=0).columns}
    pedir = ["CO_UNIDADE", "CO_PROFISSIONAL_SUS", "CO_CBO", "TP_SUS_NAO_SUS", "IND_VINCULACAO",
             "QT_CARGA_HORARIA_AMBULATORIAL", "QT_CARGA_HORARIA_OUTROS", "QT_CARGA_HOR_HOSP_SUS"]
    faltam = [c for c in pedir if us._chave(c) not in cols_c]
    if faltam:
        print("Colunas que não achei:", faltam)
    usar = [cols_c[us._chave(c)] for c in pedir if us._chave(c) in cols_c]
    linhas, total_lido = [], 0
    for p in pd.read_csv(carga, sep=sep_c, encoding=cod_c, dtype=str, usecols=usar, chunksize=200_000, keep_default_na=False, low_memory=False):
        total_lido += len(p)
        p.columns = [c.upper() for c in p.columns]
        p = p.loc[p["CO_UNIDADE"].map(us.so_digitos).isin(unidades)]
        if len(p):
            linhas.append(p)
    print(f"Linhas lidas no arquivo inteiro: {total_lido:,}".replace(",", "."))
    if not linhas:
        print("NENHUMA linha de profissional bate com as unidades de Rio Claro pela chave CO_UNIDADE.")
        print("=> a chave está diferente nos dois arquivos. Peça ao Claude para olhar o formato de CO_UNIDADE.")
        return 0
    d = pd.concat(linhas, ignore_index=True)
    d["unid"] = d["CO_UNIDADE"].map(us.so_digitos)

    def num(c):
        return pd.to_numeric(d[c].str.replace(",", ".", regex=False), errors="coerce").fillna(0) if c in d else pd.Series(0, index=d.index)
    d["amb"], d["hosp"], d["outros"] = num("QT_CARGA_HORARIA_AMBULATORIAL"), num("QT_CARGA_HOR_HOSP_SUS"), num("QT_CARGA_HORARIA_OUTROS")
    print(f"Vínculos das unidades de Rio Claro: {len(d)} | unidades com algum vínculo: {d['unid'].nunique()} de {len(unidades)}")
    print(f"  com horas ambulatoriais > 0: {int((d['amb'] > 0).sum())} | só horas hospitalares: {int(((d['amb'] == 0) & (d['hosp'] > 0)).sum())}"
          f" | só 'outros': {int(((d['amb'] == 0) & (d['hosp'] == 0) & (d['outros'] > 0)).sum())} | tudo zero: {int(((d['amb'] == 0) & (d['hosp'] == 0) & (d['outros'] == 0)).sum())}")
    for c in ("TP_SUS_NAO_SUS", "IND_VINCULACAO"):
        if c in d:
            print(f"  {c}:", {k: int(v) for k, v in d[c].value_counts().head(8).items()})

    # ---------- 4. médicos por especialidade ----------
    titulo("4. Médicos por especialidade em Rio Claro (profissionais distintos; com a regra atual x sem regra de horas)")
    onto = os.path.join(pasta, f"tbAtividadeProfissional{mes}.csv")
    cod_o = us._codificacao(onto)
    o = pd.read_csv(onto, sep=us._separador(onto, cod_o), encoding=cod_o, dtype=str, keep_default_na=False)
    o.columns = [c.upper() for c in o.columns]
    medicas = {r["CO_CBO"].strip(): r["DS_ATIVIDADE_PROFISSIONAL"].strip() for _, r in o.iterrows()
               if us._sem_acento(r["DS_ATIVIDADE_PROFISSIONAL"]).upper().startswith("MEDICO")}
    m = d[d["CO_CBO"].str.strip().isin(medicas)].copy()
    m["esp"] = m["CO_CBO"].str.strip().map(medicas)
    if m.empty:
        print("Nenhum vínculo com ocupação MEDICO nessas unidades."); return 0
    tab = m.groupby("esp").agg(
        com_regra_atual=("CO_PROFISSIONAL_SUS", lambda s: s[m.loc[s.index, "amb"] > 0].nunique()),
        sem_regra_de_horas=("CO_PROFISSIONAL_SUS", "nunique"), unidades=("unid", "nunique")).sort_values("sem_regra_de_horas", ascending=False)
    print(tab.head(30).to_string())
    for chave in ("DERMATOLOG", "CARDIOLOG", "GINECOLOG", "MASTOLOG", "ONCOLOG"):
        sub = m[m["esp"].str.upper().str.contains(chave)]
        print(f"\n{chave}: {sub['CO_PROFISSIONAL_SUS'].nunique()} profissionais em {sub['unid'].nunique()} unidade(s):")
        for u, g in sub.groupby("unid"):
            print(f"   - {nome_de.get(u, u)} [{nat_de.get(u, '?')}] : {g['CO_PROFISSIONAL_SUS'].nunique()} (horas ambulatoriais>0: "
                  f"{g.loc[g['amb'] > 0, 'CO_PROFISSIONAL_SUS'].nunique()})")

    # ---------- 5. o que a busca devolve hoje ----------
    titulo("5. O que a busca da página devolve hoje (mesmo código da tela)")
    cnes = us.carregar_unidades()
    print("Avisos:", {k: v for k, v in cnes.attrs.items() if k.startswith("aviso") and v})
    print(f"Unidades com texto de serviços/especialidades: {int((cnes['servicos'].astype(str) != '').sum())} de {len(cnes)}")
    lista = oa.unificar(cnes, [])
    for busca in ("dermatologista", "cardiologista", "ginecologista", "ultrassom", "mamografia"):
        com = oa.filtrar(lista, "especialidade", busca=busca, so_publicos=True)
        sem = oa.filtrar(lista, "especialidade", busca=busca, so_publicos=False)
        print(f"  '{busca}': com 'só públicas' = {len(com)} | sem o filtro = {len(sem)}")
    print("\nExemplo de texto de uma unidade com mais itens:")
    cheia = cnes.assign(n=cnes['servicos'].astype(str).str.count(r"\|")).sort_values("n", ascending=False).head(1)
    for r in cheia.itertuples():
        print(f"  {r.nome} [{r.natureza}] -> {str(r.servicos)[:600]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
