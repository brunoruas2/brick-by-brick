# Case Study: Montando e Gerenciando uma Carteira de FIIs com Brick by Brick

> ⚠️ **DISCLAIMER — LEIA ANTES DE CONTINUAR**
>
> Este documento é **exclusivamente educacional e ilustrativo**. A carteira, as operações, os preços de entrada e as decisões de compra e venda descritos abaixo são **fictícios** — criados para demonstrar o fluxo de uso da ferramenta Brick by Brick, e não representam recomendações de investimento.
>
> Os indicadores exibidos (DY, P/VP, PL, spread) foram gerados a partir de dados públicos da CVM e da B3 carregados em um banco local de demonstração, e **podem estar desatualizados, incompletos ou não refletir a situação atual dos fundos citados**. Nenhum número apresentado deve ser utilizado como base para decisões reais de investimento.
>
> **Investimentos em FIIs envolvem riscos**, incluindo perda de capital, oscilação de renda e liquidez limitada. Consulte um profissional certificado (CFP/CGA) antes de tomar qualquer decisão. Este projeto não é um serviço de consultoria financeira.

---

> **Cenário fictício:** abril de 2026. SELIC em 12,93%. Juro alto comprime o valor dos imóveis e penaliza FIIs de tijolo, mas cria spread atraente para FIIs de papel. Um investidor hipotético tem uma carteira montada ao longo de 4 anos e precisa decidir o que manter, o que trocar e o que comprar.

---

## Parte 1 — Triagem inicial do universo

### Por onde começo

Abro o screener com critérios conservadores para um ambiente de juro alto: DY mínimo de 7%, P/VP abaixo de 1.10 e liquidez diária acima de R$500k (preciso conseguir sair se precisar).

```bash
python main.py screen --dy-min 7 --pvp-max 1.10 --liq-min 500000 --top 15
```

Os primeiros colocados pelo score são FIIs de CRI com DY de 200%+ — isso é artefato de dados, não realidade. Qualquer DY acima de 30% ao ano num FII listado é erro de dado, ajuste contábil ou evento pontual. **Descarto os quatro primeiros sem nem abrir.**

O screener serve pra filtrar, não pra decidir. O que me interessa na lista: TGAR11 (DY 9,4%, spread -3,5%), TRXF11 (DY 11,7%), KORE11 (DY 11,8%), XPIN11 (logística, DY 8,5%), GARE11, BPML11, MFII11, KNCR11 (único com spread positivo: +0,2%).

**Minha lógica nesse contexto:** com SELIC a 12,93%, qualquer FII de tijolo vai ter spread negativo. A pergunta correta não é "o spread é positivo?" — é "o desconto no P/VP compensa o carregamento negativo?". Para FIIs de papel (CRI/LCI), a pergunta é "o spread vs SELIC é pelo menos -2%, que é o custo de carregamento aceitável para liquidez?".

Com esse raciocínio, os candidatos reais da lista são **KNCR11** (único com spread quase zero, é FII de papel indexado ao CDI), **TRXF11** e **MFII11** (papel com spread < -2%), e para tijolo: **XPIN11** e **BPML11** — se tiverem P/VP historicamente baixo.

---

## Parte 2 — Análise individual de candidatos

### HGCR11 — FII de papel (CRI), candidato mais sólido

```bash
python main.py info HGCR11 --pvp-hist
```

**O que observo:**

- DY 12m: **11,51%** — melhor da minha carteira
- Spread vs SELIC: **-1,42%** — o mais próximo de zero entre os FIIs de tijolo/misto
- P/VP atual: **0,977** — mas o histórico 24 meses mostra: média 0,993, mínimo 0,929 (jan/25), máximo 1,050 (jun/24)
- **Tendência de DY preocupante:** 1,09% em abr/25 → 0,97% em fev/26. MM6 caindo de 1,09% para 1,02%

O P/VP está dentro da faixa histórica (nem caro nem barato). O problema é a tendência de DY: queda de quase 11% nos últimos 10 meses. Isso pode ser compressão de CDI nas carteiras de CRI, renegociação de contratos, ou amortizações sem reinvestimento equivalente. **Entra na watchlist com alvo de entrada a R$92 — P/VP ~0,92, que seria o mínimo histórico revisitado.**

```bash
python main.py portfolio watch HGCR11 --preco-alvo 92 --obs "DY em queda, aguardar P/VP historico minimo"
```

### HGLG11 — Logística, principal posição da carteira

```bash
python main.py info HGLG11 --pvp-hist --yoc-alvo 152
```

**O que observo:**

- P/VP atual: **0,942** — histórico 24 meses: média 0,977, mínimo 0,925, máximo 1,033
- Está **abaixo da média histórica**, mas longe do mínimo. Não é o ponto ideal de compra, mas também não está caro
- DY 12m: 7,31% com consistência altíssima (std dev de 0,026 — quase zero variação mês a mês)
- PL crescendo **+27,9% em 12 meses** — fundo captando recursos, sinal positivo de confiança do mercado
- Cotistas +9,8% — base crescendo, liquidez tende a aumentar

