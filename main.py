"""
Brick by Brick -- CLI principal

Uso:
    python main.py update                  # atualiza todas as fontes
    python main.py update cadastro         # apenas o cadastro de FIIs (CVM)
    python main.py update inf-mensal       # apenas informe mensal (CVM)
    python main.py update cotahist         # apenas cotacoes historicas (B3)
    python main.py update benchmarks       # apenas SELIC/CDI/IPCA (BCB)
    python main.py status                  # estado do banco local
    python main.py screen                  # screener de FIIs
    python main.py info MXRF11             # indicadores de um FII
    python main.py compare MXRF11 HGLG11  # comparacao lado a lado
    python main.py --help
"""

import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Força UTF-8 no Windows para evitar UnicodeEncodeError com rich/typer
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

app = typer.Typer(
    name="brick",
    help="Brick by Brick -- Analise de Fundos Imobiliarios",
    add_completion=False,
)
portfolio_app = typer.Typer(help="Gestao da carteira de FIIs")
app.add_typer(portfolio_app, name="portfolio")
console = Console()

_SOURCES_AVAILABLE = ["cadastro", "inf-mensal", "cotahist", "benchmarks"]


def _fmt_reais(v) -> str:
    """Formata valor em reais de forma legivel."""
    import pandas as pd
    if v is None or (hasattr(v, '__class__') and pd.isna(v)):
        return "--"
    v = float(v)
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"R$ {v/1_000:.0f}K"
    return f"R$ {v:.0f}"


def _execute_update(targets: list[str], desde_ano: int | None = None) -> list[tuple[str, int]]:
    """
    Executa a atualizacao das fontes indicadas e retorna (label, count) por fonte.
    Chamado tanto pelo comando 'update' quanto pelo scheduler.

    desde_ano: se informado, baixa inf-mensal e cotahist desde esse ano ate o atual.
    """
    import datetime as _dt
    from src.storage.database import (
        init_db, upsert_fiis, upsert_inf_mensal, update_fiis_metadata,
        upsert_cotacoes, upsert_benchmarks, update_fiis_isin,
        upsert_isin_ticker, link_tickers,
    )
    from src.collectors import cvm_cadastro, cvm_inf_mensal

    init_db()
    results: list[tuple[str, int]] = []

    ano_atual = _dt.datetime.now().year
    if desde_ano:
        years = list(range(desde_ano, ano_atual + 1))
    else:
        years = None  # usa o padrao do coletor (atual + anterior)

    if "cadastro" in targets:
        records = cvm_cadastro.fetch()
        results.append(("Cadastro CVM", upsert_fiis(records)))

    if "inf-mensal" in targets:
        inf_records, meta_records = cvm_inf_mensal.fetch(years=years)
        results.append(("Informe Mensal CVM", upsert_inf_mensal(inf_records)))
        results.append(("  segmento/mandato", update_fiis_metadata(meta_records)))
        update_fiis_isin(meta_records)

    if "cotahist" in targets:
        from src.collectors import b3_cotahist
        cotacao_records, isin_ticker_records = b3_cotahist.fetch(years=years)
        results.append(("COTAHIST B3", upsert_cotacoes(cotacao_records)))
        upsert_isin_ticker(isin_ticker_records)

    if "benchmarks" in targets:
        from src.collectors import bcb_series
        results.append(("Benchmarks BCB (24m)", upsert_benchmarks(bcb_series.fetch(months=24))))

    n_linked = link_tickers()
    results.append(("  tickers vinculados a CNPJs", n_linked))

    return results


