# Case Study: Montando e Gerenciando uma Carteira de FIIs com Brick by Brick

> **DISCLAIMER — LEIA ANTES DE CONTINUAR**
>
> Este documento é **exclusivamente educacional e ilustrativo**. A carteira, as operações, os preços de entrada e as decisões de compra e venda descritos abaixo são **fictícios** — criados para demonstrar o fluxo de uso da ferramenta Brick by Brick, e não representam recomendações de investimento.
>
> Os indicadores exibidos (DY, P/VP, PL, spread) foram gerados a partir de dados públicos da CVM e da B3 carregados em um banco local de demonstração, e **podem estar desatualizados, incompletos ou não refletir a situação atual dos fundos citados**. Nenhum número apresentado deve ser utilizado como base para decisões reais de investimento.
>
> **Investimentos em FIIs envolvem riscos**, incluindo perda de capital, oscilação de renda e liquidez limitada. Consulte um profissional certificado (CFP/CGA) antes de tomar qualquer decisão. Este projeto não é um serviço de consultoria financeira.

---

> **Cenário fictício:** abril de 2026. SELIC em 12,93%. Juro alto comprime o valor dos imóveis e penaliza FIIs de tijolo, mas cria spread atraente para FIIs de papel. Um investidor hipotético tem uma carteira montada ao longo de 4 anos e precisa decidir o que manter, o que trocar e o que comprar.

---

## Parte 0 — Diagnóstico macro: qual segmento está melhor posicionado?

Antes de abrir qualquer fundo individualmente, preciso entender onde o mercado está criando valor. Com SELIC alta, minha hipótese é que FIIs de papel (CRI indexado ao CDI/IPCA) deveriam estar com spread melhor do que tijolo. Mas hipótese é hipótese — vou checar os dados.

```bash
python main.py segment
```

**O que encontro:**

```
Medianas por segmento

Segmento                    N   DY 12m med   P/VP med   Spread med   Liq med
Papel (CRI/CRA)            38    11,2%        0,978       -1,7%       R$ 2,1M
Recebíveis Imobiliários    12    10,4%        0,991       -2,5%       R$ 890K
Logistica                  18     8,3%        0,936       -4,6%       R$ 3,4M
Lajes Corporativas         14     7,9%        0,879       -5,0%       R$ 1,2M
Shoppings                  11     7,4%        0,894       -5,5%       R$ 2,8M
Híbrido                    22     7,1%        0,917       -5,8%       R$ 1,1M
```

A tabela confirma a hipótese — e também revela algo útil: **logística está com spread -4,6%, P/VP mediano de 0,936**, o que é razoável para tijolo em ciclo de juro alto. Shoppings em -5,5% com P/VP 0,894 — mercado está descontando o segmento.

Quero ver o ranking dentro de logística especificamente, porque é onde tenho minha maior posição (HGLG11):

```bash
python main.py segment logistica --top 8
```

```
Top 8 -- Logistica (18 FIIs com dados)

#   Ticker    Preco      P/VP   DY 12m   Spread    Liq 30d    Score
1   HGLG11    R$ 158,40  0,942   7,31%   -5,62%    R$ 4,2M    72
2   XPLG11    R$ 107,20  0,914   8,12%   -4,81%    R$ 3,1M    70
3   XPIN11    R$ 68,50   0,951   8,45%   -4,48%    R$ 1,8M    68
4   BTLG11    R$ 102,80  0,923   7,89%   -5,04%    R$ 5,6M    67
5   BRCO11    R$ 88,30   0,907   8,67%   -4,26%    R$ 980K    65
...
```

**HGLG11 lidera em score dentro do segmento** — consistência de DY (std dev baixíssimo) é o fator que o separa de XPLG11. Isso me dá contexto antes de abrir os individuais.

---

## Parte 1 — Triagem do universo com o screener

Com o contexto de segmento estabelecido, abro o screener com critérios conservadores para juro alto: DY mínimo de 7%, P/VP abaixo de 1,10 e liquidez diária acima de R$500k.

```bash
python main.py screen --dy-min 7 --pvp-max 1.10 --liq-min 500000 --top 15
```

