<div align="center">

<img src="logo.png" alt="Brickie — seu analista de FIIs" width="340"/>

# Brick by Brick

### *"Tijolo por tijolo, construindo riqueza."*

**Um CLI em Python para analisar e acompanhar Fundos de Investimento Imobiliário (FIIs) — usando apenas fontes de dados primárias, públicas e gratuitas.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/Licença-MIT-green?style=flat-square)](LICENSE)
[![Data Sources](https://img.shields.io/badge/Dados-CVM%20%7C%20B3%20%7C%20BCB-orange?style=flat-square)](ROADMAP.md)
[![Status](https://img.shields.io/badge/M1%20M2%20M3-Concluídos-brightgreen?style=flat-square)]()

🇺🇸 [Read in English](README.md)

</div>

---

## O que é o Brick by Brick?

**Brick by Brick** é um CLI em Python para coletar, analisar e acompanhar Fundos de Investimento Imobiliário (FIIs) do Brasil. O nome é um trocadilho com "Tijolo por Tijolo" — termo carinhoso para os FIIs de imóveis físicos — e reflete a filosofia de construir uma carteira sólida um tijolo de cada vez.

O projeto é construído sobre um único princípio: **sem scrapers de terceiros, sem APIs pagas, sem dependências frágeis**. Cada dado vem diretamente de fontes governamentais oficiais que são legalmente obrigadas a publicar essas informações.

---

## Conheça o Brickie

<img src="logo.png" alt="Brickie — seu analista de FIIs" width="220"/>

**Brickie** é o seu analista de FIIs sem rodeios. Ele lê os informes oficiais da CVM, processa os dados de preço da B3, confere as taxas de referência do BCB e te diz quais tijolos valem a pena adicionar na sua carteira — e quais têm rachaduras.

---

## Como usar

Veja o **[USAGE.md](USAGE.md)** para o guia completo de uso, incluindo:

- Instalação e primeira execução
- Descobrir FIIs com o screener
- Pesquisar um FII com `info` e `compare`
- Montar e acompanhar sua carteira
- Configurar alertas automáticos e atualização agendada

**Início rápido:**

```bash
pip install -r requirements.txt

# 1. Baixa todos os dados (CVM + B3 + BCB) — ~5 min, ~200 MB
python main.py update

# 2. Roda o screener
python main.py screen --dy-min 9 --pvp-max 1.05

# 3. Pesquisa um FII
python main.py info HGLG11

# 4. Monte sua carteira — manualmente ou via importação Excel
python main.py portfolio add HGLG11 100 165.50 2024-06-15
python main.py portfolio template              # gera carteira_template.xlsx
python main.py portfolio import carteira.xlsx  # importa em lote do Excel
python main.py portfolio report
```

---

## Por que apenas fontes primárias?

Sites como Fundamentus, Status Invest e Funds Explorer são ótimos produtos — mas são empresas terceiras. Eles podem mudar o HTML, adicionar CAPTCHAs, bloquear scrapers, ficar offline ou simplesmente fechar. Nossa pipeline de dados quebraria junto com eles.

Tudo que precisamos já está disponível publicamente pelos próprios reguladores:

| Fonte | O que coletamos | URL |
|-------|----------------|-----|
| **CVM** | Cadastro de FIIs, informes mensais (DY, VPA, PL, composição) | `dados.cvm.gov.br` |
| **B3** | Preços históricos diários (COTAHIST) — todos os FIIs desde 1986 | `bvmf.bmfbovespa.com.br` |
| **BCB** | Séries temporais SELIC, CDI, IPCA (benchmark) | `api.bcb.gov.br` |

Todos são chamadas `requests.get()` simples — sem autenticação, sem rate-limit, sem scraping.

---

## Indicadores

| Indicador | Fonte | Observação |
|-----------|-------|------------|
| DY mensal | CVM Informe Mensal | `Percentual_Dividend_Yield_Mes` |
| VPA (valor patrimonial da cota) | CVM Informe Mensal | `Valor_Patrimonial_Cotas` |
| Preço de mercado | B3 COTAHIST | `PREULT`, filtro `CODBDI == "12"` |
| **P/VP** | B3 ÷ CVM | Preço / VPA — calculado, não coletado |
| **DY 12 meses** | CVM | Soma dos 12 DY mensais |
| **Spread vs SELIC** | CVM + BCB | DY 12m − SELIC acumulada 12m |
| Liquidez (média 30d) | B3 COTAHIST | Média do `VOLTOT` em 30 dias |
| Consistência de DY | CVM | Desvio padrão do DY mensal — menor = mais estável |
| Taxa de administração | CVM Informe Mensal | `Percentual_Despesas_Taxa_Administracao` |
| Composição do portfólio | CVM Informe Mensal | CRI, LCI, imóveis por tipo |
| SELIC / CDI / IPCA | BCB SGS | Benchmark para comparação de rentabilidade |

---

## Arquitetura

```
brick-by-brick/
├── src/
│   ├── collectors/
│   │   ├── cvm_cadastro.py      # Cadastro de FIIs — cad_fi.csv
│   │   ├── cvm_inf_mensal.py    # Informes mensais — DY, VPA, PL, composição
│   │   ├── b3_cotahist.py       # Preços históricos — COTAHIST
│   │   └── bcb_series.py        # SELIC, CDI, IPCA — BCB API SGS
│   ├── storage/
│   │   └── database.py          # Schema SQLite, upserts, migrations
│   ├── analysis/
│   │   ├── indicadores.py       # P/VP, DY 12m, spread vs SELIC, consistência
│   │   └── screener.py          # Filtros e ranking por score ponderado
│   └── portfolio/
│       ├── carteira.py          # Gestão de posições e P&L
│       ├── relatorio.py         # Relatório mensal da carteira
│       └── alertas.py           # Verificação de alertas e oportunidades
├── data/                        # Dados locais — no .gitignore
│   └── brickbybrick.sqlite      # Banco de dados SQLite
├── main.py                      # CLI principal (Typer)
├── requirements.txt
├── ROADMAP.md                   # Plano de desenvolvimento
└── USAGE.md                     # Guia de uso e referência de comandos
```

---

## Stack

```
requests      # HTTP — CVM, B3, BCB
pandas        # DataFrames e leitura de CSV
numpy         # Cálculos numéricos
sqlite3       # Banco relacional local (stdlib)
typer         # Framework de CLI
rich          # Tabelas e cores no terminal
schedule      # Agendador de tarefas
openpyxl      # Geração e leitura de templates Excel
```

> Sem Plotly, sem Jupyter, sem Parquet, sem Jinja2. Tudo roda no terminal.

---

## Roadmap

| Milestone | Escopo | Status |
|-----------|--------|--------|
| **M1 — Fundação** | Coleta de dados (CVM + B3 + BCB) + storage SQLite | ✅ Concluído |
| **M2 — Análise** | Indicadores, screener, `info`, `compare` | ✅ Concluído |
| **M3 — Carteira** | Gestão de posições, P&L, relatório mensal, alertas, scheduler | ✅ Concluído |
| **M4 — Interface** | GUI (web, desktop ou dashboard) — escopo a definir | ⬜ Futuro |

Veja [ROADMAP.md](ROADMAP.md) para todos os detalhes.

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">

*"O mercado pode ser irracional por mais tempo do que você pode permanecer solvente — então analise os tijolos antes de comprar."*

**Brick by Brick — construa riqueza, um FII de cada vez.**

</div>
