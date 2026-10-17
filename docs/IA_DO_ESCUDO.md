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
- **Privacidade:** o texto da pergunta **nunca é gravado**, de nenhuma pergunta. `perguntas_usuarios` só conta o assunto (ex.: `evolucao`), para saber o que as pessoas perguntam; quem escreve "estou com câncer, o que faço?" não deixa rastro. Relato de violência e sintoma pessoal não entram nem nessa contagem.

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
| ~~A chave funciona e o modelo `gemini-3.8-flash` existe~~ **COMPROVADO em 17/10/2026** (6 de 6 passos, chamada simples em 6,7 s; o texto do passo 5 passou na conferência) | Dois cliques em `Testar IA (Gemini).bat` (ou `py algoritimos\testar_gemini.py`). Se o modelo não existir, o script lista os que a chave aceita; trocar com `GEMINI_MODEL=...` no `.env` |
| O texto do Gemini passa na conferência na prática (não é descartado o tempo todo) | Passo 5 do mesmo script; depois abrir o painel e perguntar. O selo diz se foi IA ou resposta direta |
| ~~Quanto o Gemini melhora o entendimento~~ **MEDIDO em 17/10/2026** (`py algoritimos\teste_entendimento.py --com-gemini`) | Entendeu direto 80 → **91**/91 (desenvolvimento), 47 → **62**/62 (teste) e 31 → **35**/35 (final), com 0 respostas erradas; fora do assunto no teste 3 → 4 de 4. Só foram ao Gemini as perguntas que as regras não resolviam sozinhas (11, 15 e 4). Perguntas escritas pela equipe, não por usuárias; falta um conjunto novo às cegas |
| O painel com o banco real (7 cânceres, todas as cidades) | Abrir `Abrir Escudo Feminino.bat` e perguntar; rodar `py dashboard\teste_painel.py` |
| A caixa com pessoas de verdade | Teste de usabilidade com colegas e gestores; anotar à mão, com consentimento, as perguntas que não foram entendidas (o painel só conta o assunto, nunca o texto) para ampliar o vocabulário |

Custo e limites operacionais: cada pergunta usa até 2 chamadas ao Gemini (entender, se as regras não bastarem, e redigir); há limite de 40 perguntas com IA por sessão; o prazo de espera por chamada é de 25 s; sem a chave o Escudo funciona inteiro.

## 6b. Concordância entre o Gemini e a busca local (17/10/2026, em teste)

**Hipótese:** um id de assunto válido devolvido pelo Gemini ainda pode ser o assunto errado, e resposta errada sem aviso é o pior erro. **Mudança:** na segunda chance, o Gemini só gera resposta direta se o assunto estiver entre os palpites da busca local (palavras + letras). Se estiver sozinho, a pessoa vê o palpite dele e os da busca, e confirma com um clique. **Como medir:** `py algoritimos\teste_entendimento.py --com-gemini` mostra, por conjunto, respondeu direto / palpite com a certa / errou antes e depois, e quantas perguntas o Gemini resolveu junto com a busca ou sozinho. **Resultado medido com o Gemini real (17/10/2026, mesmo gabarito, regra antiga x nova):** regra antiga 91/91, 62/62 e 35/35 respondidas direto, 0 erros; regra nova 89/91, 61/62 e 34-35/35 direto, 3 perguntas viraram palpite (o Gemini estava sozinho; o palpite continha a certa), 0 erros em duas execuções do desenvolvimento e do teste. No conjunto final a regra nova errou 1 pergunta numa execução e 0 na outra: o Gemini escolheu mal entre candidatos que a própria busca local já tinha, caso que a concordância não evita, e ele não é determinístico mesmo com temperatura 0. **Leitura:** com perguntas escritas pela equipe a regra antiga já tinha 0 erros, então a nova não preveniu nenhum erro e custou 3 cliques em 188 perguntas (1,6%). O benefício dela (barrar um id plausível e errado sem apoio local) só se testa com perguntas fora do vocabulário, que este gabarito não tem. **Decisão (17/10/2026): ENVIADA ao `main`, pelos números.** Comparação limpa (`py algoritimos\comparar_regras.py`, mesma resposta do Gemini avaliada pelas duas regras, 60 consultas): nos conjuntos da equipe (desenvolvimento, teste, final) a regra antiga não errou nenhuma resposta direta e a nova custou 3 confirmações; no conjunto adversarial (`gabarito_adversarial.json`, 37 perguntas escritas depois de ler o vocabulário: **não é às cegas**) o Gemini sozinho errou 1 de 16 ("o que mais pesa na rotina das enfermarias femininas?" -> `tempo`, esperado `mais_aparece`, fora dos palpites locais): a regra antiga responderia isso direto, a nova pediu confirmação. Saldo: 1 resposta errada evitada contra 9 confirmações a mais (6 delas no adversarial). É um ganho pequeno e medido num conjunto desenhado para isso; mantida porque um clique custa pouco e resposta errada sem aviso custa mais. Limites: o Gemini não é determinístico mesmo com temperatura 0; erro dele entre candidatos que a busca local já tinha (ex.: "qual desses cânceres tá lotando mais o hospital?" -> `tempo`) a regra não evita; falta um conjunto às cegas e testar com pessoas. Defeito conhecido das regras locais, não corrigido de propósito para não contaminar o conjunto: "como foi feita essa contagem?" vira `sobre_ia` (esperado `metodo`).

