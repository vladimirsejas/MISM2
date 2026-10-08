import os
import re
import shutil
import sqlite3
import pandas as pd

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DADOS = os.path.join(RAIZ_PROJETO, "dados")
BANCO = os.path.join(RAIZ_PROJETO, "banco", "escudo_feminino.db")

# Só os arquivos ESTADUAIS entram no banco. Cada um traz as
# internações de todas as moradoras de SP, já com o município de
# residência (MUNIC_RES) -- inclusive as de Rio Claro. As pastas
# municipais antigas (ex.: cancer_mama_rio_claro) repetiam essas
# mesmas internações: carregar as duas contava Rio Claro em dobro
# (confirmado no banco real em 09/2026: 1.668 + as mesmas 1.668).
# Por isso elas não têm mais caminho na carga; se ainda estiverem em
# dados\, são ignoradas com aviso. Fonte única também deixa todas
# as cidades comparáveis entre si.
MAPA = {
    "cancer_mama_sp": ("MAMA", "SP"),
    "cancer_colorretal_sp": ("COLORRETAL", "SP"),
    "cancer_colo_utero_sp": ("COLO_UTERO", "SP"),
    "cancer_ovario_sp": ("OVARIO", "SP"),
    "cancer_pulmao_sp": ("PULMAO", "SP"),
    "cancer_tireoide_sp": ("TIREOIDE", "SP"),
    "cancer_pele_nao_melanoma_sp": ("PELE_NAO_MELANOMA", "SP"),
}

# Colunas sem as quais um arquivo não entra (a carga diz quais faltam).
COLUNAS_OBRIGATORIAS = ["ANO_CMPT", "IDADE", "DIAS_PERM", "MORTE", "VAL_TOT"]

# Registros com código de município fora do catálogo IBGE: até esta
# fração do arquivo, ficam de fora com aviso (ex.: código ignorado ou
# de outra UF); acima disso o arquivo inteiro é recusado, porque aí o
# problema é o catálogo ou o arquivo, não uns poucos registros.
TOLERANCIA_DESCONHECIDOS = 0.01

CANDIDATOS_CODIGO_MUNICIPIO = [
    "MUNIC_RES",
    "MUNIC_RESID",
    "CODMUNRES",
    "COD_MUN_RES",
    "CODMUN_RES",
    "MUNICIPIO_RES",
    "MUNICIPIO_RESIDENCIA",
    "MUNICIPIO",
]


def limpar_codigo(valor):
    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    if texto.endswith(".0"):
        texto = texto[:-2]

    digitos = re.sub(r"\D", "", texto)

    if len(digitos) in (6, 7):
        return int(digitos)

    return None


def encontrar_coluna_codigo(df):
    colunas = {str(c).strip().upper(): c for c in df.columns}

    for candidato in CANDIDATOS_CODIGO_MUNICIPIO:
        if candidato in colunas:
            return colunas[candidato]

    return None


def selecionar_csv_unico(caminho_pasta, pasta):
    """
    Exige um único CSV por pasta -- a carga lê só um arquivo (não
    concatena vários). Se sobrar mais de um (ex.: o CSV antigo
    2021-2025 ao lado do novo 2013-2025 recém-baixado), a ordem
    alfabética decidiria sozinha qual entra no banco, sem avisar, e
    o erro passaria despercebido. Falhar aqui é melhor do que
    carregar o arquivo errado ou contar o mesmo ano duas vezes.
    """

    arquivos_csv = sorted(
        arquivo
        for arquivo in os.listdir(caminho_pasta)
        if arquivo.lower().endswith(".csv")
    )

    if not arquivos_csv:
        return None

    if len(arquivos_csv) > 1:
        raise RuntimeError(
            f"A pasta '{pasta}' tem mais de um CSV: {arquivos_csv}. "
            "A carga lê um único arquivo por pasta -- deixe só o mais "
            "atual (ex.: o que cobre 2013-2025) dentro dela e mova os "
            "arquivos antigos para fora de dados\\, senão a carga pode "
            "pegar o arquivo errado sem avisar ou duplicar anos que "
            "existam nos dois arquivos."
        )

    return os.path.join(caminho_pasta, arquivos_csv[0])


