"""Bateria da CAIXA DE BUSCA de "Onde ser atendida" (18/10/2026).

Corpus imita o CNES real de Rio Claro (rótulos e nomes que apareceram na saída do diagnóstico do autor) e o
que o autor conhece da rede: raio X nas UPAs, ultrassom no CEAD, o AME tem tudo, UBS só com especialistas.
Cada linha é (o que a pessoa digita, unidades que DEVEM aparecer, unidades que NÃO podem aparecer).

    py algoritimos\\teste_busca_caixa.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import onde_atendida as oa  # noqa: E402


def un(nome, tipo, grupo, natureza, servicos, bairro="Centro", endereco="Rua 1, 10"):
    return {"nome": nome, "tipo": tipo, "grupo": grupo, "natureza": natureza, "servicos": servicos,
            "bairro": bairro, "endereco": endereco}


MED_GIN = "MEDICO GINECOLOGISTA E OBSTETRA (7 no ambulatório, 7 cadastrados)"
UNIDADES = [
    un("AME Ambulatorio Med de Especialidades de Rio Claro", "Policlínica", "especialidade", "publica",
       "MAMOGRAFIA | ULTRASONOGRAFIA | RADIOLOGIA | TOMOGRAFIA COMPUTADORIZADA | EXAMES CITOPATOLOGICOS | DENSITOMETRIA OSSEA | "
       "SERVICO DE DIAGNOSTICO POR IMAGEM | MEDICO DERMATOLOGISTA (4 no ambulatório, 4 cadastrados) | MEDICO CARDIOLOGISTA (4 no ambulatório, 4 cadastrados) | "
       "MEDICO OFTALMOLOGISTA (3 no ambulatório, 3 cadastrados) | PSICOLOGO CLINICO (2 no ambulatório, 2 cadastrados)"),
    un("Centro de Especialidades e Apoio Diagnostico CEAD", "Policlínica", "especialidade", "publica",
       "ULTRASONOGRAFIA | SERVICO DE DIAGNOSTICO POR IMAGEM | " + MED_GIN + " | MEDICO CARDIOLOGISTA (4 no ambulatório, 4 cadastrados) | "
       "MEDICO DERMATOLOGISTA (3 no ambulatório, 3 cadastrados) | MEDICO EM RADIOLOGIA E DIAGNOSTICO POR IMAGEM (2 no ambulatório, 2 cadastrados)"),
    un("UPA Central", "Pronto atendimento", "urgencia", "publica",
       "RADIOLOGIA | SERVICO DE DIAGNOSTICO POR IMAGEM | MEDICO CLINICO (9 no ambulatório, 9 cadastrados)"),
    un("UBS Dr Mario Fittipaldi", "Centro de saúde / Unidade básica", "basica", "publica",
       "ACOMPANHAMENTO DO PRE-NATAL | RADIOLOGIA [POR TERCEIRO] | ULTRASONOGRAFIA [POR TERCEIRO] | MAMOGRAFIA [POR TERCEIRO] | "
       "SERVICO DE DIAGNOSTICO POR IMAGEM [POR TERCEIRO] | " + MED_GIN + " | MEDICO PEDIATRA (2 no ambulatório, 2 cadastrados) | "
       "ENFERMEIRO DA ESTRATEGIA DE SAUDE DA FAMILIA (3 no ambulatório, 3 cadastrados)", "Jardim Wenzel", "Rua 21, 4219"),
    un("UBS Dr Silvio Arnaldo Piva", "Centro de saúde / Unidade básica", "basica", "publica",
       "ACOMPANHAMENTO DO PRE-NATAL | " + MED_GIN + " | NUTRICIONISTA (1 no ambulatório, 1 cadastrado)", "Vila Paulista", "Av 3, 1784"),
    un("Santa Casa de Rio Claro", "Hospital geral", "hospital", "sem_fins",
       "MAMOGRAFIA | ULTRASONOGRAFIA | RADIOLOGIA | TOMOGRAFIA COMPUTADORIZADA | SERVICO DE DIAGNOSTICO POR IMAGEM | "
       "ACOMPANHAMENTO DO PRE-NATAL DE ALTO RISCO | ATENCAO A SAUDE AUDITIVA | SERVICO DE DIAGNOSTICO DE LABORATORIO CLINICO | "
       "MEDICO DERMATOLOGISTA (2 no ambulatório, 8 cadastrados) | MEDICO ONCOLOGISTA CLINICO (7 no ambulatório, 7 cadastrados) | " + MED_GIN),
    un("Clinica Reis", "Consultório isolado", "especialidade", "privada",
       "MEDICO DERMATOLOGISTA (1 no ambulatório, 1 cadastrado) | MEDICO CARDIOLOGISTA (1 no ambulatório, 1 cadastrado)"),
    un("Hadas Urban Spa Rio Claro", "Consultório isolado", "especialidade", "privada",
       "MEDICO DERMATOLOGISTA (1 no ambulatório, 1 cadastrado)"),
    un("Clinica Gamela", "Clínica", "especialidade", "privada", "FISIOTERAPEUTA GERAL (2 no ambulatório, 2 cadastrados)"),
    un("Laboratorio Central", "Unidade de apoio diagnóstico", "especialidade", "privada",
       "SERVICO DE DIAGNOSTICO DE LABORATORIO CLINICO | EXAMES CITOPATOLOGICOS"),
    un("Farmacia Popular Centro", "Farmácia", "outros", "publica", ""),
]
DF = pd.DataFrame(UNIDADES)

AME = "AME Ambulatorio Med de Especialidades de Rio Claro"
CEAD = "Centro de Especialidades e Apoio Diagnostico CEAD"
UPA = "UPA Central"
FITT = "UBS Dr Mario Fittipaldi"
PIVA = "UBS Dr Silvio Arnaldo Piva"
SC = "Santa Casa de Rio Claro"
REIS = "Clinica Reis"
SPA = "Hadas Urban Spa Rio Claro"
GAMELA = "Clinica Gamela"
LAB = "Laboratorio Central"

# (digitado, deve ter, não pode ter)
CASOS = [
    # exames, do jeito que se fala
    ("raio x", {UPA, AME, SC}, {FITT, PIVA, CEAD}),
    ("raio-x", {UPA, AME, SC}, {FITT, PIVA}),
    ("rx", {UPA, AME, SC}, {FITT, PIVA}),
    ("radiografia", {UPA, AME, SC}, {FITT, PIVA}),
    ("onde faço raio x pelo SUS", {UPA, AME, SC}, {FITT, PIVA}),
    ("ultrassom", {CEAD, AME, SC}, {FITT, PIVA, UPA}),
    ("ultra som", {CEAD, AME, SC}, {FITT, PIVA, UPA}),
    ("usg", {CEAD, AME, SC}, {FITT, PIVA, UPA}),
    ("ultrassonografia", {CEAD, AME, SC}, {FITT, PIVA, UPA}),
    ("mamografia", {AME, SC}, {FITT, PIVA, UPA, CEAD}),
    ("mamo", {AME, SC}, {FITT, PIVA, UPA}),
    ("preventivo", {AME, LAB}, {FITT, UPA}),
    ("papanicolau", {AME, LAB}, {FITT, UPA}),
    ("exame de sangue", {SC, LAB}, {FITT, UPA, AME}),
    ("tomografia", {AME, SC}, {FITT, UPA, CEAD}),
    ("densitometria", {AME}, {FITT, UPA, SC}),
    # erro de digitação, plural, hífen, acento
    ("ultrasom", {CEAD, AME, SC}, {FITT, UPA}),
    ("mamografa", {AME, SC}, {FITT, UPA}),
    ("dermatolgista", {AME, CEAD, SC, REIS, SPA}, {FITT, UPA}),
    ("ginecologsta", {CEAD, FITT, PIVA, SC}, {UPA, REIS}),
    ("ginecologistas", {CEAD, FITT, PIVA, SC}, {UPA, REIS}),
    ("Ginecologista", {CEAD, FITT, PIVA, SC}, {UPA, REIS}),
    ("pré-natal", {FITT, PIVA, SC}, {UPA, AME}),
    ("prenatal", {FITT, PIVA, SC}, {UPA, AME}),
    ("pre natal", {FITT, PIVA, SC}, {UPA, AME}),
    # especialistas e outros profissionais
    ("dermatologista", {AME, CEAD, SC, REIS, SPA}, {FITT, PIVA, UPA}),
    ("pele", {AME, CEAD, SC, REIS, SPA}, {FITT, UPA}),
    ("cardiologista", {AME, CEAD, REIS}, {FITT, UPA, SC}),
    ("pediatra", {FITT}, {UPA, AME}),
    ("psicologo", {AME}, {FITT, UPA}),
    ("psicóloga", {AME}, {FITT, UPA}),
    ("nutricionista", {PIVA}, {FITT, UPA, AME}),
    ("fisioterapia", {GAMELA}, {FITT, UPA}),
    ("enfermeiro", {FITT}, {UPA, AME}),
    ("oncologista", {SC}, {FITT, UPA, AME}),
    # exame NÃO é médico: radiologista cadastrado não significa que a unidade tem o aparelho
    ("raio x", {UPA}, {CEAD}),
    # nome de lugar e trecho dentro de palavra
    ("ame", {AME}, {GAMELA}),
    ("gamela", {GAMELA}, {AME}),
    ("fittipaldi", {FITT}, {PIVA}),
    ("santa casa", {SC}, {FITT}),
    ("jardim wenzel", {FITT}, {PIVA}),
    # duas coisas na mesma frase: as DUAS
    ("mamografia e ultrassom", {AME, SC}, {CEAD, UPA, FITT}),
    ("dermatologista e cardiologista", {AME, CEAD, REIS}, {SPA, SC, FITT}),
    # como a pessoa fala: parte do corpo, situação
    ("coração", {AME, CEAD, REIS}, {FITT, UPA, SC}),
    ("problema no olho", {AME}, {FITT, UPA}),
    ("estou grávida", {FITT, PIVA, SC}, {UPA, AME}),
    ("consulta para criança", {FITT}, {UPA, AME}),
    ("pele", {SPA, REIS}, {FITT}),
    # sem resultado de verdade
    ("zzzzzz", set(), {AME, UPA, FITT}),
    ("helicoptero", set(), {AME, UPA, FITT}),
]


def main():
    falhas = []
    for digitado, deve, nao_pode in CASOS:
        achadas = set(oa.filtrar(DF, None, busca=digitado)["nome"])
        faltou, sobrou = deve - achadas, achadas & nao_pode
        if not deve:
            ok = not achadas
        else:
            ok = not faltou and not sobrou
        marca = "OK  " if ok else "FALHOU"
        print(f"{marca} '{digitado}'" + ("" if ok else f"  faltou={sorted(faltou)} sobrou={sorted(sobrou)}" + (f" achou={sorted(achadas)}" if not deve else "")))
        if not ok:
            falhas.append(digitado)

    # sugestões quando nada casa: o que existe no cadastro e se parece com o digitado
    sug = [t for _, t in oa.sugestoes(DF, "dermatologa")]
    ok = bool(sug) and sug[0] == "DERMATOLOGISTA" and len(sug) <= 5
    print(("OK  " if ok else "FALHOU") + f" sugestões para 'dermatologa': {sug}")
    if not ok:
        falhas.append("sugestoes")
    ok = oa.sugestoes(DF, "zzzzzz") == [] and oa.sugestoes(DF, "") == []
    print(("OK  " if ok else "FALHOU") + " sugestões: nada parecido -> nada (não inventa)")
    if not ok:
        falhas.append("sugestoes_vazias")
    ok = oa.corrigir_busca(DF, "ultrasom") == "ultrassom" and oa.corrigir_busca(DF, "dermatologista") == "dermatologista"
    print(("OK  " if ok else "FALHOU") + " correção: erro conserta, palavra certa nunca é trocada")
    if not ok:
        falhas.append("correcao")
    # o destaque no cartão segue a mesma regra da busca (e exame não destaca médico)
    ok = (oa.casa_item("RADIOLOGIA", "raio x") and not oa.casa_item("MEDICO EM RADIOLOGIA E DIAGNOSTICO POR IMAGEM (2 no ambulatório, 2 cadastrados)", "raio x")
          and oa.casa_item("MEDICO DERMATOLOGISTA (1 no ambulatório, 1 cadastrado)", "dermatologista"))
    print(("OK  " if ok else "FALHOU") + " destaque: exame destaca serviço, nunca médico")
    if not ok:
        falhas.append("destaque")

    # CASO REAL (CNES de Rio Claro, 18/10/2026): a UBS registra radiologia/ultrassom/mamografia POR TERCEIRO (TP_CARACTERISTICA=2);
    # ela não faz esses exames no local e não pode aparecer na busca deles
    ok = all(FITT not in set(oa.filtrar(DF, None, busca=q)["nome"]) for q in ("raio x", "ultrassom", "mamografia", "imagem", "diagnostico por imagem"))
    print(("OK  " if ok else "FALHOU") + " UBS com serviço por terceiro não aparece como se fizesse o exame")
    if not ok:
        falhas.append("terceiro")
    ok = oa.servicos_de_terceiros(DF[DF["nome"] == FITT].iloc[0]["servicos"]) == ["RADIOLOGIA", "ULTRASONOGRAFIA", "MAMOGRAFIA", "SERVICO DE DIAGNOSTICO POR IMAGEM"]
    print(("OK  " if ok else "FALHOU") + " o que é por terceiro continua disponível para o cartão mostrar à parte")
    if not ok:
        falhas.append("terceiro_cartao")
    esp, svc = oa.opcoes_de_busca(DF)
    imagem = [q for _, t, q in svc if t == "SERVICO DE DIAGNOSTICO POR IMAGEM"]
    ok = imagem == [4]  # AME, CEAD, UPA, Santa Casa: a UBS não entra na contagem da lista
    print(("OK  " if ok else "FALHOU") + f" a lista 'o que existe' conta só quem faz ({imagem})")
    if not ok:
        falhas.append("lista_terceiro")

    # a ordem: o lugar cujo NOME bate com a busca vem primeiro
    primeiro = list(oa.filtrar(DF, None, busca="ame")["nome"])[:1]
    print(("OK  " if primeiro == [AME] else "FALHOU") + f" ordem: 'ame' põe o AME primeiro ({primeiro})")
    if primeiro != [AME]:
        falhas.append("ordem")

    # sem digitar nada, a escolha de grupo continua funcionando
    base = set(oa.filtrar(DF, "urgencia")["nome"])
    ok = base == {UPA}
    print(("OK  " if ok else "FALHOU") + " sem busca: o grupo escolhido continua valendo")
    if not ok:
        falhas.append("grupo")

    if falhas:
        print(f"\n{len(falhas)} FALHA(S): {falhas}")
        sys.exit(1)
    print("\nTodas as checagens da caixa de busca passaram.")


if __name__ == "__main__":
    main()
