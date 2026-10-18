"""Lista OFICIAL dos estabelecimentos habilitados em oncologia no Brasil (Ministério da Saúde, habilitação 2023).

Lê a planilha "Hospitais habilitados em Oncologia.xlsx" (em banco\\cnes ou no caminho dado) e grava, em
dados_geograficos\\, só dado público:
  - hospitais_oncologia_br.csv : o Brasil todo
  - hospitais_oncologia_sp.csv : o recorte de São Paulo (o que as ferramentas antigas já leem)

A planilha usa CÉLULAS MESCLADAS: em muitas linhas a UF, o município e a macrorregião ficam em branco porque
valem os da linha de cima. A primeira versão (18/10/2026) só lia as linhas com UF preenchida e perdeu 8 dos 88
estabelecimentos de SP (Albert Einstein, Santa Casa de Itu...). Aqui a UF/município/macro são preenchidos para baixo.
Sem dependências: lê o .xlsx com zipfile + xml.

    py etl\\gerar_lista_hospitais_oncologia.py
    py etl\\gerar_lista_hospitais_oncologia.py "C:\\caminho\\planilha.xlsx"
"""
import csv
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PADRAO = os.path.join(RAIZ, "banco", "cnes", "Hospitais habilitados em Oncologia.xlsx")
SAIDA = os.path.join(RAIZ, "dados_geograficos")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def ler_planilha(caminho):
    """Primeira aba do .xlsx como lista de linhas (cada linha é uma lista de textos ou None)."""
    with zipfile.ZipFile(caminho) as z:
        compartilhadas = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                compartilhadas.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        aba = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n))[0]
        linhas = {}
        for c in ET.fromstring(z.read(aba)).iter(f"{{{NS['m']}}}c"):
            ref = re.match(r"([A-Z]+)(\d+)", c.get("r"))
            col = 0
            for ch in ref.group(1):
                col = col * 26 + ord(ch) - 64
            v = c.find("m:v", NS)
            if c.get("t") == "inlineStr":
                valor = "".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t"))
            elif v is None or v.text is None:
                continue
            elif c.get("t") == "s":
                valor = compartilhadas[int(v.text)]
            else:
                valor = v.text
            linhas.setdefault(int(ref.group(2)), {})[col - 1] = valor.strip() if isinstance(valor, str) else valor
        if not linhas:
            return []
        return [[linhas.get(n, {}).get(i) or None for i in range(10)] for n in range(1, max(linhas) + 1)]


def tipo_do_estabelecimento(habilitacoes, codigos):
    """UNACON, CACON, hospital geral com cirurgia oncológica ou serviço de radioterapia (o mais completo vale)."""
    texto = " ".join(habilitacoes).upper()
    cods = re.findall(r"17\.\d\d", " ".join(codigos))
    if "CACON" in texto.replace("UNACON", "") or any(c in ("17.12", "17.13") for c in cods):
        return "CACON"
    if "UNACON" in texto or any(c in ("17.06", "17.07", "17.08", "17.09", "17.10", "17.11") for c in cods):
        return "UNACON"
    if "HOSPITAL GERAL" in texto or "17.14" in cods:
        return "Hospital geral com cirurgia oncológica"
    if "RADIOTERAPIA" in texto or any(c in ("17.15", "17.16") for c in cods):
        return "Serviço isolado de radioterapia"
    return "Tipo não informado"  # a planilha traz o estabelecimento sem código nem descrição de habilitação


def estabelecimentos(linhas):
    """Todos os estabelecimentos (um por CNES), com UF/município/macrorregião preenchidos para baixo."""
    cabecalhos = [i for i, r in enumerate(linhas) if r[1] == "UF"]
    if not cabecalhos:
        raise SystemExit("Não achei o cabeçalho (coluna UF) na planilha.")
    uf = mun = macro = None
    saida = {}
    for i, r in enumerate(linhas):
        if i <= cabecalhos[0]:
            continue
        if r[1] == "UF":  # 2º quadro da planilha: recomeça o preenchimento
            uf = mun = macro = None
            continue
        uf, mun, macro = (r[1] or uf), (r[2] or mun), (r[3] or macro)
        if not r[5]:
            continue
        cnes = re.sub(r"\D", "", str(r[5])).zfill(7)
        d = saida.setdefault(cnes, {"cnes": cnes, "uf": uf, "municipio": mun, "regiao_de_saude": macro,
                                    "nome_ministerio": r[4] or "", "codigos": [], "habilitacoes": []})
        if r[6]:
            d["codigos"].append(r[6])
        if r[7]:
            d["habilitacoes"].append(r[7])
    for d in saida.values():
        d["codigo_habilitacao"] = " | ".join(d.pop("codigos"))
        d["habilitacao"] = " | ".join(d.pop("habilitacoes"))
        d["tipo"] = tipo_do_estabelecimento([d["habilitacao"]], [d["codigo_habilitacao"]])
    return list(saida.values())


CAMPOS_SP = ["cnes", "municipio", "regiao_de_saude", "nome_ministerio", "codigo_habilitacao", "habilitacao", "tipo"]
CAMPOS_BR = ["cnes", "uf"] + CAMPOS_SP[1:]


def gravar(lista, pasta=SAIDA):
    os.makedirs(pasta, exist_ok=True)
    for nome, campos, itens in (("hospitais_oncologia_br.csv", CAMPOS_BR, lista),
                                ("hospitais_oncologia_sp.csv", CAMPOS_SP, [d for d in lista if d["uf"] == "SP"])):
        with open(os.path.join(pasta, nome), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
            w.writeheader()
            w.writerows(itens)


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else PADRAO
    if not os.path.isfile(caminho):
        print(f"Planilha não encontrada: {caminho}\nColoque 'Hospitais habilitados em Oncologia.xlsx' em banco\\cnes ou passe o caminho.")
        return 1
    lista = estabelecimentos(ler_planilha(caminho))
    gravar(lista)
    por_uf = {}
    for d in lista:
        por_uf[d["uf"]] = por_uf.get(d["uf"], 0) + 1
    tipos = {}
    for d in lista:
        tipos[d["tipo"]] = tipos.get(d["tipo"], 0) + 1
    print(f"{len(lista)} estabelecimentos habilitados no Brasil, {len(por_uf)} estados.")
    print("Por tipo:", tipos)
    print("Por estado:", dict(sorted(por_uf.items(), key=lambda x: -x[1])))
    print("Gravado em dados_geograficos\\hospitais_oncologia_br.csv e hospitais_oncologia_sp.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
