import html
import os
import re
import sqlite3
import sys

import pandas as pd
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "algoritimos"))
sys.path.insert(0, os.path.join(AQUI, ".."))

import onde_atendida as oa  # noqa: E402
import unidades_saude as us  # noqa: E402
from configuracao_geografica import BANCO, UF_REFERENCIA  # noqa: E402
from estilo import CSS  # noqa: E402
from navegacao import barra_de_navegacao  # noqa: E402

# ============================================================
# ONDE SER ATENDIDA -- uma página só, 10/2026
#
# "Onde, na minha cidade, uma mulher procura atendimento?" Junta o CNES
# (cadastro oficial e completo das unidades de saúde) com o catálogo
# conferido de Rio Claro (telefone, horário, data de verificação e o
# apoio à mulher), em palavras de quem procura e com o Google Maps em
# cada lugar: "Como chegar" abre a rota a partir de onde a pessoa está,
# "Ligar" disca. Substitui as páginas "Onde ser atendida" (CNES) e
# "Mapa de serviços" (catálogo), que respondiam à mesma pergunta.
#
# Sem o arquivo do CNES a página continua útil (só catálogo conferido).
# Só descreve: cadastro não é vaga nem serviço aberto, e a página diz
# isso. Não ranqueia lugares. A lógica está em algoritimos/onde_atendida.py.
# ============================================================

st.set_page_config(page_title="MISM2 · Onde ser atendida", page_icon="E", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.un-grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 14px; margin: 10px 0; }
.un-cartao { background: #fff; border: 1px solid #e6dceb; border-left: 6px solid #cdbfeb; border-radius: 4px 18px 4px 18px;
             padding: 14px 18px 16px; }
