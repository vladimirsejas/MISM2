# Protocolo de avaliação aninhada das previsões

## Objetivo

Comparar, em avaliação temporal de um ano à frente, o modelo selecionado por
`inteligencia.prever_com_validacao` com a referência ingênua (repetição do
último valor observado), sem permitir que o ano-alvo participe da seleção.

## Protocolo

- Janela principal: oito observações anuais anteriores ao ano-alvo.
- Sensibilidade: dez observações anuais anteriores.
- Em cada corte, a função de seleção recebe exclusivamente as linhas anteriores
  ao ano-alvo. O valor real do ano-alvo só é usado depois, para calcular o erro.
- Métrica primária: erro absoluto; MAE é resumido por território e série.
- Rio Claro (`MUNICIPIO`) e Estado de São Paulo (`SP`) são apresentados
  separadamente.
- Empates por previsão: diferença absoluta de erro até 1e-9.
- Na análise pareada por série, os erros anuais são primeiro resumidos por
  série. O teste exato de sinais exclui séries empatadas e informa quantos
  pares efetivamente entraram no teste.

## Reprodutibilidade

Da raiz do repositório:

```powershell
python algoritimos\avaliacao_aninhada.py
python -m pytest algoritimos\teste_avaliacao_aninhada.py -q
```

O programa grava duas tabelas de previsões, duas tabelas resumidas por série e
`metadados.json` em `analises/avaliacao_aninhada/`. Os metadados incluem o
SHA-256 do CSV de entrada e o SHA do commit do checkout, quando executado em
um clone Git.

## Interpretação

A janela de oito anos foi definida como principal por corresponder ao mínimo
de treinamento declarado no código do projeto. A janela de dez anos é uma
análise de sensibilidade. Como ambas foram examinadas antes da formalização
deste protocolo, essa escolha deve ser relatada no artigo.

As previsões de anos consecutivos dentro de uma mesma série são dependentes.
Por isso, os anos não são tratados como unidades independentes no teste de
sinais: primeiro se calcula uma diferença média por série. O teste é
exploratório, pois há apenas 14 séries (sete cânceres em dois territórios).
Não se deve interpretar um valor-p isolado como validação definitiva.

O ajuste dos meses incompletos é herdado de `teste_previsao.serie_real()`:
os valores anuais são escalados pela razão 12/meses disponíveis, conforme o
mapa de meses documentado no teste. Essa regra é uma hipótese de
comparabilidade e deve ser descrita como limitação; o teste de vazamento não
valida a correção dessa hipótese.

## Limites

O teste de invariância ao futuro verifica que modificar os valores do ano-alvo
e dos anos seguintes não altera seleção ou previsão, para os cortes cobertos
pela base. Ele não comprova que a base histórica esteja correta, que o ajuste
de meses seja não enviesado, nem que o modelo generalize para outros períodos,
territórios ou populações.
