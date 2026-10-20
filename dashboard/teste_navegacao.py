"""Teste da barra de navegação: toda página mostra os mesmos destinos e marca onde a pessoa está."""
import os
import sys

from streamlit.testing.v1 import AppTest

AQUI = os.path.dirname(os.path.abspath(__file__))
falhas = []


def checar(nome, ok):
    print(("OK   " if ok else "FALHOU ") + nome)
    if not ok:
        falhas.append(nome)


PAGINAS = {  # arquivo: (marcada como "você está aqui", destinos que precisam ter link)
    "pages/apoio.py": ("Apoio à mulher", ["Onde ser atendida", "Hospitais de câncer"]),
    "pages/onde_ser_atendida.py": ("Onde ser atendida", ["Apoio à mulher", "Hospitais de câncer"]),
    "pages/hospitais_cancer.py": ("Hospitais de câncer", ["Apoio à mulher", "Onde ser atendida"]),
}
for arquivo, (aqui, outros) in PAGINAS.items():
    at = AppTest.from_file(os.path.join(AQUI, arquivo), default_timeout=90)
    at.run()
    texto = " ".join(m.value for m in at.markdown)
    botoes = [b.label for b in at.button]
    checar(f"{arquivo}: abre sem erro", not at.exception)
    checar(f"{arquivo}: marca '{aqui}' como 'você está aqui'", f"{aqui}<small>você está aqui</small>" in texto)
    checar(f"{arquivo}: leva às outras duas ({', '.join(outros)})", all(o in texto for o in outros))
    if arquivo != "pages/apoio.py":
        checar(f"{arquivo}: tem o botão Início", "🏠 Início" in botoes)
if falhas:
    print(f"\n{len(falhas)} falha(s).")
    sys.exit(1)
print("\nTodas as checagens da navegação passaram.")
