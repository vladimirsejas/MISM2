"""Testes da família de símbolos autorais do MISM2."""
import re
import unittest

from dashboard.simbolos_mism import simbolo


class TestSimbolosMISM(unittest.TestCase):
    def test_todos_os_simbolos_geram_svg(self):
        for nome in (
            "saude", "tendencias", "territorio",
            "atualizacao", "confiabilidade", "pesquisa",
        ):
            with self.subTest(nome=nome):
                svg = simbolo(nome)
                self.assertIn("<svg ", svg)
                self.assertIn("</svg>", svg)
                self.assertIn('viewBox="0 0 64 64"', svg)

    def test_tamanho_personalizado(self):
        self.assertIn('width="80" height="80"', simbolo("pesquisa", tamanho=80))

    def test_nome_desconhecido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            simbolo("icone-generico")

    def test_tamanho_fora_da_faixa_e_rejeitado(self):
        with self.assertRaises(ValueError):
            simbolo("saude", tamanho=500)

    def test_cor_deve_ser_hexadecimal(self):
        with self.assertRaises(ValueError):
            simbolo("saude", cor='red" onload="alert(1)')


if __name__ == "__main__":
    unittest.main()