@app.command()
def update(
    source: str = typer.Argument(
        "all",
        help="Fonte: all | cadastro | inf-mensal | cotahist | benchmarks",
    ),
    desde_ano: int = typer.Option(
        None, "--desde-ano",
        help="Ano inicial para inf-mensal e cotahist (ex: 2024). Padrao: ano atual e anterior.",
    ),
):
    """
    Baixa dados das fontes primarias (CVM, B3, BCB) e salva no banco local.

    Sem argumentos atualiza todas as fontes. Idempotente.
    Use --desde-ano para baixar historico mais antigo de inf-mensal e cotahist.
    """
    console.print(Panel.fit("Brick by Brick -- Atualizacao de dados", style="bold blue"))
    console.print("[dim]  Banco:[/dim] data/brickbybrick.sqlite\n")

    targets = _SOURCES_AVAILABLE if source == "all" else [source]

    for t in targets:
        if t not in _SOURCES_AVAILABLE:
            console.print(
                f"[red]Fonte desconhecida: '{t}'. "
                f"Disponiveis: {', '.join(_SOURCES_AVAILABLE)}[/red]"
            )
            raise typer.Exit(code=1)

    results = _execute_update(targets, desde_ano=desde_ano)

    console.print()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Fonte", style="cyan")
    table.add_column("Registros", justify="right", style="green")
    for label, count in results:
        table.add_row(label, str(count))
    console.print(table)


@app.command()
def screen(
    dy_min:     float = typer.Option(None,  "--dy-min",     help="DY 12m minimo (%)"),
    pvp_max:    float = typer.Option(None,  "--pvp-max",    help="P/VP maximo"),
    liq_min:    float = typer.Option(None,  "--liq-min",    help="Liquidez 30d minima (R$)"),
    spread_min: float = typer.Option(None,  "--spread-min", help="Spread vs SELIC minimo (%)"),
    segmento:   str   = typer.Option(None,  "--segmento",   help="Filtro de segmento"),
    top:        int   = typer.Option(20,    "--top",        help="Numero de resultados"),
):
    """Filtra e ranqueia FIIs por score ponderado."""
    import pandas as pd
    from src.analysis.screener import screen as run_screen

    df = run_screen(
        dy_min=dy_min, pvp_max=pvp_max, liq_min=liq_min,
        spread_min=spread_min, segmento=segmento, top_n=top,
    )

    if df.empty:
        console.print("[yellow]Nenhum FII encontrado com esses filtros.[/yellow]")
        console.print("[dim]Dica: rode 'python main.py update' para atualizar os dados.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", title=f"Top {len(df)} FIIs")
    table.add_column("#",         justify="right",  width=3)
    table.add_column("Ticker",    style="cyan",     width=8)
    table.add_column("Segmento",                    width=18)
    table.add_column("Preco",     justify="right",  width=8)
    table.add_column("P/VP",      justify="right",  width=6)
    table.add_column("DY 12m",    justify="right",  width=8)
    table.add_column("Liq 30d",   justify="right",  width=10)
    table.add_column("Spread",    justify="right",  width=8)
    table.add_column("Score",     justify="right",  width=6)

    for i, row in df.iterrows():
        pvp_val   = f"{row['p_vp']:.2f}"   if pd.notna(row.get('p_vp'))          else "--"
        dy_val    = f"{row['dy_12m']:.1f}%" if pd.notna(row.get('dy_12m'))        else "--"
        liq_val   = _fmt_reais(row.get('liquidez_30d'))
        spr_val   = f"{row['spread_selic']:.1f}%" if pd.notna(row.get('spread_selic')) else "--"
        preco_val = f"R${row['preco']:.2f}" if pd.notna(row.get('preco'))          else "--"
        score_val = f"{row['score']:.0f}"   if pd.notna(row.get('score'))          else "--"
        seg       = str(row.get('segmento') or "--")[:18]

        table.add_row(
            str(i + 1), row["ticker"], seg,
            preco_val, pvp_val, dy_val, liq_val, spr_val, score_val,
        )

    console.print(table)


