<div align="center">

<img src="logo.png" alt="Brickie — your FII analyst" width="340"/>

# 🧱 Brick by Brick

### *"Tijolo por tijolo, construindo riqueza."*

**A Python toolkit for analyzing and tracking Brazilian Real Estate Investment Funds (FIIs) — using only primary, public, and free data sources.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Data Sources](https://img.shields.io/badge/Data-CVM%20%7C%20B3%20%7C%20BCB%20%7C%20IBGE-orange?style=flat-square)](ROADMAP.md)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow?style=flat-square)]()

🇧🇷 [Leia em Português](README.pt-br.md)

</div>

---

## What is Brick by Brick?

**Brick by Brick** is a Python project for collecting, analyzing, and tracking Brazilian Real Estate Investment Funds (FIIs). The name is a pun on "Tijolo por Tijolo" — the Portuguese term for real-estate-backed FIIs — and reflects the philosophy of building a solid investment portfolio one brick (one FII) at a time.

The project is built on a single principle: **no third-party scrapers, no paid APIs, no fragile dependencies**. Every data point comes directly from official government sources that are legally required to publish this information — and always will be.

---

## Meet Brickie 🧱

<img src="logo.png" alt="Brickie — your FII analyst" width="260"/>

**Brickie** is your no-nonsense FII analyst. He reads official CVM filings, crunches B3 price data, checks the BCB benchmark rates, and tells you which bricks are worth adding to your portfolio — and which ones have cracks.

---

## Why only primary sources?

Sites like Fundamentus, Status Invest, and Funds Explorer are great products — but they are third-party businesses. They can change their HTML, add CAPTCHAs, block scrapers, go offline, or simply shut down. Our data pipeline would break with them.

Everything we need is already publicly available from the official regulators:

| Source | What we get | URL |
|--------|-------------|-----|
| **CVM** | FII registry, monthly reports (DY, P/VP, PL, composition), daily NAV | `dados.cvm.gov.br` |
| **B3** | Historical market prices (COTAHIST) — all FIIs since 1986 | `bvmf.bmfbovespa.com.br` |
| **BCB** | SELIC, CDI, IPCA time series (benchmark) | `api.bcb.gov.br` |
| **IBGE** | IPCA monthly variation | `servicodados.ibge.gov.br` |
| **FundosNet** | Management reports, AGO/AGE documents (PDF) | `fnet.bmfbovespa.com.br` |

All of these are `requests.get()` calls — no authentication, no rate-limit tricks, no scraping.

---

## What indicators are collected

| Indicator | Source | Notes |
|-----------|--------|-------|
| Monthly DY | CVM Informe Mensal | Direct field `Percentual_Dividend_Yield_Mes` |
| Effective monthly return | CVM Informe Mensal | Direct field `Percentual_Rentabilidade_Efetiva_Mes` |
| Net Asset Value (NAV / VPA) | CVM Informe Mensal | Direct field `Valor_Patrimonial_Cotas` |
| Market price | B3 COTAHIST | `PREULT`, filter `CODBDI == "12"` |
| **P/VP (calculated)** | B3 ÷ CVM | Market price / NAV — computed here, not fetched |
| **12-month DY (calculated)** | CVM | Sum of 12 monthly DY fields |
| Daily liquidity | B3 COTAHIST | `VOLTOT`, 30-day average |
| Net equity (PL) | CVM Informe Diário | `VL_PATRIM_LIQ` |
| Number of shareholders | CVM Informe Mensal | `Total_Numero_Cotistas` |
| Admin & management fees | CVM Informe Mensal | `Percentual_Despesas_Taxa_Administracao` |
| Portfolio composition | CVM Informe Mensal | CRI, LCI, real estate by type |
| SELIC / CDI / IPCA | BCB + IBGE | Benchmark for return comparison |

---

## Project Roadmap

The project is structured in 7 phases. See [ROADMAP.md](ROADMAP.md) for full details.

```
Phase 1 — Data collection (CVM + B3 + BCB)       [ ] Pending
Phase 2 — Storage (SQLite + Parquet)              [ ] Pending
Phase 3 — Indicator calculation                   [ ] Pending
Phase 4 — Screener & ranking                      [ ] Pending
Phase 5 — Portfolio management                    [ ] Pending
Phase 6 — Dashboard & reports                     [ ] Pending
Phase 7 — Automation & alerts                     [ ] Pending
```

---

## Architecture

```
brick-by-brick/
├── src/
│   ├── collectors/
│   │   ├── cvm_cadastro.py       # FII registry — cad_fi.csv
│   │   ├── cvm_inf_mensal.py     # Monthly reports — DY, PL, composition
│   │   ├── cvm_inf_diario.py     # Daily NAV and equity
│   │   ├── b3_cotahist.py        # Historical market prices
│   │   ├── bcb_series.py         # SELIC, CDI, IPCA
│   │   └── fundosnet.py          # Management report PDFs
│   ├── storage/
│   │   └── database.py           # SQLite + Parquet
│   ├── analysis/
│   │   ├── indicadores.py        # P/VP, DY 12m, spread vs SELIC
│   │   ├── screener.py           # Filter and rank FIIs
│   │   └── comparador.py         # Side-by-side FII comparison
│   ├── portfolio/
│   │   ├── carteira.py           # Position management
│   │   └── relatorio_mensal.py   # Monthly portfolio report
│   ├── reports/
│   │   └── dashboard.py          # Plotly interactive dashboard
│   └── alerts/
│       └── monitor.py            # Telegram / email alerts
├── data/                         # Local data (gitignored)
├── notebooks/                    # Jupyter exploration
├── config.yaml                   # Settings
├── carteira.json                 # Your portfolio
├── ROADMAP.md                    # Full project plan
└── main.py                       # CLI entry point
```

---

## Stack

```python
# Data collection — primary sources only
requests          # HTTP: CVM, B3, BCB, IBGE, FundosNet
zipfile + io      # In-memory ZIP extraction

# Processing
pandas            # DataFrames and CSV reading
numpy             # Numerical calculations

# Storage
sqlite3           # Local relational database
pyarrow           # Parquet for long time series

# Visualization
plotly            # Interactive dashboard

# Reports
jinja2            # HTML templates

# Alerts
python-telegram-bot  # Telegram notifications
smtplib           # Email (stdlib)

# Scheduling
schedule          # Lightweight job scheduler
```

---

## Getting Started

> Setup instructions will be added when Phase 1 is complete.

```bash
git clone https://github.com/brunoruas2/brick-by-brick.git
cd brick-by-brick
pip install -r requirements.txt
python main.py
```

---

## Contributing

This project is in early development. The roadmap is public and contributions are welcome once the core pipeline is stable. Open an issue to discuss ideas.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

*"O mercado pode ser irracional por mais tempo do que você pode permanecer solvente — então analise os tijolos antes de comprar."*

**🧱 Brick by Brick — build wealth, one FII at a time.**

</div>
