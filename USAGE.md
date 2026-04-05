# Brick by Brick — Guia de uso

> CLI para análise e acompanhamento de Fundos de Investimento Imobiliário (FIIs) com dados das fontes primárias oficiais: CVM, B3 e BCB.

---

## Instalação

```bash
# Clone o repositório e instale as dependências
git clone https://github.com/brunoruas2/brick-by-brick
cd brick-by-brick
pip install -r requirements.txt
```

---

## Fluxo completo de uso

### 1. Primeira execução — popular o banco

Na primeira vez, baixe todos os dados. O processo demora entre 3 e 8 minutos dependendo da conexão (faz o download de ~200 MB da B3, CVM e BCB).

```bash
python main.py update
```

O banco SQLite é criado automaticamente em `data/brickbybrick.sqlite`. Para conferir o que foi carregado:

```bash
python main.py status
```

Saída esperada:

```
   Tabela       Registros
   fiis             499
   isin_ticker      467
   cotacoes       92898
   inf_mensal     16140
   benchmarks        25
   carteira           0
   movimentacoes      0
```

---

### 2. Descobrir FIIs — screener

O screener ranqueia todos os FIIs por um score ponderado (DY 30% · Spread SELIC 25% · P/VP 20% · Liquidez 15% · Consistência DY 10%).

```bash
# Top 20 FIIs pelo score padrão
python main.py screen

# Com filtros: DY mínimo 9%, P/VP máximo 1.05, top 30
python main.py screen --dy-min 9 --pvp-max 1.05 --top 30

# Apenas segmento Logística com liquidez mínima de R$ 1M
python main.py screen --segmento "Logistica" --liq-min 1000000

# Opções disponíveis
python main.py screen --help
```

| Opção | Descrição | Exemplo |
|---|---|---|
| `--dy-min` | DY 12m mínimo (%) | `--dy-min 8` |
| `--pvp-max` | P/VP máximo | `--pvp-max 1.10` |
| `--liq-min` | Liquidez 30d mínima (R$) | `--liq-min 500000` |
| `--spread-min` | Spread vs SELIC mínimo (%) | `--spread-min 2` |
| `--segmento` | Filtro parcial de segmento | `--segmento logistica` |
| `--top` | Número de resultados | `--top 30` |

---

### 3. Pesquisar um FII — info e compare

Antes de comprar, analise o FII em detalhe e compare com alternativas do mesmo segmento.

```bash
# Indicadores completos + histórico de DY dos últimos 13 meses
python main.py info HGLG11

# Comparação lado a lado de dois ou mais FIIs
python main.py compare HGLG11 XPLG11 BTLG11
```

Indicadores exibidos: preço de mercado, VPA, P/VP, DY do mês, DY 12m, liquidez 30d, SELIC 12m, spread vs SELIC, consistência de proventos, gestor, taxa de administração.

---

### 4. Montar a carteira

#### Opção A — entrada manual (uma operação por vez)

```bash
# Registrar uma compra: TICKER COTAS PRECO DATA
python main.py portfolio add HGLG11 100 165.50 2024-06-15
python main.py portfolio add MXRF11 500  9.85  2024-08-10
python main.py portfolio add XPLG11 200 103.20 2024-09-20

# Compra adicional do mesmo FII — preco médio é recalculado automaticamente
python main.py portfolio add HGLG11  50 158.00 2026-01-10

# Registrar uma venda
python main.py portfolio sell MXRF11 100 10.20 2026-04-01
```

#### Opção B — importação em lote via Excel

Ideal para quem já tem um histórico de operações ou prefere editar uma planilha.

**Passo 1 — gerar o template:**

```bash
python main.py portfolio template
# → cria carteira_template.xlsx no diretório atual

# Caminho personalizado:
python main.py portfolio template --output minha_carteira.xlsx
```

O arquivo gerado contém:
- Cabeçalho formatado com as colunas obrigatórias
- Linhas de exemplo com fundo azul claro
- Lista suspensa na coluna `tipo` (compra / venda)
- Aba `instrucoes` com a descrição de cada campo

**Colunas do template:**

| Coluna | Formato | Exemplo |
|--------|---------|---------|
| `ticker` | Texto maiúsculo | `HGLG11` |
| `tipo` | `compra` ou `venda` | `compra` |
| `data` | YYYY-MM-DD | `2024-06-15` |
| `cotas` | Inteiro positivo | `100` |
| `preco` | Preço por cota (R$) | `165.50` |

**Passo 2 — preencher e validar:**

```bash
# Valida o arquivo sem salvar nada no banco
python main.py portfolio import carteira_template.xlsx --dry-run
```