O `--yoc-alvo 152` me diz: se entrar a R$152 (próximo do mínimo histórico), o YoC seria 7,50% ao ano. Em ambiente de SELIC 12,93%, é um spread de -5,4% — carregamento pesado. Mas o crescimento de PL de 28% em 12 meses sugere que o fundo está se expandindo, o que historicamente precede valorização de cota.

**Decisão:** mantenho a posição. Não aumento agora porque o custo de carregamento é alto. Adiciono à watchlist com alerta para o P/VP próximo do mínimo histórico (0,925).

### VISC11 — Shoppings, sinal de alerta

```bash
python main.py info VISC11 --pvp-hist
```

**O que observo e me preocupa:**

- P/VP atual: **0,920** — histórico 24 meses: **média 0,862**, mínimo 0,766, máximo 0,959
- **VISC11 está no topo da sua faixa histórica.** O P/VP atual de 0,92 está acima da média de 0,862 — ou seja, está caro para o próprio padrão histórico do fundo
- PL: **-5,6% em 12 meses** — fundo encolhendo. Cotistas -1,1%

Este é o sinal mais importante: o mercado está pagando acima da média histórica por um fundo cujo patrimônio está diminuindo. Isso geralmente acontece porque o índice de shoppings subiu no curto prazo — não porque o fundo melhorou. **Risco de reversão.**

O DY de 7,31% parece atraente, mas o YoC que importa é o meu, calculado sobre o preço médio de compra de R$103,35. Estou recebendo 7,31% × 103,35 / 108,64 = **6,96% efetivo** sobre o preço atual — ligeiramente abaixo do DY nominal porque o preço subiu.

**Decisão:** coloco VISC11 em observação. Se o PL continuar encolhendo por mais 2 trimestres, vendo e realoco.

### KNRI11 — O mais fraco da carteira

```bash
python main.py info KNRI11
```

**O que observo:**

- P/VP: **1,017** — único da carteira acima do valor patrimonial
- DY 12m: **6,90%** — o mais baixo de todos
- Spread vs SELIC: **-6,03%** — o pior spread
- Consistência DY: **0,0547** — mais volátil (em dez/25 pagou 0,76%, em jan/26 pagou 0,54% — variação grande)
- PL crescendo apenas +1,8% em 12 meses — anêmico comparado ao HGLG11 (+27,9%)

Estou pagando prêmio sobre o VPA (P/VP > 1) por um fundo com o pior DY, o pior spread e crescimento de PL mínimo. Historicamente, quando FIIs de tijolo ficam caros (P/VP > 1) em ambiente de juro alto, o mercado corrige. **Candidato a venda.**

---

## Parte 3 — Diagnóstico da carteira atual

