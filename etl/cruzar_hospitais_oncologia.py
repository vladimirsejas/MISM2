import csv
import os
import sqlite3
import sys

import pandas as pd

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ_PROJETO, "algoritimos"))
import localizacao  # noqa: E402
import unidades_saude as us  # noqa: E402

# =====================================
# HOSPITAIS HABILITADOS EM ONCOLOGIA EM SP x CNES x BANCO (só lê; não altera nada)
#
# A lista oficial é a planilha do Ministério da Saúde "Hospitais habilitados em Oncologia" (habilitação 2023), recorte
# de SP, guardada em dados_geograficos\hospitais_oncologia_sp.csv (só dado público de estabelecimento). Este script
# cruza cada hospital da lista, pelo CNES, com:
#   - o arquivo nacional do CNES que o projeto já usa (banco\cnes\tbEstabelecimento*.csv): endereço, telefone,
#     coordenada e se o cadastro está ativo (dado mais novo que o PDF da Secretaria de 2021);
#   - o banco do Escudo: quantas internações por câncer o SIH registra em cada hospital (tabela internacoes);
#   - o catálogo do Apoio: todo CNES guardado lá precisa existir na lista oficial.
# Abre o banco em modo somente leitura. Não coloca ponto no mapa: coordenada é só conferida.
#
# Uso:  py etl\cruzar_hospitais_oncologia.py            (relatório na tela)
#       py etl\cruzar_hospitais_oncologia.py --salvar   (também grava analises\hospitais_oncologia_sp_cruzado.csv)
# =====================================

ARQUIVO_OFICIAL = os.path.join(RAIZ_PROJETO, "dados_geograficos", "hospitais_oncologia_sp.csv")
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")
SAIDA = os.path.join(RAIZ_PROJETO, "analises", "hospitais_oncologia_sp_cruzado.csv")
MINIMO_FORA_DA_LISTA = 200  # internações para um hospital fora da lista aparecer no relatório
LIMITE_KM_DO_CENTRO = 35    # coordenada do CNES a mais que isso do centro do município do hospital é apontada como suspeita
CAIXA_SP = (-25.5, -19.6, -53.3, -44.0)  # lat_min, lat_max, lon_min, lon_max (com folga): fora disso é erro de cadastro


