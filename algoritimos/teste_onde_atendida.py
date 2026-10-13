import os
import sys
import tempfile

# =====================================
# TESTE DA LÓGICA DE "ONDE SER ATENDIDA" (onde_atendida.py), sem Streamlit:
#   - links do Google Maps (rota) e de ligar;
#   - sem CNES: a lista existe, só com o catálogo conferido (a página nunca fica vazia);
#   - com CNES: cruza por código e por nome, enriquece com telefone/horário/data, sem duplicar;
#   - apoio à mulher vem só do catálogo; creche e curso ficam de fora.
# Uso (da pasta do projeto):  py algoritimos\teste_onde_atendida.py
# =====================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402

import onde_atendida as oa  # noqa: E402
import unidades_saude as us  # noqa: E402


def cat(**kw):
    base = {"tipo": "saude", "subtipo": "ubs", "nome": "UBS Jardim das Flores", "cep": "13500100", "endereco": "Av Paulista, 120",
            "telefone": "(19) 3534-1234", "horario": "Seg a sex 7h às 17h", "lat": -22.41, "lon": -47.56, "geo": "coordenada_fonte",
            "fonte_url": "https://exemplo.gov.br", "verificado_em": "2026-10-08", "conferido": True, "aviso": None, "cnes": "2080001"}
    base.update(kw)
    return base


