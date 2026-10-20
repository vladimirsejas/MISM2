import asyncio
import re
import sys

# =====================================
# QUAIS MESES O PYSUS OFERECE PARA UM ANO? (rodar no computador do autor; a nuvem não alcança o DATASUS)
#
# NÃO baixa dados. Pergunta ao PySUS os arquivos de SP do ano pedido (SIH/RD, SIA/AQ, SIA/AR, CNES/EQ, CNES/LT e o SIM, que é um
# arquivo por ano) e diz quais meses existem e quais NÃO foram listados pelo DATASUS. Ausência na lista é lacuna da fonte (ainda não publicado ou nunca publicado), não erro de download.
# Serve para decidir a atualização de 2025 e 2026 sem baixar tudo de novo.
#
# Uso (Python 3.12):
#   py -3.12 etl\listar_meses_pysus.py             ano corrente
#   py -3.12 etl\listar_meses_pysus.py --ano 2026
# =====================================

ESTADO = "SP"
# (base, grupo, para que serve). grupo None = base sem grupo e sem mês (SIM: um arquivo DO<UF><ANO> por ano).
BASES = [("sih", "RD", "internações (SIH/SUS)"), ("sia", "AQ", "APAC de quimioterapia (SIA/SUS)"),
         ("sia", "AR", "APAC de radioterapia (SIA/SUS)"), ("cnes", "EQ", "equipamentos (CNES)"),
         ("cnes", "LT", "leitos (CNES)"), ("sim", None, "óbitos (SIM)")]
# Nome do arquivo do DATASUS: <grupo><UF><AA><MM>[letra].dbc, ex.: RDSP2601.dbc (jan/2026), PASP2603a.dbc, AQSP2602.dbc.
PADRAO_NOME = re.compile(r"^(?P<grupo>[A-Z]{2})(?P<uf>[A-Z]{2})(?P<ano>\d{2})(?P<mes>\d{2})", re.IGNORECASE)


def meses_no_nome(nome):
    """(ano com 4 dígitos, mês) lidos do nome do arquivo, ou None se o nome não segue o padrão."""
    achado = PADRAO_NOME.match(str(nome).strip().split("/")[-1])
    if not achado:
        return None
    mes = int(achado.group("mes"))
    if not 1 <= mes <= 12:
        return None
    return 2000 + int(achado.group("ano")), mes


def resumir(nomes, ano):
    """Separa os nomes em meses presentes (do ano pedido), meses que faltam e nomes que não deu para ler."""
    presentes, ilegiveis = set(), []
    for nome in nomes:
        lido = meses_no_nome(nome)
        if lido is None:
            ilegiveis.append(str(nome))
        elif lido[0] == ano:
            presentes.add(lido[1])
    return sorted(presentes), [m for m in range(1, 13) if m not in presentes], ilegiveis


def existe_arquivo_anual(nomes, ano):
    """SIM: o arquivo do ano se chama DO<UF><ANO> (ex.: DOSP2023)."""
    return any(str(n).strip().split("/")[-1].upper().startswith(f"DO{ESTADO}{ano}") for n in nomes)


async def listar(ano, pysus_cls=None):
    """Devolve {(base, grupo): (presentes, faltando, ilegiveis) | ("anual", existe, nomes) | o texto do erro}."""
    if pysus_cls is None:
        from pysus import PySUS as pysus_cls
    resultado = {}
    async with pysus_cls() as pysus:
        for base, grupo, _ in BASES:
            try:
                if grupo is None:
                    arquivos = list(await pysus.query(dataset=base, state=ESTADO, year=ano))
                    nomes = [getattr(a, "name", a) for a in arquivos]
                    resultado[(base, grupo)] = ("anual", existe_arquivo_anual(nomes, ano), nomes[:3])
                    continue
                arquivos = list(await pysus.query(dataset=base, group=grupo, state=ESTADO, year=ano))
                resultado[(base, grupo)] = resumir([getattr(a, "name", a) for a in arquivos], ano)
            except Exception as erro:  # noqa: BLE001
                resultado[(base, grupo)] = f"{type(erro).__name__}: {str(erro)[:200]}"
    return resultado


def main(ano=None, pysus_cls=None):
    if ano is None:
        ano = int(sys.argv[sys.argv.index("--ano") + 1]) if "--ano" in sys.argv else __import__("datetime").date.today().year
    print(f"MESES QUE O PYSUS OFERECE ({ESTADO}, {ano}) -- nada é baixado")
    resultado = asyncio.run(listar(ano, pysus_cls))
    for base, grupo, para_que in BASES:
        valor = resultado[(base, grupo)]
        print(f"\n=== {base.upper()}{'/' + grupo if grupo else ''}: {para_que}")
        if isinstance(valor, str):
            print(f"  NÃO FUNCIONOU: {valor}")
            continue
        if valor[0] == "anual":
            if valor[1]:
                print(f"  existe o arquivo de {ano} (DO{ESTADO}{ano})")
            else:
                outro = [n for n in valor[2] if str(n).upper().startswith("MORTALIDADE_GERAL")]
                if outro:
                    print(f"  NÃO existe DO{ESTADO}{ano}, mas o DATASUS lista {outro[0]} (outro formato, do Brasil inteiro): "
                          "o Escudo ainda não lê. Veja: py -3.12 etl\\sondar_mortalidade_geral.py --ano " + str(ano))
                else:
                    print(f"  NÃO LISTADO pelo DATASUS: o arquivo de {ano} (lacuna da fonte; a fonte lista: {valor[2] or 'nada'})")
            continue
        presentes, faltando, ilegiveis = valor
        print(f"  existem {len(presentes)} de 12 meses: {', '.join(f'{m:02d}' for m in presentes) or 'nenhum'}")
        if faltando:
            print(f"  NÃO LISTADOS pelo DATASUS: {', '.join(f'{m:02d}' for m in faltando)} "
                  "(lacuna da fonte, não falha de download)")
        if ilegiveis:
            print(f"  {len(ilegiveis)} nome(s) fora do padrão, ex.: {ilegiveis[:3]}")
    print("\nCole esta saída no chat: com os meses reais eu monto a atualização de 2025 e 2026.")
    return resultado


if __name__ == "__main__":
    main()
