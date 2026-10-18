"""Teste do leitor da planilha do Ministério (UF em branco por célula mesclada, 2º quadro, CNES curto)."""
import os
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_lista_hospitais_oncologia as g  # noqa: E402

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


def xlsx(caminho, linhas):
    """.xlsx mínimo (textos em linha) só para o teste."""
    cols = "ABCDEFGHIJ"
    corpo = []
    for n, linha in enumerate(linhas, start=1):
        cel = "".join(f'<c r="{cols[i]}{n}" t="inlineStr"><is><t>{escape(str(v))}</t></is></c>'
                      for i, v in enumerate(linha) if v is not None)
        corpo.append(f'<row r="{n}">{cel}</row>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           f'<sheetData>{"".join(corpo)}</sheetData></worksheet>')
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", xml)


CAB = ["TOTAL DE HABILITAÇÕES", "UF", "MUNICÍPIO", "MACRORREGIÃO DE SAÚDE", "ESTABELECIMENTO", "CNES", "CÓDIGO", "HABILITAÇÃO"]
LINHAS = [
    [None] * 8, ["HOSPITAIS HABILITADOS EM ONCOLOGIA"], [None] * 8, CAB,
    ["1", "SP", "São Paulo", "RRAS 6", "Hospital A", "2077523", "17.06", "UNACON"],
    ["1", "SP", "São Paulo", "RRAS 6", "Hospital B", "2077477", "17.13", "CACON com Serviço de Oncologia Pediátrica"],
    [None, None, "São Paulo", "RRAS 6", "Hospital Israelita Albert Einstein", "2058391", "17.15", "Serviço de Radioterapia de Complexo Hospitalar"],
    [None, None, "Campinas", "RRAS 15", "Hospital Geral C", "2091755", "17.14", "Hospital Geral com Cirurgia Oncológica"],
    ["1", "MG", "Belo Horizonte", "Macro Centro", "Hospital D", "10464", "17.07", "UNACON com Serviço de Radioterapia"],
    [None, None, None, None, "Sem descrição", "7777777", None, None],
    ["317"], [None] * 8,
    CAB,
    ["1", "RJ", "Niterói", "Macro Metro", "Serviço E", "8753", "17.15", "Serviço de Radioterapia de Complexo Hospitalar"],
    ["7"],
]

with tempfile.TemporaryDirectory() as pasta:
    caminho = os.path.join(pasta, "p.xlsx")
    xlsx(caminho, LINHAS)
    lista = {d["cnes"]: d for d in g.estabelecimentos(g.ler_planilha(caminho))}
    checar("lê todos os estabelecimentos dos dois quadros (7)", len(lista) == 7)
    checar("linha com UF em branco herda a UF e o município da de cima (o defeito que perdeu 8 hospitais de SP)",
           lista["2058391"]["uf"] == "SP" and lista["2058391"]["municipio"] == "São Paulo")
    checar("a UF muda quando a planilha muda e a linha de continuação segue a nova",
           lista["2091755"]["uf"] == "SP" and lista["2091755"]["municipio"] == "Campinas"
           and lista["0010464"]["uf"] == "MG" and lista["7777777"]["uf"] == "MG" and lista["7777777"]["municipio"] == "Belo Horizonte")
    checar("o 2º quadro recomeça o preenchimento (não herda a UF do último hospital do 1º)", lista["0008753"]["uf"] == "RJ")
    checar("CNES curto ganha zeros à esquerda (7 dígitos)", all(len(c) == 7 for c in lista) and "0010464" in lista and "0008753" in lista)
    checar("tipos: UNACON, CACON, hospital geral, radioterapia, não informado",
           [lista[c]["tipo"] for c in ("2077523", "2077477", "2091755", "2058391", "7777777")]
           == ["UNACON", "CACON", "Hospital geral com cirurgia oncológica", "Serviço isolado de radioterapia", "Tipo não informado"])
    g.gravar(list(lista.values()), pasta)
    br = open(os.path.join(pasta, "hospitais_oncologia_br.csv"), encoding="utf-8-sig").read().splitlines()
    sp = open(os.path.join(pasta, "hospitais_oncologia_sp.csv"), encoding="utf-8-sig").read().splitlines()
    checar("grava o Brasil (7) e o recorte de SP (4) com os cabeçalhos esperados",
           len(br) == 8 and len(sp) == 5 and br[0].startswith("cnes;uf;municipio") and sp[0].startswith("cnes;municipio"))

if falhas:
    print("\nFALHARAM:", *falhas, sep="\n  - ")
    sys.exit(1)
print("\nTodas as checagens do leitor da planilha passaram.")