@app.command()
def info(ticker: str = typer.Argument(..., help="Ticker do FII (ex: HGLG11)")):
    """Exibe indicadores detalhados de um FII."""
    import pandas as pd
    from src.analysis.indicadores import get_indicators_for, get_dy_history

    df = get_indicators_for([ticker])
    if df.empty:
        console.print(f"[red]FII '{ticker.upper()}' nao encontrado.[/red]")
        console.print("[dim]Verifique o ticker ou rode: python main.py update[/dim]")
        return

    row = df.iloc[0]

    def _str_or_dash(v) -> str:
        return str(v) if pd.notna(v) and str(v).strip() else "--"

    console.print(f"\n[bold cyan]{row['ticker']}[/bold cyan] -- {row['nome']}")
    console.print(f"Segmento : {_str_or_dash(row.get('segmento'))}")
    console.print(f"Gestor   : {_str_or_dash(row.get('gestor'))}")
    console.print(f"Taxa adm : {row['taxa_adm']:.2f}%" if pd.notna(row.get('taxa_adm')) else "Taxa adm : --")
    console.print()

    ind = Table(show_header=False, box=None, padding=(0, 2))
    ind.add_column("Indicador", style="dim")
    ind.add_column("Valor",     style="bold")

    def _add(label, value): ind.add_row(label, value)

    _add("Preco mercado", f"R$ {row['preco']:.2f}  ({row.get('data_preco', '--')})" if pd.notna(row.get('preco')) else "--")
    _add("VPA (CVM)",     f"R$ {row['vpa']:.2f}  ({row.get('data_vpa', '--')})"    if pd.notna(row.get('vpa'))   else "--")
    _add("P/VP",          f"{row['p_vp']:.4f}"  if pd.notna(row.get('p_vp'))          else "--")
    _add("DY mes atual",  f"{row['dy_mes_atual']:.2f}%"  if pd.notna(row.get('dy_mes_atual'))  else "--")
    _add("DY 12 meses",   f"{row['dy_12m']:.2f}%"  if pd.notna(row.get('dy_12m'))       else "--")
    _add("Liquidez 30d",  _fmt_reais(row.get('liquidez_30d')))
    _add("SELIC 12m",     f"{row['selic_12m']:.2f}%"  if pd.notna(row.get('selic_12m'))  else "--")
    _add("Spread SELIC",  f"{row['spread_selic']:.2f}%"  if pd.notna(row.get('spread_selic')) else "--")
    _add("Consist. DY",   f"{row['consistencia_dy']:.4f}" if pd.notna(row.get('consistencia_dy')) else "--")

    console.print(ind)

    # Historico DY
    hist = get_dy_history(ticker, months=13)
    if not hist.empty:
        console.print("\n[bold]Historico DY (ultimos meses):[/bold]")
        htable = Table(show_header=True, header_style="dim")
        htable.add_column("Referencia", width=12)
        htable.add_column("DY mes",  justify="right", width=8)
        htable.add_column("VPA",     justify="right", width=10)
        for _, hr in hist.iterrows():
            dy  = f"{hr['dy_mes']:.2f}%"  if pd.notna(hr['dy_mes']) else "--"
            vpa = f"R$ {hr['vpa']:.2f}"   if pd.notna(hr['vpa'])    else "--"
            htable.add_row(str(hr['data_referencia'])[:7], dy, vpa)
        console.print(htable)


@app.command()
def compare(tickers: list[str] = typer.Argument(..., help="Tickers para comparar (ex: HGLG11 XPLG11)")):
    """Compara indicadores de dois ou mais FIIs lado a lado."""
    import pandas as pd
    from src.analysis.indicadores import get_indicators_for

    df = get_indicators_for(tickers)
    if df.empty:
        console.print("[red]Nenhum FII encontrado.[/red]")
        return

    found = df["ticker"].tolist()
    missing = [t.upper() for t in tickers if t.upper() not in found]
    if missing:
        console.print(f"[yellow]Nao encontrado: {', '.join(missing)}[/yellow]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Indicador", style="dim", width=18)
    for t in found:
        table.add_column(t, justify="right", width=12)

    def _row(label, col, fmt):
        vals = []
        for _, r in df.iterrows():
            v = r.get(col)
            vals.append(fmt(v) if pd.notna(v) else "--")
        table.add_row(label, *vals)

    _row("Segmento",    "segmento",       lambda v: str(v)[:12] if v else "--")
    _row("Preco",       "preco",          lambda v: f"R$ {v:.2f}")
    _row("VPA",         "vpa",            lambda v: f"R$ {v:.2f}")
    _row("P/VP",        "p_vp",           lambda v: f"{v:.4f}")
    _row("DY mes",      "dy_mes_atual",   lambda v: f"{v:.2f}%")
    _row("DY 12m",      "dy_12m",         lambda v: f"{v:.2f}%")
    _row("Liquidez 30d","liquidez_30d",   _fmt_reais)
    _row("SELIC 12m",   "selic_12m",      lambda v: f"{v:.2f}%")
    _row("Spread",      "spread_selic",   lambda v: f"{v:.2f}%")
    _row("Consist. DY", "consistencia_dy",lambda v: f"{v:.4f}")

    console.print(table)


