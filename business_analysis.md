# Brick by Brick — Análise de Negócio

> Avaliação sob a perspectiva de um analista financeiro especializado em FIIs.  
> Objetivo: identificar o que a ferramenta já resolve, onde ela falha e o que seria necessário para ela se tornar a **única ferramenta** de pesquisa e gestão de carteira.  
> Última revisão: após conclusão de M4 (abril/2026).

---

## 1. O que a ferramenta já faz bem

### Fundação de dados
- Coleta automatizada de **todas as fontes primárias** (CVM, B3, BCB) — sem dependência de terceiros que podem mudar HTML, cobrar API ou fechar
- Histórico longo configurável: `inf_mensal` e `cotahist` desde qualquer ano via `--desde-ano`
- Pipeline idempotente — rodar `update` duas vezes não duplica dados

### Análise fundamental
- Screener com score ponderado cobrindo DY, spread vs SELIC, P/VP, liquidez e consistência
- **`info` agora entrega análise completa:** indicadores pontuais + histórico de DY + tendências MM6/MM12/MM24 + P/VP histórico (24 meses) + crescimento de PL e cotistas + composição de receita
- `--yoc-alvo`: calcula o YoC projetado a um preço-alvo de entrada — elimina a calculadora do processo

### Gestão de carteira
- Reconstrução fiel do histórico de posições a partir das movimentações
- **YoC e payback em meses** — mais honestos que DY bruto de qualquer site
- **Detecção e correção de grupamentos/desdobramentos** — diferencial real; praticamente nenhuma ferramenta retail trata isso corretamente
- **`portfolio allocation`**: concentração por ativo e segmento com barras visuais
- **`portfolio income`**: histórico de renda mensal recebida com média, máximo e mínimo
- **`portfolio watchlist`**: candidatos monitorados com preço-alvo e distância atual
- Importação em lote via Excel; exportação de histórico para CSV/Excel
- Relatório mensal com comparativo vs SELIC e IPCA

---

## 2. Fluxo de trabalho de um analista de FIIs

### Fase 1 — Triagem do universo
**O que precisa:** filtrar ~500 FIIs para uma lista de 20-30 candidatos.

| Critério | Status |
|---|---|
| DY 12m, P/VP, liquidez, spread SELIC | ✅ Screener cobre |
| Filtro por segmento | ✅ `--segmento` (match parcial) |
| Filtro por tamanho (PL mínimo) | ✅ `--pl-min` |
| Excluir FIIs em liquidação/encerramento | ✅ Filtro por situação CVM |
| Filtro por nr. de cotistas (liquidez indireta) | ❌ Não existe |
| Pesos do score ajustáveis via CLI | ❌ Só via código (dict no `screener.py`) |
| Ranking automático por segmento (sem precisar filtrar) | ❌ Não existe |

### Fase 2 — Análise individual de um candidato
**O que precisa:** entender a qualidade e a tendência do fundo antes de comprar.

| Critério | Status |
|---|---|
| DY atual e histórico 13 meses | ✅ `info` |
| Tendência de DY (MM6/MM12/MM24) | ✅ `info` — sempre exibido |
| P/VP atual vs histórico 24 meses | ✅ `info --pvp-hist` |
| Crescimento do PL (fundo está captando?) | ✅ `info` — var. 12m/24m |
| Crescimento de cotistas | ✅ `info` — var. 12m |
| Composição de receita (imoveis, CRI, LCI) | ✅ `info` — últimos 3 meses |
| YoC projetado a preço-alvo de entrada | ✅ `info --yoc-alvo` |
| Comparação automática com pares do segmento | ❌ `compare` exige saber os tickers |
| Taxa de vacância | ❌ Lacuna estrutural — CVM não publica dado estruturado |
| Perfil de vencimento de contratos | ❌ Lacuna estrutural |

### Fase 3 — Análise do segmento
**O que precisa:** entender qual segmento está barato/caro no ciclo atual.

| Critério | Status |
|---|---|
| Média de DY por segmento | ❌ Não existe |
| Média de P/VP por segmento | ❌ Não existe |
| Ranking dos melhores FIIs por segmento | ❌ Não existe (apenas filtro `--segmento` no screener) |
| Comparação DY do segmento vs SELIC | ❌ Não existe |
| Evolução histórica de DY médio do segmento | ❌ Não existe |

> **Esta fase continua sem cobertura.** É a maior lacuna restante para uso como ferramenta única de análise — um analista que não consegue avaliar o momento do segmento sem saber os tickers de cor ainda precisará de uma fonte externa.

### Fase 4 — Construção da carteira
**O que precisa:** decidir tamanho de posição e concentração.

| Critério | Status |
|---|---|
| Registrar compras e vendas | ✅ |
| Ver P&L de capital | ✅ |
| Ver YoC por posição e acumulado | ✅ |
| Concentração por segmento (% do capital) | ✅ `portfolio allocation` |
| Concentração por ativo (% do capital total) | ✅ `portfolio allocation` |
| Watchlist de candidatos | ✅ `portfolio watch / watchlist` |
| Peso-alvo por segmento e desvio atual | ❌ Exibe atual, não compara com meta |

