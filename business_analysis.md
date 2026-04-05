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

Lacunas que não são resolvíveis com as fontes primárias atuais via coleta estruturada:

| Dado | Por que é importante | Status |
|---|---|---|
| **Taxa de vacância** | Principal driver de risco em FIIs de tijolo | Resolvível via PDF (ver seção 9) |
| **Perfil de vencimento de contratos** | Quando os aluguéis vencem e precisam ser renovados | Resolvível via PDF |
| **Localização e qualidade dos ativos** | Imóvel prime vs secundário impacta vacância e reavaliação | Resolvível via PDF |
| **IFIX composição e retorno total** | Benchmark padrão do mercado | Permanece bloqueado (B3 paga) |
| **Distribuições efetivamente pagas** | CVM reporta intenção, não confirmação | Permanece bloqueado (extratos de corretoras) |

Os três primeiros itens eram considerados bloqueados por estarem em PDFs não estruturados. Com parsing via Claude API, passam a ser tratáveis — com a restrição de escopo descrita na seção 9.

---

## 7. Avaliação geral — estado atual após M4

> As notas abaixo refletem o estado pós-M4. A seção 9 detalha o plano para M5.

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

### O que M5 deve resolver antes de qualquer GUI

1. P0.1 — Watchlist → alerts (trivial)
2. P0.2 — Projeção de renda futura (simples)
3. P0.3 — Análise de segmento (média)
4. P0.4 — Enriquecimento via PDF com Claude API (complexo, alto impacto)

O plano detalhado de cada um está na seção 9.

---

## 9. Plano de implementação — M5

### Princípio de escopo

Nenhuma das features abaixo roda sobre todos os ~500 FIIs do banco. O escopo é sempre **carteira ativa + watchlist** — no máximo 15-20 fundos. Isso mantém custo, tempo de execução e ruído de dados sob controle.

---

### P0.1 — Alerta de preço-alvo da watchlist

**Complexidade:** trivial (~30 min)  
**Arquivo:** `src/portfolio/alertas.py`

A watchlist já tem `preco_alvo` por ticker. O `alerts` já tem a infraestrutura de alertas. Falta conectar os dois.

**Mudança necessária em `alertas.py`:**

```python
from src.storage.database import get_watchlist

def _check_watchlist_targets(ind_map: dict) -> list[Alerta]:
    alertas = []
    for item in get_watchlist():
        if not item.get("preco_alvo"):
            continue
        ticker = item["ticker"]
        r = ind_map.get(ticker, {})
        preco = r.get("preco")
        if preco and pd.notna(preco) and float(preco) <= float(item["preco_alvo"]):
            dist = (float(preco) / float(item["preco_alvo"]) - 1) * 100
            alertas.append(Alerta(
                nivel="oportunidade",
                ticker=ticker,
                tipo="preco_alvo_watchlist",
                mensagem=(
                    f"Preco R${preco:.2f} atingiu alvo R${item['preco_alvo']:.2f} "
                    f"({dist:+.1f}%)  —  {item.get('obs') or ''}"
                ),
            ))
    return alertas
```

Adicionar chamada de `_check_watchlist_targets(ind_map)` dentro de `check_alerts()`. O `ind_map` já é construído para os tickers da carteira — basta expandir para incluir os tickers da watchlist.

**Output esperado:**
```
[OPRTND]  HGCR11  preco_alvo_watchlist  Preco R$91.80 atingiu alvo R$92.00 (-0.2%) — DY em queda, aguardar P/VP minimo
```

---

### P0.2 — Projeção de renda futura

**Complexidade:** baixa (~2h)  
**Arquivos:** `src/portfolio/relatorio.py`, `main.py`

**Lógica:**
1. Para cada posição ativa em `get_posicoes()`, pegar o DY médio dos últimos 6 meses via `get_historico_dividendos()`
2. Projetar: `dividendo_mensal_est = cotas × preco_atual × dy_med_6m / 100`
3. Somar por mês para os próximos N meses
4. Exibir como tabela separada do histórico, claramente rotulada como estimativa

**Mudança em `relatorio_income()`:**

