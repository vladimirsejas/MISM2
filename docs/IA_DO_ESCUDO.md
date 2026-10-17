# A IA do Escudo Feminino — o que é, o que foi medido e o que falta comprovar

Escrito em 17/10/2026. Este documento descreve a IA que existe no Escudo **hoje**, como ela foi
avaliada (com os limites da avaliação) e o que só o autor consegue comprovar no computador dele.
Para a decisão e as regras de manutenção, ver a seção "Pergunte à Lia" do `CLAUDE.md`.

## 1. Onde há IA (e o que é regra comum)

| Parte | O que faz | Técnica | Onde |
|---|---|---|---|
| **Entender a pergunta** | Liga o que a pessoa escreveu a um de 21 assuntos que o Escudo sabe responder, e identifica o câncer e o ano | Recuperação de informação: vetores TF-IDF de **palavras** (radicais de 5 letras) e de **trechos de letras** (3 a 5), semelhança por cosseno contra um vocabulário popular escrito à mão; limiares de confiança; **Gemini como segunda chance**, escolhendo numa lista fechada | `algoritimos/entendimento.py` |
| **Prever** | Para cada câncer, projeta as internações dos próximos 3 anos | Aprendizado de máquina simples: **5 modelos** (repetir o último ano, média de 3 anos, tendência linear, tendência dos 6 últimos anos, suavização exponencial com tendência amortecida) **escolhidos por validação temporal** (backtest: treina até o ano t, prevê t+1 a t+3, anda um ano). Faixa de incerteza vinda do erro medido nos testes | `algoritimos/inteligencia.py` (seção "Previsão com validação") |
| **Redigir** | Explica a resposta em linguagem simples ou técnica | **Gemini** (modelo de linguagem), cercado: recebe só a pergunta e os números já calculados; o texto é conferido antes de aparecer | `algoritimos/ia_linguagem.py`, `algoritimos/assistente.py` |
| **Segurança e abstenção** | Violência, risco de vida e emergência de saúde recebem texto fixo com telefones; pergunta sem relação ou sem dados é recusada com clareza | Regras revisáveis (**não são IA**, e é de propósito: onde há risco, a resposta não pode depender de nota) | `entendimento.py`, `assistente.py` |

O que **não** é IA: os cálculos de `inteligencia.py` (contagens, tendência, ano fora do padrão, radar do futuro)
e a árvore de botões da Lia. Eles continuam sendo a única fonte dos números; a IA interpreta e explica,
o Escudo calcula e comprova.

## 2. O caminho de uma pergunta

```
pergunta escrita na lateral, junto da Lia (dashboard/app.py: formulário "caixa_form")
  -> segurança (violência / suicídio / emergência)? texto fixo, Apoio à mulher, NÃO é gravada, a IA nem é chamada
  -> conversa social ("obrigada")? Lia responde
  -> entendimento.compreender: assunto + câncer + ano (+ contexto da resposta anterior)
        regras entendem com folga?  segue
        senão e há Gemini: classificar_pergunta escolhe um assunto da LISTA FECHADA (ou "nenhuma"); a escolha é conferida
        senão: até 3 palpites em botões, ou "isso foge do que sei" (nunca chuta)
  -> assistente.montar: a resposta vem de lia.responder (mesmos números dos botões) ou é montada aqui
        (previsão validada, óbitos e tempo de todos os cânceres, ajuda, sobre a IA, causa, sem dados)
  -> assuntos de DADOS: Gemini redige (redigir_resposta) -> assistente.conferir
        número que não está nos cálculos? promessa ("vai ficar")? explicação de causa? -> descarta e mostra a resposta direta
  -> balão da Lia: pergunta, texto, selo (IA ou "sem IA"), fonte e limite, "o que o Escudo calculou"; o painel vai ao gráfico
```

Sem chave, sem rede, com erro ou cota esgotada, ou depois de 40 perguntas com IA na sessão: a resposta direta
da Lia aparece. A caixa nunca fica muda e nunca mostra erro técnico.