Os primeiros colocados pelo score são FIIs de CRI com DY de 200%+ — isso é artefato de dados, não realidade. Qualquer DY acima de 30% ao ano num FII listado é erro de dado, ajuste contábil ou evento pontual. **Descarto os quatro primeiros sem nem abrir.**

O que me interessa na lista: TGAR11 (DY 9,4%, spread -3,5%), TRXF11 (DY 11,7%), KORE11 (DY 11,8%), XPIN11 (logística, DY 8,5%), GARE11, BPML11, MFII11, KNCR11 (único com spread positivo: +0,2%).

**Minha lógica nesse contexto:** com SELIC a 12,93%, qualquer FII de tijolo vai ter spread negativo. A pergunta correta não é "o spread é positivo?" — é "o desconto no P/VP compensa o carregamento negativo?". Para FIIs de papel (CRI/LCI), a pergunta é "o spread vs SELIC é pelo menos -2%, que é o custo de carregamento aceitável para liquidez?".

Com esse raciocínio, os candidatos reais da lista são **KNCR11** (único com spread quase zero, é FII de papel indexado ao CDI), **TRXF11** e **MFII11** (papel com spread < -2%), e para tijolo: **XPIN11** e **BPML11** — se tiverem P/VP historicamente baixo.

---

## Parte 2 — Análise individual dos candidatos

### HGCR11 — FII de papel (CRI), candidato mais sólido

```bash
python main.py info HGCR11 --pvp-hist
```

**O que observo:**

- DY 12m: **11,51%** — melhor da minha carteira
- Spread vs SELIC: **-1,42%** — o mais próximo de zero entre os FIIs de tijolo/misto
- P/VP atual: **0,977** — histórico 24 meses: média 0,993, mínimo 0,929 (jan/25), máximo 1,050 (jun/24)
- **Tendência de DY preocupante:** 1,09% em abr/25 → 0,97% em fev/26. MM6 caindo de 1,09% para 1,02%

O P/VP está dentro da faixa histórica (nem caro nem barato). O problema é a tendência de DY: queda de quase 11% nos últimos 10 meses. Isso pode ser compressão de CDI nas carteiras de CRI, renegociação de contratos, ou amortizações sem reinvestimento equivalente.

Quero entender a causa antes de entrar. Para isso, enriqueço o fundo com o relatório gerencial via FundosNet:

```bash
python main.py portfolio enrich HGCR11
```

O comando baixa o último relatório gerencial do FundosNet (PDF público, sem autenticação) e extrai os dados via Claude API. O que aparece no `info` em seguida:

```bash
python main.py info HGCR11
```

```
Relatorio gerencial (extrato via IA):
  Competencia   2026-03
  Vacancia      3,8%
  Locatarios    Carteira diversificada: 47 devedores, maior concentracao
                16,2% (incorporadora Alfa S.A.)
  Contratos     Prazo medio ponderado de 3,2 anos. Vencimentos concentrados
                em 2027 (38% da carteira) -- risco de reinvestimento relevante
  Alertas       Gestor sinaliza reducao de CDI-spread nas novas alocacoes
                frente ao aperto de liquidez do mercado de CRI. Distribuicao
                do 1T26 impactada por amortizacao antecipada em dois CRIs.
```

**Isso muda minha tese.** A queda de DY não é conjuntural — é estrutural: 38% da carteira vence em 2027 e o gestor já sinalizou que o reinvestimento será em CDI-spreads menores. Isso explica o MM6 em queda e me diz que o DY de 11,51% não se sustenta. **Revisito o tamanho da posição pretendida. Entra na watchlist com alvo mais conservador.**

```bash
python main.py portfolio watch HGCR11 --preco-alvo 92 --obs "DY em queda estrutural, aguardar P/VP historico minimo (0.929)"
```

### HGLG11 — Logística, principal posição da carteira

```bash
python main.py info HGLG11 --pvp-hist --yoc-alvo 152
```

**O que observo:**