def ler_oficiais(caminho=ARQUIVO_OFICIAL):
    """[{cnes, municipio, regiao_de_saude, nome_ministerio, codigo_habilitacao, habilitacao, tipo}] (cnes com 7 dígitos)."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in linha.items()} for linha in csv.DictReader(f, delimiter=";")]


def internacoes_por_cnes(banco, cnes):
    """{cnes: (internações, nome na tabela hospitais ou '')}; vazio se o banco ou as colunas não existem."""
    if not os.path.exists(banco):
        return {}
    conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    try:
        existe_nomes = bool(conexao.execute("SELECT name FROM sqlite_master WHERE name='hospitais'").fetchone())
        saida = {}
        for c in cnes:
            formas = (c, c.lstrip("0"))  # o banco pode guardar o CNES curto sem os zeros da frente
            n = conexao.execute(f"SELECT COUNT(*) FROM internacoes WHERE cnes IN ({','.join('?' * len(formas))})",
                                formas).fetchone()[0]
            nome = ""
            if existe_nomes:
                linha = conexao.execute(f"SELECT nome FROM hospitais WHERE cnes IN ({','.join('?' * len(formas))})",
                                        formas).fetchone()
                nome = linha[0] if linha else ""
            saida[c] = (n, nome)
        return saida
    except sqlite3.Error:
        return {}
    finally:
        conexao.close()


def maiores_fora_da_lista(banco, cnes_oficiais, minimo=MINIMO_FORA_DA_LISTA, limite=15):
    """Hospitais com muitas internações por câncer no SIH que NÃO estão na lista de habilitados: [(cnes, nome, n)]."""
    if not os.path.exists(banco):
        return []
    conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    try:
        linhas = conexao.execute("SELECT cnes, COUNT(*) FROM internacoes WHERE cnes IS NOT NULL GROUP BY cnes "
                                 "HAVING COUNT(*) >= ? ORDER BY COUNT(*) DESC", (minimo,)).fetchall()
        fora = [(c, n) for c, n in linhas if str(c).zfill(7) not in cnes_oficiais][:limite]
        nomes = {}
        if fora and conexao.execute("SELECT name FROM sqlite_master WHERE name='hospitais'").fetchone():
            nomes = dict(conexao.execute(
                f"SELECT cnes, nome FROM hospitais WHERE cnes IN ({','.join('?' * len(fora))})", [c for c, _ in fora]))
        return [(c, nomes.get(c, ""), n) for c, n in fora]
    except sqlite3.Error:
        return []
    finally:
        conexao.close()


def centros_dos_municipios(banco, cnes):
    """{cnes: (latitude, longitude)} do centro do município DO HOSPITAL (internacoes.municipio_hospital x municipios_localizacao).
    Só serve para conferir a coordenada do CNES: não é a posição do hospital."""
    if not os.path.exists(banco):
        return {}
    conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    try:
        saida = {}
        for c in cnes:
            formas = (c, c.lstrip("0"))
            linha = conexao.execute(
                f"SELECT m.latitude, m.longitude FROM internacoes i JOIN municipios_localizacao m ON m.codigo6 = i.municipio_hospital "
                f"WHERE i.cnes IN ({','.join('?' * len(formas))}) LIMIT 1", formas).fetchone()
            if linha:
                saida[c] = (float(linha[0]), float(linha[1]))
        return saida
    except sqlite3.Error:
        return {}
    finally:
        conexao.close()


def total_de_internacoes(banco):
    """Internações por câncer com hospital identificado no banco (para a parcela dos hospitais habilitados); 0 se não der."""
    if not os.path.exists(banco):
        return 0
    conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    try:
        return int(conexao.execute("SELECT COUNT(*) FROM internacoes WHERE cnes IS NOT NULL").fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        conexao.close()


def telefone_do_cnes(valor):
    """Telefone legível. O CNES às vezes junta dois números ou um ramal no mesmo campo: mostra o 1º e o resto à parte."""
    d = us.so_digitos(valor)
    if len(d) > 11:
        return f"{us.telefone_legivel(d[:10])} (+ {d[10:]})"
    return us.telefone_legivel(d)


def coordenada_confere(lat, lon, centro):
    """'ok', 'sem' (não tem), 'fora de SP' ou 'longe do município' (a mais de LIMITE_KM_DO_CENTRO do centro dele)."""
    if lat is None or lon is None:
        return "sem"
    la0, la1, lo0, lo1 = CAIXA_SP
    if not (la0 <= lat <= la1 and lo0 <= lon <= lo1):
        return "fora de SP"
    if centro is not None and localizacao.distancia_km(lat, lon, centro[0], centro[1]) > LIMITE_KM_DO_CENTRO:
        return "longe do município"
    return "ok"


def ler_cnes(pasta, cnes, tamanho_pedaco=us.TAMANHO_PEDACO):
    """{cnes: {nome, endereco, cep, telefone, lat, lon, ativo}} dos estabelecimentos pedidos no arquivo nacional do CNES.
    Devolve ({}, aviso) se o arquivo não existe ou não tem a coluna do CNES."""
    caminho = us.achar_arquivo(pasta)
    if caminho is None:
        return {}, "Arquivo tbEstabelecimento*.csv não encontrado em banco\\cnes: o relatório segue sem endereço e telefone."
    cod = us._codificacao(caminho)
    sep = us._separador(caminho, cod)
    colunas = list(pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, nrows=0).columns)
    achados = us._mapear_colunas(colunas)
    if "cnes" not in achados:
        return {}, f"O arquivo {os.path.basename(caminho)} não tem a coluna do CNES (colunas: {', '.join(colunas[:20])})."
    usar = list(dict.fromkeys(achados.values()))
    saida = {}
    for pedaco in pd.read_csv(caminho, sep=sep, encoding=cod, dtype=str, usecols=usar, chunksize=tamanho_pedaco,
                              keep_default_na=False, low_memory=False):
        codigos = pedaco[achados["cnes"]].map(us.so_digitos).str.zfill(7)
        for _, linha in pedaco.loc[codigos.isin(cnes)].iterrows():
            def campo(nome):
                return str(linha[achados[nome]]).strip() if nome in achados else ""
            motivo = us.so_digitos(campo("desabilitado")).lstrip("0") if "desabilitado" in achados else ""
            lat = pd.to_numeric(campo("lat").replace(",", "."), errors="coerce")
            lon = pd.to_numeric(campo("lon").replace(",", "."), errors="coerce")
            saida[us.so_digitos(campo("cnes")).zfill(7)] = {
                "nome": us.nome_legivel(campo("nome")),
                "endereco": us.endereco_legivel(campo("logradouro"), campo("numero"), campo("bairro")),
                "cep": us.cep_legivel(campo("cep")), "telefone": telefone_do_cnes(campo("telefone")),
                "lat": None if pd.isna(lat) else float(lat), "lon": None if pd.isna(lon) else float(lon),
                "ativo": motivo == "", "unidade": us.so_digitos(campo("unidade")),
            }
    return saida, ""


def conferir_catalogo(oficiais):
    """Problemas do catálogo do Apoio: CNES guardado que não está na lista oficial. [] se tudo certo."""
    import apoio
    cnes_oficiais = {o["cnes"] for o in oficiais}
    return [f"{i['id']}: CNES {i['cnes']} não está na lista oficial de SP" for i in apoio.ITENS
            if i.get("cnes") and str(i["cnes"]).zfill(7) not in cnes_oficiais]


def cruzar(oficiais, banco=BANCO, pasta_cnes=us.PASTA_CNES):
    """Lista de dicts (um por hospital oficial) com os dados do CNES e do banco, e o aviso do CNES (ou '')."""
    cnes = [o["cnes"] for o in oficiais]
    no_banco = internacoes_por_cnes(banco, cnes)
    no_cnes, aviso = ler_cnes(pasta_cnes, set(cnes))
    centros = centros_dos_municipios(banco, cnes)
    linhas = []
    for o in oficiais:
        n, nome_banco = no_banco.get(o["cnes"], (None, ""))
        c = no_cnes.get(o["cnes"])
        linhas.append({**o, "internacoes_cancer": n, "nome_no_banco": nome_banco,
                       "no_cnes": c is not None, "ativo_no_cnes": (c or {}).get("ativo"),
                       "endereco": (c or {}).get("endereco", ""), "telefone": (c or {}).get("telefone", ""),
                       "lat": (c or {}).get("lat"), "lon": (c or {}).get("lon"),
                       "coordenada": coordenada_confere((c or {}).get("lat"), (c or {}).get("lon"), centros.get(o["cnes"])),
                       "km_do_centro": (round(localizacao.distancia_km(c["lat"], c["lon"], *centros[o["cnes"]]), 1)
                                        if c and c.get("lat") is not None and c.get("lon") is not None and o["cnes"] in centros
                                        else None)})
    return linhas, aviso


def main(argv=None, banco=BANCO, pasta_cnes=us.PASTA_CNES, arquivo_oficial=ARQUIVO_OFICIAL, saida=SAIDA):
    argv = sys.argv[1:] if argv is None else argv
    oficiais = ler_oficiais(arquivo_oficial)
    linhas, aviso = cruzar(oficiais, banco, pasta_cnes)
    print(f"Lista oficial (Ministério da Saúde, habilitação 2023): {len(oficiais)} estabelecimentos habilitados em SP.\n")
    if aviso:
        print(f"[AVISO] {aviso}\n")
    if not os.path.exists(banco):
        print(f"[AVISO] Banco não encontrado em {banco}: o relatório segue sem as internações.\n")

    print("CNES      Município              Tipo                 Internações por câncer (SIH) · cadastro no CNES · nome")
    for r in sorted(linhas, key=lambda r: (-(r["internacoes_cancer"] or 0), r["municipio"])):
        n = "sem banco" if r["internacoes_cancer"] is None else f"{r['internacoes_cancer']:>6}"
        if not r["no_cnes"]:
            cad = "não está no arquivo do CNES"
        else:
            ativo = "ativo" if r["ativo_no_cnes"] else "DESABILITADO"
            geo = {"ok": "coordenada ok", "sem": "sem coordenada"}.get(r["coordenada"], f"COORDENADA SUSPEITA ({r['coordenada']})")
            cad = f"{ativo}, {geo}, tel {r['telefone'] or '-'}"
        print(f"{r['cnes']}  {r['municipio']:<22.22} {r['tipo']:<20.20} {n:>9} · {cad} · {r['nome_ministerio'][:45]}")

    com_cnes = [r for r in linhas if r["no_cnes"]]
    if com_cnes:
        boas = sum(1 for r in com_cnes if r["coordenada"] == "ok")
        suspeitas = [f"{r['municipio']} {r['cnes']} ({r['coordenada']}"
                     + (f", {r['km_do_centro']:.0f} km do centro; lat {r['lat']}, lon {r['lon']}" if r["km_do_centro"] is not None else f"; lat {r['lat']}, lon {r['lon']}")
                     + ")" for r in com_cnes if r["coordenada"] not in ("ok", "sem")]
        print(f"\nCoordenadas do CNES: {boas} de {len(com_cnes)} dentro de SP e a até {LIMITE_KM_DO_CENTRO} km do centro do município do hospital"
              + (f"; suspeitas: {'; '.join(suspeitas)}" if suspeitas else "") + ". Conferida só a plausibilidade; ponto no mapa só depois de olhar.")
    total = total_de_internacoes(banco)
    habilitados = sum(r["internacoes_cancer"] or 0 for r in linhas)
    if total:
        print(f"\nInternações por câncer no SIH em hospitais da lista oficial: {habilitados} de {total} "
              f"({100 * habilitados / total:.1f}%). O resto está em hospitais que não constam na lista de 2023 (a lista é de um só ano e o banco vai de 2013 a 2025).")
    sem = [r for r in linhas if r["internacoes_cancer"] == 0]
    if sem:
        print(f"\nHospitais da lista sem nenhuma internação por câncer no banco: {len(sem)} de {len(linhas)}"
              + (" (primeiros: " + "; ".join(f"{r['municipio']} {r['cnes']}" for r in sem[:8]) + ")" if len(sem) < 40 else ""))
    fora = maiores_fora_da_lista(banco, {o["cnes"] for o in oficiais})
    if fora:
        print(f"\nHospitais com {MINIMO_FORA_DA_LISTA}+ internações por câncer no SIH que NÃO estão na lista de habilitados "
              "(não é erro: pode ser cirurgia em hospital geral, habilitação antiga ou nova):")
        for c, nome, n in fora:
            print(f"  {c}  {n:>6} internações  {nome}")
    problemas = conferir_catalogo(oficiais)
    print("\nCatálogo do Apoio x lista oficial: " + ("todos os CNES do catálogo estão na lista." if not problemas
                                                      else "PROBLEMAS:"))
    for p in problemas:
        print("  - " + p)

    if "--salvar" in argv:
        os.makedirs(os.path.dirname(saida), exist_ok=True)
        pd.DataFrame(linhas).to_csv(saida, sep=";", index=False, encoding="utf-8-sig")
        print(f"\nGravado em {saida}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
