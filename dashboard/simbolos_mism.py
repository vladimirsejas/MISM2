"""Símbolos autorais do MISM2 — linguagem visual do observatório.

Desenhos SVG próprios, leves e sem dependência de bibliotecas externas.
Cada símbolo usa a paleta lavanda/berinjela e traço consistente.
"""
from html import escape

BERINJELA = "#6B2E6F"
LAVANDA = "#A58AB8"
FUNDO = "#F3ECF9"

_DESENHOS = {
    "saude": """
      <path d="M32 7C21 7 14 15 14 25c0 12 10 22 18 29 8-7 18-17 18-29C50 15 43 7 32 7Z"/>
      <path d="M19 31h8l5-11 6 21 5-10h4" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "tendencias": """
      <path d="M9 51h46M13 51V38m13 13V29m13 22V34m13 17V17" />
      <path d="m10 32 14-9 13 7 16-17" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="53" cy="13" r="3" fill="{cor}"/>
    """,
    "territorio": """
      <path d="m32 6 23 13v26L32 58 9 45V19Z" stroke-linejoin="round"/>
      <path d="M9 19 32 32 55 19M32 32v26"/>
      <circle cx="32" cy="32" r="4" fill="{cor}"/>
    """,
    "atualizacao": """
      <circle cx="32" cy="32" r="21"/>
      <path d="M32 18v15l11 7" stroke-linecap="round"/>
      <path d="M23 5h18M32 5v6" stroke-linecap="round"/>
    """,
    "confiabilidade": """
      <path d="m32 6 23 9v16c0 13-9 21-23 27C18 52 9 44 9 31V15Z" stroke-linejoin="round"/>
      <path d="m20 32 8 8 16-18" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "pesquisa": """
      <circle cx="27" cy="27" r="15"/>
      <path d="m38 38 14 14" stroke-linecap="round"/>
      <path d="M20 27h14M27 20v14" stroke-linecap="round"/>
    """,
}


def simbolo(nome: str, tamanho: int = 56, cor: str = BERINJELA,
            fundo: str = FUNDO) -> str:
    """Retorna SVG acessível. Nomes: saude, tendencias, territorio,
    atualizacao, confiabilidade, pesquisa."""
    if nome not in _DESENHOS:
        raise ValueError(f"Símbolo MISM2 desconhecido: {nome}")
    if not 16 <= tamanho <= 256:
        raise ValueError("tamanho deve ficar entre 16 e 256 pixels")
    # Cores entram em atributos SVG; rejeita conteúdo arbitrário.
    for valor in (cor, fundo):
        if not valor.startswith("#") or len(valor) not in (4, 7):
            raise ValueError("Use cores hexadecimais (#RGB ou #RRGGBB)")
    desenho = _DESENHOS[nome].format(cor=cor)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tamanho}" '
        f'height="{tamanho}" viewBox="0 0 64 64" role="img" '
        f'aria-label="{escape(nome)}">'
        f'<rect x="1" y="1" width="62" height="62" rx="16" fill="{fundo}"/>'
        f'<g fill="none" stroke="{cor}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round">{desenho}</g>'
        '</svg>'
    )
