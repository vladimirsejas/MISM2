import base64
import functools
import os

# ============================================================
# O ROSTO DA LIA (ilustração vetorial, ver docs/LIA.md)
#
# Mulher negra madura, cabelo crespo curto grisalho, óculos, blusa
# berinjela -- pesquisadora, não médica: sem jaleco, sem crachá, sem
# marca de instituição real. O mesmo desenho em 5 expressões; só
# mudam sobrancelhas, olhos, boca e o pequeno símbolo no canto, para
# o rosto ser o mesmo em todas e ficar nítido em qualquer tamanho.
# ============================================================

PELE = "#7a4a2e"
PELE_SOMBRA = "#643b23"
CABELO_ESCURO = "#3b3634"
CABELO_CINZA = "#9c9794"
CABELO_CLARO = "#cfcac6"
BLUSA = "#5b2a55"
GOLA = "#e9dff0"
ARMACAO = "#27212b"
FUNDO = "#efe9f7"

# (sobrancelha esquerda, sobrancelha direita, olhos, boca, símbolo)
EXPRESSOES = {
    "acolhedora": {
        "sobrancelhas": ("M71 78 Q80 74 89 77", "M111 77 Q120 74 129 78"),
        "olhos": "sorrindo",
        "boca": '<path d="M88 118 Q100 128 112 118" stroke="#3a1f14" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "simbolo": None,
    },
    "explicando": {
        "sobrancelhas": ("M71 77 Q80 73 89 76", "M111 76 Q120 73 129 77"),
        "olhos": "abertos",
        "boca": '<path d="M89 118 Q100 125 111 118" stroke="#3a1f14" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "simbolo": "grafico",
    },
    "atenta": {
        "sobrancelhas": ("M71 74 Q80 69 89 73", "M111 73 Q120 69 129 74"),
        "olhos": "abertos",
        "boca": '<ellipse cx="100" cy="120" rx="5" ry="4" fill="#3a1f14"/>',
        "simbolo": "lupa",
    },
    "cautelosa": {
        "sobrancelhas": ("M71 76 Q80 76 89 73", "M111 73 Q120 76 129 76"),
        "olhos": "abertos",
        "boca": '<path d="M90 121 L110 119" stroke="#3a1f14" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "simbolo": "cuidado",
    },
    "pensativa": {
        "sobrancelhas": ("M71 77 Q80 73 89 76", "M111 72 Q120 68 129 72"),
        "olhos": "para_cima",
        "boca": '<path d="M91 120 Q101 123 110 117" stroke="#3a1f14" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "simbolo": "pergunta",
    },
}

ROTULOS = {
    "acolhedora": "Lia, acolhedora",
    "explicando": "Lia explicando um dado",
    "atenta": "Lia atenta: encontrou um sinal",
    "cautelosa": "Lia cautelosa: este dado pede cuidado",
    "pensativa": "Lia pensativa: explicando como calculou",
}


def _cabelo():
    """Cabelo crespo curto, sal e pimenta: uma base escura com o
    formato do penteado e, por cima, cachos pequenos em posições
    variadas -- a maioria escuros, uns grisalhos e poucos claros.
    Posições pseudoaleatórias com semente fixa: o cabelo é o mesmo em
    todas as expressões."""
    import math
    import random
    rnd = random.Random(7)
    partes = [f'<ellipse cx="100" cy="80" rx="58" ry="52" fill="{CABELO_ESCURO}"/>']
    for _ in range(170):
        ang = rnd.uniform(math.pi * 0.88, math.pi * 2.12)
        raio = rnd.uniform(0.55, 1.0)
        x = 100 + 56 * raio * math.cos(ang)
        y = 80 + 50 * raio * math.sin(ang)
        if y > 104:  # não desce abaixo da orelha
            continue
        sorteio = rnd.random()
        cor = CABELO_ESCURO if sorteio < 0.55 else (CABELO_CINZA if sorteio < 0.88 else CABELO_CLARO)
        partes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(5.5, 8.5):.1f}" fill="{cor}"/>')
    for _ in range(40):  # brilho dos cachos
        ang = rnd.uniform(math.pi * 0.95, math.pi * 2.05)
        x = 100 + 52 * rnd.uniform(0.6, 1.0) * math.cos(ang)
        y = 80 + 46 * rnd.uniform(0.6, 1.0) * math.sin(ang)
        if y > 100:
            continue
        partes.append(f'<path d="M{x - 3:.1f} {y:.1f} q3 -4 6 0" stroke="{CABELO_CLARO}" '
                      f'stroke-width="1.3" fill="none" opacity=".7"/>')
    return "".join(partes)