- P/VP atual: **0,942** — histórico 24 meses: média 0,977, mínimo 0,925, máximo 1,033
- Está abaixo da média histórica, mas longe do mínimo. Não é o ponto ideal de compra, mas também não está caro
- DY 12m: 7,31% com consistência altíssima (std dev de 0,026 — quase zero variação mês a mês)
- PL crescendo **+27,9% em 12 meses** — fundo captando recursos, sinal positivo de confiança do mercado
- Cotistas +9,8% — base crescendo, liquidez tende a aumentar

O `--yoc-alvo 152` me diz: se entrar a R$152 (próximo do mínimo histórico), o YoC seria 7,50% ao ano. Em ambiente de SELIC 12,93%, é um spread de -5,4% — carregamento pesado. Mas o crescimento de PL de 28% em 12 meses sugere que o fundo está se expandindo.

Enriqueço para ver o que está por trás do crescimento de PL:

```bash
python main.py portfolio enrich HGLG11
```

```
Relatorio gerencial (extrato via IA):
  Competencia   2026-03
  Vacancia      4,2%
  Locatarios    AB InBev: 18,1% | Mercado Livre: 14,3% | GPA: 9,7% |
                Outros 22 locatarios: 57,9%
  Contratos     Prazo medio de 5,1 anos. Proximos vencimentos: 2029 (31%).
                Sem concentracao critica de vencimento nos proximos 24 meses
  Alertas       3a emissao de cotas concluida (R$620M captados). Expansao
                do portfolio com 2 galpoes em Guarulhos e 1 em Cajamar.
                Vacancia fisica abaixo da media historica de 6,3%.
```

**Isso confirma minha tese.** Vacância baixa (4,2% vs histórico de 6,3%), contratos longos sem concentração de vencimento crítica, base de locatários sólida e emissão de cotas bem-sucedida explica o PL +28%. **Mantenho e adiciono à watchlist para reforçar no mínimo histórico.**

### VISC11 — Shoppings, sinal de alerta

```bash
python main.py info VISC11 --pvp-hist
```

**O que observo e me preocupa:**

- P/VP atual: **0,920** — histórico 24 meses: **média 0,862**, mínimo 0,766, máximo 0,959
- **VISC11 está no topo da sua faixa histórica.** O P/VP atual de 0,92 está acima da média de 0,862 — ou seja, está caro para o próprio padrão histórico do fundo
- PL: **-5,6% em 12 meses** — fundo encolhendo. Cotistas -1,1%

Enriqueço para entender se há algo no relatório que justifique o prêmio:

```bash
python main.py portfolio enrich VISC11
```

```
Relatorio gerencial (extrato via IA):
  Competencia   2026-03
  Vacancia      8,4%
  Locatarios    Riachuelo: 11,2% | C&A: 9,8% | Renner: 8,7% |
                Alimentacao (varios): 18,3% | Outros: 52,0%
  Contratos     Vencimento de 22% dos contratos de ancora em 2027.
                Negociacoes em andamento -- sem confirmacao de renovacao
  Alertas       Vacancia acima da media do segmento. Ancora do Shopping
                Cascavel notificou intencao de nao renovar (4,2% da receita).
                Gestora avalia desinvestimento de 1 ativo nao-core
```

**O relatório gerencial muda o diagnóstico de "neutro" para "preocupante".** A vacância de 8,4% é elevada, um ancora relevante não vai renovar, e 22% dos contratos vencem em 2027 com resultado incerto. O mercado está pagando prêmio histórico por um fundo com fundamentos deteriorando. **Candid a venda. A decisão de sair depende do timing — prefiro vender com P/VP acima de 0,90 antes que esses eventos apareçam no DY.**

### KNRI11 — O mais fraco da carteira

```bash
python main.py info KNRI11
```

**O que observo:**

- P/VP: **1,017** — único da carteira acima do valor patrimonial
- DY 12m: **6,90%** — o mais baixo de todos
- Spread vs SELIC: **-6,03%** — o pior spread
- Consistência DY: **0,0547** — mais volátil (em dez/25 pagou 0,76%, em jan/26 pagou 0,54%)
- PL crescendo apenas +1,8% em 12 meses — anêmico comparado ao HGLG11 (+27,9%)

