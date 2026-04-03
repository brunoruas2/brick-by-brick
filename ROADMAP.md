# Roadmap: Sistema de Análise de Fundos Imobiliários (FIIs) em Python

## Princípio fundamental

> **Usar apenas fontes primárias, públicas e gratuitas.**
> Todas as fontes abaixo são disponibilizadas pelos próprios órgãos reguladores (CVM, B3, BCB, IBGE) e acessíveis via `requests.get()` simples, sem autenticação, sem risco de descontinuação por terceiros.

---

## Fontes primárias disponíveis

### CVM — Portal de Dados Abertos (`dados.cvm.gov.br`)

A CVM é a fonte mais rica. Todos os arquivos são CSV/ZIP baixáveis diretamente.

| Dataset | URL | Formato | Atualização |
|---|---|---|---|
| **Cadastro de FIIs** | `https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv` | CSV | Ter–Sáb |
| **Informe Mensal FII** | `https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ANO}.zip` | ZIP/CSV | Semanal |
| **Informe Trimestral FII** | `https://dados.cvm.gov.br/dados/FII/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fii_{ANO}.zip` | ZIP/CSV | Semanal |
| **Demonstrações Financeiras** | `https://dados.cvm.gov.br/dados/FII/DOC/DFIN/DADOS/dfin_fii_{ANO}.csv` | CSV | Semanal |
| **Informe Diário (todos FI)** | `https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{YYYYMM}.zip` | ZIP/CSV | Diária |
| **Medidas FIE (PL + cotistas)** | `https://dados.cvm.gov.br/dados/FIE/MEDIDAS/DADOS/medidas_mes_fie_{YYYYMM}.csv` | CSV | Semanal |

**O que cada arquivo contém:**

`inf_mensal_fii_{ANO}.zip` — 3 CSVs dentro:
- `_geral_`: Nome, CNPJ, ISIN, segmento, administrador, tipo de gestão, prazo
- `_complemento_`: **DY do mês, rentabilidade efetiva, rentabilidade patrimonial**, PL, cotas emitidas, VPA, número de cotistas, taxas de administração
- `_ativo_passivo_`: Composição do portfólio — CRIs, LCIs, imóveis por tipo (renda, venda, construção), contas a receber de aluguel, **rendimentos a distribuir**

`inf_diario_fi_{YYYYMM}.zip`:
- `VL_QUOTA` — valor da cota (NAV oficial do fundo, base para calcular P/VP)
- `VL_PATRIM_LIQ` — patrimônio líquido diário
- `NR_COTST` — número de cotistas
- `CAPTAC_DIA`, `RESG_DIA` — fluxo de entrada/saída

`cad_fi.csv` — Filtrar por `TP_FUNDO == "FII"`:
- CNPJ, nome, situação, classe ANBIMA, gestor, administrador, custodiante, auditor
- Taxa de administração, taxa de performance, PL
- Data de início, data de cancelamento

---

### B3 — Séries Históricas de Cotações (COTAHIST)

Preços de mercado diários desde 1986. Arquivo de largura fixa, sem autenticação.

```
https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ANO}.ZIP
```

Exemplos:
```
https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2023.ZIP
https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2024.ZIP
https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2025.ZIP
```

**Como identificar FIIs no arquivo:** filtrar `CODBDI == "12"` (código BDI para Fundos Imobiliários).

**Campos disponíveis por linha:**

| Campo | Posição | Descrição |
|---|---|---|
| `CODBDI` | 11–12 | `"12"` = FII |
| `CODNEG` | 13–24 | Ticker (ex: `HGLG11`) |
| `NOMRES` | 28–39 | Nome resumido |
| `PREABE` | 57–69 | Preço de abertura (÷100) |
| `PREMAX` | 70–82 | Preço máximo (÷100) |
| `PREMIN` | 83–95 | Preço mínimo (÷100) |
| `PREMED` | 96–108 | Preço médio (÷100) |
| `PREULT` | 109–121 | Preço de fechamento (÷100) |
| `TOTNEG` | 148–152 | Número de negócios |
| `QUATOT` | 153–170 | Quantidade total negociada |
| `VOLTOT` | 171–188 | Volume financeiro (÷100) |
| `CODISI` | 231–242 | Código ISIN |

Layout oficial: `https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf`

---

### BCB — API SGS (benchmarks de rentabilidade)

