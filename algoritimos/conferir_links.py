import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

import apoio

# =====================================
# CONFERIDOR DOS LINKS DO APOIO À MULHER (só lê; não altera nada)
#
# O botão "Abrir a página oficial" de cada cartão precisa levar à página DO ASSUNTO. A nuvem não abre os sites do governo,
# então esta conferência roda no notebook do autor. Para cada link do catálogo ele diz:
#   OK              abriu e ficou no mesmo endereço (ignorando http/https, www e barra no fim);
#   REDIRECIONOU    abriu, mas terminou em OUTRA página (ex.: uma lista de cartilhas): confira se serve ao cartão;
#   AVISO           a página abre, mas o certificado do site não pôde ser verificado (site do governo mal configurado;
#                   o navegador pode mostrar alerta): confira no navegador antes de confiar;
#   ERRO            não abriu (404, bloqueio, sem rede...). Bloqueio 403 de site do governo pode ser só robô: abra no navegador.
#
# Uso:  py algoritimos\conferir_links.py              (todos os cartões)
#       py algoritimos\conferir_links.py tfd cancer_intestino   (só estes ids)
# =====================================

CABECALHO = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Escudo-Feminino-conferidor/1.0",
             "Accept-Language": "pt-BR,pt;q=0.9"}
TEMPO = 60
PAUSA = 0.4


def _tentar(url, contexto=None):
    pedido = urllib.request.Request(url, headers=CABECALHO)
    with urllib.request.urlopen(pedido, timeout=TEMPO, context=contexto) as r:
        return r.status, r.geturl()


def _e_certificado(e):
    motivo = getattr(e, "reason", e)
    return isinstance(motivo, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(e)


def abrir(url):
    """(status, endereço final, erro). Segue redirecionamentos; nunca levanta exceção.
    Tempo esgotado: tenta mais uma vez. Certificado não verificável: abre sem verificar e marca o erro como
    "CERTIFICADO..." (classificado como AVISO se a página abrir)."""
    for tentativa in range(2):
        try:
            status, final = _tentar(url)
            return status, final, None
        except urllib.error.HTTPError as e:
            return e.code, url, f"HTTP {e.code}"
        except Exception as e:
            if _e_certificado(e):
                try:
                    status, final = _tentar(url, ssl._create_unverified_context())
                    return status, final, "CERTIFICADO não verificável (a página abre)"
                except urllib.error.HTTPError as e2:
                    return e2.code, url, f"HTTP {e2.code}"
                except Exception as e2:
                    return None, url, f"{type(e2).__name__}: {e2}"
            esgotou = isinstance(e, (socket.timeout, TimeoutError)) or isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError))
            if esgotou and tentativa == 0:
                continue
            return None, url, f"{type(e).__name__}: {e}"


def _normal(url):
    p = urlparse(url)
    host = p.netloc.lower().removeprefix("www.")
    return host, p.path.rstrip("/").lower()


def classificar(url, status, final, erro):
    if erro and erro.startswith("CERTIFICADO") and status is not None and status < 400:
        return "AVISO"
    if erro or status is None or status >= 400:
        return "ERRO"
    return "OK" if _normal(url) == _normal(final) else "REDIRECIONOU"


def conferir(ids=None, abrir_url=abrir, pausa=PAUSA, itens=None):
    """[(id, classe, url, final, erro)] para cada cartão (um link repetido é consultado uma vez só)."""
    itens = itens if itens is not None else apoio.ITENS
    vistos, saida = {}, []
    for item in itens:
        if ids and item["id"] not in ids:
            continue
        url = item["link"]
        if url not in vistos:
            status, final, erro = abrir_url(url)
            vistos[url] = (classificar(url, status, final, erro), final, erro)
            if pausa:
                time.sleep(pausa)
        classe, final, erro = vistos[url]
        saida.append((item["id"], classe, url, final, erro))
    return saida


def main(argv=None):
    ids = set(argv if argv is not None else sys.argv[1:])
    print(f"Conferindo os links do Apoio ({'todos' if not ids else ', '.join(sorted(ids))})... pode levar alguns minutos.\n")
    resultado = conferir(ids or None)
    contagem = {"OK": 0, "REDIRECIONOU": 0, "AVISO": 0, "ERRO": 0}
    for id, classe, url, final, erro in resultado:
        contagem[classe] += 1
        if classe == "OK":
            continue
        print(f"[{classe}] {id}")
        print(f"   cadastrado: {url}")
        print(f"   {'terminou em' if classe == 'REDIRECIONOU' else 'problema'}: {final if classe == 'REDIRECIONOU' else erro}")
    print(f"\nResumo: {contagem['OK']} OK, {contagem['REDIRECIONOU']} redirecionaram, {contagem['AVISO']} com aviso de certificado, {contagem['ERRO']} com erro, de {len(resultado)} cartões.")
    print("Cole a lista [REDIRECIONOU], [AVISO] e [ERRO] no chat para eu corrigir os links.")
    return 0 if not (contagem["REDIRECIONOU"] or contagem["ERRO"] or contagem["AVISO"]) else 2


if __name__ == "__main__":
    sys.exit(main())