def encontrar_pastas_validas(base_dados):
    """
    Lista as subpastas de `base_dados` que a carga reconhece (as
    chaves de MAPA). Falha alto se nenhuma bater -- por exemplo, se
    os CSVs foram deixados soltos direto em dados\\ em vez de dentro
    de dados\\cancer_mama_sp\\ etc. Sem essa checagem, esse
    engano não gera erro nenhum: o laço da carga simplesmente ignora
    todo mundo que não bate com MAPA e termina com TOTAL: 0, fácil de
    passar despercebido.
    """

    pastas = [
        entrada
        for entrada in sorted(os.listdir(base_dados))
        if entrada in MAPA
    ]

    if not pastas:
        raise RuntimeError(
            f"Nenhuma subpasta reconhecida foi encontrada em '{base_dados}'. "
            "A carga espera uma subpasta estadual por câncer (ex.: "
            "dados\\cancer_mama_sp\\, com um único CSV dentro dela) "
            "-- não arquivos soltos direto em dados\\. Pastas esperadas: "
            + ", ".join(sorted(MAPA))
        )

    return pastas


def pastas_ignoradas(base_dados):
    """
    Subpastas de dados\\ com cara de base (cancer_...) que a carga
    NÃO lê -- hoje, as municipais antigas (cancer_mama_rio_claro
    etc.). Só para avisar: elas podem ficar no computador como
    arquivo, mas não entram no banco.
    """

    return [
        entrada
        for entrada in sorted(os.listdir(base_dados))
        if entrada.startswith("cancer_") and entrada not in MAPA
        and os.path.isdir(os.path.join(base_dados, entrada))
    ]


def canceres_faltando(pastas):
    """Cânceres de MAPA sem pasta estadual em dados\\."""

    presentes = {MAPA[pasta][0] for pasta in pastas}
    return sorted({tipo for tipo, _ in MAPA.values()} - presentes)


def municipios_duplicados(conexao):
    """
    (Município, câncer) com internações vindas de mais de uma fonte
    (origem). Com só os arquivos estaduais a lista deve vir vazia;
    se não vier, esses totais estão contados em dobro. É por
    câncer: mama do estadual + ovário da pasta da cidade é normal.
    """

    return conexao.execute("""
        SELECT municipio, tipo_cancer, GROUP_CONCAT(DISTINCT origem)
        FROM internacoes
        GROUP BY municipio, tipo_cancer
        HAVING COUNT(DISTINCT origem) > 1
    """).fetchall()


def detectar_separador(caminho_csv, encoding="latin1"):
    """
    Descobre se o CSV usa ';' (padrão do extrato bruto do DATASUS) ou
    ',' (visto em arquivos consolidados por outra ferramenta, ex.:
    pysus) -- olhando só a linha de cabeçalho, sem carregar o arquivo
    inteiro. Sem isso, um CSV separado por vírgula lido com sep=';'
    vira uma única coluna gigante e a carga falha com KeyError em
    ANO_CMPT sem dizer por quê.
    """

    with open(caminho_csv, encoding=encoding) as arquivo:
        cabecalho = arquivo.readline()

    def colunas(separador):
        return {coluna.strip().strip('"') for coluna in cabecalho.split(separador)}

    if "ANO_CMPT" in colunas(";"):
        return ";"

    if "ANO_CMPT" in colunas(","):
        return ","

    raise RuntimeError(
        f"Não encontrei a coluna ANO_CMPT no cabeçalho de '{caminho_csv}' "
        "nem separando por ';' nem por ','. Cabeçalho encontrado: "
        f"{cabecalho.strip()!r}"
    )


def carregar_catalogo(conexao):
    linhas = conexao.execute(
        "SELECT codigo_ibge, origem, nome, uf "
        "FROM municipios WHERE uf = 'SP'"
    ).fetchall()

    por_codigo = {}
    for codigo, origem, nome, uf in linhas:
        texto = str(codigo)
        por_codigo[texto] = origem
        por_codigo[texto[:6]] = origem

    return por_codigo


