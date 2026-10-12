import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "algoritimos"))

from geografia_servicos import carregar_bases, preparar_servicos, filtrar_servicos, combinar_catalogos  # noqa: E402

st.set_page_config(page_title="Mapa de serviços · MISM2", layout="wide")
st.title("Serviços públicos de Rio Claro")
st.caption(
    "Localização de referência para encontrar serviços. Pontos aproximados por CEP "
    "são identificados separadamente; não representam o endereço exato."
)

try:
    catalogo, indice = carregar_bases()
    catalogo_cnes = []
    arquivo_cnes = RAIZ / "banco" / "geografia_cnes" / "cnes_servicos_rioclaro.json"
    if arquivo_cnes.exists():
        dados_cnes = json.loads(arquivo_cnes.read_text(encoding="utf-8"))
        catalogo_cnes = dados_cnes.get("servicos", [])
        catalogo["meta"]["cnes_local"] = dados_cnes.get("meta", {})
    servicos_unidos = combinar_catalogos(catalogo["servicos"], catalogo_cnes)
    servicos = preparar_servicos(servicos_unidos, indice["ceps"])
    if not arquivo_cnes.exists():
        st.info("O catálogo CNES local ainda não foi gerado. Para acrescentar estabelecimentos, serviços e equipes dos CSVs já baixados, execute: python etl/geografia_cnes.py")
except (OSError, ValueError, json.JSONDecodeError) as erro:
    st.error(f"Não foi possível carregar os dados geográficos: {erro}")
    st.stop()

tipos_disponiveis = sorted({str(s.get("tipo") or "outros") for s in servicos})
rotulos = {
    "mulher": "Apoio à mulher",
    "assistencia": "Assistência social",
    "creche": "Educação infantil",
    "saude": "Saúde",
    "emprego_curso": "Trabalho e cursos",
}
c1, c2 = st.columns([2, 1])
with c1:
    busca = st.text_input("Buscar serviço, endereço, bairro ou CEP", placeholder="Ex.: CRAS, Cervezão, UBS...")
with c2:
    tipos_selecionados = st.multiselect(
        "Categorias",
        options=tipos_disponiveis,
        default=tipos_disponiveis,
        format_func=lambda tipo: rotulos.get(tipo, tipo.replace("_", " ").title()),
    )

somente_exatos = st.checkbox("Mostrar somente pontos com coordenadas cadastradas na fonte")
resultado = filtrar_servicos(
    servicos,
    texto=busca,
    tipos=set(tipos_selecionados),
    somente_exatos=somente_exatos,
)

localizados = [s for s in resultado if s["localizavel"]]
exatos = [s for s in localizados if s["precisao"] == "coordenada_da_fonte"]
aproximados = [s for s in localizados if s["precisao"] == "aproximada_por_cep"]
sem_local = len(resultado) - len(localizados)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Serviços encontrados", len(resultado))
m2.metric("Com coordenada da fonte", len(exatos))
m3.metric("Aproximados por CEP", len(aproximados))
m4.metric("Sem posição confiável", sem_local)

if localizados:
    mapa = pd.DataFrame([
        {"lat": s["lat"], "lon": s["lon"], "serviço": s["nome"]}
        for s in localizados
    ])
    st.map(mapa, latitude="lat", longitude="lon", use_container_width=True)
    st.caption(
        "O mapa usa apenas coordenadas dentro da área de referência de Rio Claro. "
        "A distância visual entre pontos não comprova cobertura nem tempo de deslocamento."
    )
else:
    st.info("Nenhum serviço desta busca tem localização suficientemente confiável para aparecer no mapa.")

def resumir_horarios(servico):
    linhas_horario = []
    for item in servico.get("horarios_cnes", []):
        partes = []
        dia = item.get("DS_DIA_SEMANA") or item.get("CO_DIA_SEMANA")
        if dia:
            partes.append(dia)
        inicio, fim = item.get("HR_INICIO"), item.get("HR_FIM")
        if inicio or fim:
            partes.append(f"{inicio or '?'}–{fim or '?'}")
        turno = item.get("DS_TURNO_ATENDIMENTO") or item.get("CO_TURNO_ATENDIMENTO")
        if turno:
            partes.append(turno)
        if partes:
            linhas_horario.append(" ".join(partes))
    resumo = "; ".join(dict.fromkeys(linhas_horario))
    return resumo or servico.get("horario") or "Confirmar com o serviço"


linhas = []
for s in resultado:
    if s["precisao"] == "coordenada_da_fonte":
        situacao = "Coordenada cadastrada na fonte"
    elif s["precisao"] == "aproximada_por_cep":
        situacao = f"Centro aproximado do CEP (raio informado: {s['raio_m']} m)"
    else:
        situacao = "Sem posição confiável — disponível na lista"
    linhas.append({
        "Serviço": s.get("nome") or "Sem nome",
        "Categoria": rotulos.get(s.get("tipo"), s.get("tipo") or "Não classificada"),
        "Endereço": s.get("endereco") or "Não informado",
        "CEP": s.get("cep") or "Não informado",
        "Telefone": s.get("telefone") or "Não informado",
        "Horário": resumir_horarios(s),
        "Localização": situacao,
        "Verificado em": s.get("verificado_em") or "Data não informada",
        "Serviços declarados no CNES": "; ".join(
            dict.fromkeys(x.get("descricao", "") for x in s.get("servicos_cnes", []) if x.get("descricao"))
        ) or "Não detalhados",
        "Equipes CNES": "; ".join(
            dict.fromkeys(
                x.get("NO_FANTASIA_ESF") or x.get("NO_REFERENCIA") or x.get("NO_EQUIPE")
                or x.get("DS_EQUIPE") or x.get("DS_AREA_ESF") or x.get("DS_SEGMENTO_ESF") or ""
                for x in s.get("equipes_cnes", [])
                if x.get("NO_FANTASIA_ESF") or x.get("NO_REFERENCIA") or x.get("NO_EQUIPE")
                or x.get("DS_EQUIPE") or x.get("DS_AREA_ESF") or x.get("DS_SEGMENTO_ESF")
            )
        ) or "Não informado",
        "Fonte": s.get("fonte_url") or "",
    })

st.subheader("Lista de serviços")
if linhas:
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
else:
    st.info("Nenhum serviço corresponde aos filtros selecionados.")

meta_catalogo = catalogo.get("meta", {})
meta_cep = indice.get("meta", {})
st.caption(
    "Fontes dos dados: catálogo público de serviços e IBGE/CNEFE 2022 para o índice de CEP. "
    f"Índice CEP gerado em {meta_cep.get('gerado_em', 'data não informada')}. "
    "Confirme endereço, telefone e horário na fonte antes de se deslocar."
)
with st.expander("Sobre a precisão e as fontes"):
    st.write(
        "As coordenadas da fonte são priorizadas. Quando não há coordenada cadastrada, "
        "o sistema usa o centro aproximado do CEP apenas se o raio de incerteza for de até "
        "800 metros. Serviços sem localização confiável continuam na lista e não recebem "
        "um ponto inventado. O CEP pessoal da usuária não é solicitado nem enviado por esta página."
    )
    st.write(f"Registros no catálogo: {len(catalogo.get('servicos', []))}.")
    st.write(f"Fonte do índice: {meta_cep.get('fonte', 'não informada')}.")