Estou pagando prêmio sobre o VPA (P/VP > 1) por um fundo com o pior DY, o pior spread e crescimento de PL mínimo. **Candidato a venda.**

---

## Parte 3 — Diagnóstico da carteira atual

```bash
python main.py portfolio show
python main.py portfolio allocation
python main.py portfolio dividends --resumo
```

**Situação encontrada:**

```
Custo total:  R$ 8.318
Valor atual:  R$ 8.566
P&L capital:  +R$ 248  (+3,0%)

Payback estimado: ~138 meses (11,5 anos)
Renda mensal:     R$ 56-65/mês (média R$ 59,37)
YoC acumulado:    29,34% do custo recuperado em dividendos
```

**Alocação por peso:**
- HGBS11: 35,9% — concentração excessiva em um único ativo
- HGLG11: 32,8%
- VISC11: 22,8%
- HGCR11:  4,5% — subposição em papel num momento de juro alto
- KNRI11:  3,9% — posição pequena mas cara

**Problemas identificados:**

1. **Concentração em shoppings (HGBS11 + VISC11 = 58,7%)** — duas posições do mesmo segmento, sendo que VISC11 está no topo histórico e HGBS11 tem PL encolhendo (-3,7%)
2. **Subexposição a papel (HGCR11 = 4,5%)** — com SELIC a 12,93%, FIIs de CRI/CDI deveriam ter peso maior
3. **KNRI11 = pagando prêmio pelo pior ativo da carteira**

### Projeção de renda futura

Com os dados do histórico, projeto os próximos 6 meses mantendo a carteira atual:

```bash
python main.py portfolio income --meses 12 --projecao 6
```

```
Renda mensal -- 12 meses reais + 6 projetados

Mes       Ativos   Renda
2025-04       4    R$ 56,23
2025-05       4    R$ 58,44
...
2026-03       5    R$ 63,81
2026-04*      5    R$ 59,37    (estimativa)
2026-05*      5    R$ 59,37
2026-06*      5    R$ 59,37
2026-07*      5    R$ 59,37
2026-08*      5    R$ 59,37
2026-09*      5    R$ 59,37

* Estimativa: media dos ultimos 6 meses reais (R$ 59,37/mes).
  Nao considera variacao de cotas ou DY.

Media mensal (real):     R$ 59,37
Projecao 6m (estimativa): R$ 356,22  (R$ 59,37/mes)
```

Isso me diz que, mantendo a carteira atual, devo receber cerca de R$356 em dividendos nos próximos 6 meses. O número é conservador — não inclui eventual rebalanceamento. Serve como baseline para comparar com o cenário pós-rebalanceamento.

---

## Parte 4 — Monitoramento mensal

### O que rodo todo mês (5 minutos)

```bash
python main.py update cotahist   # precos novos
python main.py alerts            # alguma coisa mudou?
python main.py portfolio report  # proventos estimados do mes
```

O `alerts` agora inclui verificação automática da watchlist. Em um dia aleatório de maio, rodo:

```bash
python main.py alerts
```

```
Alertas e oportunidades

Nivel       Ticker   Tipo                   Detalhe
[ATENCAO]   VISC11   spread_negativo        DY 12m (7,1%) abaixo da SELIC (12,93%) -- spread -5,8%
[AVISO]     HGBS11   dy_queda               DY do mes (0,48%) abaixo de 80% da media mensal 12m (0,52%)
[OPRTND]    KNCR11   preco_alvo_watchlist   Preco R$ 102,40 atingiu alvo R$ 103,00 (-0,6%) -- watchlist
[OPRTND]    XPIN11   score_alto             Score 71 | DY 12m 8,5% | P/VP 0,94 | Logistica
```

**O alerta do KNCR11 é novo** — o preço chegou ao alvo que eu defini na watchlist. Não preciso verificar manualmente toda semana: o sistema me avisa quando o gatilho é ativado. Rodo o `info` para confirmar os números antes de tomar qualquer decisão:

```bash
python main.py info KNCR11
```

