import os
import tempfile

# O teste monta o próprio CNES sintético: sem o Parquet real (dados_parquet/cnes) para "sem arquivo" continuar valendo.
os.environ["ESCUDO_PARQUET_PASTA"] = os.path.join(tempfile.gettempdir(), "sem_parquet_escudo")

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

    # pacote do CNES aberto numa subpasta (BASE_DE_DADOS_CNES_AAAAMM): ainda acha o arquivo
    with tempfile.TemporaryDirectory() as pasta:
        sub = os.path.join(pasta, "BASE_DE_DADOS_CNES_202608")
        os.makedirs(sub)
        escrever(sub, "tbEstabelecimento202608.csv", CABECALHO, LINHAS)
        df = us.carregar_unidades(pasta, "3543907")
        assert not df.attrs["aviso"] and len(df) > 0, df.attrs
        assert us.diagnosticar(pasta)["arquivo"] == "tbEstabelecimento202608.csv"
        print("[OK] acha o arquivo em subpasta")

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

    # serviços CNES: os quatro arquivos precisam ter o mesmo mês; a classificação é chave composta
    # serviço+classificação, para não associar rótulos de outro serviço com o mesmo código.
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202608.csv",
                 "CO_UNIDADE;CO_CNES;CO_IBGE;NO_FANTASIA;TP_UNIDADE;CO_MOTIVO_DESAB",
                 ["1001;2080001;3543907;AME RIO CLARO;04;"])
        escrever(pasta, "rlEstabServClass202608.csv", "CO_UNIDADE;CO_SERVICO;CO_CLASSIFICACAO",
                 ["1001;151;002"])
        escrever(pasta, "tbClassificacaoServico202608.csv",
                 "CO_CLASSIFICACAO_SERVICO;CO_SERVICO_ESPECIALIZADO;DS_CLASSIFICACAO_SERVICO",
                 ["002;151;MAMOGRAFIA", "002;152;MEDICINA NUCLEAR IN VITRO"])
        escrever(pasta, "tbServicoEspecializado202608.csv",
                 "CO_SERVICO_ESPECIALIZADO;DS_SERVICO_ESPECIALIZADO",
                 ["151;SERVICO DE DIAGNOSTICO POR IMAGEM", "152;SERVICO DE MEDICINA NUCLEAR"])
        df = us.carregar_unidades(pasta, tamanho_pedaco=1)
        servicos = df.iloc[0]["servicos"]
        assert "MAMOGRAFIA" in servicos and "SERVICO DE DIAGNOSTICO POR IMAGEM" in servicos, servicos
        assert "MEDICINA NUCLEAR" not in servicos, servicos
        assert not df.attrs["aviso_servicos"]
        print("[OK] serviços CNES associados pela chave composta e pelo mesmo mês")

    # serviço PRÓPRIO x POR TERCEIRO (TP_CARACTERISTICA 1 x 2): o CNES real de Rio Claro registra a UBS com radiologia,
    # ultrassom e mamografia por terceiro; ela não faz o exame no local
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202608.csv",
                 "CO_UNIDADE;CO_CNES;CO_IBGE;NO_FANTASIA;TP_UNIDADE;CO_MOTIVO_DESAB",
                 ["1001;2080001;3543907;AME RIO CLARO;04;", "1002;2080002;3543907;UBS DO BAIRRO;02;"])
        escrever(pasta, "rlEstabServClass202608.csv", "CO_UNIDADE;CO_SERVICO;CO_CLASSIFICACAO;TP_CARACTERISTICA;CO_CNPJCPF",
                 ["1001;151;002;1;NAO INFORMADO",     # o AME faz mamografia
                  "1002;151;002;2;2047470",           # a UBS tem mamografia por terceiro
                  "1002;112;001;1;NAO INFORMADO",     # e pré-natal próprio
                  "1002;151;003;1;NAO INFORMADO",     # radiologia própria E por terceiro: vale a própria
                  "1002;151;003;2;2047470"])
        escrever(pasta, "tbClassificacaoServico202608.csv",
                 "CO_CLASSIFICACAO_SERVICO;CO_SERVICO_ESPECIALIZADO;DS_CLASSIFICACAO_SERVICO",
                 ["002;151;MAMOGRAFIA", "003;151;RADIOLOGIA", "001;112;ACOMPANHAMENTO DO PRE-NATAL"])
        escrever(pasta, "tbServicoEspecializado202608.csv", "CO_SERVICO_ESPECIALIZADO;DS_SERVICO_ESPECIALIZADO",
                 ["151;SERVICO DE DIAGNOSTICO POR IMAGEM", "112;SERVICO DE ATENCAO AO PRE-NATAL"])
        df = us.carregar_unidades(pasta, tamanho_pedaco=2)
        ame = df[df["nome"].str.contains("Ame", case=False)].iloc[0]["servicos"]
        ubs = df[df["nome"].str.contains("Ubs", case=False)].iloc[0]["servicos"]
        assert "MAMOGRAFIA" in ame and us.TAG_TERCEIRO not in ame, ame
        assert f"MAMOGRAFIA{us.TAG_TERCEIRO}" in ubs, ubs
        assert "ACOMPANHAMENTO DO PRE-NATAL" in ubs and f"ACOMPANHAMENTO DO PRE-NATAL{us.TAG_TERCEIRO}" not in ubs, ubs
        assert f"RADIOLOGIA{us.TAG_TERCEIRO}" not in ubs and "RADIOLOGIA" in ubs, ubs  # próprio vence terceiro
        print("[OK] serviço próprio x por terceiro (TP_CARACTERISTICA): a UBS não 'faz' o exame que tem por terceiro")

    # médicos especialistas: conta profissionais distintos com carga ambulatorial, só de ocupações "MEDICO ..."
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202608.csv",
                 "CO_UNIDADE;CO_CNES;CO_IBGE;NO_FANTASIA;TP_UNIDADE;CO_MOTIVO_DESAB",
                 ["1001;2080001;3543907;AME RIO CLARO;04;", "1002;2080002;3543907;UBS SEM MEDICO;02;",
                  "9001;2090001;3550308;CLINICA EM SAO PAULO;04;"])
        escrever(pasta, "tbAtividadeProfissional202608.csv",
                 "CO_CBO;DS_ATIVIDADE_PROFISSIONAL;TP_CLASSIFICACAO_PROFISSIONAL",
                 ["225135;MEDICO DERMATOLOGISTA;", "225120;MEDICO CARDIOLOGISTA;", "322205;TECNICO DE ENFERMAGEM;",
                  "251510;PSICOLOGO CLINICO;", "223505;ENFERMEIRO;", "223710;NUTRICIONISTA;", "223105;MEDICO VETERINARIO;"])
        escrever(pasta, "tbCargaHorariaSus202608.csv",
                 "CO_UNIDADE;CO_PROFISSIONAL_SUS;CO_CBO;TP_SUS_NAO_SUS;QT_CARGA_HORARIA_AMBULATORIAL",
                 ["1001;P1;225135;S;20", "1001;P1;225135;S;10",   # a mesma pessoa em dois vínculos conta uma vez
                  "1001;P2;225135;S;20", "1001;P3;225135;S;0",    # sem carga ambulatorial: cadastrado, mas fora do ambulatório
                  "1001;P4;225120;S;8", "1001;P5;322205;S;40",    # técnico de enfermagem: não entra
                  "1001;P8;251510;S;20", "1001;P9;223105;S;20",   # psicólogo entra; veterinário não
                  "9001;P6;225135;S;20"])                         # unidade de outra cidade: ignorada
        df = us.carregar_unidades(pasta, tamanho_pedaco=2)
        ame = df[df["nome"].str.contains("Ame", case=False)].iloc[0]["servicos"]
        assert "MEDICO DERMATOLOGISTA (2 no ambulatório, 3 cadastrados)" in ame, ame  # P3 sem horas: cadastrado, mas não no ambulatório
        assert "MEDICO CARDIOLOGISTA (1 no ambulatório, 1 cadastrado)" in ame, ame
        assert "ENFERMAGEM" not in ame and "VETERINARIO" not in ame, ame
        assert "PSICOLOGO CLINICO (1 no ambulatório, 1 cadastrado)" in ame, ame
        assert df[df["nome"].str.contains("Sem Medico", case=False)].iloc[0]["servicos"] == ""
        assert "P1" not in " ".join(df["servicos"]), "nenhum código de profissional pode sair"
        assert not df.attrs["aviso_medicos"]
        print("[OK] especialistas médicos: contagem por unidade, sem identificar pessoas")
    # arquivo REAL é de ~1 GB: os primeiros 200 KB são UTF-8 e um byte de latin-1 aparece depois (já quebrou no notebook)
    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202608.csv", "CO_UNIDADE;CO_CNES;CO_IBGE;NO_FANTASIA;TP_UNIDADE;CO_MOTIVO_DESAB",
                 ["1001;2080001;3543907;AME RIO CLARO;04;"])
        escrever(pasta, "tbAtividadeProfissional202608.csv", "CO_CBO;DS_ATIVIDADE_PROFISSIONAL", ["225135;MEDICO DERMATOLOGISTA"])
        linhas = [f"7{i:06d};PX{i};322205;S;1;0;USUARIO" for i in range(12000)]  # outras unidades, ~250 KB de ASCII
        linhas += ["1001;PA;225135;S;1;20;JOS\xba DA SILVA", "1001;PB;225135;S;1;20;MAR\xcdA"]
        with open(os.path.join(pasta, "tbCargaHorariaSus202608.csv"), "wb") as f:
            f.write("CO_UNIDADE;CO_PROFISSIONAL_SUS;CO_CBO;TP_SUS_NAO_SUS;IND_VINCULACAO;QT_CARGA_HORARIA_AMBULATORIAL;CO_USUARIO\n"
                    .encode("latin-1"))
            f.write(("\n".join(linhas) + "\n").encode("latin-1"))
        assert os.path.getsize(os.path.join(pasta, "tbCargaHorariaSus202608.csv")) > 250_000
        df = us.carregar_unidades(pasta)
        assert not df.attrs["aviso_medicos"], df.attrs["aviso_medicos"]
        assert "MEDICO DERMATOLOGISTA (2 no ambulatório, 2 cadastrados)" in df.iloc[0]["servicos"], df.iloc[0]["servicos"]
        print("[OK] arquivo grande com byte fora de UTF-8 depois do começo: lido sem perder os médicos")

    with tempfile.TemporaryDirectory() as pasta:
        escrever(pasta, "tbEstabelecimento202608.csv", "CO_UNIDADE;CO_CNES;CO_IBGE;NO_FANTASIA;TP_UNIDADE;CO_MOTIVO_DESAB",
                 ["1001;2080001;3543907;AME RIO CLARO;04;"])
        df = us.carregar_unidades(pasta)
        assert len(df) == 1 and df.attrs["aviso_medicos"], "sem os arquivos de profissionais: aviso, sem quebrar"
        print("[OK] sem arquivos de profissionais: aviso, sem exceção")

    print("\nTodas as checagens das unidades de saúde passaram.")


if __name__ == "__main__":
    main()