```python
def relatorio_income(meses: int = 12, projecao: int = 0) -> None:
    # ... (código atual do histórico) ...

    if projecao > 0:
        posicoes = get_posicoes()
        hist = get_historico_dividendos()

        projecao_mensal = 0.0
        for _, pos in posicoes.iterrows():
            t = pos["ticker"]
            sub = hist[hist["ticker"] == t].dropna(subset=["dividendo_recebido"])
            dy_med = sub.tail(6)["dividendo_recebido"].mean() if len(sub) >= 3 else None
            if dy_med:
                projecao_mensal += dy_med

        console.print(f"\n[bold]Projecao (proximos {projecao} meses) [dim]— estimativa baseada nos ultimos 6 meses[/dim][/bold]")
        pt = Table(show_header=True, header_style="bold")
        pt.add_column("Mes",   width=8)
        pt.add_column("Renda est.", justify="right", width=13)
        pt.add_column("", width=25)

        import datetime as dt
        from dateutil.relativedelta import relativedelta
        hoje = dt.date.today().replace(day=1)
        for i in range(1, projecao + 1):
            mes = (hoje + relativedelta(months=i)).strftime("%Y-%m")
            barra_len = max(1, int(projecao_mensal / monthly["renda"].max() * 25)) if not monthly.empty else 10
            pt.add_row(mes, f"R$ {projecao_mensal:,.2f}", "[dim]" + "#" * barra_len + "[/dim]")
        console.print(pt)
        console.print(f"[dim]Total estimado {projecao}m: R$ {projecao_mensal * projecao:,.2f}[/dim]")
```

**Novo parâmetro no CLI:**
```bash
python main.py portfolio income --meses 12 --projecao 6
```

**Limitação a comunicar ao usuário:** a projeção assume DY constante. Não prevê cortes de distribuição, novas compras, vendas ou variação de preço. É um piso de expectativa, não uma promessa.

---

### P0.3 — Análise de segmento

**Complexidade:** média (~4h)  
**Arquivos:** `src/analysis/indicadores.py` (nova função), `main.py` (novo comando)

**Nova função em `indicadores.py`:**

```python
def get_segment_summary() -> pd.DataFrame:
    """
    Agrega indicadores por segmento.
    Retorna: segmento, n_fiis, dy_mediano, pvp_mediano,
             spread_mediano, liq_mediana, melhor_ticker, melhor_score
    """
    from src.analysis.screener import screen
    df = screen(top_n=9999, liq_min=100_000)   # todos com liquidez mínima
    if df.empty:
        return pd.DataFrame()

    agg = (
        df.groupby("segmento")
        .agg(
            n_fiis       = ("ticker",       "count"),
            dy_mediano   = ("dy_12m",       "median"),
            pvp_mediano  = ("p_vp",         "median"),
            spread_med   = ("spread_selic", "median"),
            liq_mediana  = ("liquidez_30d", "median"),
            melhor_score = ("score",        "max"),
        )
        .reset_index()
    )
    # Ticker com maior score por segmento
    best = df.loc[df.groupby("segmento")["score"].idxmax(), ["segmento", "ticker"]]
    agg = agg.merge(best.rename(columns={"ticker": "melhor_ticker"}), on="segmento")
    return agg.sort_values("dy_mediano", ascending=False).reset_index(drop=True)
```

**Novo comando `segment` em `main.py`:**

```bash
python main.py segment           # visao geral de todos os segmentos
python main.py segment logistica  # detalha os FIIs de logistica com rankings
```

Saída do `segment` (visão geral):
```
Segmento           FIIs  DY med  P/VP med  Spread   Liq med    Melhor
Papel/CRI            45   11.2%     0.97   -1.7%   R$ 2.1M   KNCR11
Logistica            28    8.4%     0.93   -4.5%   R$ 3.8M   HGLG11
Shoppings            22    7.8%     0.87   -5.1%   R$ 5.2M   VISC11
Lajes corp.          18    7.1%     0.82   -5.8%   R$ 1.9M   KNRI11
Residencial          12    6.9%     0.79   -6.0%   R$ 0.4M   ALZR11
```

Saída do `segment logistica` (detalhe):
```
python main.py segment logistica --top 10
# = screener filtrado + compare automático dos top 5
```

Internamente, `segment NOME --top N` chama `screen(segmento=NOME, top_n=N)` e exibe com a tabela já existente do screener. Zero código novo além da agregação.

---

### P0.4 — Enriquecimento via PDF + Claude API

**Complexidade:** alta (~2 dias)  
**Impacto:** resolve as três lacunas estruturais mais críticas (vacância, contratos, qualidade)  
**Escopo:** apenas carteira + watchlist — nunca todos os FIIs

#### Visão geral do fluxo

```
portfolio enrich [TICKER]
       │
       ├─ 1. Resolve tickers da carteira + watchlist
       │
       ├─ 2. Para cada ticker:
       │       a. Busca CNPJ no banco (tabela fiis)
       │       b. Consulta FundosNet API → URL do último relatório gerencial
       │       c. Verifica cache: já extraído esse mês? → pula
       │       d. Baixa o PDF
       │       e. Envia ao Claude API com prompt estruturado
       │       f. Armazena resultado na tabela relatorio_gerencial
       │
       └─ 3. Exibe resumo do que foi extraído
```