```bash
python main.py portfolio show
python main.py portfolio allocation
python main.py portfolio income --meses 12
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

---

## Parte 4 — Monitoramento mensal

### O que rodo todo mês (5 minutos)

```bash
python main.py update cotahist   # preços novos
python main.py alerts            # alguma coisa mudou?
python main.py portfolio report  # proventos estimados do mês
```

### O que olho trimestralmente (30 minutos)

```bash
python main.py update inf-mensal  # DY e VPA novos da CVM
python main.py portfolio dividends --resumo  # payback e YoC atualizados
python main.py portfolio income   # renda mensal evoluiu?
python main.py portfolio watchlist # algum candidato chegou ao preço-alvo?
```

Para cada ativo da carteira, verifico:

| Indicador | Sinal de alerta | Ação |
|---|---|---|
| DY mes < 80% da MM6 | Distribuição anômala ou queda estrutural | Investigar fato relevante |
| PL var. 12m < 0% por 2 trimestres | Fundo encolhendo | Coloca em revisão |
| P/VP > 1,10 em ambiente de juro alto | Mercado sobreprêmio | Avaliar venda |
| Spread vs SELIC < -8% | Carregamento alto demais | Avaliar substituição |
| Cotistas var. 12m < -5% | Saída de investidores | Sinal vermelho |

### O que ocorreu em KNRI11 no trimestre

Rodei `info KNRI11` e vi:
- Jan/26: DY = 0,54% (mínimo dos últimos 12 meses)
- Fev/26: DY = 0,67% (recuperação, mas abaixo do histórico de 0,61-0,62%)
- P/VP = 1,017 — ainda acima de 1,0

O DY inconsistente (alta variação mês a mês) é sintoma de que o fundo faz distribuição complementar esporádica — lucro eventual, não renda recorrente de contratos. Em FII de tijolo, isso é sinal de qualidade inferior à do HGLG11, que paga 0,68% todo mês com std dev de 0,026.

---

## Parte 5 — Decisão de reposicionamento: saindo de KNRI11

### A lógica do swap

Não saio de um ativo apenas porque ele está ruim. Saio quando identifico um destino melhor e o custo de trocar (spread de bid/ask, possível ganho de capital) é justificado pelo diferencial de renda.

**Posição atual em KNRI11:**
- 2 cotas × R$166,79 = R$333,58 de valor atual
- Preço médio: R$139,94 → **ganho de capital de R$53,70 (+19,2%)**
- YoC mensal atual: ~0,67% × 139,94 / 166,79 = **0,56% efetivo sobre meu custo**

**Destino: HGCR11**

Por que HGCR11 em vez de reforçar HGLG11?

- Com R$333 vendo KNRI11 e compro ~3 cotas de HGCR11 @ R$97,28
- YoC no novo ativo: 0,97% × 97,28 / 97,28 = **0,97%/mês** (pago a preço de mercado)
- Diferencial de renda mensal por cota: 0,97% - 0,56% = **+0,41% ao mês**

Isso equivale a R$333 × 0,41% = **+R$1,37/mês** de renda adicional com o mesmo capital.

Além disso: estou trocando P/VP 1,017 (caro) por P/VP 0,977 (próximo do justo), DY -6,03% de spread por DY -1,42% de spread, e reduzindo concentração em tijolo no pior momento do ciclo para tijolo.

**O único risco:** a tendência de queda do DY do HGCR11. Por isso minha posição vai ser conservadora — 3 cotas, não 6.

### Executando a operação

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

A nova alocação move HGCR11 de 4,5% para ~7,5% do portfólio — ainda subposição em papel para o contexto atual, mas um passo na direção certa sem concentrar demais em um ativo com tendência de queda de DY.

---

## Parte 6 — O que monitorar nos próximos 6 meses

### Watchlist ativa

```bash
python main.py portfolio watchlist
```

| Ticker | Alvo | Racional |
|---|---|---|
| HGCR11 | R$92 | Aguardar P/VP próximo do mínimo histórico (0,929) |
| XPIN11 | R$67 | Logística, P/VP abaixo de 0,95 seria entrada interessante |
| KNCR11 | R$103 | Único FII com spread positivo vs SELIC — preço-alvo de 0,98× VPA |

```bash
python main.py portfolio watch XPIN11 --preco-alvo 67 --obs "logistica, aguardar P/VP < 0.95"
python main.py portfolio watch KNCR11 --preco-alvo 103 --obs "papel CDI, spread positivo"
```

### Gatilhos de saída para VISC11

Sei exatamente o que me fará vender VISC11. Não vou esperar "parecer ruim" — tenho critérios:

1. **PL var. 12m negativo por 3 trimestres consecutivos** — fundo encolhendo estruturalmente
2. **P/VP voltar acima de 0,95** — com PL encolhendo, prêmio de mercado seria injustificável
3. **DY cair abaixo de 0,60%/mês** por dois meses seguidos — perda de poder de distribuição

Se dois desses três ocorrerem simultaneamente, vendo e realoco em KNCR11 (caso o preço chegue ao alvo).

### Gatilho de compra adicional em HGLG11

Compro mais HGLG11 se o P/VP voltar ao mínimo histórico de 0,925, que corresponderia a ~R$153 com o VPA atual. O `--yoc-alvo` me diz que a R$153 o YoC seria 7,45%/ano — ainda com spread negativo, mas o crescimento de PL de 28% em 12 meses justifica o prêmio de qualidade.

```bash
python main.py portfolio watch HGLG11 --preco-alvo 153 --obs "reforcar posicao no minimo historico P/VP 0.925"
```

---

## Síntese: o que a ferramenta resolveu neste case

| Decisão | Sem a ferramenta | Com a ferramenta |
|---|---|---|
| Identificar VISC11 caro | Comprar e "achar" caro pelo feeling | P/VP 0,92 vs média histórica 0,862 — dado objetivo |
| Identificar KNRI11 como pior ativo | Olhar DY pontual e achar "ok" | Juntar P/VP>1 + spread -6% + PL +1,8% + consistência alta |
| Calcular ganho do swap KNRI→HGCR | Estimativa manual por planilha | `--yoc-alvo` + `dividends --resumo` em 2 minutos |
| Saber quando HGLG11 está barato | Feeling subjetivo | P/VP histórico: média 0,977, alvo 0,925 |
| Monitorar tendência de DY do HGCR11 | Não monitoraria, só DY pontual | MM6/MM12/MM24 mostrando queda estrutural |
| Critérios de saída de VISC11 | "Quando parecer ruim" | 3 gatilhos objetivos definidos com base em dados reais |

A ferramenta não toma decisões — ela elimina a ambiguidade. O que era julgamento subjetivo ("parece caro") vira dado objetivo ("está no 94º percentil histórico de P/VP"). O que era feeling ("esse fundo tá bom") vira evidência ("PL +28% em 12 meses, 544k cotistas, DY consistente com std dev de 0,026").