```
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{CODIGO}/dados?formato=json
```

| Código | Série | Uso no projeto |
|---|---|---|
| **11** | Taxa SELIC diária (% a.d.) | Benchmark diário |
| **12** | Taxa CDI diária (% a.d.) | Benchmark diário |
| **433** | IPCA variação mensal (%) | Correção inflacionária |
| **4390** | SELIC acumulada no mês (%) | Benchmark mensal simples |

Todos sem autenticação. Janela máxima por consulta: 10 anos.

---

### IBGE — IPCA via API SIDRA

```
https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/{YYYYMM}/variaveis/63?localidades=N1[all]
```

Retorna variação mensal do IPCA em JSON, sem autenticação.

---

### FundosNet (CVM/B3) — Documentos dos fundos

Acesso a relatórios de gestão, AGO/AGE, fatos relevantes, prospectos:

```
# Pesquisa de documentos recentes
GET https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados
  ?f[tipoFundo]=FII&f[ultimosNDias]=30&l=50

# Download de documento por ID
GET https://fnet.bmfbovespa.com.br/fnet/publico/downloadDocumento?id={ID}
```

Retorna JSON com metadados e link para PDF. Sem autenticação.

---

## O que cada fonte nos dá

| Indicador | Fonte primária | Campo exato |
|---|---|---|
| Lista de todos os FIIs | CVM `cad_fi.csv` | `TP_FUNDO == "FII"` |
| CNPJ ↔ Ticker | CVM `cad_fi.csv` + B3 COTAHIST | Cruzar CNPJ com CODNEG |
| Preço de mercado (histórico) | B3 COTAHIST | `PREULT` |
| Volume e liquidez diária | B3 COTAHIST | `VOLTOT`, `TOTNEG` |
| Valor da cota (NAV oficial) | CVM Informe Diário | `VL_QUOTA` |
| **P/VP** (calculado) | B3 ÷ CVM | `PREULT` / `VL_QUOTA` |
| Patrimônio Líquido | CVM Informe Diário / Mensal | `VL_PATRIM_LIQ` |
| Número de cotistas | CVM Informe Diário / Mensal | `NR_COTST` |
| **DY do mês** | CVM Informe Mensal `_complemento_` | `Percentual_Dividend_Yield_Mes` |
| Rentabilidade efetiva do mês | CVM Informe Mensal `_complemento_` | `Percentual_Rentabilidade_Efetiva_Mes` |
| Rendimentos a distribuir | CVM Informe Mensal `_ativo_passivo_` | `Rendimentos_Distribuir` |
| Composição (CRI, LCI, imóveis) | CVM Informe Mensal `_ativo_passivo_` | Várias colunas de ativos |
| Contas a receber de aluguel | CVM Informe Mensal `_ativo_passivo_` | `Contas_Receber_Aluguel` |
| Taxa de administração | CVM Informe Mensal `_complemento_` | `Percentual_Despesas_Taxa_Administracao` |
| Segmento / tipo de mandato | CVM Informe Mensal `_geral_` | `Segmento_Atuacao`, `Mandato` |
| Gestor e administrador | CVM `cad_fi.csv` | `GESTOR`, `ADMIN` |
| SELIC / CDI (benchmark) | BCB SGS | Séries 11, 12, 4390 |
| IPCA (benchmark) | BCB SGS / IBGE SIDRA | Série 433 |
| Relatórios de gestão (PDF) | FundosNet | `/downloadDocumento?id=` |

> **Nota sobre vacância:** O informe mensal não tem um campo direto de "taxa de vacância". Ela pode ser inferida a partir de `Contas_Receber_Aluguel` e `Imoveis_Renda_Acabados` vs `Total_Ativo`, ou extraída dos relatórios de gestão mensais via FundosNet (PDF). Esta será a única informação que exigirá parsing de PDF.

---

## Arquitetura do Projeto

