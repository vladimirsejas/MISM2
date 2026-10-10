import tempfile
import unittest
from pathlib import Path

from rede_servicos_local import carregar_estabelecimentos, resumir_rede_local


class TesteRedeServicosLocal(unittest.TestCase):
    def test_filtra_apenas_rio_claro_e_remove_cnes_duplicado(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            arquivo = pasta / "tbEstabelecimento202608.csv"
            arquivo.write_text(
                "CO_CNES;NO_FANTASIA;CO_MUNICIPIO_GESTOR;TP_UNIDADE\n"
                "123;Unidade A;3543907; posto\n"
                "123;Unidade A duplicada;3543907; posto\n"
                "456;Unidade B;3509502; hospital\n",
                encoding="latin-1",
            )

            dados = carregar_estabelecimentos(pasta)

            self.assertEqual(len(dados), 1)
            self.assertEqual(dados.iloc[0]["cnes"], "123")
            self.assertEqual(dados.iloc[0]["nome"], "Unidade A")
            self.assertEqual(dados.iloc[0]["codigo_municipio"], "3543907")

    def test_pasta_sem_arquivo_retorna_aviso_sem_excecao(self):
        with tempfile.TemporaryDirectory() as temporario:
            dados = carregar_estabelecimentos(temporario)
            self.assertTrue(dados.empty)
            self.assertIn("Nenhum arquivo", dados.attrs["aviso"])

    def test_resumo_vazio_nao_inventa_quantidades(self):
        resumo = resumir_rede_local(carregar_estabelecimentos("pasta_inexistente"))
        self.assertEqual(resumo["total_estabelecimentos"], 0)


if __name__ == "__main__":
    unittest.main()