**Risco:** perguntas com paráfrase que o vocabulário não cobre deixam de ser resolvidas direto (viram 1 clique). Se a medição real mostrar perda grande sem ganho de acerto, reverter este commit. Medido só com Gemini simulado na nuvem; o efeito real depende da execução no notebook.

## 6b2. Painel com o banco real e Gemini real, ponta a ponta (17/10/2026)

No notebook do autor, com `banco\escudo_feminino.db` (464.340 internações, 7 cânceres, 645 municípios, fluxo 100%, mês gravado): as 5 abas abriram sem erro e as 3 perguntas feitas à caixa (evolução da mama, "qual câncer mais interna?", fluxo de outros estados) foram entendidas e **redigidas pelo Gemini com o texto aprovado na conferência de números**. `comparar_regras.py` repetido (57 consultas): regra antiga 2 erros diretos, regra nova 1 (ela evitou 1; 10 confirmações a mais). O erro persistente é "qual desses cânceres tá lotando mais o hospital?" -> `tempo` (esperado `mais_aparece`): o Gemini escolhe mal entre candidatos que a busca local já tinha, fora do alcance da regra. Falta: conjunto de perguntas às cegas, teste com pessoas e o arquivo real do CNES (`py algoritimos\unidades_saude.py`).

## 6b3. Teste com uma pessoa (autor), no notebook

`py dashboard\teste_perguntas_humano.py`: a pessoa digita perguntas como escreveria de verdade na caixa da Lia (banco e Gemini reais, com memória da conversa), vê a resposta e marca se era o que queria (s/n/p). Não grava nada (nem o banco). O resumo final serve de conjunto às cegas (a intenção esperada é a que a pessoa julgou certa) e de teste de usabilidade inicial.

## 6b4. Primeiro teste com uma pessoa (autor), no notebook, 17/10/2026

Com `py dashboard\teste_perguntas_humano.py` (banco e Gemini reais), o autor escreveu 6 perguntas do jeito que escreveria e julgou cada resposta. **Medida antes de corrigir (a estimativa honesta): 5 certas de 6.** Falha: "qual o caminho para quem acabou de descobrir um CA de pulmão?" recebeu a explicação sobre a IA (as regras decidiram `sobre_ia` com confiança e o Gemini nem foi chamado): o assunto "apoio" quase não pontuava para "acabei de descobrir um câncer". Também: "quais as cidades que mais têm câncer de mama, proporcionalmente?" virou botões genéricos, quando o certo era dizer que a base não tem a população. **Recusa explicativa (`SEM_POPULACAO`):** para ranking ou proporção entre cidades a Lia agora diz que falta a população de cada cidade (próxima etapa, IBGE), por que contar internações favorece cidades grandes e o que dá para comparar hoje (parcela de cada câncer, letalidade, permanência, ritmo), com botão "Comparar com outra cidade"; outras faltas de dado seguem com a recusa geral. **Correção:** frases novas, gerais, em "apoio" (descoberta do diagnóstico) e "sem_dados" (ranking de cidades e proporção por habitante); conferido que o conjunto final continua com 33 diretas e 0 erros. As 6 perguntas viraram teste de regressão (`gabarito_humano.json`, seção 3c de `teste_entendimento.py`): **já não são às cegas**. O que ainda vale: a pessoa de verdade acha lacunas que a equipe não acha, então repetir com outras pessoas.