### Fase 5 — Monitoramento contínuo
**O que precisa:** ser avisado quando algo mudar.

| Critério | Status |
|---|---|
| Alerta de P/VP alto | ✅ `alerts` |
| Alerta de DY abaixo da média | ✅ `alerts` |
| Alerta de spread negativo vs SELIC | ✅ `alerts` |
| Alerta de P&L em queda | ✅ `alerts` |
| **Alerta de preço-alvo da watchlist atingido** | ❌ Watchlist existe mas não dispara alerta |
| Histórico de renda mensal recebida | ✅ `portfolio income` |
| **Projeção de renda futura** (próximos 12 meses) | ❌ `income` mostra histórico, não projeção |
| Alerta de queda de PL (fundo encolhendo) | ❌ Não existe |
| Calendário de pagamentos por FII | ❌ CVM não publica dado estruturado |

### Fase 6 — Reposicionamento
**O que precisa:** decidir quando sair de um ativo e entrar em outro.

| Critério | Status |
|---|---|
| Comparar YoC da posição atual vs alternativa no mesmo segmento | ❌ Processo manual — dois `info` separados |
| Calcular ganho de DY líquido ao trocar de posição | ❌ Não existe |
| Drawdown de renda (pior sequência de queda de proventos) | ❌ Não existe |

---

## 3. Features críticas ausentes após M4 (novo P0)

Com M4 concluído, os bloqueadores anteriores (watchlist, alocação, P/VP histórico) foram resolvidos. Os novos P0 são:

### 3.1 Análise de segmento
**Problema:** a Fase 3 permanece completamente descoberta. Um analista que não conhece os tickers de cor não consegue avaliar se logística está cara ou barata em relação a lajes ou shoppings sem recorrer a uma fonte externa.

**O que falta:**
- Médias de DY e P/VP por segmento calculadas a partir do screener
- Ranking interno de cada segmento (quais são os melhores FIIs de logística agora?)
- `compare --segmento logistica --vs HGLG11` — compara automaticamente com os melhores pares

**Complexidade:** média. Os dados já estão no banco — é questão de agregar `get_all_indicators()` por segmento.

### 3.2 Alerta de preço-alvo da watchlist
**Problema:** o investidor adiciona um FII à watchlist com preço-alvo de R$ 95, mas só descobre que o preço chegou lá se rodar `portfolio watchlist` manualmente. O valor da watchlist é exatamente o alerta passivo.

**Proposta:** integrar watchlist ao `alerts` — quando `preco_atual <= preco_alvo`, gerar alerta `[OPRTND]` com nível verde. Zero nova coleta necessária.

**Complexidade:** baixa. A lógica já existe em `alertas.py`, basta adicionar a verificação contra `get_watchlist()`.

### 3.3 Projeção de renda futura
**Problema:** `portfolio income` mostra o que foi recebido (histórico). O investidor de renda precisa saber o que espera receber nos próximos meses — fundamental para planejamento de fluxo de caixa.

**Proposta:** `portfolio income --projecao 12` — usando a média dos últimos 6 meses de DY × cotas atuais, projeta os próximos N meses como estimativa. Deixar explícito que é estimativa baseada em DY histórico.

**Complexidade:** baixa. Os dados necessários já existem em `get_historico_dividendos()` e `get_posicoes()`.

---

## 4. Features de alta prioridade (P1)

### 4.1 Comparação automática por segmento
`compare HGLG11 XPLG11 BTLG11` exige saber os tickers. Um analista quer "me mostre os 5 melhores de logística e compare com HGLG11". Isso resolve a Fase 3 pelo lado da pesquisa.

**Proposta:** `compare --segmento logistica --vs HGLG11 --top 5`

### 4.2 Pesos do score ajustáveis via CLI
O score atual é fixo (DY 30% · Spread 25% · P/VP 20% · Liquidez 15% · Consistência 10%). Um investidor conservador em renda quer penalizar mais P/VP alto; um agressivo quer priorizar DY. Hoje isso exige editar `screener.py`.

**Proposta:** `screen --peso-dy 40 --peso-pvp 30 --peso-liq 15 --peso-spread 15` — rebalanceia dinamicamente.

### 4.3 Peso-alvo por segmento no `allocation`
A ferramenta mostra onde o capital está hoje mas não compara com onde o analista quer que esteja. A informação de desvio ("quero 30% em logística, tenho 15%") é mais útil que a posição absoluta.

**Proposta:** arquivo de configuração simples (`carteira_config.json`) com pesos-alvo por segmento. O `allocation` exibiria coluna "Alvo", "Atual" e "Desvio" em cores.

### 4.4 Análise de drawdown de renda
Qual foi o pior período de queda de proventos na carteira? Essencial para dimensionar reserva de emergência e validar a resiliência do portfólio.