```
fii_analyzer/
├── src/
│   ├── collectors/
│   │   ├── cvm_cadastro.py         # cad_fi.csv — lista e cadastro de todos os FIIs
│   │   ├── cvm_inf_mensal.py       # Informe mensal — DY, PL, rentabilidade, ativos
│   │   ├── cvm_inf_diario.py       # Informe diário — VL_QUOTA e PL diários
│   │   ├── b3_cotahist.py          # COTAHIST — preço de mercado histórico
│   │   ├── bcb_series.py           # API BCB — SELIC, CDI, IPCA
│   │   └── fundosnet.py            # Documentos dos fundos (PDF)
│   ├── storage/
│   │   └── database.py             # SQLite + Parquet
│   ├── analysis/
│   │   ├── indicadores.py          # Calcular P/VP, DY acumulado, liquidez média
│   │   ├── screener.py             # Filtros e ranking
│   │   └── comparador.py           # Comparação entre FIIs
│   ├── portfolio/
│   │   ├── carteira.py             # Gestão de posições
│   │   └── relatorio_mensal.py     # Relatório mensal
│   ├── reports/
│   │   └── dashboard.py            # Gráficos e visualizações (Plotly)
│   └── alerts/
│       └── monitor.py              # Alertas automáticos
├── data/                           # Dados locais (no .gitignore)
│   ├── raw/                        # Arquivos brutos baixados (ZIP, CSV)
│   ├── processed/                  # Dados processados (Parquet)
│   └── database.sqlite             # Banco relacional
├── notebooks/                      # Jupyter para exploração
├── config.yaml                     # Configurações gerais
├── carteira.json                   # Carteira do usuário
└── main.py                         # CLI principal
```

---

## Fases de Implementação

### Fase 1 — Coleta de dados primários
**Status:** `[ ] Pendente`

**Objetivo:** Baixar dados diretamente das fontes oficiais (CVM e B3), sem intermediários.

`src/collectors/cvm_cadastro.py`
- Baixar `cad_fi.csv` da CVM
- Filtrar apenas `TP_FUNDO == "FII"`
- Retorna DataFrame com CNPJ, nome, situação, gestor, administrador, taxas

`src/collectors/cvm_inf_mensal.py`
- Baixar ZIP do informe mensal por ano: `inf_mensal_fii_{ANO}.zip`
- Extrair os 3 CSVs: `_geral_`, `_complemento_`, `_ativo_passivo_`
- Campos-chave: DY do mês, rentabilidade efetiva, PL, VPA, cotistas, taxas, composição dos ativos

`src/collectors/cvm_inf_diario.py`
- Baixar ZIP mensal: `inf_diario_fi_{YYYYMM}.zip`
- Filtrar apenas CNPJs de FIIs (cruzar com cadastro)
- Campos: `VL_QUOTA` (NAV), `VL_PATRIM_LIQ`, `NR_COTST`

`src/collectors/b3_cotahist.py`
- Baixar `COTAHIST_A{ANO}.ZIP` da B3
- Parsear arquivo de largura fixa (245 bytes/linha)
- Filtrar `CODBDI == "12"` para FIIs
- Extrair: ticker, data, abertura, máxima, mínima, fechamento, volume, negócios

`src/collectors/bcb_series.py`
- Buscar SELIC (série 4390), CDI (série 12) e IPCA (série 433) via API BCB
- Armazenar histórico mensal para benchmark de rentabilidade

**Entregável:** Pipeline de ingestão que baixa e estrutura todos os dados brutos.

---

### Fase 2 — Armazenamento
**Status:** `[ ] Pendente`

**Objetivo:** Persistir os dados de forma eficiente para consultas históricas.

**Estrutura do banco SQLite:**