### Garantias que têm teste (`teste_assistente.py`)
- Sem IA, a resposta da caixa é **exatamente** a fala da Lia para aquele assunto (chat e painel não divergem).
- Texto da IA com número novo, "vai aumentar/ficar" ou "por causa de/devido a" é **descartado**.
- Segurança, sintoma, apoio, onde ser atendida, causa e "sem dados" **não passam pela IA** (o Gemini nem é chamado).
- Gemini com erro de rede, cota esgotada, resposta vazia ou assunto inventado: a caixa continua respondendo.
- Relato de violência e sintoma pessoal **não são gravados** em `perguntas_usuarios`.

### Três situações de resposta (abstenção por critério verificável, não por "porcentagem de confiança")
1. **Respondida:** a regra reconheceu o assunto com nota alta e folga sobre o 2º lugar, ou o Gemini escolheu um assunto da lista e o câncer citado existe no banco.
2. **Ambígua:** até 3 palpites em botões. A pessoa escolhe; nada é chutado.
3. **Sem informação:** `sem_dados` ("eu não tenho": cor/raça, renda, escolaridade, estadiamento, sobrevida, população — conferido contra as colunas que a carga realmente grava), `causa` ("o Escudo detecta, não explica por quê"), câncer não acompanhado, ano sem dados ou além do horizonte da previsão, previsão com poucos anos ("prefiro não projetar").

## 3. A previsão e o que ela prova

`prever_com_validacao` (testes em `teste_previsao.py`, com dados sintéticos de resposta conhecida e a base pública de Rio Claro):
- **Validação temporal:** cada modelo é ajustado só com o passado de cada teste (13 anos geram 18 previsões testadas por modelo).
- **Referência simples:** o modelo escolhido é comparado com "repetir o último ano". Só "ganha" se errar pelo menos 10% menos; senão a previsão é marcada como frágil e a frase diz isso. Em Rio Claro, por exemplo, o ovário não ganhou do método ingênuo.
- **Incerteza:** faixa de ~90% pelo erro medido nos testes, que nunca encolhe com o horizonte.
- **Empate:** erros até 2% maiores que o melhor empatam e vence o mais simples (menos chance de "ganhar por sorte").
- **Coerência com o painel:** quando a tendência linear vence, a previsão é idêntica à projeção desenhada no gráfico.
- **Limites:** poucos anos por série (13), escolher entre 5 modelos com poucos testes tem ruído, anos incompletos entram já ajustados (média dos meses disponíveis x 12), e é projeção de tendência de **internações**, não de casos novos nem incidência.
Um modelo mais sofisticado não foi acrescentado porque não há evidência de que melhoraria com 13 pontos por série.

## 4. Avaliação do entendimento

`py algoritimos\teste_entendimento.py` (reprodutível; sem rede). O gabarito (`gabarito_perguntas.json`) tem **221 perguntas** em três conjuntos.

**O que "entendida corretamente" significa aqui:** o assunto reconhecido é o esperado (ou, nas perguntas com duas intenções, um dos aceitáveis) **e**, quando a pergunta cita um câncer, o câncer certo foi identificado. Mede **entendimento**, não a exatidão do texto final; a exatidão do texto vem por construção (é a mesma fala da Lia) e está coberta por `teste_assistente.py`.

| Conjunto | Perguntas de conteúdo | 1ª execução, antes de ajustar | Depois dos ajustes | Caixa antiga (mesmas perguntas) |
|---|---|---|---|---|
| Desenvolvimento (usado para ajustar) | 91 | 67 de 88 direto (76%), **4 erradas** | 80 (88%), 0 erradas | 39 (43%), 52 erradas |
| Teste | 62 | 43 direto (69%), **2 erradas** | 47 (76%), 0 erradas | 30 (48%), 32 erradas |
| Final (escrito às cegas, depois) | 35 | **21 direto (60%), 1 errada**; fora do assunto 3 de 8; saudação/segurança 2 de 5 | 31 (89%) — **já não é independente** | 17 (49%) |

