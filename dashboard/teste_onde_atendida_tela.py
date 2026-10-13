import os
import sys
import tempfile

# =====================================
# TESTE DE ACEITAÇÃO DA PÁGINA "ONDE SER ATENDIDA" (dashboard/pages/onde_ser_atendida.py)
#
# Abre a página DE VERDADE (Streamlit AppTest) e clica:
#   A. sem arquivo do CNES: a página NÃO fica vazia (catálogo conferido), com Como chegar (Google Maps),
#      Ligar, horário e data de conferência, e o apoio à mulher;
#   B. com um CNES sintético: as unidades do CNES entram junto do catálogo, sem quebrar;
#   C. cada escolha (pílulas), a busca em todas, o filtro público/privado e o "Mostrar mais";
#   D. nada de "vaga garantida": o aviso "não garante" aparece.
# Não precisa de banco (as internações por câncer são opcionais).
# Uso (da pasta do projeto):  py dashboard\teste_onde_atendida_tela.py
# =====================================

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PAGINA = os.path.join(RAIZ, "dashboard", "pages", "onde_ser_atendida.py")
falhas = []

CABECALHO = ("CO_CNES;CO_IBGE;NO_FANTASIA;TP_UNIDADE;CO_NATUREZA_JUR;NO_LOGRADOURO;NU_ENDERECO;NO_BAIRRO;"
             "CO_CEP;NU_TELEFONE;NU_LATITUDE;NU_LONGITUDE;CO_MOTIVO_DESAB")
LINHAS = [
    "2080001;3543907;UBS JARDIM DAS FLORES;02;1244;AV PAULISTA;120;JARDIM FLORES;13500100;1935341234;-22.41;-47.56;",
    "2080002;3543907;SANTA CASA DE RIO CLARO;05;3999;RUA 3;0;CENTRO;13500000;1935345000;-22.405;-47.561;",
    "2080003;3543907;CLINICA ESTRELA LTDA;36;2062;RUA 7;45;VILA NOVA;13506000;19999998888;-10.0;-40.0;",
    "2080004;3543907;UPA CENTRAL;73;1244;RUA 8;10;CENTRO;13500000;1935000001;-22.40;-47.57;",
    "2080005;3543907;FARMACIA POPULAR;43;1244;RUA 9;11;CENTRO;13500000;;;;",
]


def checar(nome, condicao):
    print(("OK   " if condicao else "FALHOU ") + nome)
    if not condicao:
        falhas.append(nome)


def abrir():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(PAGINA, default_timeout=60)
    at.run()
    return at


def texto(at):
    return " ".join(str(m.value) for m in at.markdown) + " " + " ".join(str(w.value) for w in at.warning)


def esquecer_modulos():
    for nome in ("unidades_saude", "onde_atendida"):  # o módulo lê PASTA_CNES na importação
        sys.modules.pop(nome, None)


def cartoes(at):
    return texto(at).count('class="un-cartao')


