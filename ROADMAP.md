# Roadmap: Brick by Brick — Sistema de Análise de FIIs em Python

## Milestones

| Milestone | Escopo | Status |
|---|---|---|
| **M1 — Fundação** | Coleta de dados primários (CVM + B3 + BCB) + storage SQLite | ✅ Concluído |
| **M2 — Análise** | Indicadores, screener, `info`, `compare` | ✅ Concluído |
| **M3 — Carteira** | Posições, P&L, dividendos históricos, splits, alertas, scheduler | ✅ Concluído |
| **M4 — Aprofundamento analítico** | P/VP histórico, tendências, alocação por segmento, watchlist, projeção de renda | ✅ Concluído |
| **M5 — Interface** | GUI web ou desktop — escopo a definir após M4 validado | 🔲 Futuro |

---

## M1–M3: O que está implementado

### Coleta de dados

| Coletor | Fonte | O que traz |
|---|---|---|
| `cvm_cadastro.py` | CVM `cad_fi.csv` | CNPJ, nome, situação, gestor, taxas |
| `cvm_inf_mensal.py` | CVM `inf_mensal_fii_{ANO}.zip` | DY, VPA, PL, cotas, cotistas, composição de ativos |
| `b3_cotahist.py` | B3 `COTAHIST_A{ANO}.ZIP` | Preços diários históricos, ISIN→ticker |
| `bcb_series.py` | BCB API SGS | SELIC, CDI, IPCA mensais |

- Histórico configurável: `update inf-mensal --desde-ano 2020`
- Pipeline idempotente: rodar `update` duas vezes não duplica dados

### Análise fundamental (`screen`, `info`, `compare`)

- **Screener** com score ponderado (DY 30% · Spread SELIC 25% · P/VP 20% · Liquidez 15% · Consistência DY 10%)
- Filtros: `--dy-min`, `--pvp-max`, `--liq-min`, `--spread-min`, `--segmento`, `--top`
- **`info TICKER`**: P/VP, DY mensal e 12m, liquidez, spread vs SELIC, histórico DY 13 meses
- **`compare TICKER1 TICKER2`**: comparação lado a lado dos principais indicadores

### Gestão de carteira (`portfolio *`)

| Comando | O que faz |
|---|---|
| `add / sell` | Registra compra ou venda; recalcula preço médio |
| `import / template` | Importação em lote via Excel com validação |
| `show` | Posições ativas com P&L de capital e DY estimado |
| `report [--month]` | Relatório mensal: proventos estimados, YoC, spread vs SELIC/IPCA |
| `dividends` | Histórico real de dividendos recebidos: YoC mensal, payback em meses |
| `history` | Log completo de movimentações |
| `check-splits` | Detecção automática de grupamentos/desdobramentos não registrados |
| `add-split` | Registra evento de split para correção histórica (tipo: grupamento/desdobramento) |
| `allocation` | Alocação do capital por ativo e por segmento com proporções visuais |
| `income` | Renda mensal histórica em dividendos com gráfico de barras |
| `watch / watchlist` | Watchlist de candidatos com preço-alvo e indicadores ao vivo |

- **YoC (Yield on Cost)**: dividendo recebido ÷ custo de aquisição — mais honesto que DY bruto
- **Payback em meses**: custo total ÷ média mensal dos últimos 6 meses de dividendos
- **Correção de splits**: grupamentos e desdobramentos são detectados e corrigem automaticamente o histórico de cotas e preço médio

### Automação e alertas (`alerts`, `scheduler`)

- Alertas de carteira: spread negativo, P&L abaixo do limiar, P/VP alto, DY em queda
- Oportunidades: FIIs fora da carteira com score alto
- Scheduler embutido: atualiza cotahist diariamente (seg–sex), inf-mensal aos domingos, benchmarks no dia 1

---

## M4 — Aprofundamento analítico ✅

> Base da análise de negócio: `business_analysis.md`

### Bloco A — Análise individual

| Feature | Comando | Status |
|---|---|---|
| **P/VP histórico** — série mensal com média, mín, máx | `info TICKER --pvp-hist` | ✅ |
| **Tendência de DY** — médias móveis MM6/MM12/MM24 | sempre no `info` | ✅ |
| **Crescimento de PL e cotistas** — variação 12m/24m | sempre no `info` | ✅ |
| **Composição de receita** — imóveis, CRI, LCI (% do PL, 3 meses) | sempre no `info` | ✅ |
| **YoC projetado por preço-alvo** | `info TICKER --yoc-alvo PRECO` | ✅ |

### Bloco B — Gestão de carteira

| Feature | Comando | Status |
|---|---|---|
| **Alocação por ativo e segmento** | `portfolio allocation` | ✅ |
| **Watchlist** — monitorar candidatos sem comprar | `portfolio watch / watchlist` | ✅ |
| **Renda mensal histórica** — gráfico de barras | `portfolio income [--meses N]` | ✅ |

### Bloco C — Screener e refinamentos

| Feature | Implementação | Status |
|---|---|---|
| **Filtro por PL mínimo** | `screen --pl-min` | ✅ |
| **Export CSV/Excel** | `screen --export`, `dividends --export` | ✅ |
| **Volatilidade da renda** | coluna "Vol. mensal" no sumário de dividendos | ✅ |

### O que NÃO entra no M4 (lacunas estruturais)

