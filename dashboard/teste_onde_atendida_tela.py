import os
import sys
import tempfile

# =====================================
# TESTE DE ACEITAÇÃO DA PÁGINA "ONDE SER ATENDIDA" (dashboard/pages/onde_ser_atendida.py)
#
# Abre a página DE VERDADE (Streamlit AppTest) com um CNES sintético e clica:
#   A. sem arquivo do CNES: aviso claro, sem quebrar;
#   B. com arquivo: cartões com tipo em palavras, endereço, telefone e link de mapa;
#   C. cada tipo de serviço (pílulas), a busca, o bairro e o filtro público/privado;
#   D. nada de "vaga garantida": o aviso de que cadastro não é serviço aberto aparece.
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


def main():
    with tempfile.TemporaryDirectory() as vazia, tempfile.TemporaryDirectory() as cheia:
        # A. sem arquivo
        os.environ["ESCUDO_CNES_PASTA"] = vazia
        at = abrir()
        checar("A. sem CNES: sem exceção", not at.exception)
        checar("A. sem CNES: avisa onde colocar o arquivo", "tbEstabelecimento" in texto(at))

        # B. com arquivo
        with open(os.path.join(cheia, "tbEstabelecimento202608.csv"), "w", encoding="latin-1", newline="") as f:
            f.write(CABECALHO + "\n" + "\n".join(LINHAS) + "\n")
        os.environ["ESCUDO_CNES_PASTA"] = cheia
        for nome in list(sys.modules):  # outra pasta: o módulo lê PASTA_CNES na importação
            if nome == "unidades_saude":
                del sys.modules[nome]
        at = abrir()
        t = texto(at)
        checar("B. com CNES: sem exceção", not at.exception)
        checar("B. cartão da UBS com nome legível, tipo em palavras e endereço",
               "UBS Jardim das Flores" in t and "Centro de saúde / Unidade básica" in t and "Av Paulista, 120" in t)
        checar("B. telefone formatado e link do mapa", "(19) 3534-1234" in t and "google.com/maps/search" in t)
        checar("B. 'Tudo' esconde farmácia (grupo outros)", "Farmacia Popular" not in t)
        checar("B. filtro padrão tira a clínica privada", "Clinica Estrela" not in t)
        checar("D. avisa que cadastro não é vaga nem serviço aberto", "não garante" in t)

        # C. pílulas, busca, filtro privado
        radio = next(r for r in at.radio if r.key == "un_grupo")
        checar("C. as pílulas trazem a contagem", any("Hospitais (1)" in o for o in radio.options))
        radio.set_value("hospital").run()
        t = texto(at)
        checar("C. Hospitais: só a Santa Casa", "Santa Casa de Rio Claro" in t and "UBS Jardim" not in t and not at.exception)
        next(r for r in at.radio if r.key == "un_grupo").set_value("urgencia").run()
        checar("C. Urgência: a UPA", "Upa Central" in texto(at) or "UPA Central" in texto(at))
        next(r for r in at.radio if r.key == "un_grupo").set_value("Tudo").run()
        next(c for c in at.checkbox if c.key == "un_publicos").set_value(False).run()
        checar("C. sem o filtro público, a clínica privada aparece", "Clinica Estrela" in texto(at) and not at.exception)
        next(c for c in at.checkbox if c.key == "un_publicos").set_value(True).run()
        next(i for i in at.text_input if i.key == "un_busca").set_value("jardim").run()
        t = texto(at)
        checar("C. busca 'jardim': só a UBS", "UBS Jardim das Flores" in t and "Santa Casa" not in t)
        next(i for i in at.text_input if i.key == "un_busca").set_value("zzzz").run()
        checar("C. busca sem resultado: mensagem, sem quebrar", any("Nenhuma unidade" in str(i.value) for i in at.info) and not at.exception)
        next(i for i in at.text_input if i.key == "un_busca").set_value("").run()
        next(s for s in at.selectbox if s.key == "un_bairro").set_value("Centro").run()
        t = texto(at)
        checar("C. bairro Centro: Santa Casa e UPA, sem a UBS", "Santa Casa" in t and "UBS Jardim" not in t and not at.exception)

    if falhas:
        print("\nFALHARAM:", *falhas, sep="\n  - ")
        sys.exit(1)
    print("\nTodas as checagens da página Onde ser atendida passaram.")


if __name__ == "__main__":
    main()