@app.command()
def status():
    """Exibe o estado atual do banco de dados local."""
    import sqlite3
    from src.config import DB_PATH

    if not DB_PATH.exists():
        console.print("[yellow]Banco nao encontrado. Rode: python main.py update[/yellow]")
        raise typer.Exit()

    conn = sqlite3.connect(DB_PATH)
    table = Table(title="Estado do banco", show_header=True, header_style="bold")
    table.add_column("Tabela", style="cyan")
    table.add_column("Registros", justify="right")

    for t in ["fiis", "isin_ticker", "cotacoes", "cota_oficial", "inf_mensal", "benchmarks",
              "carteira", "movimentacoes"]:
        try:
            (count,) = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        except Exception:
            count = "?"
        table.add_row(t, str(count))

    conn.close()
    console.print(table)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

@app.command()
def alerts(
    pvp_max:      float = typer.Option(1.20,  "--pvp-max",   help="Limiar de P/VP para aviso"),
    pl_min:       float = typer.Option(-15.0, "--pl-min",    help="Limiar de P&L%% para atencao"),
    dy_queda:     float = typer.Option(0.80,  "--dy-queda",  help="Fracao da media 12m para alerta de DY"),
    score_min:    float = typer.Option(70.0,  "--score-min", help="Score minimo para sugerir oportunidade"),
):
    """Verifica alertas da carteira e oportunidades do screener."""
    from src.portfolio.alertas import check_alerts

    lista = check_alerts(
        pvp_max=pvp_max,
        pl_pct_min=pl_min,
        dy_queda_pct=dy_queda,
        score_min=score_min,
    )

    if not lista:
        console.print("[green]Sem alertas. Carteira dentro dos parametros configurados.[/green]")
        return

    _ESTILOS = {
        "atencao":     ("red",    "[ATENCAO]"),
        "aviso":       ("yellow", "[AVISO]  "),
        "oportunidade":("green",  "[OPRTND] "),
    }

    table = Table(show_header=True, header_style="bold", title="Alertas e oportunidades")
    table.add_column("Nivel",  width=10)
    table.add_column("Ticker", style="cyan", width=8)
    table.add_column("Tipo",   width=16)
    table.add_column("Detalhe")

    for a in lista:
        cor, label = _ESTILOS.get(a.nivel, ("white", a.nivel))
        table.add_row(
            f"[{cor}]{label}[/{cor}]",
            a.ticker,
            a.tipo,
            a.mensagem,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

@app.command()
def scheduler():
    """
    Inicia o agendador de atualizacoes automaticas (processo em foreground).

    Agenda padrao:
      Dias uteis 20:30  -- cotahist (precos diarios)
      Domingo    21:00  -- cadastro + inf-mensal (dados mensais CVM)
      Dia 1      07:00  -- benchmarks (SELIC/CDI/IPCA BCB)

    Pressione Ctrl+C para encerrar.
    """
    try:
        import schedule
    except ImportError:
        console.print("[red]Dependencia ausente. Instale com: pip install schedule[/red]")
        raise typer.Exit(code=1)

    import time
    from datetime import datetime

    def _ts() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def _job(sources: list[str], label: str) -> None:
        console.print(f"\n[dim]{_ts()}[/dim] [cyan]Iniciando:[/cyan] {label}")
        try:
            results = _execute_update(sources)
            for lbl, cnt in results:
                console.print(f"  [dim]{lbl}:[/dim] {cnt}")
            console.print(f"[dim]{_ts()}[/dim] [green]Concluido:[/green] {label}")
        except Exception as e:
            console.print(f"[dim]{_ts()}[/dim] [red]Erro em '{label}': {e}[/red]")

        # Verifica alertas apos cada atualizacao
        try:
            from src.portfolio.alertas import check_alerts
            lista = check_alerts()
            urgentes = [a for a in lista if a.nivel == "atencao"]
            if urgentes:
                console.print(f"[red]  {len(urgentes)} alerta(s) de atencao -- rode: python main.py alerts[/red]")
        except Exception:
            pass

    def _job_benchmarks() -> None:
        """Roda apenas no dia 1 de cada mes."""
        if datetime.now().day == 1:
            _job(["benchmarks"], "benchmarks BCB")
        # Se nao for dia 1, silencio (o schedule chama todo dia no horario)

    # Agenda
    schedule.every().monday.at("20:30").do(_job, ["cotahist"], "cotahist (precos diarios)")
    schedule.every().tuesday.at("20:30").do(_job, ["cotahist"], "cotahist (precos diarios)")
    schedule.every().wednesday.at("20:30").do(_job, ["cotahist"], "cotahist (precos diarios)")
    schedule.every().thursday.at("20:30").do(_job, ["cotahist"], "cotahist (precos diarios)")
    schedule.every().friday.at("20:30").do(_job, ["cotahist"], "cotahist (precos diarios)")
    schedule.every().sunday.at("21:00").do(_job, ["cadastro", "inf-mensal"], "cadastro + inf-mensal CVM")
    schedule.every().day.at("07:00").do(_job_benchmarks)

    # Exibe agenda ao iniciar
    console.print(Panel.fit("Brick by Brick -- Scheduler", style="bold blue"))
    t = Table(show_header=True, header_style="bold", title="Agenda configurada")
    t.add_column("Horario",  width=20)
    t.add_column("Tarefa")
    t.add_row("Seg-Sex 20:30", "update cotahist  (precos diarios B3)")
    t.add_row("Dom    21:00", "update cadastro + inf-mensal  (CVM)")
    t.add_row("Dia 1  07:00", "update benchmarks  (SELIC/CDI/IPCA BCB)")
    console.print(t)
    console.print("[dim]Pressione Ctrl+C para encerrar.[/dim]\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler encerrado pelo usuario.[/yellow]")


# ---------------------------------------------------------------------------
# Carteira
# ---------------------------------------------------------------------------

@portfolio_app.command("add")
def portfolio_add(
    ticker: str  = typer.Argument(..., help="Ticker do FII (ex: HGLG11)"),
    cotas:  int  = typer.Argument(..., help="Numero de cotas compradas"),
    preco:  float = typer.Argument(..., help="Preco unitario pago (R$)"),
    data:   str  = typer.Argument(..., help="Data da operacao (YYYY-MM-DD)"),
):
    """Registra uma compra na carteira."""
    from src.portfolio.carteira import add_compra
    try:
        add_compra(ticker, cotas, preco, data)
        console.print(
            f"[green]Compra registrada:[/green] "
            f"{cotas}x {ticker.upper()} @ R$ {preco:.2f}  em {data}"
        )
    except Exception as e:
        console.print(f"[red]Erro: {e}[/red]")
        raise typer.Exit(code=1)


@portfolio_app.command("sell")
def portfolio_sell(
    ticker: str  = typer.Argument(..., help="Ticker do FII (ex: HGLG11)"),
    cotas:  int  = typer.Argument(..., help="Numero de cotas vendidas"),
    preco:  float = typer.Argument(..., help="Preco unitario recebido (R$)"),
    data:   str  = typer.Argument(..., help="Data da operacao (YYYY-MM-DD)"),
):
    """Registra uma venda na carteira."""
    from src.portfolio.carteira import add_venda
    try:
        add_venda(ticker, cotas, preco, data)
        console.print(
            f"[green]Venda registrada:[/green] "
            f"{cotas}x {ticker.upper()} @ R$ {preco:.2f}  em {data}"
        )
    except ValueError as e:
        console.print(f"[red]Erro: {e}[/red]")
        raise typer.Exit(code=1)


@portfolio_app.command("show")
def portfolio_show():
    """Exibe as posicoes ativas com preco atual e P&L de capital."""
    from src.portfolio.relatorio import show_posicoes
    show_posicoes()


@portfolio_app.command("report")
def portfolio_report(
    month: str = typer.Option(
        None, "--month", "-m",
        help="Mes do relatorio (YYYY-MM). Padrao: mes atual.",
    ),
):
    """Relatorio mensal: posicoes, proventos estimados, YoC e benchmarks."""
    from src.portfolio.relatorio import relatorio_mensal
    relatorio_mensal(month)


@portfolio_app.command("template")
def portfolio_template(
    output: str = typer.Option(
        "carteira_template.xlsx",
        "--output", "-o",
        help="Caminho do arquivo Excel a gerar.",
    ),
):
    """Gera um arquivo Excel com o template de importacao de carteira."""
    from src.portfolio.carteira import export_template
    try:
        export_template(output)
        console.print(f"[green]Template salvo em:[/green] {output}")
        console.print("[dim]Preencha o arquivo e importe com: python main.py portfolio import <arquivo>[/dim]")
    except Exception as e:
        console.print(f"[red]Erro ao gerar template: {e}[/red]")
        raise typer.Exit(code=1)


@portfolio_app.command("import")
def portfolio_import(
    arquivo: str = typer.Argument(..., help="Caminho do Excel preenchido."),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Valida sem inserir no banco.",
    ),
):
    """Importa movimentacoes de carteira a partir de um arquivo Excel."""
    import os
    from src.portfolio.carteira import import_from_excel

    if not os.path.isfile(arquivo):
        console.print(f"[red]Arquivo nao encontrado: {arquivo}[/red]")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[yellow]Modo dry-run: nenhuma alteracao sera salva.[/yellow]")

    try:
        n_ok, erros = import_from_excel(arquivo, dry_run=dry_run)
    except ValueError as e:
        console.print(f"[red]Erro no arquivo: {e}[/red]")
        raise typer.Exit(code=1)

    if n_ok:
        label = "validadas" if dry_run else "importadas"
        console.print(f"[green]{n_ok} operacao(oes) {label} com sucesso.[/green]")
    if erros:
        console.print(f"[yellow]{len(erros)} linha(s) com erro:[/yellow]")
        for e in erros:
            console.print(f"  [red]•[/red] {e}")
    if not n_ok and not erros:
        console.print("[yellow]Nenhuma operacao encontrada no arquivo.[/yellow]")


