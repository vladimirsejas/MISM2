import os
import tempfile

import unidades_saude as us

# =====================================
# TESTE DAS UNIDADES DE SAÚDE DA CIDADE (unidades_saude.py, 10/2026)
#
# CSV sintético no formato do CNES (latin-1, separador ;), com os casos
# de borda que importam:
#   - o município vale pelo ENDEREÇO (CO_IBGE), não pelo gestor;
#   - código de 6 ou 7 dígitos;
#   - unidade desabilitada fica de fora (e é contada);
#   - CNES repetido vira uma linha;
#   - coordenada fora da cidade não vai para o mapa;
#   - tipo em palavras, natureza pública / sem fins / privada;
#   - sem coluna de município: não chuta, devolve o motivo.
# Não precisa de banco nem de Streamlit.
# =====================================

CABECALHO = ("CO_CNES;CO_IBGE;CO_MUNICIPIO_GESTOR;NO_FANTASIA;NO_RAZAO_SOCIAL;TP_UNIDADE;CO_NATUREZA_JUR;"
             "NO_LOGRADOURO;NU_ENDERECO;NO_BAIRRO;CO_CEP;NU_TELEFONE;NU_LATITUDE;NU_LONGITUDE;CO_MOTIVO_DESAB")
LINHAS = [
    # ativa, pública, UBS, com mapa válido
    "2080001;3543907;3543907;UBS JARDIM DAS FLORES;FUNDACAO MUNICIPAL DE SAUDE;02;1244;AV PAULISTA;120;JARDIM FLORES;"
    "13500100;1935341234;-22.4100;-47.5600;",
    # código de município com 6 dígitos (sem o verificador), hospital sem fins lucrativos, vírgula decimal
    "2080002;354390;3543907;SANTA CASA DE RIO CLARO;ASSOCIACAO SANTA CASA;05;3999;RUA 3;0;CENTRO;13500000;"
    "1935345000;-22,4050;-47,5610;",
    # privada, coordenada ERRADA (fora da cidade)
    "2080003;3543907;3543907;CLINICA ESTRELA LTDA;ESTRELA SERVICOS;36;2062;RUA 7;45;VILA NOVA;13506000;19999998888;"
    "-10.0;-40.0;",
    # desabilitada: sai
    "2080004;3543907;3543907;POSTO FECHADO;X;01;1244;RUA 9;1;CENTRO;13500000;;;;05",
    # CNES repetido: uma linha só
    "2080001;3543907;3543907;UBS JARDIM DAS FLORES DUPLICADA;X;02;1244;AV PAULISTA;120;JARDIM FLORES;13500100;;;;",
    # outra cidade (gestor é Rio Claro, mas o endereço é de Limeira): NÃO entra
    "2080005;3526902;3543907;UPA DE LIMEIRA;X;73;1244;RUA 1;1;CENTRO;13480000;;;;",
    # gestor de outra cidade, mas o endereço é Rio Claro (unidade estadual): ENTRA
    "2080006;3543907;3550308;AME RIO CLARO;SECRETARIA ESTADUAL;04;1023;RUA 5;10;CENTRO;13500000;1935000000;;;",
    # sem tipo conhecido
    "2080007;3543907;3543907;UNIDADE ESTRANHA;X;99;;RUA 6;2;CENTRO;13500000;;;;",
]


def escrever(pasta, nome, cabecalho, linhas, codificacao="latin-1"):
    with open(os.path.join(pasta, nome), "w", encoding=codificacao, newline="") as f:
        f.write(cabecalho + "\n" + "\n".join(linhas) + "\n")


