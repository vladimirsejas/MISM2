import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listar_meses_pysus as lm  # noqa: E402

falhas = []


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


checar("lê ano e mês do nome do arquivo", lm.meses_no_nome("RDSP2601.dbc") == (2026, 1)
       and lm.meses_no_nome("PASP2603a.dbc") == (2026, 3) and lm.meses_no_nome("sih/RDSP2412.dbc") == (2024, 12))
checar("nome fora do padrão ou mês impossível vira None", lm.meses_no_nome("LEIAME.txt") is None
       and lm.meses_no_nome("RDSP2613.dbc") is None)
presentes, faltando, ilegiveis = lm.resumir(["RDSP2601.dbc", "RDSP2602.dbc", "RDSP2501.dbc", "x.txt"], 2026)
checar("resumir: só conta o ano pedido, lista o que falta e separa o nome ilegível",
       presentes == [1, 2] and faltando == list(range(3, 13)) and ilegiveis == ["x.txt"])


class Arquivo:
    def __init__(self, nome):
        self.name = nome


class PySUSFalso:
    chamadas = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def query(self, dataset, state, year, group=None):
        PySUSFalso.chamadas.append((dataset, group, state, year))
        if group == "AR":
            raise RuntimeError("grupo desconhecido")
        if dataset == "sim":
            return [Arquivo("DOSP2023.dbc"), Arquivo("DOSP2022.dbc")]
        return [Arquivo(f"{group}SP26{m:02d}.dbc") for m in (1, 2, 3)]


r = asyncio.run(lm.listar(2026, PySUSFalso))
checar("listar pergunta SIH, SIA (quimio e radio), CNES (equipamentos e leitos) e SIM de SP no ano pedido e nada é baixado",
       PySUSFalso.chamadas == [("sih", "RD", "SP", 2026), ("sia", "AQ", "SP", 2026), ("sia", "AR", "SP", 2026),
                               ("cnes", "EQ", "SP", 2026), ("cnes", "LT", "SP", 2026), ("sim", None, "SP", 2026)]
       and not hasattr(PySUSFalso, "download"))
checar("SIM é um arquivo por ano: 2026 não existe na lista simulada (só 2022 e 2023); 2023 existe",
       r[("sim", None)] == ("anual", False, ["DOSP2023.dbc", "DOSP2022.dbc"])
       and asyncio.run(lm.listar(2023, PySUSFalso))[("sim", None)][1] is True)
checar("existe_arquivo_anual não confunde DOSP2023 com DORJ2023 nem com outro ano",
       lm.existe_arquivo_anual(["DOSP2023.dbc"], 2023) and not lm.existe_arquivo_anual(["DORJ2023.dbc"], 2023)
       and not lm.existe_arquivo_anual(["DOSP2023.dbc"], 2024))
checar("um erro numa base não derruba as outras", isinstance(r[("sia", "AR")], str) and r[("sih", "RD")][0] == [1, 2, 3]
       and r[("cnes", "LT")][0] == [1, 2, 3])
print()
print("Todas as checagens passaram." if not falhas else f"{len(falhas)} falha(s).")
sys.exit(1 if falhas else 0)