def main():
    # links
    l = oa.link_como_chegar("UBS Jardim", "Av Paulista, 120")
    assert l.startswith("https://www.google.com/maps/dir/?api=1&destination=") and "Rio+Claro" in l and "Av+Paulista" in l
    assert oa.link_ligar("(19) 3534-1234") == "tel:+551935341234"
    assert oa.link_ligar("(19) 3535-4558 / (19) 3532-6991") == "tel:+551935354558"
    assert oa.link_ligar("(19) 9 9956-3042 (WhatsApp)") == "tel:+5519999563042"
    assert oa.link_ligar("3534-1234") == "tel:+551935341234" and oa.link_ligar("0800 123 4567") == "tel:08001234567"
    assert oa.link_ligar("") == "" and oa.link_ligar(None) == "" and oa.link_ligar("sem telefone") == ""
    print("[OK] links do Google Maps e de ligar")

    servicos = [
        cat(),
        cat(nome="Hospital Sem Codigo", subtipo="hospital", cnes=None, telefone="(19) 3500-0000", endereco="Rua 3, 10"),
        cat(tipo="mulher", subtipo="ddm", nome="Delegacia de Defesa da Mulher (DDM) de Rio Claro", cnes=None, aviso="Endereço de 2017"),
        cat(tipo="mulher", subtipo="patrulha", nome="Patrulha Maria da Penha", cnes=None, telefone=None, conferido=False, aviso=None, lat=None, lon=None, geo=None),
        cat(tipo="assistencia", subtipo="cras", nome="CRAS Região Mãe Preta", cnes=None, telefone="(19) 3524-9954"),
        cat(tipo="creche", subtipo="creche", nome="EMEI Qualquer", cnes=None),
        cat(tipo="emprego_curso", subtipo="curso", nome="Curso X", cnes=None),
        cat(tipo="assistencia", subtipo="scfv", nome="Convivência Y", cnes=None),
        cat(subtipo="farmacia", nome="Farmácia Z", cnes=None),
    ]

    # sem CNES: só o catálogo conferido, e só o que é saúde ou apoio
    df = oa.unificar(None, servicos)
    nomes = set(df["nome"])
    assert "UBS Jardim das Flores" in nomes and "Hospital Sem Codigo" in nomes and "Patrulha Maria da Penha" in nomes
    assert not ({"EMEI Qualquer", "Curso X", "Convivência Y", "Farmácia Z"} & nomes), nomes
    assert df.attrs["tem_cnes"] is False
    ddm = df[df["nome"].str.contains("Delegacia")].iloc[0]
    assert ddm["grupo"] == "apoio" and ddm["tipo"] == "Delegacia de Defesa da Mulher" and ddm["conferido_em"] == "08/10/2026"
    pat = df[df["nome"].str.contains("Patrulha")].iloc[0]
    assert "conferido" in pat["aviso"].lower() and pat["link_ligar"] == "" and pat["link_chegar"].startswith("https://www.google.com/maps/dir")
    ubs = df[df["nome"] == "UBS Jardim das Flores"].iloc[0]
    assert ubs["mapa"] and ubs["horario"] == "Seg a sex 7h às 17h" and ubs["link_ligar"] == "tel:+551935341234"
    assert list(df[df["grupo"].astype(str) == "apoio"]["tipo"])[-1].startswith("CRAS"), "no apoio, a assistência social vem depois do que é da mulher"
    assert oa.contar(df)["apoio"] == 3 and oa.contar(df)["basica"] == 1
    print("[OK] sem CNES: lista conferida, só saúde e apoio, com aviso nos itens não conferidos")

    # com CNES: UBS casa por código, hospital por nome (sem código no catálogo); sem duplicar
    cnes = pd.DataFrame([
        {"cnes": "2080001", "nome": "UBS Jardim das Flores", "tipo": "Centro de saúde / Unidade básica", "grupo": "basica",
         "natureza": "publica", "endereco": "Av Paulista, 120 – Jardim Flores", "bairro": "Jardim Flores", "cep": "13500-100",
         "telefone": "", "lat": -22.41, "lon": -47.56, "mapa": True},
        {"cnes": "2080002", "nome": "Hospital Sem Codigo", "tipo": "Hospital geral", "grupo": "hospital",
         "natureza": "sem_fins", "endereco": "Rua 3, 10", "bairro": "Centro", "cep": "", "telefone": "(19) 3534-0000",
         "lat": float("nan"), "lon": float("nan"), "mapa": False},
        {"cnes": "2080003", "nome": "Clinica Estrela", "tipo": "Clínica", "grupo": "especialidade",
         "natureza": "privada", "endereco": "Rua 7, 45", "bairro": "Vila Nova", "cep": "", "telefone": "",
         "lat": float("nan"), "lon": float("nan"), "mapa": False},
    ])
    cnes.attrs.update({"tem_natureza": True, "arquivo": "tbEstabelecimento202608.csv"})
    df = oa.unificar(cnes, servicos)
    assert df.attrs["tem_cnes"] is True and df.attrs["arquivo"] == "tbEstabelecimento202608.csv"
    assert list(df["nome"]).count("UBS Jardim das Flores") == 1 and list(df["nome"]).count("Hospital Sem Codigo") == 1
    ubs = df[df["nome"] == "UBS Jardim das Flores"].iloc[0]
    assert ubs["telefone"] == "(19) 3534-1234" and ubs["horario"] and ubs["conferido_em"] == "08/10/2026" and ubs["origem"] == "cnes"
    hosp = df[df["nome"] == "Hospital Sem Codigo"].iloc[0]
    assert hosp["telefone"] == "(19) 3534-0000", "o telefone do CNES não é trocado pelo do catálogo"
    assert "Clinica Estrela" in set(df["nome"]) and set(df["grupo"].astype(str)) <= set(oa.ORDEM)
    print("[OK] com CNES: cruza por código e por nome, enriquece e não duplica")

    # filtros
    assert list(oa.filtrar(df, "hospital")["nome"]) == ["Hospital Sem Codigo"]
    assert "Clinica Estrela" not in set(oa.filtrar(df, "especialidade", so_publicos=True)["nome"])
    assert list(oa.filtrar(df, "basica", busca="delegacia")["nome"]) == ["Delegacia de Defesa da Mulher (DDM) de Rio Claro"]
    assert oa.filtrar(df, "basica", busca="zzzz").empty
    print("[OK] filtros: escolha, busca em todas e só públicas")

    # catálogo ausente ou ilegível: lista vazia, sem exceção
    assert oa.carregar_catalogo(os.path.join(tempfile.gettempdir(), "nao_existe.json")) == []
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{quebrado")
    assert oa.carregar_catalogo(f.name) == []
    os.unlink(f.name)
    assert oa.unificar(None, []).empty
    print("[OK] catálogo ausente ou quebrado: sem exceção")

    # o catálogo de verdade do projeto
    real = oa.carregar_catalogo()
    df = oa.unificar(None, real)
    assert len(real) == 164 and len(df) >= 45 and oa.contar(df)["apoio"] >= 8, (len(real), len(df), oa.contar(df))
    assert (df["link_chegar"].str.startswith("https://www.google.com/maps/dir")).all()
    print(f"[OK] catálogo real: {len(df)} lugares, {oa.contar(df)}")
    print("\nTodas as checagens de Onde ser atendida (lógica) passaram.")


if __name__ == "__main__":
    main()