Saída esperada:
```
Modo dry-run: nenhuma alteracao sera salva.
4 operacao(oes) validadas com sucesso.
```

**Passo 3 — importar:**

```bash
python main.py portfolio import carteira_template.xlsx
```

Linhas com erro são reportadas individualmente sem interromper as demais:
```
3 operacao(oes) importadas com sucesso.
1 linha(s) com erro:
  • Linha 5 (XXXX11): Posicao ativa nao encontrada para XXXX11
```

---

### 5. Acompanhar a carteira

```bash
# Visão rápida: posições ativas, preço atual, P&L de capital
python main.py portfolio show

# Relatório mensal completo: proventos estimados, YoC e comparativo com SELIC/IPCA
python main.py portfolio report

# Relatório de um mês específico (usa preços e DY da competência correta)
python main.py portfolio report --month 2025-12

# Histórico de dividendos recebidos: YoC mensal, acumulado e payback
python main.py portfolio dividends

# Dividendos de um FII específico
python main.py portfolio dividends --ticker HGLG11

# Dividendos a partir de um mês (ex: 2025-01)
python main.py portfolio dividends --desde 2025-01

# Apenas o sumário consolidado, sem detalhe mês a mês
python main.py portfolio dividends --resumo

# Histórico de todas as operações
python main.py portfolio history

# Histórico de um FII específico
python main.py portfolio history HGLG11
```

**Indicadores do relatório mensal:**

| Indicador | O que representa |
|---|---|
| P. Médio | Preço médio ponderado de compra |
| Valor atual | Cotas × preço de fechamento do mês analisado (B3) |
| P&L | Ganho/perda de capital vs custo de aquisição |
| Prov. est. | Estimativa de provento do mês (cotas × VPA × DY%) |
| YoC mês | Yield on Cost mensal (provento est. / custo total) |
| YoC anual | YoC mês × 12 |
| Spread YoC vs SELIC | YoC mensal menos SELIC do mesmo mês |

**Indicadores do histórico de dividendos (`portfolio dividends`):**

| Indicador | O que representa |
|---|---|
| P. Cota | Preço de fechamento do último pregão do mês (B3) |
| DY mês | Dividend yield mensal reportado pela CVM para aquele mês |
| Div/cota | Dividendo estimado por cota = DY% × preço de fechamento |
| Recebido | Cotas detidas no mês × dividendo/cota |
| YoC mês | Dividendo recebido / custo total × 100 |
| YoC acum. | Total recebido / custo total × 100 (sumário por ativo) |
| Payback | Percentual do custo de aquisição recuperado em dividendos |

> A posição mensal é reconstruída a partir do histórico de compras e vendas — o relatório reflete exatamente quantas cotas você detinha em cada mês, ao preço médio vigente naquele momento.

---

### 5b. Grupamentos e desdobramentos de cotas

Alguns fundos realizam **grupamento** (reverse split: N cotas antigas → 1 nova) ou **desdobramento** (forward split: 1 cota → N novas). Sem registrar esses eventos, o histórico de dividendos ficaria distorcido.

**Verificar se há anomalias na carteira:**

```bash
# Varre o histórico de cotas emitidas e aponta possíveis eventos não registrados
python main.py portfolio check-splits

# Restringir a busca a um ticker específico
python main.py portfolio check-splits HGBS11
```

**Registrar um grupamento ou desdobramento confirmado:**

```bash
# Grupamento 10:1 — 10 cotas antigas viraram 1 nova (reverse split)
python main.py portfolio add-split HGLG11 2021-10 10

# Desdobramento 1:10 — 1 cota antiga virou 10 novas (forward split)
python main.py portfolio add-split HGBS11 2025-05 10 --tipo desdobramento

# Com observação livre
python main.py portfolio add-split HGLG11 2021-10 10 --obs "Fato relevante 15/10/2021"
```

| Opção | Valores | Padrão |
|---|---|---|
| `--tipo` | `grupamento` \| `desdobramento` | `grupamento` |
| `--obs` | Texto livre (fato relevante, fonte) | — |

Após registrar o evento, rode `portfolio dividends` para ver o histórico corrigido. O custo total permanece inalterado — apenas as cotas e o preço médio são normalizados para refletir a quantidade correta em cada período.

---

### 6. Verificar alertas

```bash
# Alertas com limiares padrão
python main.py alerts

# Limiares personalizados
python main.py alerts --pvp-max 1.10 --pl-min -10 --score-min 75
```

Tipos de alerta:

| Cor | Tipo | Condição padrão |
|---|---|---|
| Vermelho — ATENCAO | `spread_negativo` | DY 12m abaixo da SELIC |
| Vermelho — ATENCAO | `pl_negativo` | P&L de capital < −15% |
| Amarelo — AVISO | `pvp_alto` | P/VP > 1.20 |
| Amarelo — AVISO | `dy_queda` | DY do mês < 80% da média mensal 12m |
| Verde — OPRTND | `score_alto` | FII fora da carteira com score ≥ 70 |

---

### 7. Manter os dados atualizados

#### Opção A — atualização manual

```bash
# Atualiza tudo
python main.py update

# Apenas preços (mais rápido, para uso diário)
python main.py update cotahist

# Apenas dados mensais da CVM (DY, VPA, PL)
python main.py update inf-mensal

# Apenas benchmarks (SELIC/CDI/IPCA)
python main.py update benchmarks
```

> **Histórico mais antigo:** por padrão, `inf-mensal` e `cotahist` baixam apenas o ano atual e o anterior. Se a sua carteira tiver compras mais antigas ou se o relatório de dividendos avisar sobre meses sem DY, baixe os anos necessários com `--desde-ano`:
>
> ```bash
> # Baixa inf-mensal e cotahist de 2024 até hoje
> python main.py update inf-mensal --desde-ano 2024
> python main.py update cotahist   --desde-ano 2024
> ```

#### Opção B — scheduler automático (foreground)

```bash
python main.py scheduler
```

Mantém o banco atualizado automaticamente enquanto o processo estiver rodando:

| Horário | Tarefa |
|---|---|
| Seg–Sex 20:30 | `update cotahist` — preços diários B3 |
| Dom 21:00 | `update cadastro + inf-mensal` — dados mensais CVM |
| Dia 1 às 07:00 | `update benchmarks` — SELIC/CDI/IPCA BCB |

Após cada atualização automática, o scheduler verifica alertas e avisa no terminal se houver itens de atenção.

#### Opção C — agendamento pelo sistema operacional

Para rodar sem manter terminal aberto, configure uma tarefa no SO para executar `python main.py update` no horário desejado:

**Windows (Task Scheduler):**
```
Programa: python
Argumentos: C:\caminho\para\main.py update
Gatilho: diário às 21:00
```

**Linux / macOS (cron):**
```bash
# Edite o crontab: crontab -e
30 20 * * 1-5 cd /caminho/para/projeto && python main.py update cotahist
0  21 * * 0   cd /caminho/para/projeto && python main.py update cadastro && python main.py update inf-mensal
0   7 1 * *   cd /caminho/para/projeto && python main.py update benchmarks
```

---

## Referência rápida de comandos

```
python main.py update [fonte]              # Atualiza dados (all | cadastro | inf-mensal | cotahist | benchmarks)
python main.py status                      # Estado do banco de dados
python main.py screen [filtros]            # Screener com score ponderado
python main.py info TICKER                 # Indicadores detalhados de um FII
python main.py compare TICKER [TICKER...]  # Comparação lado a lado

python main.py portfolio add       TICKER COTAS PRECO DATA           # Registra compra
python main.py portfolio sell      TICKER COTAS PRECO DATA           # Registra venda
python main.py portfolio template  [--output ARQUIVO]                # Gera template Excel
python main.py portfolio import    ARQUIVO [--dry-run]               # Importa do Excel
python main.py portfolio show                                        # Posições com P&L
python main.py portfolio report    [--month YYYY-MM]                 # Relatório mensal
python main.py portfolio dividends   [--ticker T] [--desde YYYY-MM] [--resumo]  # Histórico de dividendos
python main.py portfolio history     [TICKER]                                    # Histórico de operações
python main.py portfolio check-splits [TICKER]                                   # Detecta grupamentos/desdobramentos nao registrados
python main.py portfolio add-split   TICKER YYYY-MM FATOR [--tipo T] [--obs S]  # Registra evento de split

python main.py alerts [opções]             # Alertas e oportunidades
python main.py scheduler                   # Agendador automático (foreground)
```

---

## Fontes de dados

Todos os dados vêm de fontes primárias, públicas e gratuitas — sem dependência de terceiros.

| Dado | Fonte | Frequência |
|---|---|---|
| Cadastro de FIIs (CNPJ, gestor, taxas) | CVM `dados.cvm.gov.br` | Ter–Sáb |
| DY mensal, VPA, PL, composição do ativo | CVM Informe Mensal FII | Semanal |
| Preços diários históricos (B3) | B3 COTAHIST | Diária |
| SELIC, CDI, IPCA | BCB API SGS | Mensal |
