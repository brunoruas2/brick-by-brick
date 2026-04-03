<div align="center">

<img src="logo.png" alt="Brickie — seu analista de FIIs" width="340"/>

# 🧱 Brick by Brick

### *"Tijolo por tijolo, construindo riqueza."*

**Um toolkit em Python para analisar e acompanhar Fundos de Investimento Imobiliário (FIIs) do Brasil — usando apenas fontes de dados primárias, públicas e gratuitas.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/Licença-MIT-green?style=flat-square)](LICENSE)
[![Data Sources](https://img.shields.io/badge/Dados-CVM%20%7C%20B3%20%7C%20BCB%20%7C%20IBGE-orange?style=flat-square)](ROADMAP.md)
[![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow?style=flat-square)]()

🇺🇸 [Read in English](README.md)

</div>

---

## O que é o Brick by Brick?

**Brick by Brick** é um projeto Python para coletar, analisar e acompanhar Fundos de Investimento Imobiliário (FIIs) do Brasil. O nome é um trocadilho com "Tijolo por Tijolo" — termo carinhoso para os FIIs de imóveis físicos — e reflete a filosofia de construir uma carteira sólida um tijolo (um FII) de cada vez.

O projeto é construído sobre um único princípio: **sem scrapers de terceiros, sem APIs pagas, sem dependências frágeis**. Cada dado vem diretamente de fontes governamentais oficiais que são legalmente obrigadas a publicar essas informações — e sempre serão.

---

## Conheça o Brickie 🧱

<img src="logo.png" alt="Brickie — seu analista de FIIs" width="260"/>

**Brickie** é o seu analista de FIIs sem rodeios. Ele lê os informes oficiais da CVM, processa os dados de preço da B3, confere as taxas de referência do BCB e te diz quais tijolos valem a pena adicionar na sua carteira — e quais têm rachaduras.

---

## Por que apenas fontes primárias?

Sites como Fundamentus, Status Invest e Funds Explorer são ótimos produtos — mas são empresas terceiras. Eles podem mudar o HTML, adicionar CAPTCHAs, bloquear scrapers, ficar offline ou simplesmente fechar. Nossa pipeline de dados quebraria junto com eles.

Tudo que precisamos já está disponível publicamente pelos próprios reguladores:

| Fonte | O que coletamos | URL |
|-------|----------------|-----|
| **CVM** | Cadastro de FIIs, informes mensais (DY, P/VP, PL, composição), cota diária | `dados.cvm.gov.br` |
| **B3** | Preços históricos de mercado (COTAHIST) — todos os FIIs desde 1986 | `bvmf.bmfbovespa.com.br` |
| **BCB** | Séries temporais SELIC, CDI, IPCA (benchmark) | `api.bcb.gov.br` |
| **IBGE** | Variação mensal do IPCA | `servicodados.ibge.gov.br` |
| **FundosNet** | Relatórios de gestão, AGO/AGE (PDF) | `fnet.bmfbovespa.com.br` |

Todos são chamadas `requests.get()` — sem autenticação, sem truques de rate-limit, sem scraping.

---

## Quais indicadores são coletados

| Indicador | Fonte | Observação |
|-----------|-------|------------|
| DY mensal | CVM Informe Mensal | Campo direto `Percentual_Dividend_Yield_Mes` |
| Rentabilidade efetiva mensal | CVM Informe Mensal | Campo direto `Percentual_Rentabilidade_Efetiva_Mes` |
| Valor Patrimonial da Cota (VPA) | CVM Informe Mensal | Campo direto `Valor_Patrimonial_Cotas` |
| Preço de mercado | B3 COTAHIST | `PREULT`, filtro `CODBDI == "12"` |
| **P/VP (calculado)** | B3 ÷ CVM | Preço de mercado / VPA — calculado aqui |
| **DY 12 meses (calculado)** | CVM | Soma dos 12 DY mensais |
| Liquidez diária | B3 COTAHIST | `VOLTOT`, média 30 dias |
| Patrimônio Líquido | CVM Informe Diário | `VL_PATRIM_LIQ` |
| Número de cotistas | CVM Informe Mensal | `Total_Numero_Cotistas` |
| Taxas de adm. e gestão | CVM Informe Mensal | `Percentual_Despesas_Taxa_Administracao` |
| Composição do portfólio | CVM Informe Mensal | CRI, LCI, imóveis por tipo |
| SELIC / CDI / IPCA | BCB + IBGE | Benchmark para comparação de rentabilidade |

---

## Roadmap do Projeto

O projeto está estruturado em 7 fases. Veja [ROADMAP.md](ROADMAP.md) para todos os detalhes.

```
Fase 1 — Coleta de dados (CVM + B3 + BCB)        [ ] Pendente
Fase 2 — Armazenamento (SQLite + Parquet)         [ ] Pendente
Fase 3 — Cálculo de indicadores                   [ ] Pendente
Fase 4 — Screener e ranking                       [ ] Pendente
Fase 5 — Gestão de carteira                       [ ] Pendente
Fase 6 — Dashboard e relatórios                   [ ] Pendente
Fase 7 — Automação e alertas                      [ ] Pendente
```

---

## Arquitetura

```
brick-by-brick/
├── src/
│   ├── collectors/
│   │   ├── cvm_cadastro.py       # Cadastro de FIIs — cad_fi.csv
│   │   ├── cvm_inf_mensal.py     # Informes mensais — DY, PL, composição
│   │   ├── cvm_inf_diario.py     # Cota diária e patrimônio
│   │   ├── b3_cotahist.py        # Preços históricos de mercado
│   │   ├── bcb_series.py         # SELIC, CDI, IPCA
│   │   └── fundosnet.py          # PDFs de relatórios de gestão
│   ├── storage/
│   │   └── database.py           # SQLite + Parquet
│   ├── analysis/
│   │   ├── indicadores.py        # P/VP, DY 12m, spread vs SELIC
│   │   ├── screener.py           # Filtros e ranking de FIIs
│   │   └── comparador.py         # Comparação lado a lado
│   ├── portfolio/
│   │   ├── carteira.py           # Gestão de posições
│   │   └── relatorio_mensal.py   # Relatório mensal da carteira
│   ├── reports/
│   │   └── dashboard.py          # Dashboard interativo Plotly
│   └── alerts/
│       └── monitor.py            # Alertas por Telegram / e-mail
├── data/                         # Dados locais (no .gitignore)
├── notebooks/                    # Exploração em Jupyter
├── config.yaml                   # Configurações
├── carteira.json                 # Sua carteira
├── ROADMAP.md                    # Plano completo do projeto
└── main.py                       # CLI principal
```

---

## Stack

```python
# Coleta de dados — apenas fontes primárias
requests          # HTTP: CVM, B3, BCB, IBGE, FundosNet
zipfile + io      # Extração de ZIPs em memória

# Processamento
pandas            # DataFrames e leitura de CSV
numpy             # Cálculos numéricos

# Armazenamento
sqlite3           # Banco relacional local
pyarrow           # Parquet para séries temporais longas

# Visualização
plotly            # Dashboard interativo

# Relatórios
jinja2            # Templates HTML

# Alertas
python-telegram-bot  # Notificações via Telegram
smtplib           # E-mail (stdlib)

# Agendamento
schedule          # Agendador de tarefas simples
```

---

## Como começar

> Instruções de instalação serão adicionadas quando a Fase 1 estiver concluída.

```bash
git clone https://github.com/brunoruas2/brick-by-brick.git
cd brick-by-brick
pip install -r requirements.txt
python main.py
```

---

## Contribuindo

O projeto está em desenvolvimento inicial. O roadmap é público e contribuições são bem-vindas assim que o pipeline principal estiver estável. Abra uma issue para discutir ideias.

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">

*"O mercado pode ser irracional por mais tempo do que você pode permanecer solvente — então analise os tijolos antes de comprar."*

**🧱 Brick by Brick — construa riqueza, um FII de cada vez.**

</div>