def main():
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202608.csv", CABECALHO, LINHAS)
        df = us.carregar_unidades(pasta, "3543907", tamanho_pedaco=3)  # pedaços pequenos: testa a leitura em partes
        assert not df.attrs["aviso"], df.attrs["aviso"]
        nomes = set(df["nome"])
        assert "UPA de Limeira" not in nomes and "Posto Fechado" not in nomes, nomes
        assert {"UBS Jardim das Flores", "Santa Casa de Rio Claro", "AME Rio Claro", "Clinica Estrela Ltda"} <= nomes, nomes
        assert len(df) == 5, (len(df), sorted(nomes))
        assert df.attrs["criterio_municipio"] == "endereço" and df.attrs["desabilitados"] == 1
        print("[OK] município pelo endereço (6 ou 7 dígitos), desabilitada fora e contada, CNES repetido numa linha, "
              "outra cidade fora")

        ubs = df[df["nome"] == "UBS Jardim das Flores"].iloc[0]
        assert ubs["tipo"] == "Centro de saúde / Unidade básica" and str(ubs["grupo"]) == "basica"
        assert ubs["natureza"] == "publica" and ubs["telefone"] == "(19) 3534-1234" and ubs["cep"] == "13500-100"
        assert ubs["endereco"] == "Av Paulista, 120 – Jardim Flores", ubs["endereco"]
        assert bool(ubs["mapa"]) and ubs["link_mapa"].startswith("https://www.google.com/maps/search/?api=1&query=")
        santa = df[df["nome"] == "Santa Casa de Rio Claro"].iloc[0]
        assert str(santa["grupo"]) == "hospital" and santa["natureza"] == "sem_fins"
        assert santa["endereco"] == "Rua 3, s/n – Centro", santa["endereco"]
        assert bool(santa["mapa"]) and abs(santa["lat"] + 22.405) < 1e-9  # vírgula decimal lida
        clin = df[df["nome"] == "Clinica Estrela Ltda"].iloc[0]
        assert clin["natureza"] == "privada" and not bool(clin["mapa"])  # coordenada errada: fica na lista, não no mapa
        ame = df[df["nome"] == "AME Rio Claro"].iloc[0]
        assert ame["natureza"] == "publica" and str(ame["grupo"]) == "especialidade"
        estranha = df[df["nome"] == "Unidade Estranha"].iloc[0]
        assert estranha["tipo"] == "Tipo 99 (sem descrição)" and str(estranha["grupo"]) == "outros"
        assert estranha["natureza"] == "desconhecida"
        print("[OK] tipo em palavras, grupo, natureza, telefone, CEP, endereço, mapa só com coordenada da cidade, "
              "tipo desconhecido não é inventado")

        # ordem: grupos na ordem da página (básica primeiro), depois nome
        assert [str(g) for g in df["grupo"]][0] == "basica" and list(df["grupo"].astype(str)).index("hospital") > 0
        cont = us.contar_por_grupo(df)
        assert cont["basica"] == 1 and cont["hospital"] == 1 and cont["especialidade"] == 2 and cont["outros"] == 1
        print("[OK] contagem por grupo:", cont)

        # filtros
        assert list(us.filtrar(df, grupos=["hospital"])["nome"]) == ["Santa Casa de Rio Claro"]
        publicas = us.filtrar(df, naturezas=["publica", "sem_fins"])
        assert "Clinica Estrela Ltda" not in set(publicas["nome"]) and len(publicas) == 3
        assert list(us.filtrar(df, busca="jardim FLORES")["nome"]) == ["UBS Jardim das Flores"]
        assert list(us.filtrar(df, busca="2080006")["nome"]) == ["AME Rio Claro"]
        assert list(us.filtrar(df, busca="sao")["nome"]) == []  # sem acento nem caixa, mas sem achar o que não existe
        assert len(us.filtrar(df, bairro="Centro")) == 3
        print("[OK] filtros: grupo, natureza, busca sem acento/caixa (nome, endereço, CNES) e bairro")

        # a leitura nunca promete vaga nem funcionamento
        frases = " ".join(us.leitura_lista(df, publicas, ["basica"], True))
        assert "não garante" in frases and "Papanicolau" in frases and "SUS" in frases
        print("[OK] leitura avisa que cadastro não é vaga nem serviço aberto")

        # diagnóstico mostra o que foi reconhecido
        d = us.diagnosticar(pasta)
        assert d["arquivo"] == "tbEstabelecimento202608.csv" and "municipio_local" in d["reconhecidas"]
        assert "motivo de desabilitação" not in d["ausentes"]
        print("[OK] diagnóstico das colunas")

    # UTF-8 com acento + só município do gestor (sem endereço): usa o gestor e diz isso
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202609.csv", "CO_CNES;CO_MUNICIPIO_GESTOR;NO_FANTASIA;TP_UNIDADE",
                 ["1;3543907;POSTO SÃO JOÃO;01", "2;3550308;POSTO DE SAMPA;01"], codificacao="utf-8")
        df = us.carregar_unidades(pasta)
        assert list(df["nome"]) == ["Posto São João"] and df.attrs["criterio_municipio"] == "gestor", df
        assert df.attrs["tem_natureza"] is False and df.iloc[0]["natureza"] == "desconhecida"
        print("[OK] UTF-8 com acento; sem coluna do endereço usa o gestor e registra o critério")

    # sem coluna de município: recusa, com o motivo
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202609.csv", "CO_CNES;NO_FANTASIA", ["1;POSTO A"])
        df = us.carregar_unidades(pasta)
        assert df.empty and "município" in df.attrs["aviso"], df.attrs
        print("[OK] sem coluna de município: não chuta, explica")

    # sem arquivo / pasta que não existe
    with tempfile.TemporaryDirectory() as pasta:
        df = us.carregar_unidades(pasta)
        assert df.empty and "tbEstabelecimento" in df.attrs["aviso"]
    assert us.carregar_unidades(os.path.join(pasta, "nao_existe")).empty
    assert us.diagnosticar(os.path.join(pasta, "nao_existe"))["arquivo"] is None
    print("[OK] sem arquivo: aviso, sem exceção")

    # nomes e formatos
    assert us.nome_legivel("UBS  JARDIM NOVO DE SAO JOAO") == "UBS Jardim Novo de Sao Joao"
    assert us.nome_legivel("CAPS II - ADULTO") == "CAPS II - Adulto"
    assert us.telefone_legivel("19 3534-5612") == "(19) 3534-5612" and us.telefone_legivel("3534") == ""
    assert us.telefone_legivel("019987654321") == "(19) 98765-4321" and us.cep_legivel("13.500-100") == "13500-100"
    assert us.classificar_natureza("1244") == "publica" and us.classificar_natureza("3069") == "sem_fins"
    assert us.classificar_natureza("2062") == "privada" and us.classificar_natureza("") == "desconhecida"
    assert us.classificar_tipo("2")[1] == "basica" and us.classificar_tipo("", "HOSPITAL DIA ISOLADO")[1] == "hospital"
    print("[OK] nomes, telefone, CEP, natureza e tipo (código com ou sem zero à esquerda, ou texto)")

    print("\nTodas as checagens das unidades de saúde passaram.")


if __name__ == "__main__":
    main()