Spread de +0,1% vs SELIC com P/VP de 0,98 — dentro da tese. Anoto para a revisão trimestral.

### O que olho trimestralmente (30 minutos)

```bash
python main.py update inf-mensal                 # DY e VPA novos da CVM
python main.py portfolio enrich                  # atualiza relatorios gerenciais
python main.py portfolio dividends --resumo      # payback e YoC atualizados
python main.py portfolio income --projecao 3     # projecao do proximo trimestre
python main.py portfolio watchlist               # candidatos e distancia ao preco-alvo
python main.py segment                           # macro de segmentos mudou?
```

A tabela de segmentos que revejo trimestralmente me diz se a rotação setorial está acontecendo: se logística começar a fechar spread enquanto papel abre, é sinal de que o mercado está antecipando queda de juros — e isso muda a estratégia de alocação.

Para cada ativo da carteira, verifico:

| Indicador | Sinal de alerta | Ação |
|---|---|---|
| DY mes < 80% da MM6 | Distribuição anômala ou queda estrutural | Investigar fato relevante |
| PL var. 12m < 0% por 2 trimestres | Fundo encolhendo | Coloca em revisão |
| P/VP > 1,10 em ambiente de juro alto | Mercado sobreprêmio | Avaliar venda |
| Spread vs SELIC < -8% | Carregamento alto demais | Avaliar substituição |
| Cotistas var. 12m < -5% | Saída de investidores | Sinal vermelho |
| Vacancia no relatorio gerencial > media historica | Deterioracao operacional | Investigar |

### O que ocorreu em KNRI11 no trimestre

Rodei `info KNRI11` e vi:
- Jan/26: DY = 0,54% (mínimo dos últimos 12 meses)
- Fev/26: DY = 0,67% (recuperação, mas abaixo do histórico de 0,61-0,62%)
- P/VP = 1,017 — ainda acima de 1,0

O DY inconsistente (alta variação mês a mês) é sintoma de que o fundo faz distribuição complementar esporádica — lucro eventual, não renda recorrente de contratos. Em FII de tijolo, isso é sinal de qualidade inferior à do HGLG11, que paga 0,68% todo mês com std dev de 0,026.

---

## Parte 5 — Decisão de rebalanceamento

### Primeiro: validar a direção com backtest

Antes de executar qualquer operação, valido a intuição com dados históricos. A pergunta é: **se eu tivesse trocado KNRI11 por HGCR11 há 12 meses, teria sido melhor?**

```bash
python main.py backtest swap KNRI11 HGCR11 2025-04 --cotas 2
```

```
Backtest -- Swap hipotetico  KNRI11 -> HGCR11  em 2025-04
Comparacao: manter o FII original vs. ter trocado pelo alternativo.

Real: KNRI11  (entrada: 2025-04)
  Cotas: 2,00  |  Preco entrada: R$ 148,20  |  Capital: R$ 296,40
  Preco atual (mes fechado): R$ 166,79
  Valor atual: R$ 333,58
  Dividendos recebidos: R$ 22,14
  Retorno total: +18,9%

Simulado: HGCR11  (entrada: 2025-04)
  Cotas: 3,05  |  Preco entrada: R$ 97,15  |  Capital: R$ 296,31
  Preco atual (mes fechado): R$ 97,28
  Valor atual: R$ 296,70
  Dividendos recebidos: R$ 35,89
  Retorno total: +12,3%

Comparacao:

                    KNRI11        HGCR11       Delta
Capital investido   R$ 296,40     R$ 296,31    R$ -0,09
Dividendos totais   R$ 22,14      R$ 35,89     +R$ 13,75
Valor atual         R$ 333,58     R$ 296,70    -R$ 36,88
Retorno total       +18,9%        +12,3%       -6,6 p.p.

Custos operacionais (corretagem, IR) nao estao modelados.
```

**O backtest revela um ponto importante:** nos últimos 12 meses, KNRI11 teve ganho de capital de +R$36,88 a mais que HGCR11, o que compensou os R$13,75 de dividendos adicionais do HGCR11. O swap "teria sido pior" no curto prazo — mas isso é exatamente o que o P/VP > 1,0 estava precificando.

