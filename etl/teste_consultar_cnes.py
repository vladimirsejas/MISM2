"""Teste da consulta ao CNES (arquivo sintético)."""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consultar_cnes as q  # noqa: E402

falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


CAB = "CO_UNIDADE;CO_CNES;NO_FANTASIA;NO_RAZAO_SOCIAL;NO_LOGRADOURO;NU_ENDERECO;NO_BAIRRO;CO_CEP;NU_TELEFONE;NU_LATITUDE;NU_LONGITUDE;CO_MOTIVO_DESAB"
LINHAS = [
    "5103402655519;2655519;HOSPITAL SANTA CASA;SOCIEDADE BENEFICENTE SANTA CASA;PRACA DO SEMINARIO;141;CENTRO;78015140;6530511946;-15,596000;-56,097000;12",
    "5103409841903;9841903;HOSPITAL ESTADUAL SANTA CASA;ESTADO DE MATO GROSSO;PRACA DO SEMINARIO;141;CENTRO;78015140;6536188800;-15,598000;-56,099000;",
    "3543902082888;2082888;SANTA CASA DE RIO CLARO;SANTA CASA;RUA DOIS;297;CENTRO;13500000;1935357000;-22,411;-47,561;",
]
with tempfile.TemporaryDirectory() as pasta:
    with open(os.path.join(pasta, "tbEstabelecimento202608.csv"), "w", encoding="latin-1", newline="") as f:
        f.write(CAB + "\n" + "\n".join(LINHAS) + "\n")
    achados, aviso = q.consultar(pasta, ["2655519", "9841903"])
    checar("por código: acha os dois, sem aviso", not aviso and {r["cnes"] for r in achados} == {"2655519", "9841903"})
    checar("diz quem está ativo e quem está desabilitado (e o ativo vem primeiro)",
           achados[0]["cnes"] == "9841903" and achados[0]["ativo"] and not achados[1]["ativo"] and achados[1]["motivo_desab"] == "12")
    checar("traz estado e município pelo CO_UNIDADE (MT, 510340 = Cuiabá)", achados[0]["uf"] == "MT" and achados[0]["municipio6"] == "510340")
    checar("traz coordenada para conferir no mapa", abs(achados[0]["lat"] + 15.598) < 1e-6)
    por_nome, _ = q.consultar(pasta, nome="santa casa", uf="MT")
    checar("por nome (sem acento/maiúscula) filtrando o estado: só Mato Grosso", {r["cnes"] for r in por_nome} == {"2655519", "9841903"})
    todos, _ = q.consultar(pasta, nome="Santa Casa")
    checar("por nome sem filtrar o estado: acha também a de Rio Claro", {r["cnes"] for r in todos} == {"2655519", "9841903", "2082888"})
    checar("código inexistente: nada", q.consultar(pasta, ["1111111"])[0] == [])
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        codigo = q.main(["2655519", "9841903"], pasta=pasta)
    texto = saida.getvalue()
    checar("o relatório imprime DESABILITADO, ATIVO e o link do Google Maps", codigo == 0 and "DESABILITADO" in texto and "ATIVO" in texto and "google.com/maps?q=-15.598000,-56.099000" in texto)
    with contextlib.redirect_stdout(io.StringIO()):
        sem_arquivo = q.main(["2655519"], pasta=os.path.join(pasta, "nao_existe"))
    checar("sem o arquivo do CNES: avisa, sem quebrar", sem_arquivo == 1)

if falhas:
    print("\nFALHARAM:", *falhas, sep="\n  - ")
    sys.exit(1)
print("\nTodas as checagens da consulta ao CNES passaram.")
