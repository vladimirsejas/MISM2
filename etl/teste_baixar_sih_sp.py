import os
import tempfile
from pathlib import Path

import pandas as pd

import baixar_sih_sp as b
import completude_meses as cm

# =====================================
# TESTE do baixar_sih_sp.py com um DATASUS SIMULADO (sem internet):
#   - 2024/06 não é listado na 1ª rodada (como os buracos reais);
#   - 2024/03 falha 2 vezes antes de baixar (tem que tentar de novo);
#   - cada mês traz homens e outros CIDs (os filtros descartam) e
#     moradoras de outro estado (ENTRAM: o Estado conta o atendimento em SP).
# 1ª rodada: 11 de 12 meses, NÃO troca os CSVs. 2ª rodada (mês volta):
# pula os 11 prontos, baixa só o que falta, troca os CSVs com backup,
# e a completude dá 12/12.
# =====================================

ANO = 2024
esconder = {6}
falhas_restantes = {3: 2}
baixados = []


class Arquivo:
    def __init__(self, ano, mes):
        self.name = f"RDSP{ano % 100:02d}{mes:02d}.parquet"
        self.ano, self.mes = ano, mes


class Baixado:
    def __init__(self, path):
        self.path = path


class PySUSFalso:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def query(self, dataset, group, state, year):
        assert (dataset, group, state) == ("sih", "RD", "SP")
        return [Arquivo(year, m) for m in range(1, 13) if m not in esconder]

    async def download(self, arquivo):
        if falhas_restantes.get(arquivo.mes, 0) > 0:
            falhas_restantes[arquivo.mes] -= 1
            raise ConnectionError("conexão caiu (simulado)")
        baixados.append(arquivo.mes)
        linhas = []
        for cid in ("C509", "C530", "C189", "C200", "C56", "C341", "C73", "C443", "I10"):
            linhas += [
                {"ANO_CMPT": str(arquivo.ano), "MES_CMPT": f"{arquivo.mes:02d}", "DIAG_PRINC": cid, "SEXO": "3",
                 "MUNIC_RES": "354390", "IDADE": "50", "DIAS_PERM": "2", "MORTE": "0", "VAL_TOT": "100.0"},
                {"ANO_CMPT": str(arquivo.ano), "MES_CMPT": f"{arquivo.mes:02d}", "DIAG_PRINC": cid, "SEXO": "1",
                 "MUNIC_RES": "354390", "IDADE": "50", "DIAS_PERM": "2", "MORTE": "0", "VAL_TOT": "100.0"},
                {"ANO_CMPT": str(arquivo.ano), "MES_CMPT": f"{arquivo.mes:02d}", "DIAG_PRINC": cid, "SEXO": "3",
                 "MUNIC_RES": "330455", "IDADE": "50", "DIAS_PERM": "2", "MORTE": "0", "VAL_TOT": "100.0"},
            ]
        caminho = Path(tempfile.mkdtemp()) / arquivo.name
        pd.DataFrame(linhas).to_parquet(caminho, index=False)
        return Baixado(str(caminho))


def main():
    base = Path(tempfile.mkdtemp())
    # CSV atual de mama (antigo, incompleto) para provar backup e leitura do CID
    (base / "cancer_mama_sp").mkdir()
    pd.DataFrame({"ANO_CMPT": ["2024"], "MES_CMPT": ["01"], "DIAG_PRINC": ["C504"]}).to_csv(
        base / "cancer_mama_sp" / "antigo.csv", index=False)
    b.BASE_DADOS, b.PASTA_MESES = base, base / "_download_sih_sp"
    b.carga.BASE_DADOS = str(base)
    b.ANOS, b.ESPERA_INICIAL = [ANO], 0

    filtros = b.definir_filtros()
    assert filtros["cancer_mama_sp"][1:] == (["C50"], "do CSV atual"), filtros["cancer_mama_sp"]
    assert filtros["cancer_colorretal_sp"][1] == ["C18", "C19", "C20"]
    print("[OK] CID lido do CSV atual (mama) e padrão para os demais")

    assert b.main(PySUSFalso) == 1
    assert (base / "cancer_mama_sp" / "antigo.csv").exists()
    assert sum(b.mes_pronto(ANO, m) for m in range(1, 13)) == 11 and not b.mes_pronto(ANO, 6)
    assert 3 in baixados
    print("[OK] 1ª rodada: 2024/03 baixou depois de 2 falhas; 2024/06 listado como falta; CSVs NÃO trocados")

    esconder.clear()
    baixados.clear()
    assert b.main(PySUSFalso) == 0
    assert baixados == [6], baixados
    print("[OK] 2ª rodada: pulou os 11 prontos e baixou só 2024/06")

    backups = list(base.glob("_backup_*/cancer_mama_sp/antigo.csv"))
    assert len(backups) == 1 and not (base / "cancer_mama_sp" / "antigo.csv").exists()
    print("[OK] CSV antigo guardado no backup, fora da pasta da carga")

    novo = pd.read_csv(base / "cancer_mama_sp" / "cancer_mama_mulheres_sp_2024_2024.csv", dtype=str)
    assert len(novo) == 24 and set(novo["SEXO"]) == {"3"} and set(novo["MUNIC_RES"]) == {"354390", "330455"}
    assert set(novo["DIAG_PRINC"]) == {"C509"}
    colo = pd.read_csv(base / "cancer_colorretal_sp" / "cancer_colorretal_mulheres_sp_2024_2024.csv", dtype=str)
    assert set(colo["DIAG_PRINC"]) == {"C189", "C200"} and len(colo) == 48
    print("[OK] filtros: só mulheres e o CID do câncer; moradoras de outro estado (RJ) ENTRAM")

    cm.carga.BASE_DADOS = str(base)
    situ = cm.situacao_dos_meses(cm.contar_por_mes(str(base / "cancer_mama_sp" / "cancer_mama_mulheres_sp_2024_2024.csv")))
    assert all(v == "X" for v in situ[ANO].values()), situ
    print("[OK] completude_meses lê o CSV novo: 12/12")
    # --- lacunas da fonte: sem a opção nada troca; com a opção troca pelos meses que existem ---
    def nova_base():
        base2 = Path(tempfile.mkdtemp())
        b.BASE_DADOS, b.PASTA_MESES = base2, base2 / "_download_sih_sp_atendimento"
        b.carga.BASE_DADOS = str(base2)
        return base2

    base2 = nova_base()
    esconder.add(6)
    assert b.main(PySUSFalso) == 1 and not list(base2.glob("cancer_mama_sp/*.csv"))
    assert b.main(PySUSFalso, aceitar_lacunas=True) == 0
    csv2 = pd.read_csv(base2 / "cancer_mama_sp" / "cancer_mama_mulheres_sp_2024_2024.csv", dtype=str)
    assert len(csv2) == 22 and "06" not in set(csv2["MES_CMPT"].str.zfill(2)), len(csv2)
    print("[OK] fonte sem 2024/06: sem a opção nada troca; com --aceitar-lacunas-da-fonte troca pelos 11 meses que existem")

    base3 = nova_base()
    falhas_restantes[3] = 99  # erro de download de verdade, não lacuna da fonte
    assert b.main(PySUSFalso, aceitar_lacunas=True) == 1 and not list(base3.glob("cancer_mama_sp/*.csv"))
    print("[OK] erro de download de verdade continua barrando, mesmo com a opção")
    print("\nTodas as checagens do baixar_sih_sp passaram.")


if __name__ == "__main__":
    main()
