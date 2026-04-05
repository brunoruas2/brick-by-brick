# Brick by Brick — Análise de Negócio

> Avaliação sob a perspectiva de um analista financeiro especializado em FIIs.  
> Objetivo: identificar o que a ferramenta já resolve, onde ela falha e o que seria necessário para ela se tornar a **única ferramenta** de pesquisa e gestão de carteira.

---

## 1. O que a ferramenta já faz bem

### Fundação de dados
- Coleta automatizada de **todas as fontes primárias** (CVM, B3, BCB) — sem dependência de terceiros que podem mudar HTML, cobrar API ou fechar
- Histórico longo: inf_mensal desde qualquer ano (via `--desde-ano`), COTAHIST desde 1994
- Dados diários de preço (B3) + dados mensais de DY/VPA/PL (CVM) + benchmarks (BCB)

### Análise fundamental
- Screener com score ponderado cobrindo os principais vetores: DY, spread vs SELIC, P/VP, liquidez, consistência de proventos
- Indicadores calculados corretamente: DY 12m, spread vs SELIC, consistência (std. dev.)
- Histórico de DY por fundo (13 meses)

### Gestão de carteira
- Reconstrução fiel do histórico de posições a partir das movimentações
- YoC mensal e acumulado — indicador mais honesto que DY bruto
- Payback em meses — métrica prática de retorno do capital investido
- Detecção e correção de grupamentos/desdobramentos — ponto diferencial importante; praticamente nenhuma ferramenta retail trata isso
- Relatório mensal com comparativo vs SELIC e IPCA
- Importação em lote via Excel

---

## 2. Fluxo de trabalho de um analista de FIIs

Um analista de FIIs tipicamente trabalha em seis fases. Abaixo mapeio onde a ferramenta cobre e onde há lacunas.

### Fase 1 — Triagem do universo
**O que precisa:** filtrar ~500 FIIs para uma lista de 20-30 candidatos.

| Critério | Situação atual |
|---|---|
| DY 12m, P/VP, liquidez, spread SELIC | ✅ Screener cobre |
| Filtro por segmento | ✅ Cobre (parcial — string match) |
| Filtro por tamanho (PL mínimo) | ❌ Não existe |
| Filtro por nr. de cotistas (liquidez indireta) | ❌ Não existe |
| Excluir FIIs em liquidação/encerramento | ✅ Filtro por situação |
| Peso ajustável no score por perfil de investidor | ❌ Só via código |

### Fase 2 — Análise individual de um candidato
**O que precisa:** entender a qualidade e a tendência do fundo antes de comprar.

| Critério | Situação atual |
|---|---|
| DY atual e histórico 12m | ✅ `info` e `compare` |
| Tendência de DY (crescendo, estável, caindo) | ❌ Só vejo 13 meses lineares |
| P/VP atual vs histórico do próprio fundo | ❌ Só P/VP pontual, sem contexto histórico |
| Crescimento do PL (fundo está captando?) | ❌ Não existe |
| Crescimento de cotistas (saúde do fundo) | ❌ Não existe |
| Taxa de vacância | ❌ Não disponível na CVM — lacuna estrutural |
| Distribuição de receitas (imoveis_renda, CRI, LCI) | ⚠️ Dados existem no banco mas não são exibidos no `info` |
| Comparação com pares do mesmo segmento | ⚠️ `compare` existe mas exige saber os tickers manualmente |

### Fase 3 — Análise do segmento
**O que precisa:** entender qual segmento está barato/caro e bem/mal posicionado no ciclo.

| Critério | Situação atual |
|---|---|
| Média de DY por segmento | ❌ Não existe |
| Média de P/VP por segmento | ❌ Não existe |
| Melhores FIIs por segmento (ranking interno) | ❌ Não existe |
| Comparação de segmentos vs SELIC | ❌ Não existe |

### Fase 4 — Construção da carteira
**O que precisa:** decidir tamanho de posição e concentração por segmento.

| Critério | Situação atual |
|---|---|
| Registrar compras e vendas | ✅ |
| Ver P&L de capital | ✅ |
| Ver YoC por posição | ✅ |
| Concentração da carteira por segmento (%) | ❌ Não existe |
| Concentração por ativo (% do capital total) | ❌ Não existe |
| Peso alvo por segmento e desvio atual | ❌ Não existe |
| Watchlist de candidatos (interesse mas não comprado) | ❌ Não existe |

### Fase 5 — Monitoramento contínuo
**O que precisa:** ser avisado quando algo mudar sem precisar rodar análises manuais.

| Critério | Situação atual |
|---|---|
| Alerta de P/VP alto | ✅ |
| Alerta de DY abaixo da média | ✅ |
| Alerta de spread negativo vs SELIC | ✅ |
| Alerta de P&L em queda | ✅ |
| Projeção de renda mensal (próximos 12 meses) | ❌ Não existe |
| Calendário de pagamentos (qual mês cada FII costuma pagar) | ❌ Não existe |
| Alerta de preço-alvo atingido (para compra ou venda) | ❌ Não existe |
| Alerta de queda de PL (fundo encolhendo) | ❌ Não existe |