def main():
    with tempfile.TemporaryDirectory() as vazia, tempfile.TemporaryDirectory() as cheia:
        # A. sem arquivo do CNES: continua útil, com o catálogo conferido
        os.environ["ESCUDO_CNES_PASTA"] = vazia
        esquecer_modulos()
        at = abrir()
        t = texto(at)
        checar("A. sem CNES: sem exceção e sem tela vazia", not at.exception and not at.warning and cartoes(at) > 0)
        radio = next(r for r in at.radio if r.key == "un_grupo")
        checar("A. escolhas em palavras, com contagem", "Posto de saúde (22)" in radio.options and "Apoio à mulher (12)" in radio.options)
        checar("A. Como chegar abre o Google Maps (rota)", "google.com/maps/dir/?api=1&amp;destination=" in t or "google.com/maps/dir/?api=1&destination=" in t)
        checar("A. Ligar, horário e data de conferência no cartão", 'href="tel:+55' in t and "🕒" in t and "conferido em" in t)
        checar("D. avisa que a lista não garante vaga", "não garante" in t)
        radio.set_value("apoio").run()
        t = texto(at)
        checar("A. Apoio à mulher: delegacia, patrulha (com ⚠ a confirmar) e CRAS",
               "Delegacia de Defesa da Mulher" in t and "Patrulha Maria da Penha" in t and "⚠" in t and "CRAS" in t and not at.exception)
        next(r for r in at.radio if r.key == "un_grupo").set_value("hospital").run()
        checar("A. Hospital: lista os 3 do catálogo", cartoes(at) == 3 and not at.exception)

        # B. com CNES sintético
        with open(os.path.join(cheia, "tbEstabelecimento202608.csv"), "w", encoding="latin-1", newline="") as f:
            f.write(CABECALHO + "\n" + "\n".join(LINHAS) + "\n")
        os.environ["ESCUDO_CNES_PASTA"] = cheia
        esquecer_modulos()
        at = abrir()
        t = texto(at)
        checar("B. com CNES: sem exceção", not at.exception)
        checar("B. unidade do CNES com nome legível, tipo em palavras e endereço",
               "UBS Jardim das Flores" in t and "Centro de saúde / Unidade básica" in t and "Av Paulista, 120" in t)
        checar("B. telefone do CNES formatado e Como chegar", "(19) 3534-1234" in t and "google.com/maps/dir" in t)
        checar("B. unidade do catálogo continua na lista junto do CNES", "UBS 29" in texto(at) or "UBS Wenzel" in texto(at) or cartoes(at) >= 12)
        checar("B. filtro padrão tira a clínica privada", "Clinica Estrela" not in t)

        # C. escolhas, busca, filtro privado, mostrar mais
        radio = next(r for r in at.radio if r.key == "un_grupo")
        checar("C. as escolhas trazem a contagem do CNES + catálogo", any(o.startswith("Hospital (") for o in radio.options))
        radio.set_value("hospital").run()
        t = texto(at)
        checar("C. Hospital: Santa Casa do CNES e os do catálogo", "Santa Casa de Rio Claro" in t and not at.exception)
        next(r for r in at.radio if r.key == "un_grupo").set_value("urgencia").run()
        checar("C. Urgência: a UPA", "Upa Central" in texto(at) or "UPA Central" in texto(at))
        next(r for r in at.radio if r.key == "un_grupo").set_value("especialidade").run()
        checar("C. sem o filtro público, a clínica privada aparece",
               "Clinica Estrela" not in texto(at) and "Clinica Estrela" in texto(next_desmarcar(at)) and not at.exception)
        next(c for c in at.checkbox if c.key == "un_publicos").set_value(True).run()
        next(r for r in at.radio if r.key == "un_grupo").set_value("basica").run()
        antes = cartoes(at)
        checar("C. Posto de saúde: mostra a primeira página (12)", antes == 12)
        next(b for b in at.button if b.key == "un_mais").click().run()
        checar("C. 'Mostrar mais' traz os outros", cartoes(at) > antes and not at.exception)
        next(i for i in at.text_input if i.key == "un_busca").set_value("jardim").run()
        t = texto(at)
        checar("C. busca 'jardim' (em todas as opções): a UBS do CNES", "UBS Jardim das Flores" in t and not at.exception)
        next(i for i in at.text_input if i.key == "un_busca").set_value("farmacia").run()
        checar("C. a busca acha a farmácia (grupo que não é botão)", "Farmacia Popular" in texto(at))
        next(i for i in at.text_input if i.key == "un_busca").set_value("zzzz").run()
        checar("C. busca sem resultado: mensagem, sem quebrar", any("Nenhum lugar" in str(i.value) for i in at.info) and not at.exception)

    if falhas:
        print("\nFALHARAM:", *falhas, sep="\n  - ")
        sys.exit(1)
    print("\nTodas as checagens da página Onde ser atendida passaram.")


def next_desmarcar(at):
    next(c for c in at.checkbox if c.key == "un_publicos").set_value(False).run()
    return at


if __name__ == "__main__":
    main()