Como ler:
- **A única estimativa independente de cada conjunto é a coluna "1ª execução".** O melhor número honesto de generalização é o do conjunto final: **cerca de 60% entendidos direto, com 1 resposta errada em 35**; as outras ficam como palpites em botões (ou, com o Gemini ligado, vão para a segunda chance — não medido, ver seção 6).
- O conjunto final foi escrito depois do motor pronto e inclui 7 perguntas sugeridas pelo ChatGPT (não escritas por quem fez o motor). Ele revelou falhas **graves** que o desenvolvimento não mostrava: segurança não reconhecia "minha mãe desmaiou", saudações longas não eram reconhecidas e só 3 de 8 perguntas fora do assunto eram recusadas. Foram corrigidas (e por isso o conjunto deixou de ser independente). Para medir de novo é preciso escrever um **conjunto novo**, às cegas.
- Três perguntas do final ("mulheres com HIV", "cor ou raça", "sobreviveram cinco anos") aparecem como não recusadas porque o gabarito as rotulou "fora do assunto", mas hoje recebem a resposta `sem_dados` ("eu não tenho essa informação"), que é a certa. Não foram reclassificadas no gabarito para não mexer na régua depois de medir.
- **Erro silencioso** (responde errado sem avisar): antiga 52% a 57% das perguntas; nova 0% nos conjuntos de desenvolvimento e teste e 1 em 35 no final (1ª execução). A antiga sempre responde; a nova prefere palpites ou recusa.
- Na comparação restrita aos 10 assuntos que a antiga já tinha, ela acerta 83% no teste contra 72% da nova (direto). O gabarito foi escrito por quem conhecia as palavras-chave dela, o que a favorece; a nova compensa com palpites (alcance com até 1 clique: 98% contra 48%).

**Limites da avaliação (declarados, não escondidos):**
1. As perguntas foram escritas pela equipe (e 7 por outra IA), **não por usuários reais**. Falta testar com pessoas.
2. O desenvolvimento foi usado para ajustar vocabulário e limiares. O teste foi usado para olhar números agregados, e o vocabulário continuou sendo ampliado depois, guiado por testes unitários e pelo conjunto final; portanto **só a 1ª execução de cada conjunto é independente**.
3. O gabarito tem pouca variedade de perguntas com duas intenções e de continuações de conversa; o contexto foi testado por casos escritos, não por um conjunto.
4. A medição acima é **sem o Gemini**. O efeito dele na segunda chance não foi medido.

### Protocolo para a próxima avaliação independente
1. Escrever um conjunto novo (de preferência por outras pessoas: colegas, a professora, gestores), com paráfrases, erros de digitação, linguagem popular, duas intenções, continuações e assuntos que os dados não respondem — **antes** de rodar o motor.
2. Rodar uma única vez e guardar o resultado. Só depois corrigir; o conjunto passa a ser de desenvolvimento.
3. Reportar sempre: entendeu direto, errou, palpite com a certa, recusou corretamente, recusou indevidamente, e câncer correto.

## 5. O que o ChatGPT sugeriu e o que foi aproveitado

| Sugestão | Decisão |
|---|---|
| Arquitetura em camadas: IA interpreta/explica, o Escudo calcula | **Já era o desenho**; mantido e documentado |
| Testar com perguntas que nunca apareceram | **Aceita:** conjunto final às cegas, com as 7 perguntas dele; revelou falhas reais |
| Memória de contexto (“e no estado?”, “e o de colo do útero?”) | **Aceita, em escopo mínimo:** guarda só assunto e câncer da última resposta, na sessão; recomeçar ou trocar de cidade esquece. Território e período não variam neste painel |
| Respostas com fonte e limites | **Aceita:** linha de fonte (SIH/SUS, cidade, período, "não é caso novo") em respostas de dados. Não foi inventada "data de atualização", que o sistema não tem |
| Três estados: respondida / ambígua / informação insuficiente | **Aceita:** palpites, `sem_dados` e `causa`; critérios verificáveis, sem porcentagem de confiança |
| Previsão com validação temporal, referência ingênua, incerteza e limites | **Já implementado** (seção 3) |
| Três conjuntos (desenvolvimento, validação, final) | **Parcialmente:** desenvolvimento, teste e final, com as ressalvas acima |
| Medir câncer correto e a resposta completa | **Aceita:** câncer correto medido; texto final igual ao da Lia testado |
| Não dar por concluído o que depende do Gemini, do painel e do banco reais | **Concordo:** seção 6 |
| Assistente de investigação, monitor de qualidade dos dados, relatórios | **Segunda etapa.** `completude` já cobre parte do monitor; o resto depende de decisão do autor |