def _olhos(tipo):
    if tipo == "sorrindo":
        return ('<path d="M73 92 Q80 86 87 92" stroke="#1d1411" stroke-width="3" fill="none" stroke-linecap="round"/>'
                '<path d="M113 92 Q120 86 127 92" stroke="#1d1411" stroke-width="3" fill="none" stroke-linecap="round"/>')
    dy = -2 if tipo == "para_cima" else 0
    dx = 2 if tipo == "para_cima" else 0
    return (f'<ellipse cx="80" cy="91" rx="5.5" ry="6" fill="#fff"/><ellipse cx="120" cy="91" rx="5.5" ry="6" fill="#fff"/>'
            f'<circle cx="{80 + dx}" cy="{91 + dy}" r="3.6" fill="#1d1411"/><circle cx="{120 + dx}" cy="{91 + dy}" r="3.6" fill="#1d1411"/>'
            f'<circle cx="{81 + dx}" cy="{90 + dy}" r="1.1" fill="#fff"/><circle cx="{121 + dx}" cy="{90 + dy}" r="1.1" fill="#fff"/>')


def _simbolo(tipo):
    """Pequeno selo no canto superior direito que reforça a expressão."""
    if tipo is None:
        return ""
    base = '<circle cx="164" cy="38" r="21" fill="#fffaf6" stroke="#d9c8e6" stroke-width="2"/>'
    desenhos = {
        "grafico": ('<rect x="153" y="40" width="5" height="9" rx="1" fill="#2a78d6"/>'
                    '<rect x="161" y="34" width="5" height="15" rx="1" fill="#2a78d6"/>'
                    '<rect x="169" y="28" width="5" height="21" rx="1" fill="#2a78d6"/>'),
        "lupa": ('<circle cx="161" cy="35" r="8" stroke="#5b2a55" stroke-width="3" fill="none"/>'
                 '<path d="M167 41 L174 48" stroke="#5b2a55" stroke-width="3.5" stroke-linecap="round"/>'),
        "cuidado": ('<path d="M164 25 L177 48 L151 48 Z" fill="#fab219" stroke="#c98500" stroke-width="1.5" stroke-linejoin="round"/>'
                    '<rect x="162.5" y="32" width="3" height="9" rx="1.5" fill="#3a2a00"/><circle cx="164" cy="44.5" r="1.8" fill="#3a2a00"/>'),
        "pergunta": ('<text x="164" y="47" text-anchor="middle" font-family="Georgia, serif" font-size="26" '
                     'font-weight="700" fill="#5b2a55">?</text>'),
    }
    return base + desenhos[tipo]


def _flor(cx, cy, r, petala="#f3bfb6", miolo="#e9a86a"):
    """Flor de 5 pétalas, como as da faixa de mulheres do MISM3."""
    import math
    pet = "".join(
        f'<ellipse cx="{cx + r * 0.62 * math.cos(a):.1f}" cy="{cy + r * 0.62 * math.sin(a):.1f}" '
        f'rx="{r * 0.5:.1f}" ry="{r * 0.36:.1f}" transform="rotate({math.degrees(a):.0f} '
        f'{cx + r * 0.62 * math.cos(a):.1f} {cy + r * 0.62 * math.sin(a):.1f})" fill="{petala}" '
        f'stroke="#c9877b" stroke-width=".6" stroke-opacity=".6"/>'
        for a in [i * 2 * math.pi / 5 - math.pi / 2 for i in range(5)])
    return pet + f'<circle cx="{cx}" cy="{cy}" r="{r * 0.2:.1f}" fill="{miolo}"/>'


def _folha(x, y, ang, comp=16, cor="#9fb38a"):
    return (f'<path d="M0 0 Q{comp * 0.5:.1f} {-comp * 0.34:.1f} {comp} 0 Q{comp * 0.5:.1f} {comp * 0.34:.1f} 0 0 Z" '
            f'transform="translate({x} {y}) rotate({ang})" fill="{cor}" stroke="#7d9569" stroke-width=".6" stroke-opacity=".7"/>')


def _ramos():
    """Folhagem e flores atrás e ao redor da Lia (o rosto não muda)."""
    fundo = (_folha(22, 150, -70, 30) + _folha(30, 120, -40, 26) + _folha(176, 150, -110, 30)
             + _folha(170, 118, -140, 26) + _folha(20, 96, -20, 20, "#b3c49f") + _folha(180, 94, -160, 20, "#b3c49f"))
    flores_fundo = _flor(26, 134, 9, "#fbe3dd") + _flor(176, 136, 9, "#e8dcf3", "#d9a45a") + _flor(36, 160, 7, "#f3bfb6")
    return fundo + flores_fundo


def _flores_no_cabelo():
    return (_folha(60, 52, -150, 14) + _folha(66, 46, -105, 12) + _flor(64, 56, 8, "#f3bfb6")
            + _flor(76, 46, 6, "#fbe3dd") + _flor(56, 66, 5.5, "#e8dcf3", "#d9a45a"))


