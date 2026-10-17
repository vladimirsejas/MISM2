@echo off
REM Roda de uma vez TUDO o que so o notebook consegue testar (Gemini real, banco real, painel real)
REM e salva o resultado em resultado_testes_notebook.txt (sem a chave). Basta dar dois cliques.
title Escudo Feminino - testar tudo no notebook
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set SAIDA=%~dp0resultado_testes_notebook.txt
echo Escudo Feminino - testes do notebook > "%SAIDA%"
echo Data: %date% %time% >> "%SAIDA%"
echo.
echo === 1/4 Gemini (chave e modelo) ===
echo === 1/4 Gemini (chave e modelo) === >> "%SAIDA%"
py algoritimos\testar_gemini.py >> "%SAIDA%" 2>&1
echo === 2/4 Regras do Gemini lado a lado (1 a 2 minutos) ===
echo. >> "%SAIDA%"
echo === 2/4 Regras do Gemini lado a lado === >> "%SAIDA%"
py algoritimos\comparar_regras.py >> "%SAIDA%" 2>&1
echo === 3/4 Banco real ===
echo. >> "%SAIDA%"
echo === 3/4 Banco real === >> "%SAIDA%"
py etl\validar_banco.py >> "%SAIDA%" 2>&1
echo === 4/4 Painel com o banco real (alguns minutos) ===
echo. >> "%SAIDA%"
echo === 4/4 Painel com o banco real === >> "%SAIDA%"
py dashboard\teste_painel_banco_real.py >> "%SAIDA%" 2>&1
echo. >> "%SAIDA%"
echo === FIM === >> "%SAIDA%"
echo.
echo Pronto. O resultado esta em resultado_testes_notebook.txt (abrindo agora).
notepad "%SAIDA%"
pause