## 6. O que NÃO foi comprovado (e como comprovar)

A nuvem onde isto foi feito não tem a chave do Gemini, o banco real nem o Windows do autor.

| Pendência | Como o autor comprova |
|---|---|
| A chave funciona e o modelo `gemini-3.8-flash` existe | Dois cliques em `Testar IA (Gemini).bat` (ou `py algoritimos\testar_gemini.py`). Se o modelo não existir, o script lista os que a chave aceita; trocar com `GEMINI_MODEL=...` no `.env` |
| O texto do Gemini passa na conferência na prática (não é descartado o tempo todo) | Passo 5 do mesmo script; depois abrir o painel e perguntar. O selo diz se foi IA ou resposta direta |
| Quanto o Gemini melhora o entendimento | `py algoritimos\teste_entendimento.py --com-gemini` |
| O painel com o banco real (7 cânceres, todas as cidades) | Abrir `Abrir Escudo Feminino.bat` e perguntar; rodar `py dashboard\teste_painel.py` |
| A caixa com pessoas de verdade | Teste de usabilidade com colegas e gestores; guardar as perguntas (as que não são relato pessoal ficam em `perguntas_usuarios`) para ampliar o vocabulário |

Custo e limites operacionais: cada pergunta usa até 2 chamadas ao Gemini (entender, se as regras não bastarem, e redigir); há limite de 40 perguntas com IA por sessão; o prazo de espera por chamada é de 25 s; sem a chave o Escudo funciona inteiro.

## 7. A caixa no Apoio à mulher (preparada em 17/10/2026, ainda não enviada ao `main`)

A página Apoio é para quem **procura cuidado**, então o desenho é mais cauteloso que o do painel de gestão:
- **Nenhuma IA escreve sobre serviço.** Telefone, prazo, regra e endereço saem do catálogo conferido (`apoio.py`, 81 itens, fonte oficial, data, "a confirmar"). O motor (`apoio_busca.py`) só escolhe qual item mostrar, com a mesma busca por palavras e letras do painel.
- Confiança alta: o cartão do item, idêntico ao do clique. Dúvida: até 3 candidatos em botões. Nada parecido: "não encontrei no guia" e as portas. Resposta direta errada é a exceção que mais importa.
- O Gemini, se ligado, só escolhe uma porta ou lâmina numa lista fechada (segunda chance de entender); o selo diz "o texto é do guia, não da IA".
- Segurança (violência, risco de vida, emergência) e sintoma pessoal: texto fixo, sem IA. As perguntas do Apoio não são gravadas em lugar nenhum (o teste prova que a página não abre o banco).

**Medição** (`gabarito_apoio.json`, 86 perguntas escritas antes do motor; `py algoritimos\teste_apoio_busca.py`). Primeira execução, sem ajuste: desenvolvimento 12 de 37 diretas e corretas, 0 erradas; **final, às cegas: 19 de 30 (63%), 0 erradas, o item certo entre os 3 primeiros em 29 de 30**, segurança/saudação/sintoma 5 de 6, fora do assunto 2 de 3. Depois dos ajustes: 26 de 37 e 21 de 30 (70%), 0 erradas — o final **já não é independente**. Limites: perguntas da equipe, não de usuárias; vocabulário popular do Apoio precisa da revisão do autor; "como declarar imposto de renda" encontra o item de isenção do IR para quem tem câncer (aceitável no contexto, mas conta como não recusada no gabarito).