.un-cartao.publica { border-left-color: #5b2a55; }
.un-cartao.sem_fins { border-left-color: #8d6bb0; }
.un-cartao.privada { border-left-color: #c9c4d6; }
.un-nome { font-family: Georgia, 'Times New Roman', serif; color: #2a1730; font-size: 1.18rem; line-height: 1.2; margin-top: 2px; }
.un-tipo { color: #7a6a80; font-size: .86rem; margin: 2px 0 8px; }
.un-linha { color: #3d3852; font-size: .93rem; margin: 3px 0; }
.un-aviso { color: #8a5a1e; font-size: .84rem; margin: 6px 0 0; }
.un-selo { display: inline-block; font-size: .68rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
           border-radius: 999px; padding: 2px 9px; margin: 0 6px 4px 0; }
.un-selo.publica { background: #efe5f3; color: #5b2a55; }
.un-selo.sem_fins { background: #ece7f7; color: #4d3f7a; }
.un-selo.privada, .un-selo.desconhecida { background: #efeef3; color: #625d72; }
.un-selo.cancer { background: #f6e8f3; color: #8a2f73; }
.un-selo.conferido { background: #e4ecdd; color: #3f5f2f; }
.un-botoes { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
a.un-chegar, a.un-ligar { display: inline-block; text-align: center; border-radius: 999px; padding: 9px 18px;
                          font-weight: 700; font-size: .92rem; text-decoration: none !important; }
a.un-chegar { background: #5b2a55; color: #ffffff !important; flex: 1 1 160px; }
a.un-chegar:hover { background: #3c1a38; }
a.un-ligar { border: 1.5px solid #5b2a55; color: #5b2a55 !important; background: #ffffff; }
a.un-ligar:hover { background: #f3ecf6; }
a.un-fonte { color: #8a7a90 !important; font-size: .78rem; text-decoration: none; }
[class*="st-key-un_pilulas"] label[data-testid="stRadioOption"],
[class*="st-key-un_pilulas"] label[data-baseweb="radio"] {
    border: 1px solid #cdbfeb; border-radius: 999px; padding: 6px 12px 6px 8px; background: #ffffff;
    margin: 0 6px 6px 0; cursor: pointer; }
[class*="st-key-un_pilulas"] label[data-selected="true"],
[class*="st-key-un_pilulas"] label[data-baseweb="radio"]:has(input:checked) { background: #ece7f7; border-color: #5b2a55; }
</style>
""", unsafe_allow_html=True)

PAGINA = 12
LIMITE_VISIVEL = 6  # itens de serviço/especialidade à vista no cartão; o resto fica em "Ver os outros"
NOME_CIDADE = "Rio Claro"


def versoes_cnes(arquivo):
    """Invalida o cache quando muda qualquer CSV usado na busca por serviços."""
    if not arquivo:
        return ()
    nome = os.path.basename(arquivo)
    mes = re.search(r"(\d{6})\.csv$", nome, re.IGNORECASE)
    relacionados = [arquivo]
    if mes:
        pasta = os.path.dirname(arquivo)
        relacionados.extend(os.path.join(pasta, f"{prefixo}{mes.group(1)}.csv")
                            for prefixo in ("rlEstabServClass", "tbClassificacaoServico", "tbServicoEspecializado",
                                            "tbCargaHorariaSus", "tbAtividadeProfissional"))
    return tuple((p, os.path.getmtime(p) if os.path.exists(p) else None) for p in relacionados)


@st.cache_data(show_spinner="Lendo o cadastro do CNES…")
def lista(arquivo, modificado):
    # `arquivo` e `modificado` só entram na chave do cache: ao trocar o CSV, a lista é lida de novo.
    cnes = us.carregar_unidades(nome_cidade=NOME_CIDADE)
    df = oa.unificar(cnes, oa.carregar_catalogo(), NOME_CIDADE)
    df.attrs["aviso_cnes"] = cnes.attrs.get("aviso", "")
    return df


@st.cache_data
def internacoes_por_cnes(modificado):
    """CNES (7 dígitos) -> internações por câncer feminino registradas no hospital (2013 até o último mês carregado, 7 cânceres), ou {}
    se o banco não existe ou é antigo (sem CNES). Não é qualidade nem preferência: é só o que o SIH registrou."""
    try:
        import inteligencia as ti
        if not os.path.exists(BANCO):
            return {}
        conn = sqlite3.connect(BANCO)
        try:
            dados = ti.carregar_hospitais(conn, UF_REFERENCIA)
        finally:
            conn.close()
        if not dados:
            return {}
        tabela = ti.lista_hospitais(dados)
        return dict(zip(tabela["cnes"], tabela["internacoes"]))
    except Exception:
        return {}


def inicio():
    st.markdown('<div style="background:#efe9f5;border-left:4px solid #5b2a55;border-radius:6px;padding:6px 12px;'
                'margin:4px 0 10px;font-size:.95rem;color:#2a1730">📍 Você está em: <b>Onde ser atendida</b></div>',
                unsafe_allow_html=True)
    barra_de_navegacao("onde", chave_inicio="un_inicio")


def pergunta(texto, detalhe):
    st.markdown(f'<div class="escudo-pergunta">{html.escape(texto)}</div>'
                f'<span class="escudo-escopo cidade">📍 {html.escape(NOME_CIDADE)} <small>· {html.escape(detalhe)}</small></span>',
                unsafe_allow_html=True)


def cartao(u, n_internacoes, busca=""):
    selos = f'<span class="un-selo {u.natureza}">{html.escape(us.NATUREZA_CURTA.get(u.natureza, "Não informada"))}</span>'
    if u.conferido_em:
        selos += f'<span class="un-selo conferido" title="Telefone e horário conferidos na fonte oficial">conferido em {html.escape(u.conferido_em)}</span>'
    if n_internacoes:
        quantas = f"{int(n_internacoes):,}".replace(",", ".")
        selos += (f'<span class="un-selo cancer" title="Internações dos 7 cânceres femininos acompanhados, 2013 até o último mês carregado, '
                  f'registradas no SIH/SUS (não mede qualidade)">{quantas} internações por câncer</span>')
    linhas = []
    if u.endereco:
        linhas.append(f"📍 {html.escape(u.endereco)}" + (f" · CEP {html.escape(u.cep).replace('-', '&#8209;')}" if u.cep else ""))
    if u.telefone:
        linhas.append(f"📞 {html.escape(u.telefone)}")
    if u.horario:
        linhas.append(f"🕒 {html.escape(u.horario)}")
    corpo = "".join(f'<div class="un-linha">{l}</div>' for l in linhas)
    especialistas, servicos_exames = oa.separar_registros(getattr(u, "servicos", ""))
    if especialistas or servicos_exames:
        correspondentes = {t for t in especialistas + servicos_exames if busca.strip() and oa.casa_item(t, busca)}

        def _item(t):
            texto = html.escape(oa.rotulo_legivel(t))
            return f"<b>{texto}</b>" if t in correspondentes else texto
        # o CNES pode registrar dezenas de itens por unidade: o que casou com a busca vem primeiro e à vista,
        # o resto está inteiro logo abaixo, recolhido ("Ver os outros N"); nada é cortado.
        for titulo, lista_t in (("Profissionais cadastrados no CNES", especialistas), ("Serviços e exames registrados no CNES", servicos_exames)):
            if not lista_t:
                continue
            ordenada = [t for t in lista_t if t in correspondentes] + [t for t in lista_t if t not in correspondentes]
            ate = max(len(correspondentes & set(lista_t)), LIMITE_VISIVEL)
            visiveis, resto = ordenada[:ate], ordenada[ate:]
            junta = "<br>" if lista_t is especialistas else ", "  # médicos: um por linha; serviços: lista corrida
            texto = ("<br>" if junta == "<br>" else "") + junta.join(_item(t) for t in visiveis)
            if resto:
                texto += (f'<details><summary>Ver os outros {len(resto)}</summary>'
                          f'{junta.join(_item(t) for t in resto)}</details>')
            corpo += f'<div class="un-linha"><b>{titulo} ({len(lista_t)})</b>: {texto}</div>'
        corpo += '<div class="un-aviso">Cadastro não confirma vaga, atendimento pelo SUS ou disponibilidade hoje.</div>'
    terceiros = oa.servicos_de_terceiros(getattr(u, "servicos", ""))
    if terceiros:
        corpo += ('<div class="un-linha"><details><summary>Serviços feitos por outro estabelecimento ('
                  f'{len(terceiros)})</summary>{", ".join(html.escape(oa.rotulo_legivel(t)) for t in terceiros)}<br>'
                  '<i>Segundo o CNES, a unidade oferece esses serviços por meio de terceiros: não são feitos no próprio local. '
                  'Pergunte na unidade onde fazer.</i></details></div>')
    if not (especialistas or servicos_exames) and terceiros:
        corpo += '<div class="un-aviso">Cadastro não confirma vaga, atendimento pelo SUS ou disponibilidade hoje.</div>'
    if u.aviso:
        corpo += f'<div class="un-aviso">⚠ {html.escape(u.aviso)}</div>'
    botoes = (f'<a class="un-chegar" title="Abre a rota no Google Maps" href="{html.escape(u.link_chegar)}" target="_blank" rel="noopener noreferrer">'
              f'📍 Como chegar</a>')
    if u.link_ligar:
        botoes += f'<a class="un-ligar" href="{html.escape(u.link_ligar)}">📞 Ligar</a>'
    fonte = (f'<div style="margin-top:6px"><a class="un-fonte" href="{html.escape(u.fonte_url)}" target="_blank" '
             f'rel="noopener noreferrer">fonte ↗</a></div>') if u.fonte_url else ""
    return (f'<div class="un-cartao {u.natureza}">{selos}<div class="un-nome">{html.escape(u.nome)}</div>'
            f'<div class="un-tipo">{html.escape(u.tipo)}</div>{corpo}<div class="un-botoes">{botoes}</div>{fonte}</div>')


# ---------------- topo ----------------
inicio()
st.markdown('<div class="escudo-marca">MISM2</div>'
            f'<div class="escudo-titulo">Onde ser atendida em <em>{html.escape(NOME_CIDADE)}</em></div>'
            '<div class="escudo-sub">Escolha do que você precisa. Em cada lugar, o botão <b>Como chegar</b> abre a rota no '
            'Google Maps a partir de onde você está, e o <b>Ligar</b> disca.</div>',
            unsafe_allow_html=True)
st.markdown('<div class="escudo-alerta"><b>Risco imediato:</b> ligue <b>190</b> (Polícia Militar). Emergência médica: '
            '<b>192</b> (SAMU). Violência contra a mulher: <b>Ligue 180</b>. Em perigo, não espere resposta de um painel.</div>',
            unsafe_allow_html=True)

arquivo = us.achar_arquivo()
df = lista(arquivo or "", versoes_cnes(arquivo))
tem_cnes = bool(df.attrs.get("tem_cnes"))
if tem_cnes and df.attrs.get("aviso_servicos"):
    st.caption("Busca por exames/especialidades indisponível: " + str(df.attrs["aviso_servicos"]))
if tem_cnes and df.attrs.get("aviso_medicos"):
    st.caption("Busca por médico especialista indisponível: " + str(df.attrs["aviso_medicos"]))

if df.empty:
    st.warning("Não encontrei lugares para mostrar. O catálogo conferido (dados_geograficos) e o arquivo do CNES (banco\\cnes) "
               "estão ausentes ou ilegíveis.")
    st.stop()

internacoes = internacoes_por_cnes(os.path.getmtime(BANCO) if os.path.exists(BANCO) else 0)

# ---------------- 1. do que você precisa ----------------
st.markdown('<div class="escudo-pergunta">Do que você precisa?</div>', unsafe_allow_html=True)
contagem = oa.contar(df)
opcoes = [g for g in oa.ESCOLHAS if contagem[g] > 0]
try:
    caixa = st.container(key="un_pilulas_grupo")
except TypeError:  # Streamlit antigo, sem key em container
    caixa = st.container()
with caixa:
    escolha = st.radio("O que você procura", opcoes, horizontal=True, label_visibility="collapsed",
                       format_func=lambda g: f"{oa.ESCOLHAS[g][0]} ({contagem[g]})", key="un_grupo")
st.caption(oa.ESCOLHAS[escolha][1])

especialidades_op, servicos_op = oa.opcoes_de_busca(df)
_rotulos = {"": "— escolher o que existe na cidade —"}
for _nome, _termo, _q in especialidades_op:
    _rotulos[_termo] = f"{_nome} ({_q} unidade{'s' if _q != 1 else ''})"
for _nome, _termo, _q in servicos_op[:150]:
    _rotulos[_termo] = f"Exame/serviço: {_nome} ({_q} unidade{'s' if _q != 1 else ''})"


def _usar_escolha():
    if st.session_state.get("un_escolha"):
        st.session_state["un_busca"] = st.session_state["un_escolha"]
    # a lista volta para "— escolher —": sem isso, escolher DE NOVO o mesmo item não dispara nada e a lista
    # fica mostrando um item enquanto a caixa de busca mostra outro texto (visto no notebook, 18/10/2026)
    st.session_state["un_escolha"] = ""


if len(_rotulos) > 1:
    st.selectbox("Não sabe o nome? Escolha do que existe nos cadastros da cidade (digite para filtrar)", list(_rotulos),
                 format_func=lambda t: _rotulos[t], key="un_escolha", on_change=_usar_escolha)

c1, c2 = st.columns([2.2, 1.6])
busca = c1.text_input("Busque um exame, especialista, serviço ou unidade (em todas as opções)", key="un_busca",
                      placeholder="ex.: mamografia, preventivo, ultrassom, dermatologista, AME")
c1.caption("A busca entende erros de digitação e palavras do dia a dia (raio x, ultrassom, coração, grávida). Ela usa os serviços e os profissionais registrados no CNES e localiza unidades; não informa nomes de pessoas nem agenda de consultas.")
procurando = bool(busca.strip())
busca_efetiva = oa.corrigir_busca(df, busca) if procurando else busca
if procurando and busca_efetiva.strip().lower() != busca.strip().lower():
    c1.caption(f"Mostrando resultados para “{busca_efetiva}” (corrigi a digitação com o que existe no cadastro).")
so_publicos = False
if tem_cnes and df.attrs.get("tem_natureza", False):
    so_publicos = c2.checkbox("Só públicas e sem fins lucrativos", value=True, key="un_publicos",
                              help="Onde é mais provável haver atendimento pelo SUS. Desmarque para ver também clínicas privadas.")
    c2.caption("Marcado: só a rede pública e as entidades sem fins lucrativos. Desmarque para ver também as particulares "
               "(na busca, elas aparecem em grupo separado).")

# o filtro vale SEMPRE, com ou sem busca; e a página diz quantas unidades ele está escondendo (sem isso, o botão parecia morto)
mostrar = oa.filtrar(df, escolha, busca_efetiva, so_publicos)
ocultas = (len(oa.filtrar(df, escolha, busca_efetiva, False)) - len(mostrar)) if so_publicos else 0


def aviso_ocultas():
    if ocultas > 0:
        st.info(f"{ocultas} unidade{'s' if ocultas != 1 else ''} particular{'es' if ocultas != 1 else ''} também "
                f"{'aparecem' if ocultas != 1 else 'aparece'} aqui e {'estão ocultas' if ocultas != 1 else 'está oculta'} pelo filtro "
                "“Só públicas e sem fins lucrativos”. Desmarque a caixa para ver.")


assinatura = (escolha, busca.strip().lower(), so_publicos)
if st.session_state.get("un_assinatura") != assinatura:
    st.session_state["un_assinatura"] = assinatura
    st.session_state["un_limite"] = PAGINA
limite = st.session_state.setdefault("un_limite", PAGINA)

if mostrar.empty:
    st.info("Não encontrei uma unidade com esse cadastro. Veja as sugestões abaixo ou use a lista “Não sabe o nome?”, que traz o que de fato "
            "existe nos cadastros da cidade. Confirme a disponibilidade antes de ir.")
    aviso_ocultas()
    if procurando:
        def _aplicar(termo):
            st.session_state["un_busca"] = termo
        for i, (rotulo, termo) in enumerate(oa.sugestoes(df, busca_efetiva)):
            st.button(f"Procurar: {rotulo}", key=f"un_sug_{i}", on_click=_aplicar, args=(termo,))
else:
    titulo = f"{len(mostrar)} lugar(es)" + (" encontrados na busca" if busca.strip() else f": {oa.ESCOLHAS[escolha][0].lower()}")
    pergunta(titulo, "sem ranking de qualidade")
    aviso_ocultas()
    if procurando and tem_cnes:
        publicas, particulares = oa.separar_por_natureza(mostrar)
        grupos = (("Rede pública e sem fins lucrativos", publicas),
                  ("Particulares — o CNES não informa se atendem pelo SUS", particulares))
    else:
        grupos = (("", mostrar),)
    partes, usados = [], 0
    for rotulo, sub in grupos:
        cartoes_grupo = []
        for u in sub.itertuples():
            if usados >= limite:
                break
            cartoes_grupo.append(cartao(u, internacoes.get(u.cnes), busca_efetiva))
            usados += 1
        if cartoes_grupo:
            cab = (f'<div style="grid-column:1/-1;font-weight:700;margin:10px 0 2px">{html.escape(rotulo)} ({len(sub)})</div>'
                   if rotulo else "")
            partes.append(cab + "".join(cartoes_grupo))
    cartoes = "".join(partes)
    st.markdown(f'<div class="un-grade">{cartoes}</div>', unsafe_allow_html=True)
    if len(mostrar) > limite:
        if st.button(f"Mostrar mais ({len(mostrar) - limite} restantes)", key="un_mais"):
            st.session_state["un_limite"] = limite + PAGINA
            st.rerun()

    pontos = mostrar[mostrar["mapa"]].dropna(subset=["lat", "lon"])
    if not pontos.empty:
        st.map(pontos.assign(lat=pontos["lat"].astype(float), lon=pontos["lon"].astype(float))
               .rename(columns={"lat": "latitude", "lon": "longitude"})[["latitude", "longitude"]], size=18, zoom=12, height=300)
        sem_ponto = len(mostrar) - len(pontos)
        st.caption(f"{len(pontos)} no mapa" + (f"; para os outros {sem_ponto}, use o botão “Como chegar”." if sem_ponto else "."))

    st.markdown('<div class="escudo-leitura"><b>Antes de ir</b><ul>'
                '<li>Cadastro de unidade ou serviço <b>não garante</b> vaga, atendimento pelo SUS nem que esteja aberto agora: ligue ou confirme na fonte.</li>'
                '<li>A lista descreve onde procurar; não diz qual lugar é melhor.</li>'
                + ('<li>Para pedir mamografia e Papanicolau, comece pelo <b>Posto de saúde</b>.</li>' if escolha == "basica" else '')
                + '</ul></div>', unsafe_allow_html=True)

if internacoes:
    st.caption("O selo roxo “internações por câncer” liga o cadastro ao restante do Escudo: é quantas internações dos 7 cânceres "
               "femininos o SIH/SUS registrou naquele hospital de 2013 até o último mês carregado, de pacientes de qualquer cidade. Descreve o que "
               "aconteceu; não diz qual hospital é melhor.")

with st.expander("De onde vêm estes dados e quais são os limites"):
    fonte_cnes = (f"CNES (Cadastro Nacional de Estabelecimentos de Saúde), arquivo `{html.escape(df.attrs.get('arquivo', ''))}`: "
                  f"só cadastros **ativos** do município; {df.attrs.get('desabilitados', 0)} desabilitado(s) ficaram de fora."
                  if tem_cnes else
                  "O arquivo do CNES (`tbEstabelecimento*.csv` em `banco\\cnes`) **não foi encontrado**: a página mostra só o "
                  "catálogo conferido, que é menor que o cadastro completo.")
    st.markdown(f"""
- **Catálogo conferido:** serviços de Rio Claro com fonte oficial e data de verificação em cada cartão, incluindo o apoio à mulher.
  Itens com ⚠ ainda precisam de confirmação.
- **Cadastro oficial:** {fonte_cnes}
- **Público x privado:** pela natureza jurídica do CNES. Estar no CNES **não** prova que a unidade atende pelo SUS.
- **Mapa:** só pontos com coordenada cadastrada na fonte e dentro da cidade; os demais aparecem na lista com o botão “Como chegar”,
  que faz a busca pelo nome e endereço no Google Maps (confira o ponto lá).
- **Vaga, fila e horário de hoje** não são inferidos: confirme com o lugar antes de ir.
- **Direitos, hospitais de referência e outros caminhos:** veja o [Apoio à mulher](/apoio).
""")
    exportar = mostrar.drop(columns=["mapa", "link_chegar", "link_ligar"]).assign(grupo=lambda d: d["grupo"].astype(str)) \
        if not mostrar.empty else pd.DataFrame()
    if not exportar.empty:
        st.download_button("Baixar esta lista (CSV)", exportar.to_csv(index=False, sep=";").encode("utf-8-sig"),
                           file_name="onde_ser_atendida_rio_claro.csv", mime="text/csv")