#### 4a. Nova fonte: FundosNet

A B3 mantém o FundosNet, repositório público de todos os documentos de FIIs. Já está documentado no ROADMAP. A API é pública, sem autenticação:

```
GET https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados
  ?d=1
  &a[tipoFundo]=FII
  &a[cnpj]=<CNPJ_SEM_FORMATACAO>
  &a[tipoDocumento]=GER           ← Relatório Gerencial
  &o[0][id]=desc                  ← mais recente primeiro
  &l=1                            ← apenas 1 resultado
```

Retorna JSON com `data[0].id` e `data[0].dataReferencia`. O PDF está em:
```
GET https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=<ID>
```

**Arquivo:** `src/collectors/fundosnet_relatorio.py`

```python
import requests

FUNDOSNET_API = "https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados"
FUNDOSNET_DOC = "https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento"

def buscar_ultimo_relatorio(cnpj: str) -> dict | None:
    """
    Retorna {"id": ..., "data_referencia": ..., "descricao": ...} ou None.
    """
    resp = requests.get(FUNDOSNET_API, params={
        "d": 1,
        "a[tipoFundo]": "FII",
        "a[cnpj]": cnpj,
        "a[tipoDocumento]": "GER",
        "o[0][id]": "desc",
        "l": 1,
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data[0] if data else None

def baixar_pdf(doc_id: int) -> bytes:
    """Baixa o PDF do documento e retorna os bytes brutos."""
    resp = requests.get(FUNDOSNET_DOC, params={"id": doc_id}, timeout=30)
    resp.raise_for_status()
    return resp.content
```

#### 4b. Integração com Claude API

**Arquivo:** `src/analysis/pdf_enrichment.py`

```python
import base64
import json
import anthropic

EXTRACTION_PROMPT = """
Você é um analista especializado em FIIs brasileiros. Leia o relatório gerencial
e extraia as informações abaixo. Responda APENAS com JSON válido, sem texto adicional.

{
  "vacancia_fisica_pct":       <número com 1 decimal ou null>,
  "vacancia_financeira_pct":   <número com 1 decimal ou null>,
  "contratos_venc_12m_pct":    <% do ABL ou PL com vencimento em 12 meses, ou null>,
  "contratos_venc_24m_pct":    <idem 24 meses>,
  "contratos_venc_36m_pct":    <idem 36 meses>,
  "tipo_contrato_dominante":   "atipico" | "tipico" | "misto" | null,
  "top_locatarios":            ["nome1", "nome2", "nome3"] ou [],
  "resumo_gestor":             "<1 frase objetiva sobre o tom e destaques do relatório>",
  "alertas":                   ["<risco ou evento relevante mencionado>", ...]
}

Se o fundo for de papel (CRI/LCI) e não tiver vacância ou contratos de locação física,
retorne os campos de vacância e ABL como null e foque em contratos_venc e locatarios
(substitua locatarios por devedores/emissores dos CRIs).
"""

def extrair_dados_pdf(pdf_bytes: bytes, modelo: str = "claude-haiku-4-5-20251001") -> dict:
    """
    Envia o PDF ao Claude API e retorna os dados extraídos como dict.
    Lança exceção em caso de falha de parse ou API error.
    """
    client = anthropic.Anthropic()   # usa ANTHROPIC_API_KEY do ambiente
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    msg = client.messages.create(
        model=modelo,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    )
    return json.loads(msg.content[0].text)
```

**Custo estimado:**
- Relatório gerencial típico: 500 KB a 2 MB → ~30k-120k tokens de input
- Claude Haiku: ~$0,25/M input tokens
- Por relatório: **R$0,04 a R$0,15**
- Para 15 fundos/mês: **< R$2,50/mês**

Se a extração falhar o parse JSON (relatório incomum, tabela mal formatada), retentar uma vez com `claude-sonnet-4-6` antes de registrar como erro.

#### 4c. Schema de armazenamento