## 6b5. Segundo teste com uma pessoa (autor), 17/10/2026

5 entradas (uma era um comentário digitado no lugar do veredito). **Medida antes de corrigir:** 2 palpites aceitos pelo autor ("preciso achar um hospital referência", "qual câncer cresceu mais na minha cidade", ambos com erros de digitação e dependentes do Gemini), 1 errada ("compare mama com melanoma": botões sem sentido) e 1 pedido sem resposta útil ("contato de hospital especializado em câncer": a Lia só apontava o cadastro da cidade). **Correções:** (1) comparar dois cânceres mostra todos lado a lado (`origem` "comparar_canceres", só quando não há lugar na frase); (2) câncer não acompanhado junto de um acompanhado ("mama com melanoma") agora é percebido, e o aviso só aparece nas respostas de dados, nunca nos textos fixos de sintoma e apoio; "pele não melanoma" não gera falso aviso; (3) "hospital especializado em câncer" vai para o apoio, e as respostas de apoio e de "onde ser atendida" apontam a lâmina "Hospitais no Estado". Regressão em `gabarito_humano.json` (seções 3c e 3d do teste de entendimento e 7d do assistente). Não resolvido: perguntas com vários erros de digitação ("Comapre", "creceu") ainda dependem do Gemini; sem ele viram palpites. O script de teste agora guarda como comentário o que a pessoa digitar no lugar do veredito.

## 6c. Conversa: "me explica isso melhor" e pedidos compostos (17/10/2026)

Achado de uma revisão externa (Codex/ChatGPT), confirmado no código: a caixa perdia o fio ("me explica isso melhor" depois de uma resposta virava botões genéricos) e reduzia um pedido com duas partes ("está aumentando e o que posso esperar?") a uma escolha. **Mudança:** (1) "me explica isso melhor", "não entendi", "como assim?" retomam a resposta anterior com a explicação simples do assunto, os mesmos números e um "como ler", em texto fixo, sem a IA; frases com assunto próprio não são tratadas assim, e sem resposta anterior a Lia pergunta. (2) Dois assuntos que cabem juntos (evolução e previsão, óbitos e valores, evolução e Estado) são respondidos juntos; qualquer outra combinação continua oferecendo botões. **Medido:** conjunto final 31 -> 33 respostas diretas de 35, 0 erradas; testes específicos em `teste_entendimento.py` (3b), `teste_assistente.py` (7b) e no painel (cenário I). **Limites:** continuação só retoma o último assunto de dados; não há conversa livre.

## 7. A caixa no Apoio à mulher (17/10/2026, enviada ao `main`; ainda não vista no notebook do autor)

A página Apoio é para quem **procura cuidado**, então o desenho é mais cauteloso que o do painel de gestão:
- **Nenhuma IA escreve sobre serviço.** Telefone, prazo, regra e endereço saem do catálogo conferido (`apoio.py`, 81 itens, fonte oficial, data, "a confirmar"). O motor (`apoio_busca.py`) só escolhe qual item mostrar, com a mesma busca por palavras e letras do painel.
- Confiança alta: o cartão do item, idêntico ao do clique. Dúvida: até 3 candidatos em botões. Nada parecido: "não encontrei no guia" e as portas. Resposta direta errada é a exceção que mais importa.
- O Gemini, se ligado, só escolhe uma porta ou lâmina numa lista fechada (segunda chance de entender); o selo diz "o texto é do guia, não da IA".
- Segurança (violência, risco de vida, emergência) e sintoma pessoal: texto fixo, sem IA. As perguntas do Apoio não são gravadas em lugar nenhum (o teste prova que a página não abre o banco).

**Medição** (`gabarito_apoio.json`, 86 perguntas escritas antes do motor; `py algoritimos\teste_apoio_busca.py`). Primeira execução, sem ajuste: desenvolvimento 12 de 37 diretas e corretas, 0 erradas; **final, às cegas: 19 de 30 (63%), 0 erradas, o item certo entre os 3 primeiros em 29 de 30**, segurança/saudação/sintoma 5 de 6, fora do assunto 2 de 3. Depois dos ajustes: 26 de 37 e 21 de 30 (70%), 0 erradas — o final **já não é independente**. Limites: perguntas da equipe, não de usuárias; vocabulário popular do Apoio precisa da revisão do autor; "como declarar imposto de renda" encontra o item de isenção do IR para quem tem câncer (aceitável no contexto, mas conta como não recusada no gabarito).