### Fase 6 — Reposicionamento
**O que precisa:** decidir quando sair de um ativo e entrar em outro.

| Critério | Situação atual |
|---|---|
| Comparar YoC da posição atual vs alternativa no mesmo segmento | ❌ Não existe |
| Calcular ganho de DY líquido ao trocar de posição | ❌ Não existe |
| Impacto tributário da venda (ganho de capital — isento para PF) | ⚠️ Não aplicável para PF, mas relevante para PJ |

---

## 3. Features críticas ausentes (P0 — bloqueadores)

Estas são as lacunas que impedem o uso da ferramenta como instrumento único de gestão:

### 3.1 Watchlist
**Problema:** não há como monitorar candidatos antes de comprar. O analista precisa manter uma lista mental ou em planilha externa.

**Proposta:** tabela `watchlist` no banco com ticker, preço-alvo de entrada, motivo, data de adição. Comandos: `portfolio watch TICKER --preco-alvo 95 --obs "P/VP abaixo de 0.90"` e `portfolio watchlist`.

**Impacto:** eliminaria a planilha de acompanhamento externa que todo investidor de FII mantém.

### 3.2 Concentração da carteira por segmento
**Problema:** um portfólio de FIIs diversificado exige controle de exposição por segmento (logística, shoppings, lajes corporativas, papel, residencial). Hoje não há como ver isso.

**Proposta:** comando `portfolio allocation` exibindo:
- % do capital total por segmento
- % do capital total por ativo
- Desvio de um target definido pelo usuário

### 3.3 Projeção de renda mensal
**Problema:** o investidor de renda precisa saber quanto espera receber nos próximos meses. Hoje o relatório mostra "provento estimado do mês" mas sem projeção futura.

**Proposta:** `portfolio income` — projeção para os próximos N meses usando a média dos últimos 6 meses de DY × cotas atuais. Exibir como tabela (mês a mês) e total anual esperado.

### 3.4 Histórico de P/VP do fundo
**Problema:** saber que HGLG11 está a P/VP 1.05 não diz nada sem saber se historicamente ele negocia a 0.90 ou 1.20. É a principal métrica de valuation para FIIs de tijolo.

**Proposta:** `portfolio pvp-history TICKER` — calcular P/VP mês a mês cruzando `cotacoes` (preco_fechamento_mensal) com `inf_mensal` (valor_patrimonial_cota) e exibir série histórica com média, mínimo e máximo.

---

## 4. Features de alta prioridade ausentes (P1)

### 4.1 Tendência de DY (24-36 meses)
O DY dos últimos 13 meses é insuficiente para classificar um fundo como "crescente", "estável" ou "declinante". Um FII que pagava 0.8%/mês há 3 anos e paga 0.65% hoje tem trajetória de queda — dado crítico para evitar.

**Proposta:** no `info`, mostrar médias móveis de DY em 3 janelas: 6m, 12m, 24m. Tendência positiva = média 6m > média 12m > média 24m.

### 4.2 Crescimento do PL e de cotistas
Fundos com PL crescente estão captando recursos e investindo — sinal de confiança do mercado. Fundos com PL encolhendo estão devolvendo capital ou em dificuldade.

**Proposta:** no `info`, mostrar variação do PL em 12m e 24m. Variação de cotistas em 12m.

### 4.3 Comparação automática com pares do segmento
Hoje `compare` exige saber os tickers manualmente. Um analista quer ver "me mostre os 5 melhores FIIs de logística e compare com HGLG11".

**Proposta:** `compare --segmento logistica --vs HGLG11` — filtra os N melhores do segmento pelo score e exibe side-by-side.

### 4.4 Análise de composição de receita
Os dados de `imoveis_renda`, `cri`, `lci` já estão no banco mas não são expostos no CLI. Para FIIs de papel, a composição entre CRI e LCI impacta o perfil de risco. Para FIIs de tijolo, a % de imóveis vs caixa revela qualidade.

**Proposta:** adicionar seção "Composição de ativos" no `info` com os últimos 3 meses de `imoveis_renda`, `cri`, `lci`, `contas_receber_aluguel`.

### 4.5 Ranking de segmento no screener
**Proposta:** `screen --segmento logistica --ranking` — exibe apenas os FIIs do segmento, ranqueados, com o score explicado coluna por coluna.

### 4.6 Export de dados
Um analista frequentemente quer cruzar dados em Excel ou Python externo. Hoje não há como exportar.

**Proposta:** flag `--export CSV` nos principais comandos (`screen`, `dividends`, `portfolio show`).

---

## 5. Features de média prioridade (P2)

