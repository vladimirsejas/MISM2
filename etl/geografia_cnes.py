"""Gera um catálogo local de estabelecimentos CNES para a geografia do MISM2.

Lê os CSVs nacionais em blocos, filtra Rio Claro e grava um JSON derivado em
banco/geografia_cnes/. Não modifica escudo_feminino.db e não lê tabelas de
profissionais, cooperativas ou vínculos individuais.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

MUNICIPIO = "354390"
BLOCO = 100_000
CAIXA_RIO_CLARO = (-22.60, -22.20, -47.82, -47.41)
PREFIXOS_NATUREZA_PUBLICA = ("1", "3")


def detectar_encoding(caminho: Path) -> str:
    with caminho.open("rb") as arquivo:
        amostra = arquivo.read(1_000_000)
    try:
        amostra.decode("utf-8")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def normalizar(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() in {"nan", "none"} else texto


def normalizar_cep(valor: Any) -> str:
    digitos = re.sub(r"\D", "", normalizar(valor))
    return digitos if len(digitos) == 8 else ""


def achar_arquivo(pasta: Path, prefixo: str) -> Path | None:
    encontrados = sorted(pasta.glob(prefixo + "*.csv"))
    return encontrados[-1] if encontrados else None


def ler_tabela_pequena(caminho: Path | None, codigo: str, descricao: str) -> dict[str, str]:
    if caminho is None:
        return {}
    import pandas as pd

    df = pd.read_csv(caminho, sep=";", dtype=str, encoding=detectar_encoding(caminho),
                     on_bad_lines="skip")
    if codigo not in df.columns or descricao not in df.columns:
        return {}
    return {normalizar(c): normalizar(d) for c, d in zip(df[codigo], df[descricao]) if normalizar(c)}


def ler_indice_cep(caminho: Path) -> tuple[set[str], dict[str, Any]]:
    if not caminho.exists():
        return set(), {}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    ceps = dados.get("ceps", {})
    return set(ceps) if isinstance(ceps, dict) else set(), ceps if isinstance(ceps, dict) else {}


def coordenada(valor_lat: Any, valor_lon: Any) -> tuple[float | None, float | None]:
    try:
        lat = float(str(valor_lat).strip().replace(",", "."))
        lon = float(str(valor_lon).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None, None
    lat_min, lat_max, lon_min, lon_max = CAIXA_RIO_CLARO
    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        return None, None
    return lat, lon


def ler_estabelecimentos(caminho: Path, ceps_locais: set[str],
                         incluir_privados: bool = False) -> tuple[list[dict], dict]:
    import pandas as pd

    encoding = detectar_encoding(caminho)
    colunas = list(pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding, nrows=0).columns)
    obrigatorias = {"CO_UNIDADE", "NO_FANTASIA", "CO_CEP", "CO_MUNICIPIO_GESTOR"}
    faltantes = sorted(obrigatorias - set(colunas))
    if faltantes:
        raise ValueError(f"{caminho.name}: faltam colunas obrigatórias {faltantes}")
    if not incluir_privados and "CO_NATUREZA_JUR" not in colunas:
        raise ValueError("Não foi possível confirmar a natureza jurídica; não vou incluir estabelecimentos privados sem querer.")

    desejadas = [
        "CO_UNIDADE", "CO_CNES", "NO_FANTASIA", "NO_RAZAO_SOCIAL",
        "NO_LOGRADOURO", "NU_ENDERECO", "NO_COMPLEMENTO", "NO_BAIRRO", "CO_CEP",
        "NU_TELEFONE", "CO_NATUREZA_JUR", "CO_TIPO_UNIDADE", "TP_UNIDADE",
        "CO_TIPO_ESTABELECIMENTO", "CO_MUNICIPIO_GESTOR", "NU_LATITUDE",
        "NU_LONGITUDE", "CO_MOTIVO_DESAB", "CO_TURNO_ATENDIMENTO",
    ]
    usar = [c for c in desejadas if c in colunas]
    saida: dict[str, dict] = {}
    diagnostico = {"linhas_nacionais_lidas": 0, "linhas_no_recorte": 0,
                   "excluidos_natureza": 0, "excluidos_desativacao": 0,
                   "estabelecimentos_unicos": 0}
    for bloco in pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding,
                             usecols=usar, chunksize=BLOCO, on_bad_lines="skip"):
        diagnostico["linhas_nacionais_lidas"] += len(bloco)
        gestor = bloco["CO_MUNICIPIO_GESTOR"].fillna("").str.strip().str[:6].eq(MUNICIPIO)
        if ceps_locais:
            cep = bloco["CO_CEP"].map(normalizar_cep)
            mascara = gestor | cep.isin(ceps_locais)
        else:
            mascara = gestor
        local = bloco.loc[mascara].fillna("")
        diagnostico["linhas_no_recorte"] += len(local)
        if not incluir_privados and "CO_NATUREZA_JUR" in local:
            natureza = local["CO_NATUREZA_JUR"].astype(str).str.strip().str[:1]
            antes = len(local)
            local = local.loc[natureza.isin(PREFIXOS_NATUREZA_PUBLICA)]
            diagnostico["excluidos_natureza"] += antes - len(local)
        if "CO_MOTIVO_DESAB" in local:
            motivo = local["CO_MOTIVO_DESAB"].astype(str).str.strip()
            ativos = motivo.isin(["", "0", "00"])
            diagnostico["excluidos_desativacao"] += int((~ativos).sum())
            local = local.loc[ativos]

        for linha in local.to_dict("records"):
            unidade = normalizar(linha.get("CO_UNIDADE"))
            cnes = normalizar(linha.get("CO_CNES"))
            chave = unidade or cnes
            nome = normalizar(linha.get("NO_FANTASIA")) or normalizar(linha.get("NO_RAZAO_SOCIAL"))
            if not chave or not nome:
                continue
            lat, lon = coordenada(linha.get("NU_LATITUDE"), linha.get("NU_LONGITUDE"))
            cep = normalizar_cep(linha.get("CO_CEP"))
            partes_endereco = [normalizar(linha.get(c)) for c in
                               ("NO_LOGRADOURO", "NU_ENDERECO", "NO_COMPLEMENTO", "NO_BAIRRO")]
            endereco = ", ".join(p for p in partes_endereco if p) or None
            saida[chave] = {
                "id": f"cnes-{cnes or unidade}",
                "cnes": cnes or None,
                "co_unidade": unidade or None,
                "tipo": "saude",
                "subtipo": "unidade_saude",
                "nome": nome,
                "cep": cep or None,
                "endereco": endereco,
                "telefone": normalizar(linha.get("NU_TELEFONE")) or None,
                "horario": None,
                "lat": lat,
                "lon": lon,
                "geo": "coordenada_cnes" if lat is not None else "sem_coordenada_cnes",
                "abrangencia": "local",
                "fonte": "CNES/DATASUS — competência 202608",
                "fonte_url": "https://cnes.datasus.gov.br/",
                "verificado_em": date.today().isoformat(),
                "observacao": "Cadastro nacional. Confirme endereço, horário e atendimento diretamente com a unidade.",
                "natureza_juridica": normalizar(linha.get("CO_NATUREZA_JUR")) or None,
                "tipo_unidade_codigo": normalizar(linha.get("CO_TIPO_UNIDADE") or linha.get("TP_UNIDADE") or linha.get("CO_TIPO_ESTABELECIMENTO")) or None,
                "servicos_cnes": [],
                "horarios_cnes": [],
                "equipes_cnes": [],
            }
    diagnostico["estabelecimentos_unicos"] = len(saida)
    return list(saida.values()), diagnostico


def anexar_relacoes(caminho: Path | None, estabelecimentos: list[dict],
                    tipo: str, descricoes: dict[str, str] | None = None) -> int:
    """Anexa relações por CO_UNIDADE; para ESF aceita também CO_CNES_ESF."""
    if caminho is None:
        return 0
    import pandas as pd

    por_unidade = {normalizar(x.get("co_unidade")): x for x in estabelecimentos if x.get("co_unidade")}
    por_cnes = {normalizar(x.get("cnes")): x for x in estabelecimentos if x.get("cnes")}
    encoding = detectar_encoding(caminho)
    cabecalho = list(pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding, nrows=0).columns)
    if not any(c in cabecalho for c in ("CO_UNIDADE", "CO_CNES_ESF", "CO_CNES")):
        return 0
    contagem = 0
    for bloco in pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding,
                             chunksize=BLOCO, on_bad_lines="skip"):
        bloco = bloco.fillna("")
        for linha in bloco.to_dict("records"):
            unidade = normalizar(linha.get("CO_UNIDADE"))
            cnes_esf = normalizar(linha.get("CO_CNES_ESF"))
            cnes = normalizar(linha.get("CO_CNES"))
            destino = por_unidade.get(unidade) or por_cnes.get(cnes_esf) or por_cnes.get(cnes)
            if destino is None:
                continue
            if tipo == "servico":
                cod_servico = normalizar(linha.get("CO_SERVICO_ESPECIALIZADO"))
                cod_class = normalizar(linha.get("CO_CLASSIFICACAO_SERVICO"))
                partes = []
                if cod_servico:
                    partes.append((descricoes or {}).get(cod_servico, f"Serviço {cod_servico}"))
                if cod_class:
                    partes.append((descricoes or {}).get(cod_class, f"Classificação {cod_class}"))
                item = {"codigo_servico": cod_servico or None,
                        "codigo_classificacao": cod_class or None,
                        "descricao": " — ".join(dict.fromkeys(partes)) or "Serviço/classificação CNES"}
                destino["servicos_cnes"].append(item)
            elif tipo == "horario":
                campos = ("CO_DIA_SEMANA", "DS_DIA_SEMANA", "HR_INICIO", "HR_FIM",
                          "CO_TURNO_ATENDIMENTO", "DS_HORARIO", "HR_ATENDIMENTO")
                item = {k: normalizar(linha.get(k)) for k in campos if normalizar(linha.get(k))}
                if item:
                    destino["horarios_cnes"].append(item)
            elif tipo == "equipe":
                campos = ("CO_SEQ_EQUIPE", "SEQ_EQUIPE", "TP_EQUIPE", "CO_TIPO_EQUIPE",
                          "NO_REFERENCIA", "NO_EQUIPE", "DS_EQUIPE", "NO_FANTASIA_ESF",
                          "DS_SEGMENTO_ESF", "DS_AREA_ESF", "CO_AREA", "CO_AREA_ESF")
                item = {k: normalizar(linha.get(k)) for k in campos if normalizar(linha.get(k))}
                if item:
                    destino["equipes_cnes"].append(item)
            contagem += 1
    for estabelecimento in estabelecimentos:
        for campo in ("servicos_cnes", "horarios_cnes", "equipes_cnes"):
            unicos = {}
            for item in estabelecimento.get(campo, []):
                chave = json.dumps(item, ensure_ascii=False, sort_keys=True)
                unicos[chave] = item
            estabelecimento[campo] = list(unicos.values())
    return contagem


def montar_catalogo(pasta_cnes: Path, indice_cep: Path, saida: Path,
                    incluir_privados: bool = False) -> dict:
    ceps, indice = ler_indice_cep(indice_cep)
    arquivo_estab = achar_arquivo(pasta_cnes, "tbEstabelecimento")
    if arquivo_estab is None:
        raise FileNotFoundError(f"tbEstabelecimento*.csv não encontrado em {pasta_cnes}")
    estabelecimentos, diagnostico = ler_estabelecimentos(arquivo_estab, ceps, incluir_privados)

    tipos = ler_tabela_pequena(achar_arquivo(pasta_cnes, "tbServicoEspecializado"),
                               "CO_SERVICO_ESPECIALIZADO", "DS_SERVICO_ESPECIALIZADO")
    classificacoes = ler_tabela_pequena(achar_arquivo(pasta_cnes, "tbClassificacaoServico"),
                                        "CO_CLASSIFICACAO_SERVICO", "DS_CLASSIFICACAO_SERVICO")
    descricoes = {**tipos, **classificacoes}
    rel_serv = anexar_relacoes(achar_arquivo(pasta_cnes, "rlEstabServClass"),
                               estabelecimentos, "servico", descricoes)
    rel_hor = anexar_relacoes(achar_arquivo(pasta_cnes, "tbEstabHorarioAtend"),
                              estabelecimentos, "horario")
    rel_equipe = anexar_relacoes(achar_arquivo(pasta_cnes, "tbEquipe"),
                                 estabelecimentos, "equipe")
    rel_esf = anexar_relacoes(achar_arquivo(pasta_cnes, "rlEquipeNasfEsf"),
                              estabelecimentos, "equipe")
    for item in estabelecimentos:
        item["servicos_cnes"] = sorted(item["servicos_cnes"], key=lambda x: x.get("descricao", ""))
        item["equipes_cnes"] = sorted(item["equipes_cnes"], key=lambda x: json.dumps(x, sort_keys=True))
        item["horarios_cnes"] = sorted(item["horarios_cnes"], key=lambda x: json.dumps(x, sort_keys=True))
        if item["horarios_cnes"]:
            item["horario"] = "Horários cadastrados no CNES; confirme com a unidade."
    catalogo = {
        "meta": {
            "municipio_ibge": MUNICIPIO,
            "municipio": "Rio Claro",
            "competencia_cnes": "202608",
            "gerado_em": date.today().isoformat(),
            "origem": "CNES/DATASUS",
            "total_estabelecimentos": len(estabelecimentos),
            "total_com_coordenada_cnes": sum(x["lat"] is not None for x in estabelecimentos),
            "total_com_servicos_classificados": sum(bool(x["servicos_cnes"]) for x in estabelecimentos),
            "total_com_equipes": sum(bool(x["equipes_cnes"]) for x in estabelecimentos),
            "relacoes_lidas": {"servicos": rel_serv, "horarios": rel_hor,
                               "equipes": rel_equipe, "relacao_nasf_esf": rel_esf},
            "diagnostico": diagnostico,
            "privados_incluidos": incluir_privados,
            "aviso": "Dados derivados para consulta. Horários e serviços declarados no CNES devem ser confirmados com a unidade."
        },
        "servicos": estabelecimentos,
    }
    saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = saida.with_suffix(saida.suffix + ".tmp")
    temporario.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(saida)
    return catalogo


def main() -> int:
    raiz = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnes-dir", type=Path, default=raiz / "banco" / "cnes",
                        help="Pasta dos CSVs CNES nacionais já baixados.")
    parser.add_argument("--indice-cep", type=Path,
                        default=raiz / "dados_geograficos" / "indice_cep_rioclaro.json")
    parser.add_argument("--saida", type=Path,
                        default=raiz / "banco" / "geografia_cnes" / "cnes_servicos_rioclaro.json")
    parser.add_argument("--incluir-privados", action="store_true",
                        help="Inclui todas as naturezas jurídicas; por padrão ficam públicas e sem fins lucrativos.")
    args = parser.parse_args()
    try:
        catalogo = montar_catalogo(args.cnes_dir, args.indice_cep, args.saida, args.incluir_privados)
    except (OSError, ValueError, KeyError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    meta = catalogo["meta"]
    print("Catálogo CNES gerado:", args.saida)
    print("Estabelecimentos:", meta["total_estabelecimentos"])
    print("Com coordenadas CNES:", meta["total_com_coordenada_cnes"])
    print("Com serviços classificados:", meta["total_com_servicos_classificados"])
    print("Com equipes:", meta["total_com_equipes"])
    print("Diagnóstico:", json.dumps(meta["diagnostico"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