A pergunta certa não é "foi melhor no passado?" — é "vai ser melhor de agora em diante?". O P/VP do KNRI11 (1,017) acima de 1 em ambiente de juro alto sugere que o ganho de capital daqui para frente tende a ser menor ou negativo, enquanto o diferencial de renda do HGCR11 se acumula. **O backtest não confirma nem nega — ele clarifica o risco que estou assumindo ao trocar: abro mão de eventual valorização adicional de KNRI11 em troca de renda maior e P/VP mais justo.**

Rodo também um what-if de compra adicional para calibrar o tamanho da posição pretendida em HGCR11:

```bash
python main.py backtest add HGCR11 2025-01 --capital 500
```

```
Backtest -- Compra hipotetica  HGCR11  em 2025-01

  Cotas: 5,22  |  Preco entrada: R$ 95,78  |  Capital: R$ 499,97
  Preco atual: R$ 97,28
  Valor atual: R$ 507,80
  Dividendos recebidos: R$ 56,71
  Retorno total: +12,9%

* Simulacao. Custos operacionais nao modelados.
```

R$500 alocados no início de 2025 teriam gerado R$56,71 em dividendos em 15 meses — o que me dá um YoC anualizado de ~9,1% sobre o custo. Confirma que o ativo tem entregado o que o DY promete.

### Executando o swap: saindo de KNRI11, entrando em HGCR11

**Posição atual em KNRI11:**
- 2 cotas × R$166,79 = R$333,58 de valor atual
- Preço médio: R$139,94 → **ganho de capital de R$53,70 (+19,2%)**
- YoC mensal atual: ~0,67% × 139,94 / 166,79 = **0,56% efetivo sobre meu custo**

**Destino: HGCR11** (3 cotas, posição conservadora dado o risco de queda de DY identificado no relatório gerencial)

Por que HGCR11 em vez de reforçar HGLG11?

- Com R$333 vendo KNRI11 e compro ~3 cotas de HGCR11 @ R$97,28
- YoC no novo ativo: 0,97% × 97,28 / 97,28 = **0,97%/mês** (pago a preço de mercado)
- Diferencial de renda mensal por cota: 0,97% - 0,56% = **+0,41% ao mês**

Isso equivale a R$333 × 0,41% = **+R$1,37/mês** de renda adicional com o mesmo capital. Pequeníssimo em absoluto, mas a lógica não é o valor — é a qualidade: estou trocando P/VP 1,017 (caro) por P/VP 0,977 (próximo do justo), DY -6,03% de spread por DY -1,42% de spread.

O único risco documentado no relatório gerencial: 38% da carteira do HGCR11 vence em 2027. Por isso a posição é de 3 cotas, não 6.

```bash
# Registra a venda de KNRI11
python main.py portfolio sell KNRI11 2 166.79 2026-04-10

# Registra a compra de HGCR11
python main.py portfolio add HGCR11 3 97.28 2026-04-10
```

Confiro o efeito:

```bash
python main.py portfolio show
python main.py portfolio allocation
```

A nova alocação move HGCR11 de 4,5% para ~7,5% do portfólio — ainda subposição em papel para o contexto atual, mas um passo na direção certa sem concentrar demais em um ativo com risco de vencimento identificado.

---

## Parte 6 — O que monitorar nos próximos 6 meses

### Watchlist ativa

```bash
python main.py portfolio watchlist
```

| Ticker | Alvo | Racional |
|---|---|---|
| HGCR11 | R$92 | P/VP mínimo histórico — segunda tranche só nesse nível |
| HGLG11 | R$153 | Reforçar no P/VP mínimo histórico (0,925) |
| XPIN11 | R$67 | Logística de qualidade, aguardar P/VP < 0,95 |
| KNCR11 | R$103 | Único FII com spread positivo — está no alvo, decidir em breve |

```bash
python main.py portfolio watch XPIN11 --preco-alvo 67 --obs "logistica, aguardar P/VP < 0.95"
python main.py portfolio watch KNCR11 --preco-alvo 103 --obs "papel CDI, spread positivo -- alerta ativado em maio/26"
```

