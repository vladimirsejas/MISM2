# ============================================================
# ESTILO DO ESCUDO (compartilhado)
#
# O CSS do painel (dashboard/app.py) mora aqui para as telas de apoio
# à mulher (dashboard/pages/apoio.py) terem o MESMO layout e a MESMA
# Lia: balão, rosto "respirando", cartões, abas. Foi movido de app.py
# sem mudar uma letra (o painel continua idêntico).
# ============================================================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f8f7fb; }
.block-container { max-width: 1180px; padding-top: 3.2rem; padding-bottom: 4rem; }
h1, h2, h3 { font-family: 'Manrope', sans-serif; color: #292541; letter-spacing: -0.02em; }
.escudo-marca { color: #7565a8; font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.escudo-titulo { font-family: 'Manrope', sans-serif; color: #292541; font-size: 2.1rem; font-weight: 700; line-height: 1.15; margin: 4px 0 6px; }
.escudo-sub { color: #625d72; font-size: 1.02rem; max-width: 760px; }
.escudo-pergunta { font-family: 'Manrope', sans-serif; color: #292541; font-size: 1.35rem; font-weight: 700; margin: 26px 0 2px; }
.escudo-dica { color: #8a8599; font-size: .88rem; margin-bottom: 4px; }
.escudo-escopo { display: inline-block; font-size: .82rem; font-weight: 700; border-radius: 999px; padding: 4px 13px; margin: 4px 0 8px; }
.escudo-escopo small { font-weight: 500; font-size: 1em; opacity: .9; }
.escudo-escopo.estado { background: #efe9fb; color: #5b3fa8; border: 1px solid #ddd2f5; }
.escudo-escopo.cidade { background: #e6f0fd; color: #1f5fb5; border: 1px solid #cfe1fa; }
.escudo-leitura { background: #fff; border: 1px solid #ebe8f2; border-radius: 16px; padding: 14px 20px; margin-top: 6px; color: #3d3852; }
.escudo-leitura li { margin: 5px 0; }
.escudo-alerta { background: #fff7ef; border: 1px solid #f6d9c2; border-radius: 16px; padding: 12px 18px; margin-top: 10px; color: #6b3d1e; font-size: .93rem; }
div[data-baseweb="select"] > div { border-radius: 12px; background: #fff; }
section[data-testid="stSidebar"] { min-width: 400px; }
.escudo-info { background: #f3f2f8; border: 1px solid #e6e3ef; border-radius: 16px; padding: 12px 18px; margin-top: 10px; color: #4d4863; font-size: .92rem; }
.escudo-cartao { background: #fff; border: 1px solid #ebe8f2; border-radius: 16px; padding: 16px 20px; margin: 10px 0; }
.escudo-cartao h4 { margin: 0 0 6px 0; font-family: 'Manrope', sans-serif; color: #292541; }
.escudo-cartao li { margin: 3px 0; color: #3d3852; }
.escudo-cartao .acao { color: #4d4863; font-size: .92rem; margin-top: 6px; }
.radar-cartao { border-left: 6px solid #b9b7c4; }
.radar-alerta { border-left-color: #eb6834; }
.radar-observar { border-left-color: #7565a8; }
.radar-selo { display: inline-block; font-size: .75rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
              border-radius: 999px; padding: 2px 10px; margin-left: 8px; vertical-align: middle; }
.radar-selo.alerta { background: #fde8dd; color: #a2400f; }
.radar-selo.observar { background: #ece7f7; color: #4d3f7a; }
.radar-selo.estavel { background: #efeef3; color: #625d72; }
.radar-faixa { display: flex; gap: 10px; flex-wrap: wrap; margin: 8px 0 4px; }
.radar-faixa div { flex: 1 1 200px; background: #fff; border: 1px solid #ebe8f2; border-radius: 16px; padding: 10px 14px; }
.radar-faixa b { font-family: 'Manrope', sans-serif; font-size: 1.5rem; }
.radar-faixa span { color: #706b82; font-size: .9rem; }
.lia-nome { font-family: 'Manrope', sans-serif; font-weight: 700; font-size: 1.25rem; color: #292541; }
.lia-nome span { font-weight: 500; font-size: .95rem; color: #706b82; }
.lia-cargo { color: #706b82; font-size: .85rem; line-height: 1.3; }
.lia-fala-grande { color: #3d3852; font-size: 1.08rem; margin: 2px 0 10px; }

/* ---- Lia: balão preso ao rosto, com um pouco de vida ----
   O balão é um st.container com key "lia_balao_*": o Streamlit põe a
   classe st-key-<key> nele. A key muda a cada fala, então o balão
   nasce de novo e a animação de entrada roda (e os pontinhos de
   "digitando" aparecem antes do texto). */
.lia-rosto { animation: lia-respira 5s ease-in-out infinite; transform-origin: 50% 90%; }
.lia-rosto img { border-radius: 50%; }
@keyframes lia-respira { 0%, 100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-3px) scale(1.015); } }
[class*="st-key-lia_balao"] {
    position: relative; background: #ffffff; border: 1px solid #e3dcf2; border-radius: 20px;
    padding: 16px 18px 12px; box-shadow: 0 6px 18px rgba(78, 60, 130, 0.08);
    animation: lia-balao-entra .35s ease-out both;
}
[class*="st-key-lia_balao"]::before {           /* a pontinha, apontando para o rosto */
    content: ""; position: absolute; width: 16px; height: 16px; background: #ffffff;
    border-left: 1px solid #e3dcf2; border-top: 1px solid #e3dcf2;
    top: -9px; left: 34px; transform: rotate(45deg);
}
[class*="st-key-lia_balao_centro"]::before { top: 34px; left: -9px; transform: rotate(-45deg); }
[class*="st-key-lia_balao"]::after {            /* "digitando..." antes do texto */
    content: "• • •"; position: absolute; top: 14px; left: 20px; color: #9b8fc4; letter-spacing: 2px;
    animation: lia-digitando .5s ease-out both;
}
[class*="st-key-lia_balao"] > div { animation: lia-texto-entra .3s ease-out .45s both; }
@keyframes lia-balao-entra { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: none; } }
@keyframes lia-digitando { 0% { opacity: 1; } 80% { opacity: 1; } 100% { opacity: 0; } }
@keyframes lia-texto-entra { from { opacity: 0; } to { opacity: 1; } }
[class*="st-key-lia_balao"] p { color: #3d3852; line-height: 1.55; }
[class*="st-key-lia_balao"] .stButton button {
    border-radius: 999px; background: #f4f0fb; border: 1px solid #e3dcf2; color: #4a3d78;
    font-weight: 600; min-height: 0; padding: 6px 14px;
}
[class*="st-key-lia_balao"] .stButton button:hover { background: #ebe4f8; border-color: #cdbfeb; color: #33285c; }
[class*="st-key-lia_balao"] [class*="st-key-lia_discreto"] button,
[class*="st-key-lia_balao"] [class*="st-key-bv_fechar"] button {
    background: transparent; border: none; color: #8a8599; font-weight: 500; padding: 2px 4px;
}
/* ---- Passeio pelo Escudo: outra interação, outra cara ----
   Retângulo verde-água com barra à esquerda (o balão da Lia é
   lilás/branco, arredondado, com pontinha). */
[class*="st-key-passeiocard_"] {
    background: #f0fdfa; border: 1px solid #99e0d6; border-left: 6px solid #0f9d8a; border-radius: 10px;
    padding: 12px 14px 10px; margin-top: 14px;
}
[class*="st-key-passeiocard_"] .passeio-topo { font-size: .74rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #0b7a6b; }
[class*="st-key-passeiocard_"] .passeio-pontos { color: #0f9d8a; letter-spacing: 3px; font-size: .9rem; }
[class*="st-key-passeiocard_"] .passeio-titulo { font-family: 'Manrope', sans-serif; font-weight: 700; color: #134e48;
    font-size: 1.05rem; margin: 2px 0 6px; }
[class*="st-key-passeiocard_"] p { color: #1f3d3a; }
[class*="st-key-passeiocard_"] .stButton button { border-radius: 8px; background: #ffffff; border: 1px solid #99e0d6;
    color: #0b7a6b; font-weight: 600; min-height: 0; padding: 5px 10px; }
[class*="st-key-passeiocard_"] .stButton button:hover { background: #ccf3ec; border-color: #0f9d8a; color: #0b5d52; }
[class*="st-key-passeiocard_"] [class*="st-key-pbtn_seguir"] button { background: #0f9d8a; border-color: #0f9d8a; color: #ffffff; }
[class*="st-key-passeiocard_"] [class*="st-key-pbtn_seguir"] button:hover { background: #0b7a6b; color: #ffffff; }
@media (prefers-reduced-motion: reduce) {
    .lia-rosto, [class*="st-key-lia_balao"], [class*="st-key-lia_balao"] > div { animation: none; }
    [class*="st-key-lia_balao"]::after { display: none; }
}
div[data-testid="stRadio"]:has(input[value="Panorama"]) > div { gap: 4px; border-bottom: 1px solid #e6e3ef; }
/* Botão vermelho "Apoio à mulher" (app.py): leva às lâminas de apoio */
[class*="st-key-botao_apoio"] a { display: flex; justify-content: center; align-items: center; width: 100%;
    background: #c62839; border: 1px solid #c62839; border-radius: 12px; padding: 8px 14px; text-decoration: none; }
[class*="st-key-botao_apoio"] a:hover { background: #a51f2e; border-color: #a51f2e; }
[class*="st-key-botao_apoio"] a, [class*="st-key-botao_apoio"] a p, [class*="st-key-botao_apoio"] a span {
    color: #ffffff !important; font-weight: 700; font-size: 1rem; }
[class*="st-key-botao_inicio"] button { background: #ffffff; border: 1px solid #2a78d6; color: #2a78d6;
    border-radius: 12px; font-weight: 700; }
[class*="st-key-botao_inicio"] button:hover { background: #2a78d6; color: #ffffff; }
[class*="st-key-botao_inicio"] button p { font-weight: 700; }
</style>
"""