```sql
-- Cadastro dos fundos
CREATE TABLE fiis (
    cnpj TEXT PRIMARY KEY,
    ticker TEXT,
    nome TEXT,
    situacao TEXT,
    segmento TEXT,
    mandato TEXT,
    gestor TEXT,
    administrador TEXT,
    taxa_adm REAL,
    data_inicio DATE,
    atualizado_em TIMESTAMP
);

-- Preço de mercado diário (B3 COTAHIST)
CREATE TABLE cotacoes (
    ticker TEXT,
    data DATE,
    abertura REAL,
    maxima REAL,
    minima REAL,
    fechamento REAL,
    volume REAL,
    negocios INTEGER,
    PRIMARY KEY (ticker, data)
);

-- Valor da cota oficial diário (CVM Informe Diário)
CREATE TABLE cota_oficial (
    cnpj TEXT,
    data DATE,
    vl_quota REAL,
    vl_patrimonio_liquido REAL,
    nr_cotistas INTEGER,
    PRIMARY KEY (cnpj, data)
);

-- Informe mensal consolidado
CREATE TABLE inf_mensal (
    cnpj TEXT,
    data_referencia DATE,
    dy_mes REAL,
    rentabilidade_efetiva_mes REAL,
    rentabilidade_patrimonial_mes REAL,
    patrimonio_liquido REAL,
    cotas_emitidas REAL,
    valor_patrimonial_cota REAL,  -- VPA
    nr_cotistas INTEGER,
    taxa_adm REAL,
    rendimentos_a_distribuir REAL,
    imoveis_renda REAL,
    cri REAL,
    lci REAL,
    contas_receber_aluguel REAL,
    PRIMARY KEY (cnpj, data_referencia)
);

-- Benchmarks mensais
CREATE TABLE benchmarks (
    data DATE PRIMARY KEY,
    selic_mes REAL,
    cdi_mes REAL,
    ipca_mes REAL
);

-- Carteira do usuário
CREATE TABLE carteira (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    cnpj TEXT,
    cotas INTEGER,
    preco_medio REAL,
    data_entrada DATE,
    ativa BOOLEAN DEFAULT 1
);

-- Movimentações
CREATE TABLE movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    tipo TEXT,  -- 'compra', 'venda', 'provento'
    data DATE,
    quantidade INTEGER,
    preco_unitario REAL,
    valor_total REAL
);
```

**Entregável:** Banco SQLite populado + arquivos Parquet em `data/processed/`.

---

### Fase 3 — Cálculo de indicadores
**Status:** `[ ] Pendente`

**Objetivo:** Derivar os indicadores analíticos a partir dos dados brutos.

`src/analysis/indicadores.py`

Indicadores calculados (não coletados prontos):

```python
# P/VP = preço de mercado (B3) / valor patrimonial da cota (CVM)
p_vp = cotacao_fechamento / valor_patrimonial_cota

# DY acumulado 12 meses = soma dos DY mensais dos últimos 12 meses
dy_12m = df_inf_mensal["dy_mes"].tail(12).sum()

# Liquidez média 30 dias
liquidez_30d = df_cotacoes["volume"].tail(30).mean()

# Yield on Cost (para carteira) = DY / preço médio de compra
yield_on_cost = provento_mensal / preco_medio_compra * 12

# Spread sobre SELIC = DY 12m - SELIC 12m acumulada
spread_selic = dy_12m - selic_acumulada_12m

# Consistência de proventos = desvio padrão dos DY mensais (quanto menor, mais estável)
consistencia = df_inf_mensal["dy_mes"].tail(12).std()
```

**Entregável:** Módulo de indicadores com todos os cálculos documentados e testados.

---

### Fase 4 — Screener e análise
**Status:** `[ ] Pendente`

**Objetivo:** Filtrar e rankear FIIs com base em critérios configuráveis.

`src/analysis/screener.py`

Filtros disponíveis:
- DY 12m mínimo (ex: > 8%)
- P/VP máximo (ex: < 1.10)
- Liquidez mínima 30d (ex: > R$ 500k)
- Spread sobre SELIC mínimo (ex: > 2%)
- Segmento / mandato
- Situação cadastral ativa

Score ponderado (configurável em `config.yaml`):
```yaml
screener:
  pesos:
    dy_12m: 0.30
    spread_selic: 0.25
    p_vp: 0.20
    liquidez: 0.15
    consistencia_proventos: 0.10
```

`src/analysis/comparador.py`
- Comparar dois ou mais FIIs lado a lado
- Evolução histórica de DY mensal e P/VP
- Rentabilidade acumulada vs SELIC e IPCA

**Entregável:** CLI com ranking de FIIs por score e comparativo entre fundos.

---

### Fase 5 — Gestão da carteira
**Status:** `[ ] Pendente`

**Objetivo:** Registrar operações e calcular rentabilidade real da carteira.

`src/portfolio/carteira.py`
- Registrar compras/vendas na tabela `movimentacoes`
- Calcular posição atual: cotas, preço médio, custo total
- Proventos recebidos por ativo (DY do mês × cotas × preço médio)
- P&L de capital: (preço atual − preço médio) × cotas
- Rentabilidade total: (P&L capital + proventos) / custo total

`src/portfolio/relatorio_mensal.py`
- Snapshot mensal: valor da carteira, proventos do mês, rentabilidade
- Comparativo com SELIC e IPCA do mesmo período
- Evolução histórica mês a mês

