from lia import caminho, responder

# =====================================
# PASSEIO PELO ESCUDO (combinado com o autor, 09/2026)
#
# Uma interação A MAIS, no canto da Lia, que não muda nada do que
# existe: a Lia conta a história do Escudo do começo ao fim, em 6
# paradas, NA ORDEM -- para quem chega pela primeira vez ou para
# apresentar à Secretaria. A árvore da Lia deixa a pessoa escolher;
# o Passeio conduz. Só cliques (anterior / próxima / sair); nada de
# texto digitado.
#
# As falas são as MESMAS da Lia (lia.responder): uma fonte só de
# texto, então o Passeio nunca diz algo diferente da Lia ou do painel.
# Cada parada leva o painel ao gráfico dela (o destino da resposta).
# =====================================

PARADAS = [
    ("O que mais aparece?", caminho("mais_aparece")),
    ("Está aumentando?", caminho("aumentando")),
    ("De onde vêm as pacientes de outros estados?", caminho("fluxo")),
    ("E em relação a São Paulo?", caminho("estado")),
    ("Onde podemos ter problema?", caminho("atencao")),
    ("O que estes dados não dizem", caminho("metodo")),
]

ABERTURA = "Vou te mostrar o essencial do Escudo em {n} paradas. É só ir clicando em “próxima”."
FECHAMENTO = ("Fim do passeio. Daqui, dá para explorar por conta própria pelas abas ou pedir à Lia, lá em cima, "
              "qualquer caminho.")


def parada(ctx, indice):
    """A parada `indice` (0 a len(PARADAS)-1): número, título, fala,
    expressão e destino no painel."""
    if not 0 <= indice < len(PARADAS):
        raise IndexError(f"o passeio tem {len(PARADAS)} paradas; pedida a {indice}")
    titulo, acao = PARADAS[indice]
    resposta = responder(ctx, acao)
    fala = resposta.fala
    if indice == 0:
        fala = ABERTURA.format(n=len(PARADAS)) + "\n\n" + fala
    if indice == len(PARADAS) - 1:
        fala = fala + "\n\n" + FECHAMENTO
    return {
        "numero": indice + 1,
        "total": len(PARADAS),
        "titulo": titulo,
        "fala": fala,
        "expressao": resposta.expressao,
        "destino": resposta.destino or {},
    }
