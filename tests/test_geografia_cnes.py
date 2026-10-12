import csv
import json
import tempfile
import unittest
from pathlib import Path

from etl.geografia_cnes import (
    coordenada,
    montar_catalogo,
    normalizar_cep,
)


def escrever_csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, delimiter=";", quotechar='"')
        escritor.writeheader()
        escritor.writerows(linhas)


class TestGeografiaCnes(unittest.TestCase):
    def test_normaliza_cep_preservando_oito_digitos(self):
        self.assertEqual(normalizar_cep("13500-030"), "13500030")
        self.assertEqual(normalizar_cep("1350003"), "")

    def test_rejeita_coordenada_fora_da_area_de_referencia(self):
        self.assertEqual(coordenada("-23.55", "-46.63"), (None, None))
        self.assertEqual(coordenada("-22.41", "-47.56"), (-22.41, -47.56))

    def test_gera_catalogo_local_sem_tocar_banco_analitico(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta = raiz / "cnes"
            pasta.mkdir()
            arquivo_estab = pasta / "tbEstabelecimento202608.csv"
            colunas = [
                "CO_UNIDADE", "CO_CNES", "NO_FANTASIA", "NO_RAZAO_SOCIAL",
                "CO_CEP", "CO_MUNICIPIO_GESTOR", "CO_NATUREZA_JUR", "CO_MOTIVO_DESAB",
                "NO_LOGRADOURO", "NU_ENDERECO", "NO_COMPLEMENTO", "NO_BAIRRO",
                "NU_TELEFONE", "NU_LATITUDE", "NU_LONGITUDE", "CO_TIPO_UNIDADE",
            ]
            base = {
                "CO_UNIDADE": "3543901234567", "CO_CNES": "1234567",
                "NO_FANTASIA": "UBS Teste", "NO_RAZAO_SOCIAL": "Unidade Teste",
                "CO_CEP": "13500030", "CO_MUNICIPIO_GESTOR": "354390",
                "CO_NATUREZA_JUR": "1244", "CO_MOTIVO_DESAB": "",
                "NO_LOGRADOURO": "Rua A", "NU_ENDERECO": "10", "NO_COMPLEMENTO": "",
                "NO_BAIRRO": "Centro", "NU_TELEFONE": "1935000000",
                "NU_LATITUDE": "-22.41", "NU_LONGITUDE": "-47.56", "CO_TIPO_UNIDADE": "01",
            }
            privado = dict(base, CO_UNIDADE="3543901234568", CO_CNES="1234568",
                           NO_FANTASIA="Clínica Privada", CO_NATUREZA_JUR="3999")
            inativo = dict(base, CO_UNIDADE="3543901234569", CO_CNES="1234569",
                           NO_FANTASIA="Unidade Inativa", CO_MOTIVO_DESAB="12")
            escrever_csv(arquivo_estab, colunas, [base, privado, inativo])

            escrever_csv(pasta / "tbServicoEspecializado202608.csv",
                         ["CO_SERVICO_ESPECIALIZADO", "DS_SERVICO_ESPECIALIZADO"],
                         [{"CO_SERVICO_ESPECIALIZADO": "123", "DS_SERVICO_ESPECIALIZADO": "Atenção Básica"}])
            escrever_csv(pasta / "tbClassificacaoServico202608.csv",
                         ["CO_CLASSIFICACAO_SERVICO", "DS_CLASSIFICACAO_SERVICO"],
                         [{"CO_CLASSIFICACAO_SERVICO": "45", "DS_CLASSIFICACAO_SERVICO": "Equipe Saúde da Família"}])
            escrever_csv(pasta / "rlEstabServClass202608.csv",
                         ["CO_UNIDADE", "CO_SERVICO_ESPECIALIZADO", "CO_CLASSIFICACAO_SERVICO"],
                         [{"CO_UNIDADE": "3543901234567", "CO_SERVICO_ESPECIALIZADO": "123",
                           "CO_CLASSIFICACAO_SERVICO": "45"}])
            escrever_csv(pasta / "tbEquipe202608.csv",
                         ["CO_UNIDADE", "CO_SEQ_EQUIPE", "TP_EQUIPE", "NO_REFERENCIA"],
                         [{"CO_UNIDADE": "3543901234567", "CO_SEQ_EQUIPE": "999",
                           "TP_EQUIPE": "70", "NO_REFERENCIA": "Equipe Centro"}])
            escrever_csv(pasta / "tbEstabHorarioAtend202608.csv",
                         ["CO_UNIDADE", "CO_DIA_SEMANA", "HR_INICIO", "HR_FIM"],
                         [{"CO_UNIDADE": "3543901234567", "CO_DIA_SEMANA": "2",
                           "HR_INICIO": "0800", "HR_FIM": "1700"}])

            indice = raiz / "indice.json"
            indice.write_text(json.dumps({"ceps": {"13500030": [-22.41, -47.56, 150, "setor", 2]}}),
                               encoding="utf-8")
            saida = raiz / "resultado.json"
            catalogo = montar_catalogo(pasta, indice, saida)

            self.assertTrue(saida.exists())
            self.assertEqual(catalogo["meta"]["total_estabelecimentos"], 1)
            item = catalogo["servicos"][0]
            self.assertEqual(item["nome"], "UBS Teste")
            self.assertEqual(item["cnes"], "1234567")
            self.assertEqual(len(item["servicos_cnes"]), 1)
            self.assertIn("Atenção Básica", item["servicos_cnes"][0]["descricao"])
            self.assertEqual(len(item["equipes_cnes"]), 1)
            self.assertEqual(len(item["horarios_cnes"]), 1)
            self.assertEqual(json.loads(saida.read_text(encoding="utf-8"))["meta"]["municipio_ibge"], "354390")


if __name__ == "__main__":
    unittest.main()