**Entregável:** Sistema de controle de carteira com histórico de rentabilidade real.

---

### Fase 6 — Dashboard e relatórios
**Status:** `[ ] Pendente`

**Objetivo:** Visualizações interativas e relatório HTML mensal.

`src/reports/dashboard.py` (Plotly)

Gráficos:
- Evolução do patrimônio da carteira vs SELIC+IPCA
- Dividendos recebidos por mês (barras empilhadas por FII)
- Distribuição por segmento (pizza)
- Heatmap de DY mensal por ativo (últimos 12 meses)
- P/VP histórico de cada ativo com linha de compra marcada
- Yield on Cost por ativo

Relatório HTML mensal (via Jinja2):
- Resumo executivo
- Tabela de indicadores atuais da carteira
- Alertas automáticos: queda de DY, P/VP acima de 1.15, spread negativo vs SELIC

**Entregável:** Dashboard interativo + relatório HTML gerado todo dia 10 do mês.

---

### Fase 7 — Automação
**Status:** `[ ] Pendente`

**Objetivo:** Coleta e relatórios automáticos sem intervenção manual.

Agenda de coleta:
- **Diária** (após 20h): COTAHIST do dia corrente, informe diário CVM
- **Semanal** (domingo): Informe mensal CVM, cadastro de FIIs
- **Mensal** (dia 10): Benchmarks BCB/IBGE, geração do relatório mensal

Alertas (via Telegram Bot ou e-mail):
- FII da carteira com DY abaixo da média histórica
- Novo fundo com score alto no screener
- P/VP de ativo da carteira cruzou limiar configurado

**Entregável:** Processo agendado com notificações automáticas.

---

## Stack tecnológica

```
# Coleta de dados — apenas fontes primárias
requests          # HTTP para CVM, B3, BCB, IBGE, FundosNet
zipfile + io      # Extrair ZIPs em memória

# Processamento
pandas            # Manipulação de DataFrames e leitura de CSV
numpy             # Cálculos numéricos

# Armazenamento
sqlite3           # Banco relacional local (sem dependência externa)
pyarrow           # Arquivos Parquet para séries temporais longas

# Visualização
plotly            # Dashboard interativo

# Relatórios
jinja2            # Templates HTML

# Alertas
smtplib           # E-mail (nativo Python)
python-telegram-bot  # Telegram

# Agendamento
schedule          # Agendador simples em Python
```

---

## Sequência de implementação

| Etapa | Fase | Status |
|---|---|---|
| 1 | Fase 1 — Coleta CVM (cadastro + inf. mensal + inf. diário) + B3 COTAHIST + BCB | `[ ] Pendente` |
| 2 | Fase 2 — Banco SQLite com todas as tabelas | `[ ] Pendente` |
| 3 | Fase 3 — Cálculo de indicadores (P/VP, DY 12m, liquidez, spread) | `[ ] Pendente` |
| 4 | Fase 4 — Screener com filtros e score ponderado | `[ ] Pendente` |
| 5 | Fase 5 — Gestão de carteira + rentabilidade real | `[ ] Pendente` |
| 6 | Fase 6 — Dashboard Plotly + relatório HTML mensal | `[ ] Pendente` |
| 7 | Fase 7 — Automação + alertas Telegram | `[ ] Pendente` |

---

## Referências oficiais

| Recurso | URL |
|---|---|
| CVM — Portal de dados abertos | https://dados.cvm.gov.br |
| CVM — Cadastro de fundos | https://dados.cvm.gov.br/dataset/fi-cad |
| CVM — Informe Mensal FII | https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal |
| CVM — Informe Trimestral FII | https://dados.cvm.gov.br/dataset/fii-doc-inf_trimestral |
| CVM — Informe Diário | https://dados.cvm.gov.br/dataset/fi-doc-inf_diario |
| B3 — Séries históricas | https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/series-historicas/ |
| B3 — Layout COTAHIST (PDF) | https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf |
| BCB — API SGS | https://api.bcb.gov.br/dados/serie/bcdata.sgs.{SERIE}/dados?formato=json |
| BCB — Dados abertos | https://dadosabertos.bcb.gov.br |
| IBGE — API SIDRA | https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/{MES}/variaveis/63 |
| FundosNet — Documentos | https://fnet.bmfbovespa.com.br/fnet/publico/abrirGerenciadorDocumentosCVM |
