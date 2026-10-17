import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =====================================
# UM COMANDO SÓ para trazer as bases novas -- rodar no computador do autor (Python 3.12)
#
#   py -3.12 etl\carregar_tudo_pysus.py            (tudo: população, quimio/radio, mortalidade, leitos e equipamentos)
#   py -3.12 etl\carregar_tudo_pysus.py --so sim   (uma etapa só: populacao, geo, sia, sim ou cnes)
#
# Cada etapa roda isolada: se uma falhar, as outras continuam e o fim mostra o que deu certo e o que não deu.
# Só agregados vão para o banco (nenhum CPF/cartão SUS, CEP, nascimento ou nº de documento). O SIH (internações) NÃO é tocado.
# =====================================


def etapas():
    import baixar_centroides as geo
    import baixar_cnes_capacidade as cnes
    import baixar_populacao as pop
    import baixar_sia_oncologia as sia
    import baixar_sim_obitos as sim
    return [
        ("populacao", "População de mulheres (IBGE, Censo 2022)", lambda: pop.main()),
        ("geo", "Centro de cada município de SP (IBGE, para a distância até os hospitais)", lambda: (geo.main(), None)),
        ("sia", "Quimio e radio ambulatoriais (SIA) 2013-2025", lambda: sia.main(anos=list(range(2013, 2026)), verboso=False)),
        ("sim", "Mortalidade real por câncer (SIM) 2013-2023", lambda: sim.main(anos=list(range(2013, 2024)), verboso=False)),
        ("cnes", "Leitos e equipamentos (CNES) 2013-2025", lambda: cnes.main(anos=list(range(2013, 2026)), verboso=False)),
    ]


def main(escolhidas=None):
    lista = [e for e in etapas() if not escolhidas or e[0] in escolhidas]
    resultado = []
    for chave, titulo, rodar in lista:
        print("\n" + "=" * 70 + f"\n{titulo}\n" + "=" * 70)
        inicio = time.time()
        try:
            saida = rodar()
            pendencias = saida[0] if isinstance(saida, tuple) and saida and isinstance(saida[0], list) else []
            resultado.append((titulo, "ok" if not pendencias else f"ok, com {len(pendencias)} aviso(s) da fonte", time.time() - inicio))
        except SystemExit as erro:
            resultado.append((titulo, f"parou: {erro}", time.time() - inicio))
        except Exception as erro:  # noqa: BLE001
            traceback.print_exc()
            resultado.append((titulo, f"FALHOU: {type(erro).__name__}: {str(erro)[:150]}", time.time() - inicio))
    print("\n" + "=" * 70 + "\nRESUMO\n" + "=" * 70)
    for titulo, estado, seg in resultado:
        print(f"  {titulo}: {estado} ({seg / 60:.1f} min)")
    print("\nCole TUDO o que apareceu acima no chat (os blocos PERFIL são o que preciso para conferir os códigos).")
    return resultado


if __name__ == "__main__":
    escolhidas = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--so" and i + 1 < len(sys.argv)]
    main(escolhidas or None)