| Dado | Motivo de exclusão |
|---|---|
| Taxa de vacância | Não disponível na CVM de forma estruturada — exige parsing de PDF (relatórios gerenciais) |
| Perfil de vencimento de contratos | Idem |
| IFIX retorno total | Fonte B3 paga ou scraping — fora da política de fontes primárias |
| Dividendos efetivamente pagos vs provisionados | CVM reporta intenção, não confirmação — exigiria dados de corretoras |

---

## Arquitetura atual

```
brick-by-brick/
├── src/
│   ├── collectors/
│   │   ├── cvm_cadastro.py      # Cadastro de FIIs — cad_fi.csv
│   │   ├── cvm_inf_mensal.py    # Informe mensal — DY, VPA, PL, composição
│   │   ├── cvm_inf_diario.py    # Informe diário (coletado, não usado em produção)
│   │   ├── b3_cotahist.py       # Preços históricos — COTAHIST
│   │   └── bcb_series.py        # Benchmarks — SELIC, CDI, IPCA
│   ├── storage/
│   │   └── database.py          # Schema SQLite, upserts, migrations
│   ├── analysis/
│   │   ├── indicadores.py       # P/VP, DY 12m, spread vs SELIC, consistência
│   │   └── screener.py          # Score ponderado e filtros
│   └── portfolio/
│       ├── carteira.py          # Posições, movimentações, histórico de dividendos
│       ├── relatorio.py         # Relatórios no terminal (rich)
│       ├── alertas.py           # Alertas de carteira e oportunidades
│       └── grupamentos.py       # Detecção e correção de splits/reverse splits
├── data/
│   └── brickbybrick.sqlite      # Banco local — gitignored
├── main.py                      # CLI entry point (Typer)
├── requirements.txt
├── ROADMAP.md
├── USAGE.md
└── business_analysis.md         # Análise de negócio e gaps identificados
```

**Schema SQLite atual:**

| Tabela | Conteúdo |
|---|---|
| `fiis` | Cadastro: CNPJ, ticker, ISIN, nome, segmento, gestor, taxa_adm |
| `isin_ticker` | Mapeamento ISIN → ticker (ponte CVM↔B3) |
| `cotacoes` | Preços diários B3: abertura, máxima, mínima, fechamento, volume |
| `cota_oficial` | VL_QUOTA diário CVM (informe diário) |
| `inf_mensal` | DY, VPA, PL, cotas, cotistas, composição de ativos (mensal CVM) |
| `benchmarks` | SELIC, CDI, IPCA mensais (BCB) |
| `carteira` | Posições ativas/encerradas: cotas, preço médio, data_entrada |
| `movimentacoes` | Histórico de compras e vendas |
| `grupamentos` | Eventos de split/reverse split confirmados pelo usuário |
| `watchlist` | FIIs monitorados: ticker, preço-alvo, observação |

---

## Princípio fundamental

> **Usar apenas fontes primárias, públicas e gratuitas.**  
> CVM, B3 e BCB disponibilizam todos os dados via `requests.get()` simples, sem autenticação, sem risco de descontinuação por terceiros.

---

## Fontes de dados

### CVM — Portal de Dados Abertos

| Dataset | URL | Frequência |
|---|---|---|
| Cadastro de FIIs | `dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv` | Ter–Sáb |
| Informe Mensal FII | `dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ANO}.zip` | Semanal |
| Informe Trimestral FII | `dados.cvm.gov.br/dados/FII/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fii_{ANO}.zip` | Semanal |
| Informe Diário (todos FI) | `dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{YYYYMM}.zip` | Diária |

### B3 — COTAHIST

```
https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ANO}.ZIP
```

Arquivo de largura fixa. Filtrar `CODBDI == "12"` para FIIs. Campos: ticker (CODNEG), ISIN (CODISI), preços OHLC (÷100), volume (VOLTOT), negócios (TOTNEG).

### BCB — API SGS

| Código | Série |
|---|---|
| 4390 | SELIC acumulada no mês (%) |
| 12 | CDI diário |
| 433 | IPCA variação mensal (%) |

### FundosNet (CVM/B3) — Documentos

```
GET https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados
  ?f[tipoFundo]=FII&f[ultimosNDias]=30&l=50
```

Retorna JSON com links para PDFs (relatórios de gestão, fatos relevantes, prospectos). Sem autenticação. Fora do escopo atual — candidato a M5.

---

## Stack tecnológica

```
requests      # HTTP — CVM, B3, BCB
pandas        # DataFrames e parsing de CSV/ZIP
numpy         # Cálculos numéricos
sqlite3       # Banco local (stdlib)
typer         # CLI com subcomandos e --help automático
rich          # Tabelas coloridas no terminal
schedule      # Scheduler embutido
openpyxl      # Template e importação Excel
```

> Sem Plotly, sem Jupyter, sem Parquet, sem frontend. Tudo roda no terminal.

---

## Referências

| Recurso | URL |
|---|---|
| CVM — Portal de dados abertos | https://dados.cvm.gov.br |
| CVM — Informe Mensal FII | https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal |
| B3 — Séries históricas | https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/series-historicas/ |
| BCB — API SGS | https://api.bcb.gov.br/dados/serie/bcdata.sgs.{SERIE}/dados?formato=json |
| FundosNet — Documentos | https://fnet.bmfbovespa.com.br/fnet/publico/abrirGerenciadorDocumentosCVM |