def resolver_municipios(df, origem, catalogo, tolerancia=TOLERANCIA_DESCONHECIDOS):
    coluna = encontrar_coluna_codigo(df)

    if origem == "SP" and coluna is None:
        raise RuntimeError(
            "Os arquivos estaduais de SP não possuem uma coluna de código "
            "municipal reconhecida. A carga foi interrompida para não "
            "misturar todo o Estado em um único município. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    codigos = df[coluna].map(limpar_codigo)

    municipios = codigos.map(
        lambda codigo: catalogo.get(str(codigo))
        if codigo is not None else None
    )

    # Moradoras de outros estados (código que não começa com 35): o
    # Escudo é sobre moradoras de SP, então ficam de fora -- em qualquer
    # quantidade. Era isso que derrubava a base de colorretal de SP na
    # versão de 94.005 registros (a "corrigida" tem 91.341: só SP; ver
    # docs/BASES_ORIGINAIS_2013_2025.md).
    fora_de_sp = codigos.map(lambda c: c is not None and not str(c).startswith("35"))
    if fora_de_sp.any():
        print(f"AVISO: {int(fora_de_sp.sum())} registros de moradoras de outros estados "
              "ficam de fora (o Escudo é sobre moradoras de SP).")

    desconhecidos = municipios.isna() & ~fora_de_sp

    if desconhecidos.any():
        quantidade = int(desconhecidos.sum())
        exemplos = (
            codigos[desconhecidos]
            .dropna()
            .astype(str)
            .head(10)
            .tolist()
        )
        if quantidade > tolerancia * len(df):
            raise RuntimeError(
                f"{quantidade} de {len(df)} registros de {origem} possuem código "
                "municipal sem correspondência no catálogo IBGE. Exemplos: "
                f"{exemplos}. Se forem muitos, rode antes "
                "etl\\criar_tabela_municipios.py (catálogo com as 645 cidades)."
            )
        print(f"AVISO: {quantidade} registros com código de município fora do "
              f"catálogo ficam de fora (exemplos: {exemplos}).")

    return municipios, codigos


VERSAO_CARGA = ("carga_todas_bases.py -- lê e confere todos os arquivos antes de gravar; "
                "um arquivo com problema não derruba os outros")


def ler_pasta(pasta, catalogo):
    """Lê e confere o CSV de uma pasta estadual. Devolve os dados
    prontos para o banco (None se a pasta não tiver CSV) ou levanta
    RuntimeError dizendo o que está errado -- sem tocar no banco."""

    arquivo_csv = selecionar_csv_unico(os.path.join(BASE_DADOS, pasta), pasta)

    if arquivo_csv is None:
        return None

    tipo_cancer, origem = MAPA[pasta]
    print("ARQUIVO:", os.path.basename(arquivo_csv))

    separador = detectar_separador(arquivo_csv)

    df = pd.read_csv(
        arquivo_csv,
        sep=separador,
        encoding="latin1",
        low_memory=False
    )
    df.columns = [str(c).strip().strip('"') for c in df.columns]

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise RuntimeError(
            f"faltam as colunas {faltando}. Colunas do arquivo: {list(df.columns)[:40]}"
        )

    municipios, codigos = resolver_municipios(df, origem, catalogo)

    dados = pd.DataFrame({
        "tipo_cancer": [tipo_cancer] * len(df),
        "origem": [origem] * len(df),
        "municipio": municipios,
        "codigo_ibge": codigos,
        "ano": df["ANO_CMPT"],
        # mês de competência: o Escudo precisa dele para saber quais
        # meses a fonte não oferece (inteligencia.ajustar_meses)
        "mes": pd.to_numeric(df["MES_CMPT"], errors="coerce") if "MES_CMPT" in df else None,
        "idade": df["IDADE"],
        "dias_permanencia": df["DIAS_PERM"],
        "obito": df["MORTE"],
        "valor_total": df["VAL_TOT"]
    })

    return dados[dados["municipio"].notna()]


def gravar_resultado(conexao, linhas):
    """Tabela carga_resultado: o que entrou e o que ficou de fora (com o
    motivo) na última carga. O painel lê esta tabela e mostra um aviso
    quando falta algum câncer -- o autor não precisa abrir log nenhum."""
    from datetime import datetime
    quando = datetime.now().strftime("%d/%m/%Y %H:%M")
    pd.DataFrame(
        [(quando, pasta, tipo, situacao, registros, motivo) for pasta, tipo, situacao, registros, motivo in linhas],
        columns=["quando", "pasta", "tipo_cancer", "situacao", "registros", "motivo"],
    ).to_sql("carga_resultado", conexao, if_exists="replace", index=False)
    conexao.commit()


def guardar_copia(banco):
    """Cópia do banco antes de trocar a tabela (uma só, a da última carga)."""
    if not os.path.exists(banco):
        return None
    copia = banco[:-3] + "_antes_da_carga.db" if banco.endswith(".db") else banco + ".antes_da_carga"
    shutil.copy2(banco, copia)
    return copia


def carregar():
    """
    Lê e confere TODOS os arquivos antes de mexer no banco. Antes
    (até 09/2026) o primeiro arquivo apagava a tabela e cada um
    seguinte era acrescentado: se o 2º desse erro, a carga parava e o
    banco ficava só com o 1º câncer (foi o que aconteceu com o autor:
    só colo do útero). Agora:
      - um arquivo com problema não derruba os outros: ele fica de
        fora e o motivo aparece no fim, com o que fazer;
      - a tabela nova é montada ao lado (internacoes_nova) e só troca
        de lugar com a antiga no fim;
      - antes da troca, o banco é copiado para
        escudo_feminino_antes_da_carga.db;
      - se nenhum arquivo servir, o banco não é alterado.
    """
    print(VERSAO_CARGA)

    conexao = sqlite3.connect(BANCO)

    try:
        catalogo = carregar_catalogo(conexao)
    except sqlite3.OperationalError as erro:
        conexao.close()
        raise RuntimeError(
            "A tabela municipios não existe. Execute primeiro "
            "etl\\criar_tabela_municipios.py."
        ) from erro

    pastas = encontrar_pastas_validas(BASE_DADOS)

    for pasta in pastas_ignoradas(BASE_DADOS):
        print(
            f"IGNORADA: {pasta} -- a carga usa só os arquivos estaduais "
            "(as internações dessa cidade já vêm neles, com o município "
            "de residência). Pode guardar a pasta fora de dados\\."
        )

    faltando = canceres_faltando(pastas)
    for tipo in faltando:
        print(f"ATENÇÃO: falta a pasta estadual de {tipo} "
              "(esse câncer fica fora do banco).")

    prontos, problemas = [], []

    for pasta in pastas:
        tipo_cancer, origem = MAPA[pasta]

        print("\n" + "=" * 60)
        print("PASTA:", pasta)
        print("TIPO:", tipo_cancer)
        print("ORIGEM:", origem)

        try:
            dados = ler_pasta(pasta, catalogo)
        except (Exception, MemoryError) as erro:  # noqa: B014 -- qualquer falha: segue para a próxima
            problemas.append((pasta, f"{type(erro).__name__}: {erro}"))
            print("PROBLEMA -- este arquivo fica de fora:", problemas[-1][1])
            continue

        if dados is None:
            problemas.append((pasta, "a pasta não tem nenhum CSV dentro"))
            print("PROBLEMA -- a pasta não tem CSV.")
            continue

        print("Municípios identificados:", dados["municipio"].nunique())
        print(dados["municipio"].value_counts().head(10))
        print("OK ->", len(dados), "registros")
        prontos.append((pasta, dados))

    resultado = (
        [(p, MAPA[p][0], "carregado", len(d), "") for p, d in prontos]
        + [(p, MAPA[p][0], "de fora", 0, motivo) for p, motivo in problemas]
        + [("", tipo, "sem pasta", 0, "não existe a pasta estadual em dados") for tipo in faltando]
    )

    if not prontos:
        gravar_resultado(conexao, resultado)
        conexao.close()
        raise RuntimeError(
            "Nenhum arquivo pôde ser carregado; o banco NÃO foi alterado. "
            "Problemas: " + "; ".join(f"{p}: {m}" for p, m in problemas)
            if problemas else
            "A carga encontrou pastas reconhecidas, mas nenhuma continha "
            "um CSV -- confira se os arquivos foram mesmo colocados "
            "dentro das subpastas de dados\\ (uma por câncer), e não "
            "deixados soltos na raiz."
        )

    copia = guardar_copia(BANCO)

    # Tabela nova ao lado; a antiga só sai depois que a nova está inteira.
    conexao.execute("DROP TABLE IF EXISTS internacoes_nova")
    conexao.commit()
    for n, (pasta, dados) in enumerate(prontos):
        dados.to_sql("internacoes_nova", conexao, if_exists="replace" if n == 0 else "append", index=False)
    conexao.execute("DROP TABLE IF EXISTS internacoes")
    conexao.execute("ALTER TABLE internacoes_nova RENAME TO internacoes")
    conexao.commit()
    gravar_resultado(conexao, resultado)

    duplicados = municipios_duplicados(conexao)
    conexao.close()

    if duplicados:
        print("\nATENÇÃO: municípios com internações de mais de uma fonte "
              "(totais em dobro):", duplicados)

    total_registros = sum(len(d) for _, d in prontos)
    print("\n" + "=" * 60)
    print("CARGA TERRITORIAL FINALIZADA")
    print("TOTAL:", total_registros)
    print("CÂNCERES NO BANCO:", ", ".join(MAPA[p][0] for p, _ in prontos),
          f"({len(prontos)} de {len(MAPA)})")
    if copia:
        print("Cópia do banco anterior:", copia)
    if problemas or faltando:
        print("\n" + "!" * 60)
        print("FICARAM DE FORA:")
        for pasta, motivo in problemas:
            print(f"  - {pasta}: {motivo}")
        for tipo in faltando:
            print(f"  - {tipo}: não existe a pasta estadual em dados\\")
        print("Corrija o que está acima e rode a carga de novo; mande esta "
              "mensagem ao Claude se não souber o que fazer.")
        print("!" * 60)
    print("=" * 60)


if __name__ == "__main__":
    carregar()
