import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "algoritimos"))

from geografia_servicos import carregar_bases, preparar_servicos, filtrar_servicos  # noqa: E402

st.set_page_config(page_title="Mapa de serviços · MISM2", layout="wide")
st.title("Serviços públicos de Rio Claro")
st.caption(
    "Localização de referência para encontrar serviços. Pontos aproximados por CEP "
    "são identificados separadamente; não representam o endereço exato."
)

try:
    catalogo, indice = carregar_bases()
    servicos = preparar_servicos(catalogo["servicos"], indice["ceps"])
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
        "Horário": s.get("horario") or "Confirmar com o serviço",
        "Localização": situacao,
        "Verificado em": s.get("verificado_em") or "Data não informada",
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