```sql
CREATE TABLE IF NOT EXISTS relatorio_gerencial (
    cnpj                    TEXT NOT NULL,
    ticker                  TEXT,
    competencia             TEXT NOT NULL,   -- YYYY-MM do relatório
    data_referencia         TEXT,            -- data de publicação no FundosNet
    vacancia_fisica         REAL,            -- %
    vacancia_financeira     REAL,            -- %
    contratos_venc_12m      REAL,            -- % ABL/PL
    contratos_venc_24m      REAL,
    contratos_venc_36m      REAL,
    tipo_contrato           TEXT,            -- "atipico" | "tipico" | "misto"
    top_locatarios          TEXT,            -- JSON array
    resumo_gestor           TEXT,
    alertas                 TEXT,            -- JSON array
    extraido_em             TEXT NOT NULL,   -- ISO-8601 timestamp
    modelo_claude           TEXT NOT NULL,
    PRIMARY KEY (cnpj, competencia)
);
```

Adicionada ao `_SCHEMA` e `_migrate()` em `database.py`.

#### 4d. Comando CLI

```bash
# Enriquece todos os fundos da carteira + watchlist
python main.py portfolio enrich

# Apenas um fundo específico
python main.py portfolio enrich HGLG11

# Força re-extração mesmo que já exista no cache do mês
python main.py portfolio enrich --force
```

**Comportamento de cache:** se `relatorio_gerencial` já tem um registro para `(cnpj, competencia)` do mês atual, pula sem chamar a API. Re-roda apenas se `--force` ou se o mês mudou.

**Output do comando:**
```
Enriquecendo 7 fundos (carteira: 5, watchlist: 4, 2 em comum)...

HGLG11  Baixando relatorio gerencial (fev/2026)... OK
        Enviando ao Claude (haiku)... OK
        Vacancia fisica: 2.1%  |  Venc 12m: 8.3%  |  Tipo: atipico
        Alerta: "Contrato Ambev vence em ago/2026 — negociacao em andamento"

VISC11  Baixando relatorio gerencial (fev/2026)... OK
        Enviando ao Claude (haiku)... OK
        Vacancia fisica: 4.8%  |  Venc 12m: 12.1%  |  Tipo: tipico
        Alerta: "ABL em Campinas com 3 lojas desocupadas desde nov/2025"

HGCR11  FundosNet: nenhum relatorio gerencial encontrado nos ultimos 60 dias
        [pular — FII de papel nao publica relatorio gerencial regularmente]
```

#### 4e. Integração com `info`

Após `portfolio enrich`, o comando `info TICKER` passa a exibir uma nova seção quando os dados existirem:

```bash
python main.py info HGLG11
```

```
...seções existentes...

Relatorio gerencial (fev/2026) — extraido por Claude haiku:
  Vacancia fisica     2.1%
  Vacancia financeira 1.8%
  Venc. contratos 12m 8.3%  |  24m: 22.4%  |  36m: 41.7%
  Tipo de contrato    Atipico (predominante)
  Top locatarios      Ambev, DHL, GPA
  Resumo do gestor    "Gestao destaca renovacao antecipada de 3 contratos e pipeline
                       de 2 novas aquisicoes para o semestre."
  Alertas             - Contrato Ambev vence em ago/2026 — negociacao em andamento
```

Se não houver dados: `[rode 'portfolio enrich HGLG11' para dados do relatorio gerencial]`

---

### Sequência de implementação recomendada

| # | Item | Complexidade | Impacto | Prazo est. |
|---|---|---|---|---|
| 1 | P0.1 — Watchlist → alerts | 30 min | Alto (alerta passivo) | Sessão 1 |
| 2 | P0.2 — `income --projecao` | 2h | Médio (planejamento de fluxo) | Sessão 1 |
| 3 | P0.3 — Comando `segment` | 4h | Alto (Fase 3 descoberta) | Sessão 2 |
| 4 | P0.4 — `portfolio enrich` (PDF+Claude) | 2 dias | Muito alto (rompe teto analítico) | Sessão 3-4 |

P0.1 e P0.2 são pré-requisitos simples. P0.3 é independente. P0.4 depende de `ANTHROPIC_API_KEY` no ambiente e de ter rodado `update` recentemente (precisa dos CNPJs no banco).

### Dependências externas para P0.4

```
anthropic>=0.40.0   # Claude API Python SDK — adicionar ao requirements.txt
```

Nenhuma outra dependência nova. O FundosNet é HTTP simples (mesmo `requests` já usado).

A `ANTHROPIC_API_KEY` deve estar como variável de ambiente. O comando `enrich` deve checar sua existência e exibir instrução clara se ausente:

```
[red]ANTHROPIC_API_KEY nao encontrada.[/red]
[dim]Defina a variavel de ambiente antes de rodar este comando:
  Windows:  set ANTHROPIC_API_KEY=sk-ant-...
  Linux:    export ANTHROPIC_API_KEY=sk-ant-...[/dim]
```