### 5.1 Rendimento vs IFIX
O IFIX é o índice de referência dos FIIs. Comparar a performance da carteira vs IFIX não é trivial pois o índice agrega preço + proventos (retorno total). Uma aproximação seria comparar DY acumulado da carteira vs DY médio ponderado do índice.

**Limitação:** dados do IFIX não estão nas fontes primárias usadas. Seria necessário adicionar uma nova fonte de coleta.

### 5.2 Volatilidade da renda mensal
O investidor de renda quer saber não só quanto recebe em média, mas quão previsível é esse recebimento. O desvio padrão mensal da renda recebida é uma métrica relevante.

**Proposta:** no `portfolio dividends --resumo`, adicionar coluna "Volatilidade" (std. dev. dos dividendos mensais recebidos).

### 5.3 Análise de drawdown de renda
Qual foi a maior sequência de meses em que a renda caiu? Importante para dimensionar reserva de emergência.

**Proposta:** no `portfolio dividends`, identificar sequências de queda e exibir o pior período.

### 5.4 Preço-alvo baseado em yield targeting
Calcular o preço de entrada que entregaria um YoC-alvo desejado pelo usuário, dado o DY histórico do fundo.

**Proposta:** `info HGLG11 --yoc-alvo 0.8` → "Para 0.8%/mês de YoC com o DY atual, o preço de entrada seria R$ X".

### 5.5 Calendário de pagamentos
Alguns FIIs pagam no 15º dia útil, outros no último dia do mês. O calendário permite saber em que semana do mês esperar os créditos.

**Limitação:** a CVM não publica um calendário estruturado. Seria possível inferir historicamente (mês de pagamento vs mês de referência) a partir dos dados de `rendimentos_a_distribuir`, mas com imprecisão.

---

## 6. Lacunas estruturais de dados

Estas lacunas **não podem ser resolvidas** com as fontes primárias atuais:

| Dado | Por que é importante | Fontes alternativas |
|---|---|---|
| **Taxa de vacância** | Principal driver de risco em FIIs de tijolo | Relatórios gerenciais dos gestores (PDF) — não estruturado |
| **Perfil de vencimento de contratos** | Quando os aluguéis vencem e precisam ser renovados | Relatórios gerenciais |
| **Localização e qualidade dos ativos** | Imóvel prime vs secundário impacta vacância e reavaliação | Prospecto do fundo (PDF) |
| **IFIX composição e retorno total** | Benchmark padrão do mercado | Fonte B3 paga ou scraping do site |
| **Distribuições efetivamente pagas** | CVM reporta `rendimentos_a_distribuir` (intenção), não confirmação | Extratos de corretoras |
| **Informes trimestrais e anuais** | Detalhes operacionais além do inf_mensal | CVM (disponível, mas formato PDF/XML diferente) |

---

## 7. Síntese — Roadmap sugerido para M4

Priorizando o menor esforço com maior impacto para um analista de FIIs:

### Bloco A — Análise (1-2 semanas)
1. **P/VP histórico** — cruzar cotações mensais com VPA mensal (dados já no banco)
2. **Tendência de DY 6m/12m/24m** — agregação simples dos dados existentes
3. **Composição de receita no `info`** — apenas exibir `imoveis_renda`, `cri`, `lci`
4. **Comparação automática por segmento** — `compare --segmento`

### Bloco B — Portfolio (1-2 semanas)
5. **Concentração por segmento** — `portfolio allocation`
6. **Watchlist** — nova tabela + comandos `watch` / `watchlist`
7. **Projeção de renda** — `portfolio income` projetando 12 meses

### Bloco C — Refinamentos (1 semana)
8. **Export CSV/Excel** — flag `--export` nos comandos principais
9. **Crescimento de PL e cotistas no `info`**
10. **Volatilidade da renda no sumário de dividendos**

---

## 8. Avaliação geral

| Dimensão | Nota | Comentário |
|---|---|---|
| Qualidade dos dados | 9/10 | Fontes primárias, robusto, sem dependência frágil |
| Screener | 6/10 | Funcional mas rígido — sem análise de segmento, sem P/VP histórico |
| Análise individual | 5/10 | Falta tendência, composição de receita e P/VP histórico |
| Gestão de carteira | 7/10 | YoC e payback são diferenciais reais; falta concentração e projeção |
| Monitoramento | 5/10 | Alertas básicos mas sem watchlist e sem calendário de renda |
| Repositório de dados | 8/10 | SQLite local é eficiente e portátil |

**Conclusão:** a ferramenta já supera a maioria das alternativas retail para quem quer dados confiáveis e histórico de dividendos ajustado por splits. O salto para "ferramenta única" exige principalmente três coisas: **watchlist**, **alocação por segmento** e **P/VP histórico**. Tudo isso é construtível com os dados já coletados — não há necessidade de novas fontes para os itens P0 e P1.
