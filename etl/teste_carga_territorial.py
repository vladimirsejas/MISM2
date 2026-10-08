import pandas as pd

from carga_todas_bases import limpar_codigo, resolver_municipios
from criar_tabela_municipios import normalizar_origem


def main():
    assert normalizar_origem("São Paulo", 3550308) == "SAO_PAULO"
    assert normalizar_origem("Águas de Lindóia", 3500501) == "AGUAS_DE_LINDOIA"

    catalogo = {
        "3550308": "SAO_PAULO",
        "355030": "SAO_PAULO",
        "3543907": "RIO_CLARO",
        "354390": "RIO_CLARO",
        "3526902": "LIMEIRA",
        "352690": "LIMEIRA",
    }

    df = pd.DataFrame({
        "MUNIC_RES": ["3550308", "3543907", "352690", "3526902"]
    })

    municipios, codigos = resolver_municipios(df, "SP", catalogo)

    assert municipios.tolist() == [
        "SAO_PAULO", "RIO_CLARO", "LIMEIRA", "LIMEIRA"
    ]
    assert codigos.tolist() == [3550308, 3543907, 352690, 3526902]

    df_6 = pd.DataFrame({"MUNIC_RES": ["355030", "354390"]})
    municipios_6, _ = resolver_municipios(df_6, "SP", catalogo)
    assert municipios_6.tolist() == ["SAO_PAULO", "RIO_CLARO"]

    try:
        resolver_municipios(
            pd.DataFrame({"ANO_CMPT": [2025]}), "SP", catalogo
        )
    except RuntimeError as erro:
        assert "não possuem uma coluna de código municipal" in str(erro)
    else:
        raise AssertionError("SP sem código municipal deveria falhar")

    try:
        resolver_municipios(
            pd.DataFrame({"MUNIC_RES": ["3599999"]}), "SP", catalogo
        )
    except RuntimeError as erro:
        assert "sem correspondência no catálogo IBGE" in str(erro)
    else:
        raise AssertionError("Código de SP desconhecido deveria falhar")

    # moradoras de outros estados ENTRAM como OUTRO_ESTADO (o Escudo conta o
    # atendimento em SP), em qualquer quantidade, com o código de residência mantido
    fora, codigos_fora = resolver_municipios(
        pd.DataFrame({"MUNIC_RES": ["3543907", "3106200", "3304557"]}), "SP", catalogo
    )
    assert fora.tolist() == ["RIO_CLARO", "OUTRO_ESTADO", "OUTRO_ESTADO"], fora.tolist()
    assert codigos_fora.tolist() == [3543907, 3106200, 3304557]

    print("Todas as checagens da carga territorial passaram.")


if __name__ == "__main__":
    main()