@portfolio_app.command("dividends")
def portfolio_dividends(
    ticker: str = typer.Option(
        None, "--ticker", "-t",
        help="Filtrar por ticker (ex: HGLG11).",
    ),
    desde: str = typer.Option(
        None, "--desde", "-d",
        help="Mes inicial no formato YYYY-MM.",
    ),
    resumo: bool = typer.Option(
        False, "--resumo", "-r",
        help="Exibe apenas o sumario consolidado, sem detalhe mensal.",
    ),
):
    """Historico de dividendos recebidos: YoC mensal, acumulado e payback."""
    from src.portfolio.relatorio import relatorio_dividendos
    relatorio_dividendos(ticker=ticker, desde=desde, resumo=resumo)


@portfolio_app.command("add-split")
def portfolio_add_split(
    ticker: str   = typer.Argument(..., help="Ticker do FII (ex: HGLG11)"),
    mes:    str   = typer.Argument(..., help="Mes do evento (YYYY-MM)"),
    fator:  float = typer.Argument(..., help="Fator (ex: 10)"),
    tipo:   str   = typer.Option("grupamento", "--tipo", help="grupamento (reverse split) ou desdobramento (forward split)"),
    obs:    str   = typer.Option(None, "--obs", help="Observacao opcional"),
):
    """Registra grupamento ou desdobramento de cotas para correcao do historico."""
    from src.portfolio.grupamentos import add_grupamento
    try:
        add_grupamento(ticker, mes, fator, tipo=tipo, observacao=obs)
        if tipo == "desdobramento":
            console.print(
                f"[green]Desdobramento registrado:[/green] "
                f"{ticker.upper()} em {mes}, fator 1:{fator:.0f}"
            )
        else:
            console.print(
                f"[green]Grupamento registrado:[/green] "
                f"{ticker.upper()} em {mes}, fator {fator:.0f}:1"
            )
        console.print(
            "[dim]Rode 'portfolio dividends' para ver o historico corrigido.[/dim]"
        )
    except ValueError as e:
        console.print(f"[red]Erro: {e}[/red]")
        raise typer.Exit(code=1)


