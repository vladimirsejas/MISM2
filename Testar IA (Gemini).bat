@echo off
REM Testa a chave e o modelo do Gemini (uma chamada de verdade). Basta dar dois cliques.
title Escudo Feminino - testar o Gemini
cd /d "%~dp0"
py algoritimos\testar_gemini.py
echo.
pause