**Proposta:** no `portfolio income`, identificar sequências consecutivas de queda e exibir o pior drawdown observado (em meses e em valor).

---

## 5. Features de média prioridade (P2)

### 5.1 Rendimento vs IFIX
O IFIX é o benchmark natural dos FIIs. Comparar a carteira vs IFIX sem dados oficiais estruturados é impreciso.

**Limitação permanente:** dados do IFIX não estão disponíveis via fontes primárias usadas. A única alternativa seria adicionar scraping do site da B3 — fora da política de fontes do projeto.

### 5.2 Calendário de pagamentos
Alguns FIIs pagam no 15º dia útil, outros no último dia útil. Saber em que semana do mês esperar os créditos é relevante para gestão de fluxo de caixa.

**Limitação parcial:** a CVM não publica calendário estruturado. Seria possível inferir historicamente o padrão de pagamento a partir dos dados existentes, mas com imprecisão no mês vigente.

### 5.3 Análise de reposicionamento
Dado que quero sair de HGLG11 e entrar em XPLG11, qual é o ganho líquido de YoC considerando o custo da operação (spread de bid/ask, corretagem)? Hoje é processo manual.

**Proposta:** `compare HGLG11 XPLG11 --vs-carteira` — mostra YoC atual da posição vs YoC projetado na nova posição, dado o preço atual dos dois.

---

## 6. Lacunas estruturais de dados

Estas lacunas **não podem ser resolvidas** com as fontes primárias atuais — independente de quanto o sistema evolua:

| Dado | Por que é importante | Fontes alternativas |
|---|---|---|
| **Taxa de vacância** | Principal driver de risco em FIIs de tijolo | Relatórios gerenciais dos gestores (PDF) — não estruturado |
| **Perfil de vencimento de contratos** | Quando os aluguéis vencem e precisam ser renovados | Relatórios gerenciais |
| **Localização e qualidade dos ativos** | Imóvel prime vs secundário impacta vacância e reavaliação | Prospecto do fundo (PDF) |
| **IFIX composição e retorno total** | Benchmark padrão do mercado | Fonte B3 paga ou scraping |
| **Distribuições efetivamente pagas** | CVM reporta `rendimentos_a_distribuir` (intenção), não confirmação | Extratos de corretoras |

Essas lacunas definem o teto de análise puramente quantitativa da ferramenta. Para FIIs de tijolo, a análise qualitativa dos relatórios gerenciais (vacância, contratos, localização) permanece indispensável e fora do escopo de automação com dados públicos estruturados.

---

## 7. Avaliação geral — estado atual após M4

| Dimensão | Nota | Nota anterior (pré-M4) | Evolução |
|---|---|---|---|
| Qualidade dos dados | 9/10 | 9/10 | = |
| Screener | 7/10 | 6/10 | +1 (pl-min, export; falta análise de segmento) |
| Análise individual | 8/10 | 5/10 | +3 (P/VP hist, tendências, PL, composição) |
| Gestão de carteira | 9/10 | 7/10 | +2 (allocation, income, watchlist, export) |
| Monitoramento | 6/10 | 5/10 | +1 (watchlist existe; alerta de alvo ausente) |
| Repositório de dados | 8/10 | 8/10 | = |

**Score médio: 7,8/10** (era 6,7/10 pré-M4)

---

## 8. Conclusão e próximos passos

### O que foi resolvido em M4
A ferramenta passou de "boa para coleta e histórico" para "suficiente para análise individual completa". O `info` agora entrega em uma tela o equivalente ao que um analista profissional precisa para avaliar a qualidade de um fundo: preço, VPA, DY histórico com tendências, P/VP histórico, crescimento do PL, composição de receita e YoC projetado a diferentes preços de entrada. A gestão de carteira ficou robusta com allocation, income e watchlist.

### O que ainda impede o uso como ferramenta única

1. **Análise de segmento (Fase 3 completamente descoberta):** um analista não pode avaliar o momento do ciclo de nenhum segmento sem dados agregados por segmento. Esta é a principal lacuna para o uso independente.

2. **Watchlist sem alerta passivo:** a watchlist sem integração ao `alerts` é apenas uma lista — a proposta de valor real é o disparo automático quando o preço-alvo é atingido.

3. **Projeção de renda futura:** `income` mostra o passado; o investidor de renda precisa do futuro projetado para planejamento de fluxo de caixa.

### Sugestão para M5

Se M5 for uma interface gráfica, os itens P0 acima devem ser resolvidos primeiro — uma GUI sobre um backend com lacunas analíticas apenas empacota os problemas. A sequência recomendada antes de qualquer GUI:

1. **Análise de segmento** — `segment` command com médias, rankings e comparação automática
2. **Watchlist → alerts** — integração de 5 linhas em `alertas.py`
3. **`income --projecao N`** — projeção de renda futura baseada em DY histórico
4. **Pesos do score via CLI** — `--peso-dy`, `--peso-pvp` no `screen`

Depois dessas quatro adições, a ferramenta seria genuinamente autossuficiente para as seis fases do fluxo analítico.
