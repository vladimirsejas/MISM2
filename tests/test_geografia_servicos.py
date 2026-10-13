import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "algoritimos"))

from geografia_servicos import (  # noqa: E402
    combinar_catalogos,
    coordenada_valida,
    filtrar_servicos,
    normalizar_cep,
    preparar_servicos,
    resolver_localizacao,
)


class TestGeografiaServicos(unittest.TestCase):
    def test_normaliza_cep(self):
        self.assertEqual(normalizar_cep("13500-030"), "13500030")

    def test_rejeita_coordenada_fora_de_rio_claro(self):
        self.assertFalse(coordenada_valida(-23.55, -46.63))

    def test_prioriza_coordenada_cadastrada(self):
        servico = {"lat": -22.41308, "lon": -47.56278, "cep": "13500040"}
        indice = {"13500040": [-22.4145, -47.5603, 420, "setor", 98]}
        pos = resolver_localizacao(servico, indice)
        self.assertEqual(pos["precisao"], "coordenada_da_fonte")
        self.assertEqual(pos["lat"], -22.41308)

    def test_usa_cep_apenas_com_raio_ate_800m(self):
        servico = {"lat": None, "lon": None, "cep": "13500040"}
        indice = {"13500040": [-22.4145, -47.5603, 420, "setor", 98]}
        self.assertEqual(resolver_localizacao(servico, indice)["precisao"], "aproximada_por_cep")
        indice["13500040"][2] = 1200
        self.assertFalse(resolver_localizacao(servico, indice)["localizavel"])

    def test_nao_inventa_localizacao(self):
        pos = resolver_localizacao({"cep": "00000000"}, {})
        self.assertFalse(pos["localizavel"])
        self.assertIsNone(pos["lat"])

    def test_categorias_vazias_nao_mostram_tudo(self):
        servicos = [{"nome": "UBS Centro", "tipo": "saude"}]
        self.assertEqual(filtrar_servicos(servicos, tipos=set()), [])

    def test_combina_catalogos_sem_duplicar_cnes(self):
        manuais = [{"nome": "UBS Centro", "endereco": "Rua A", "cnes": "1234567", "tipo": "saude"}]
        cnes = [
            {"nome": "Outro nome", "endereco": "Rua B", "cnes": "1234567", "tipo": "saude",
             "servicos_cnes": [{"descricao": "Atenção Básica"}]},
            {"nome": "UBS Norte", "endereco": "Rua C", "cnes": "7654321", "tipo": "saude"},
        ]
        resultado = combinar_catalogos(manuais, cnes)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[1]["cnes"], "7654321")
        self.assertEqual(resultado[0]["servicos_cnes"][0]["descricao"], "Atenção Básica")

    def test_filtros_nao_alteram_catalogo(self):
        servicos = [
            {"nome": "UBS Centro", "tipo": "saude", "endereco": "Centro", "localizavel": True,
             "precisao": "coordenada_da_fonte"},
            {"nome": "CRAS Norte", "tipo": "assistencia", "endereco": "Cervezão", "localizavel": False,
             "precisao": "sem_localizacao_confiavel"},
        ]
        filtrados = filtrar_servicos(servicos, texto="ubs", tipos={"saude"})
        self.assertEqual(len(filtrados), 1)
        self.assertEqual(len(servicos), 2)


if __name__ == "__main__":
    unittest.main()