def svg(expressao="acolhedora"):
    e = EXPRESSOES.get(expressao, EXPRESSOES["acolhedora"])
    sob_e, sob_d = e["sobrancelhas"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="{ROTULOS.get(expressao, 'Lia')}">
<title>{ROTULOS.get(expressao, 'Lia')}</title>
<defs>
<radialGradient id="fundo" cx="30%" cy="22%" r="90%"><stop offset="0" stop-color="#fbeee6"/><stop offset=".55" stop-color="{FUNDO}"/><stop offset="1" stop-color="#e3d7f0"/></radialGradient>
<radialGradient id="pele" cx="42%" cy="35%" r="75%"><stop offset="0" stop-color="#8a5636"/><stop offset=".7" stop-color="{PELE}"/><stop offset="1" stop-color="#65391f"/></radialGradient>
<linearGradient id="blusa" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6d3566"/><stop offset="1" stop-color="{BLUSA}"/></linearGradient>
<filter id="papel" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 .35  0 0 0 0 .2  0 0 0 0 .35  0 0 0 .09 0"/></filter>
</defs>
<circle cx="100" cy="100" r="98" fill="url(#fundo)"/>
<clipPath id="corte"><circle cx="100" cy="100" r="98"/></clipPath>
<g clip-path="url(#corte)">
  {_ramos()}
  <path d="M28 205 Q32 158 72 146 L128 146 Q168 158 172 205 Z" fill="url(#blusa)" stroke="#3c1a38" stroke-width="1.2" stroke-opacity=".35"/>
  {_flor(52, 176, 5, "#e8dcf3", "#d9a45a")}{_flor(146, 182, 5, "#e8dcf3", "#d9a45a")}{_flor(128, 166, 3.6, "#f3bfb6")}
  <path d="M84 146 L100 172 L116 146 Z" fill="{GOLA}"/>
  <rect x="88" y="124" width="24" height="26" rx="8" fill="{PELE_SOMBRA}"/>
  {_cabelo()}
  <ellipse cx="62" cy="98" rx="6" ry="9" fill="{PELE_SOMBRA}"/><ellipse cx="138" cy="98" rx="6" ry="9" fill="{PELE_SOMBRA}"/>
  <circle cx="62" cy="109" r="3" fill="#f4f1ec"/><circle cx="138" cy="109" r="3" fill="#f4f1ec"/>
  <ellipse cx="100" cy="98" rx="37" ry="42" fill="url(#pele)" stroke="#3b2013" stroke-width="1.3" stroke-opacity=".4"/>
  <path d="{sob_e}" stroke="#2b1c16" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="{sob_d}" stroke="#2b1c16" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  {_olhos(e["olhos"])}
  <rect x="67" y="81" width="27" height="21" rx="8" stroke="{ARMACAO}" stroke-width="2.6" fill="#ffffff" fill-opacity=".08"/>
  <rect x="106" y="81" width="27" height="21" rx="8" stroke="{ARMACAO}" stroke-width="2.6" fill="#ffffff" fill-opacity=".08"/>
  <path d="M94 89 Q100 86 106 89" stroke="{ARMACAO}" stroke-width="2.4" fill="none"/>
  <path d="M100 98 Q97 108 100 110 Q103 111 106 109" stroke="{PELE_SOMBRA}" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  <ellipse cx="80" cy="110" rx="6" ry="3.5" fill="#a25a44" opacity=".35"/><ellipse cx="120" cy="110" rx="6" ry="3.5" fill="#a25a44" opacity=".35"/>
  {e["boca"]}
  {_flores_no_cabelo()}
  <rect width="200" height="200" filter="url(#papel)"/>
</g>
{_simbolo(e["simbolo"])}
</svg>'''


PASTA_ILUSTRACOES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lia")


@functools.lru_cache(maxsize=None)
def _ilustracao(expressao):
    """Ilustração (aquarela, estilo da faixa do MISM3) da expressão, em SVG com a imagem embutida e o
    mesmo selo no canto. None se o arquivo não existir: aí vale o desenho vetorial de svg()."""
    caminho = os.path.join(PASTA_ILUSTRACOES, f"{expressao}.webp")
    if expressao not in EXPRESSOES or not os.path.exists(caminho):
        return None
    with open(caminho, "rb") as f:
        foto = base64.b64encode(f.read()).decode("ascii")
    rotulo = ROTULOS.get(expressao, "Lia")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 200" '
            f'role="img" aria-label="{rotulo}"><title>{rotulo}</title>'
            '<clipPath id="corte"><circle cx="100" cy="100" r="98"/></clipPath>'
            f'<g clip-path="url(#corte)"><image width="200" height="200" preserveAspectRatio="xMidYMid slice" '
            f'xlink:href="data:image/webp;base64,{foto}" href="data:image/webp;base64,{foto}"/></g>'
            '<circle cx="100" cy="100" r="97" fill="none" stroke="#d9c8e6" stroke-width="2"/>'
            f'{_simbolo(EXPRESSOES[expressao]["simbolo"])}</svg>')


def img(expressao="acolhedora", tamanho=96):
    """<img> com a Lia embutida (funciona em st.markdown): a ilustração, ou o desenho vetorial de reserva."""
    figura = _ilustracao(expressao) or svg(expressao)
    dados = base64.b64encode(figura.encode("utf-8")).decode("ascii")
    return (f'<img src="data:image/svg+xml;base64,{dados}" width="{tamanho}" height="{tamanho}" '
            f'alt="{ROTULOS.get(expressao, "Lia")}" style="display:block"/>')