@portfolio_app.command("check-splits")
def portfolio_check_splits(
    ticker: str = typer.Argument(None, help="Ticker para restringir a busca (opcional)"),
):
    """Varre o historico de cotas emitidas e aponta possiveis grupamentos nao registrados."""
    from src.portfolio.grupamentos import detectar_anomalias
    from src.portfolio.carteira import get_posicoes

    tickers_arg = [ticker.upper()] if ticker else None

    # Se nenhum ticker passado, usa os tickers da carteira ativa
    if not tickers_arg:
        pos = get_posicoes()
        if pos.empty:
            console.print("[yellow]Carteira vazia. Passe um ticker como argumento.[/yellow]")
            raise typer.Exit()
        tickers_arg = pos["ticker"].tolist()

    anomalias = detectar_anomalias(tickers=tickers_arg)

    if not anomalias:
        console.print("[green]Nenhuma anomalia detectada para os tickers analisados.[/green]")
        return

    t = Table(show_header=True, header_style="bold", title="Possiveis grupamentos detectados")
    t.add_column("Ticker",     style="cyan", width=8)
    t.add_column("Mes",        width=8)
    t.add_column("Fator est.", justify="right", width=10)
    t.add_column("Confianca",  width=8)
    t.add_column("Sinais")

    for a in anomalias:
        cor = "green" if a["confianca"] == "alta" else "yellow" if a["confianca"] == "media" else "dim"
        t.add_row(
            a["ticker"],
            a["mes"],
            f"{a['fator_estimado']}:1",
            f"[{cor}]{a['confianca']}[/{cor}]",
            a["sinais"],
        )

    console.print(t)
    console.print()
    console.print("[dim]Pesquise o fato relevante do fundo no mes indicado e, se confirmar,[/dim]")
    console.print("[dim]registre com: python main.py portfolio add-split TICKER YYYY-MM FATOR[/dim]")


@portfolio_app.command("history")
def portfolio_history(
    ticker: str = typer.Argument(None, help="Ticker para filtrar (opcional)"),
):
    """Exibe o historico de movimentacoes."""
    import pandas as pd
    from src.portfolio.carteira import get_movimentacoes

    df = get_movimentacoes(ticker)
    if df.empty:
        console.print("[yellow]Sem movimentacoes registradas.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold", title="Historico de movimentacoes")
    table.add_column("Data",    width=12)
    table.add_column("Ticker",  style="cyan", width=8)
    table.add_column("Tipo",    width=8)
    table.add_column("Cotas",   justify="right", width=7)
    table.add_column("Preco",   justify="right", width=10)
    table.add_column("Total",   justify="right", width=13)

    for _, r in df.iterrows():
        table.add_row(
            str(r["data"]),
            str(r["ticker"]),
            str(r["tipo"]),
            str(int(r["quantidade"])) if pd.notna(r.get("quantidade")) else "--",
            f"R$ {r['preco_unitario']:.2f}" if pd.notna(r.get("preco_unitario")) else "--",
            f"R$ {r['valor_total']:.2f}",
        )

    console.print(table)


if __name__ == "__main__":
    app()
