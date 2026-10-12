"""Identidade visual do MISM2: símbolo autoral e régua de cobertura.

Só apresentação. Nada aqui calcula dado novo: a régua desenha os meses por ano que
`inteligencia.carregar_serie` já entrega na coluna `meses` (ver docs/FONTE_DOS_DADOS.md).
"""
import math


def simbolo(tamanho=46):
    """O símbolo do MISM2: um anel de 12 pontos (os meses do ano) com 2 vazios (meses que o
    DATASUS não ofereceu) em volta de uma linha de tendência. É o mesmo desenho da régua de
    cobertura: a limitação da fonte virou a marca do observatório."""
    pontos = []
    for m in range(12):
        ang = -math.pi / 2 + m * 2 * math.pi / 12
        x, y = 32 + 24 * math.cos(ang), 32 + 24 * math.sin(ang)
        if m < 10:
            pontos.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.1" fill="#5b2a55"/>')
        else:
            pontos.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.7" fill="none" stroke="#5b2a55" stroke-width="1.3"/>')
    return (f'<svg class="mism-simbolo" width="{tamanho}" height="{tamanho}" viewBox="0 0 64 64" role="img" '
            f'aria-label="MISM2">{"".join(pontos)}'
            '<path d="M19 40 C25 38 27 31 32 31 S39 29 45 22" fill="none" stroke="#b79bd1" '
            'stroke-width="2.6" stroke-linecap="round"/>'
            '<circle cx="45" cy="22" r="2.6" fill="#5b2a55"/></svg>')


def regua_cobertura(serie):
    """Uma coluna por ano, um quadradinho por mês: cheio = mês que a fonte (DATASUS) ofereceu.
    Devolve '' se a série não traz os meses (banco antigo)."""
    if "meses" not in serie or serie["meses"].isna().all():
        return ""
    por_ano = serie.groupby("ano")["meses"].max()
    colunas = []
    for ano, meses in por_ano.items():
        meses = int(meses) if meses == meses else 0
        celulas = "".join(f'<i class="{"on" if m < meses else "off"}"></i>' for m in range(12))
        rotulo = f"{int(ano)}: {meses} de 12 meses na fonte"
        colunas.append(f'<div class="regua-col" title="{rotulo}"><div class="regua-cel">{celulas}</div>'
                       f'<span>{str(int(ano))[2:]}</span></div>')
    return ('<div class="regua"><div class="regua-cols">' + "".join(colunas) + '</div>'
            '<div class="regua-leg">Meses de cada ano que o DATASUS ofereceu: cada quadradinho é um mês, '
            'o vazio é mês ausente na fonte (não é zero).</div></div>')