O `alerts` vai me avisar automaticamente quando qualquer um desses atingir o preço-alvo. Não preciso verificar manualmente.

### Ciclo de enriquecimento trimestral

A cada trimestre, atualizo os relatórios gerenciais para capturar mudanças operacionais que não aparecem no DY:

```bash
python main.py portfolio enrich
```

Os indicadores que vou monitorar por fundo após o enriquecimento:

| Fundo | O que monitorar no relatório gerencial |
|---|---|
| HGLG11 | Vacância abaixo de 6,3% (média histórica)? Renovações 2029 confirmadas? |
| HGCR11 | Reinvestimento dos CRIs vencidos em 2027 a spreads similares ou piores? |
| VISC11 | Ancora notificante renovou ou saiu? Vacância cruzou 10%? |
| HGBS11 | PL parou de encolher? Novo ativo incorporado? |

### Gatilhos de saída para VISC11

Sei exatamente o que me fará vender VISC11 — não vou esperar "parecer ruim":

1. **Ancora confirmada como saída** — perda de 4,2% da receita é concreta, não mais "risco"
2. **P/VP voltar acima de 0,95** — com fundamentos deteriorando, prêmio é injustificável
3. **DY cair abaixo de 0,60%/mês** por dois meses seguidos — perda de poder de distribuição

Se dois desses três ocorrerem simultaneamente, vendo e realoco em KNCR11 (que já está no preço-alvo).

### Gatilho de compra adicional em HGLG11

Compro mais HGLG11 se o P/VP voltar ao mínimo histórico de 0,925, que corresponderia a ~R$153 com o VPA atual. O `--yoc-alvo` me diz que a R$153 o YoC seria 7,45%/ano — ainda com spread negativo, mas crescimento de PL de 28% e vacância 4,2% (abaixo da média histórica) justificam o prêmio de qualidade.

---

## Síntese: o que a ferramenta resolveu neste case

| Decisão | Sem a ferramenta | Com a ferramenta |
|---|---|---|
| Entender o macro antes dos ativos | Checar segmentos um a um no Google | `segment` — medianas por segmento em 10 segundos |
| Identificar VISC11 caro pelo próprio histórico | Comprar e "achar" caro pelo feeling | P/VP 0,92 vs média histórica 0,862 — dado objetivo |
| Entender a queda de DY do HGCR11 | Ver só o número, não a causa | Relatório gerencial via enriquecimento: 38% da carteira vence em 2027 |
| Descobrir o risco de vacância do VISC11 | Não descobriria — não leio 40 PDFs por mês | `enrich` extrai: ancora notificou saída, vacância em alta |
| Validar o swap KNRI→HGCR com dados históricos | Estimativa manual por planilha | `backtest swap` — retorno total dos dois cenários em segundos |
| Receber alerta quando KNCR11 atingiu o alvo | Verificar preço todo dia manualmente | `alerts` — notificação automática quando preco_atual <= preco_alvo |
| Projetar renda dos próximos 6 meses | Planilha Excel separada | `portfolio income --projecao 6` — baseline imediato |
| Definir critérios de saída de VISC11 | "Quando parecer ruim" | 3 gatilhos objetivos, dois deles verificáveis automaticamente |
| Identificar KNRI11 como pior ativo | Olhar DY pontual e achar "ok" | Juntar P/VP>1 + spread -6% + PL +1,8% + consistência alta |

A ferramenta não toma decisões — ela elimina a ambiguidade. O que era julgamento subjetivo ("parece caro") vira dado objetivo ("está no 94º percentil histórico de P/VP"). O que era preocupação vaga ("HGCR11 não está rendendo igual") vira diagnóstico concreto ("gestor sinaliza reinvestimento a spreads menores, 38% da carteira vence em 2027"). O que era sensação ("essa troca faz sentido") vira análise ("o swap teria gerado +R$13,75 em dividendos vs -R$36,88 em valor de mercado nos últimos 12 meses — entendo o trade-off que estou fazendo").

Informação não elimina risco. Mas elimina surpresa.
