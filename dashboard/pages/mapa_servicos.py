import json
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "algoritimos"))
sys.path.insert(0, str(RAIZ / "dashboard"))

from estilo import CSS  # noqa: E402
from geografia_servicos import carregar_bases, preparar_servicos, filtrar_servicos, combinar_catalogos  # noqa: E402

st.set_page_config(page_title="Escudo Feminino · Mapa de serviços", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

if st.button("🏠 Início", key="mapa_inicio"):
    try:
        st.switch_page("app.py")
    except Exception:  # Streamlit antigo
        st.markdown('<a href="/" target="_self">Voltar ao início</a>', unsafe_allow_html=True)
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
except (OSError, ValueError, json.JSONDecodeError) as erro:
    st.error(f"Não foi possível carregar os dados geográficos: {erro}")
    st.stop()

# Deixa explícito no painel se o CNES foi carregado e qual é a cobertura real.
meta_cnes = catalogo.get("meta", {}).get("cnes_local", {})
if arquivo_cnes.exists() and meta_cnes:
    st.subheader("Integração com o CNES")
    st.caption(
        f"Competência {meta_cnes.get('competencia_cnes', 'não informada')} · "
        f"Catálogo local gerado em {meta_cnes.get('gerado_em', 'data não informada')}. "
        "Os números abaixo refletem o arquivo CNES gerado neste computador."
    )
    cn1, cn2, cn3, cn4 = st.columns(4)
    cn1.metric("Estabelecimentos CNES", meta_cnes.get("total_estabelecimentos", 0))
    cn2.metric("Com coordenadas CNES", meta_cnes.get("total_com_coordenada_cnes", 0))
    cn3.metric("Com serviços classificados", meta_cnes.get("total_com_servicos_classificados", 0))
    cn4.metric("Com equipes cadastradas", meta_cnes.get("total_com_equipes", 0))

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


st.subheader("Lista de serviços")
st.caption(
    "Abra cada resultado no Google Maps para consultar o endereço e traçar a rota. "
    "Mesmo quando não há coordenada cadastrada, a busca usa o nome e o endereço disponíveis."
)

if resultado:
    for i, s in enumerate(resultado, start=1):
        nome = s.get("nome") or "Serviço sem nome"
        endereco = s.get("endereco") or ""
        cep = s.get("cep") or ""
        categoria = rotulos.get(s.get("tipo"), s.get("tipo") or "Não classificada")
        consulta_mapa = ", ".join(
            parte for parte in (nome, endereco, cep, "Rio Claro, SP") if parte
        )
        url_mapa = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(consulta_mapa)

        if s["precisao"] == "coordenada_da_fonte":
            situacao = "Coordenada cadastrada na fonte"
        elif s["precisao"] == "aproximada_por_cep":
            situacao = f"Localização aproximada pelo CEP (raio informado: {s['raio_m']} m)"
        else:
            situacao = "Sem coordenada confiável no catálogo"

        with st.expander(f"{i}. {nome} · {categoria}"):
            col_dados, col_mapa = st.columns([3, 1])
            with col_dados:
                st.write(f"**Endereço:** {endereco or 'Não informado'}")
                st.write(f"**CEP:** {cep or 'Não informado'}")
                st.write(f"**Telefone:** {s.get('telefone') or 'Não informado'}")
                st.write(f"**Horário:** {resumir_horarios(s)}")
                st.write(f"**Localização:** {situacao}")
                servicos_cnes = "; ".join(
                    dict.fromkeys(
                        x.get("descricao", "") for x in s.get("servicos_cnes", [])
                        if x.get("descricao")
                    )
                )
                if servicos_cnes:
                    st.write(f"**Serviços declarados no CNES:** {servicos_cnes}")
                equipes_cnes = "; ".join(
                    dict.fromkeys(
                        x.get("NO_FANTASIA_ESF") or x.get("NO_REFERENCIA") or x.get("NO_EQUIPE")
                        or x.get("DS_EQUIPE") or x.get("DS_AREA_ESF") or x.get("DS_SEGMENTO_ESF") or ""
                        for x in s.get("equipes_cnes", [])
                        if x.get("NO_FANTASIA_ESF") or x.get("NO_REFERENCIA") or x.get("NO_EQUIPE")
                        or x.get("DS_EQUIPE") or x.get("DS_AREA_ESF") or x.get("DS_SEGMENTO_ESF")
                    )
                )
                if equipes_cnes:
                    st.write(f"**Equipes CNES:** {equipes_cnes}")
                st.caption(
                    f"Fonte: {s.get('fonte_url') or 'catálogo local'} · "
                    f"Verificado em: {s.get('verificado_em') or 'data não informada'}"
                )
            with col_mapa:
                st.markdown(
                    f'<a href="{url_mapa}" target="_blank" rel="noopener noreferrer" '
                    'style="display:block;text-align:center;padding:0.65rem 0.5rem;'
                    'border-radius:0.5rem;background:#5b2a55;color:white;'
                    'font-weight:600;text-decoration:none;">Abrir no Google Maps ↗</a>',
                    unsafe_allow_html=True,
                )
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
