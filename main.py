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

backtest_app = typer.Typer(help="Simulacoes hipoteticas (what-if) sobre a carteira")
app.add_typer(backtest_app, name="backtest")
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
    pl_min:     float = typer.Option(None,  "--pl-min",     help="Patrimonio liquido minimo (R$, ex: 500000000)"),
    top:        int   = typer.Option(20,    "--top",        help="Numero de resultados"),
    export:     str   = typer.Option(None,  "--export",     help="Exportar resultado para CSV ou Excel (ex: resultado.csv)"),
):
    """Filtra e ranqueia FIIs por score ponderado."""
    import pandas as pd
    from pathlib import Path
    from src.analysis.screener import screen as run_screen

    df = run_screen(
        dy_min=dy_min, pvp_max=pvp_max, liq_min=liq_min,
        spread_min=spread_min, segmento=segmento, pl_min=pl_min, top_n=top,
    )

    if df.empty:
        console.print("[yellow]Nenhum FII encontrado com esses filtros.[/yellow]")
        console.print("[dim]Dica: rode 'python main.py update' para atualizar os dados.[/dim]")
        return

    if export:
        try:
            p = Path(export)
            if p.suffix.lower() in (".xlsx", ".xls"):
                df.to_excel(export, index=False)
            else:
                df.to_csv(export, index=False, encoding="utf-8-sig")
            console.print(f"[green]Exportado para:[/green] {export}")
        except Exception as e:
            console.print(f"[red]Erro ao exportar: {e}[/red]")
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
def info(
    ticker:   str   = typer.Argument(...,  help="Ticker do FII (ex: HGLG11)"),
    pvp_hist: bool  = typer.Option(False, "--pvp-hist", help="Exibe historico mensal de P/VP"),
    yoc_alvo: float = typer.Option(None,  "--yoc-alvo", help="Preco alvo para calcular YoC projetado (R$)"),
):
    """Exibe indicadores detalhados de um FII."""
    import pandas as pd
    from src.analysis.indicadores import (
        get_indicators_for, get_dy_history,
        get_dy_trend, get_crescimento_pl, get_composicao_receita, get_pvp_history,
    )

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

    if yoc_alvo and pd.notna(row.get("dy_12m")) and pd.notna(row.get("preco")):
        div_anual = float(row["preco"]) * float(row["dy_12m"]) / 100
        yoc_proj  = div_anual / yoc_alvo * 100
        _add(f"YoC @ R${yoc_alvo:.2f}", f"{yoc_proj:.2f}%  (div. anual R$ {div_anual:.2f})")

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
            dy  = f"{hr['dy_mes']*100:.2f}%"  if pd.notna(hr['dy_mes']) else "--"
            vpa = f"R$ {hr['vpa']:.2f}"   if pd.notna(hr['vpa'])    else "--"
            htable.add_row(str(hr['data_referencia'])[:7], dy, vpa)
        console.print(htable)

    # Tendencia DY (medias moveis)
    df_trend, sinais = get_dy_trend(ticker, months=24)
    if not df_trend.empty:
        console.print("\n[bold]Tendencia DY -- medias moveis:[/bold]")
        _SINAL_MAP = {"\u2191": "(+)", "\u2192": "(=)", "\u2193": "(-)"}
        sinal_str = "  ".join(
            f"MM{k[2:]}: {_SINAL_MAP.get(v, v)}" for k, v in sinais.items()
        )
        console.print(f"[dim]{sinal_str}[/dim]")
        tt = Table(show_header=True, header_style="dim")
        tt.add_column("Referencia", width=10)
        tt.add_column("DY mes",   justify="right", width=8)
        tt.add_column("MM6",      justify="right", width=7)
        tt.add_column("MM12",     justify="right", width=7)
        tt.add_column("MM24",     justify="right", width=7)
        for _, hr in df_trend.tail(12).iterrows():
            tt.add_row(
                str(hr["data_referencia"])[:7],
                f"{hr['dy_mes_pct']:.2f}%" if pd.notna(hr.get("dy_mes_pct")) else "--",
                f"{hr['mm6']:.2f}%"        if pd.notna(hr.get("mm6"))        else "--",
                f"{hr['mm12']:.2f}%"       if pd.notna(hr.get("mm12"))       else "--",
                f"{hr['mm24']:.2f}%"       if pd.notna(hr.get("mm24"))       else "--",
            )
        console.print(tt)

    # Crescimento PL e cotistas
    crescimento = get_crescimento_pl(ticker)
    if crescimento:
        console.print("\n[bold]Crescimento PL e cotistas:[/bold]")
        ct = Table(show_header=False, box=None, padding=(0, 2))
        ct.add_column("Label", style="dim")
        ct.add_column("Valor", style="bold")
        if crescimento.get("pl_atual") is not None:
            ct.add_row("PL atual",          _fmt_reais(crescimento["pl_atual"]))
        if crescimento.get("pl_var_12m") is not None:
            ct.add_row("PL var. 12m",       f"{crescimento['pl_var_12m']:+.1f}%")
        if crescimento.get("pl_var_24m") is not None:
            ct.add_row("PL var. 24m",       f"{crescimento['pl_var_24m']:+.1f}%")
        if crescimento.get("nr_cotistas_atual") is not None:
            ct.add_row("Cotistas",          f"{crescimento['nr_cotistas_atual']:,}")
        if crescimento.get("cotistas_var_12m") is not None:
            ct.add_row("Cotistas var. 12m", f"{crescimento['cotistas_var_12m']:+.1f}%")
        console.print(ct)

    # Composicao de receita (ultimos 3 meses)
    comp = get_composicao_receita(ticker, months=3)
    if not comp.empty:
        console.print("\n[bold]Composicao de receita (% do PL, ult. 3 meses):[/bold]")
        cpt = Table(show_header=True, header_style="dim")
        cpt.add_column("Mes",         width=8)
        cpt.add_column("Imoveis",     justify="right", width=9)
        cpt.add_column("CRI",         justify="right", width=8)
        cpt.add_column("LCI",         justify="right", width=8)
        cpt.add_column("Aluguel CR",  justify="right", width=10)
        for _, cr in comp.iterrows():
            cpt.add_row(
                str(cr["mes"]),
                f"{cr['imoveis_renda_pct']:.1f}%",
                f"{cr['cri_pct']:.1f}%",
                f"{cr['lci_pct']:.1f}%",
                f"{cr['contas_receber_aluguel_pct']:.1f}%",
            )
        console.print(cpt)

    # Relatorio gerencial (enriquecimento via PDF + Claude)
    from src.storage.database import get_relatorio_gerencial
    row_f = df.iloc[0]
    cnpj_fii = row_f.get("cnpj") if "cnpj" in df.columns else None
    if cnpj_fii:
        rg = get_relatorio_gerencial(str(cnpj_fii))
        if rg:
            console.print("\n[bold]Relatorio gerencial (extrato via IA):[/bold]")
            rgt = Table(show_header=False, box=None, padding=(0, 2))
            rgt.add_column("Label",  style="dim")
            rgt.add_column("Valor",  style="bold")
            rgt.add_row("Competencia", str(rg.get("competencia", "--")))
            if rg.get("vacancia") is not None:
                rgt.add_row("Vacancia",    f"{rg['vacancia']:.1f}%")
            if rg.get("locatarios"):
                rgt.add_row("Locatarios",  str(rg["locatarios"])[:120])
            if rg.get("contratos"):
                rgt.add_row("Contratos",   str(rg["contratos"])[:120])
            if rg.get("alertas"):
                rgt.add_row("Alertas",     str(rg["alertas"])[:120])
            rgt.add_row("[dim]Fonte[/dim]", f"[dim]{str(rg.get('fonte_url',''))[:60]}[/dim]")
            console.print(rgt)

    # Historico P/VP (opcional)
    if pvp_hist:
        pvp_df = get_pvp_history(ticker, months=24)
        if not pvp_df.empty:
            console.print("\n[bold]Historico P/VP mensal (24 meses):[/bold]")
            pvp_media = pvp_df["p_vp"].mean()
            pvp_min   = pvp_df["p_vp"].min()
            pvp_max   = pvp_df["p_vp"].max()
            console.print(f"[dim]Media: {pvp_media:.3f}  Min: {pvp_min:.3f}  Max: {pvp_max:.3f}[/dim]")
            pt = Table(show_header=True, header_style="dim")
            pt.add_column("Mes",   width=8)
            pt.add_column("VPA",   justify="right", width=10)
            pt.add_column("Preco", justify="right", width=10)
            pt.add_column("P/VP",  justify="right", width=8)
            for _, pr in pvp_df.iterrows():
                pvp_cor = "green" if float(pr["p_vp"]) < pvp_media else "red"
                pt.add_row(
                    str(pr["mes"]),
                    f"R$ {pr['vpa']:.2f}" if pd.notna(pr.get("vpa")) else "--",
                    f"R$ {pr['preco']:.2f}" if pd.notna(pr.get("preco")) else "--",
                    f"[{pvp_cor}]{pr['p_vp']:.3f}[/{pvp_cor}]",
                )
            console.print(pt)


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
    export: str = typer.Option(
        None, "--export",
        help="Exportar historico para CSV ou Excel (ex: dividendos.csv).",
    ),
):
    """Historico de dividendos recebidos: YoC mensal, acumulado e payback."""
    from src.portfolio.relatorio import relatorio_dividendos
    from src.portfolio.carteira import get_historico_dividendos

    if export:
        from pathlib import Path
        df = get_historico_dividendos(ticker=ticker, desde=desde)
        if df.empty:
            console.print("[yellow]Sem dados para exportar.[/yellow]")
            return
        try:
            p = Path(export)
            if p.suffix.lower() in (".xlsx", ".xls"):
                df.to_excel(export, index=False)
            else:
                df.to_csv(export, index=False, encoding="utf-8-sig")
            console.print(f"[green]Exportado para:[/green] {export}  ({len(df)} linhas)")
        except Exception as e:
            console.print(f"[red]Erro ao exportar: {e}[/red]")
        return

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


@portfolio_app.command("allocation")
def portfolio_allocation():
    """Mostra alocacao da carteira por ativo e por segmento."""
    from src.portfolio.relatorio import relatorio_alocacao
    relatorio_alocacao()


@portfolio_app.command("income")
def portfolio_income(
    meses:    int = typer.Option(12, "--meses",    "-m", help="Numero de meses a exibir."),
    projecao: int = typer.Option(0,  "--projecao", "-p",
                                 help="Projeta os proximos N meses usando a media dos ultimos 6 reais."),
):
    """Exibe a renda mensal recebida em dividendos (grafico de barras no terminal)."""
    from src.portfolio.relatorio import relatorio_income
    relatorio_income(meses=meses, projecao=projecao)


@portfolio_app.command("watch")
def portfolio_watch(
    ticker:     str   = typer.Argument(..., help="Ticker do FII (ex: HGLG11)"),
    preco_alvo: float = typer.Option(None, "--preco-alvo", "-p", help="Preco alvo de entrada (R$)"),
    obs:        str   = typer.Option(None, "--obs",             help="Observacao opcional"),
    remove:     bool  = typer.Option(False, "--remove",         help="Remove o ticker da watchlist"),
):
    """Adiciona ou remove um FII da watchlist de acompanhamento."""
    import datetime as _dt
    from src.storage.database import upsert_watchlist, remove_watchlist

    from src.storage.database import init_db
    init_db()

    t = ticker.upper()
    if remove:
        ok = remove_watchlist(t)
        if ok:
            console.print(f"[green]{t} removido da watchlist.[/green]")
        else:
            console.print(f"[yellow]{t} nao estava na watchlist.[/yellow]")
        return

    upsert_watchlist({
        "ticker":      t,
        "preco_alvo":  preco_alvo,
        "obs":         obs,
        "adicionado_em": _dt.datetime.now().isoformat(timespec="seconds"),
    })
    msg = f"[green]{t} adicionado a watchlist.[/green]"
    if preco_alvo:
        msg += f"  Alvo: R$ {preco_alvo:.2f}"
    console.print(msg)


@portfolio_app.command("watchlist")
def portfolio_watchlist():
    """Exibe a watchlist com indicadores atuais dos FIIs monitorados."""
    import pandas as pd
    from src.storage.database import get_watchlist
    from src.analysis.indicadores import get_indicators_for

    from src.storage.database import init_db
    init_db()

    items = get_watchlist()
    if not items:
        console.print(
            "[yellow]Watchlist vazia. "
            "Adicione um FII com: python main.py portfolio watch TICKER[/yellow]"
        )
        return

    tickers = [r["ticker"] for r in items]
    ind = get_indicators_for(tickers)
    ind_map = {r["ticker"]: r for _, r in ind.iterrows()} if not ind.empty else {}

    t = Table(show_header=True, header_style="bold", title="Watchlist")
    t.add_column("Ticker",    style="cyan",    width=8)
    t.add_column("Preco",     justify="right", width=9)
    t.add_column("P. Alvo",   justify="right", width=9)
    t.add_column("Distancia", justify="right", width=10)
    t.add_column("P/VP",      justify="right", width=6)
    t.add_column("DY 12m",    justify="right", width=8)
    t.add_column("Spread",    justify="right", width=8)
    t.add_column("Obs",                        width=20)

    for item in items:
        tk    = item["ticker"]
        ind_r = ind_map.get(tk, {})

        preco     = ind_r.get("preco")
        preco_str = f"R$ {preco:.2f}" if preco and pd.notna(preco) else "--"

        alvo      = item.get("preco_alvo")
        alvo_str  = f"R$ {alvo:.2f}" if alvo else "--"

        if alvo and preco and pd.notna(preco):
            dist = (preco / alvo - 1) * 100
            cor  = "green" if dist <= 0 else "red"
            dist_str = f"[{cor}]{dist:+.1f}%[/{cor}]"
        else:
            dist_str = "--"

        pvp_v   = ind_r.get("p_vp")
        dy12_v  = ind_r.get("dy_12m")
        spr_v   = ind_r.get("spread_selic")

        t.add_row(
            tk,
            preco_str,
            alvo_str,
            dist_str,
            f"{pvp_v:.2f}"  if pvp_v  and pd.notna(pvp_v)  else "--",
            f"{dy12_v:.1f}%" if dy12_v and pd.notna(dy12_v) else "--",
            f"{spr_v:.1f}%"  if spr_v  and pd.notna(spr_v)  else "--",
            str(item.get("obs") or "")[:20],
        )

    console.print(t)


@portfolio_app.command("enrich")
def portfolio_enrich(
    ticker: str  = typer.Argument(None, help="Ticker especifico (opcional). Padrao: toda a carteira + watchlist."),
    forcar: bool = typer.Option(False, "--force", "-f", help="Reprocessa mesmo que ja haja dado do mes atual."),
):
    """
    Enriquece relatorios gerenciais via FundosNet + Claude API.

    Baixa o ultimo relatorio gerencial de cada fundo da carteira e watchlist,
    extrai vacancia, contratos, locatarios e alertas do gestor, e armazena no banco.

    Requer: pip install anthropic>=0.40.0  e  variavel ANTHROPIC_API_KEY definida.

    Exemplos:
        python main.py portfolio enrich
        python main.py portfolio enrich HGLG11
        python main.py portfolio enrich --force
    """
    from src.portfolio.enrich import enriquecer, EnrichError
    from src.storage.database import init_db
    init_db()

    console.print(
        "[bold cyan]Enriquecimento via FundosNet + Claude API[/bold cyan]"
    )
    console.print(
        "[dim]Escopo: carteira ativa + watchlist. Cache: 1 relatorio por fundo por mes.[/dim]\n"
    )

    try:
        resultados = enriquecer(ticker=ticker, forcar=forcar, verbose=False)
    except Exception as e:
        console.print(f"[red]Erro: {e}[/red]")
        raise typer.Exit(code=1)

    t = Table(show_header=True, header_style="bold")
    t.add_column("Ticker",  style="cyan", width=8)
    t.add_column("Status",               width=10)
    t.add_column("Detalhe")

    _CORES = {"ok": "green", "cache": "dim", "sem_pdf": "yellow", "erro": "red"}
    _ICONS = {"ok": "ok", "cache": "cache", "sem_pdf": "sem PDF", "erro": "ERRO"}

    for r in resultados:
        cor   = _CORES.get(r["status"], "white")
        label = _ICONS.get(r["status"], r["status"])
        t.add_row(
            r["ticker"],
            f"[{cor}]{label}[/{cor}]",
            str(r.get("mensagem", ""))[:80],
        )

    console.print(t)
    n_ok = sum(1 for r in resultados if r["status"] == "ok")
    n_cache = sum(1 for r in resultados if r["status"] == "cache")
    console.print(
        f"\n[dim]{n_ok} novo(s) processado(s), {n_cache} do cache. "
        "Use 'python main.py info TICKER' para ver os dados extraidos.[/dim]"
    )


# ---------------------------------------------------------------------------
# Analise de segmento
# ---------------------------------------------------------------------------

@app.command()
def segment(
    nome:    str  = typer.Argument(None,  help="Filtro de segmento (parcial, ex: 'logistica'). Sem argumento: visao geral."),
    top:     int  = typer.Option(5, "--top", "-t", help="Numero de FIIs a exibir por segmento."),
    dy_min:  float = typer.Option(None,   "--dy-min",  help="Filtro DY 12m minimo (%)."),
    pvp_max: float = typer.Option(None,   "--pvp-max", help="Filtro P/VP maximo."),
):
    """
    Analisa FIIs por segmento de mercado.

    Sem argumentos: visao geral com medianas de DY, P/VP, spread e liquidez por segmento.
    Com nome de segmento: ranking dos melhores FIIs daquele segmento.

    Exemplos:
        python main.py segment
        python main.py segment logistica
        python main.py segment logistica --top 10
        python main.py segment "lajes corporativas" --dy-min 9
    """
    import pandas as pd
    from src.analysis.indicadores import get_all_indicators
    from src.analysis.screener import _add_score, _DEFAULT_WEIGHTS

    df = get_all_indicators()
    if df.empty:
        console.print("[yellow]Sem dados. Rode: python main.py update[/yellow]")
        return

    # Aplica filtros opcionais
    if dy_min is not None:
        df = df[df["dy_12m"].fillna(0) >= dy_min]
    if pvp_max is not None:
        df = df[df["p_vp"].fillna(999) <= pvp_max]

    df["segmento"] = df["segmento"].fillna("Outros")

    if nome:
        # Modo detalhe: top FIIs do segmento
        mask = df["segmento"].str.lower().str.contains(nome.lower(), na=False)
        sub = df[mask].copy()
        if sub.empty:
            console.print(f"[yellow]Segmento '{nome}' nao encontrado ou sem FIIs com dados.[/yellow]")
            return

        segs_encontrados = sub["segmento"].unique().tolist()
        seg_label = segs_encontrados[0] if len(segs_encontrados) == 1 else nome
        console.print(f"\n[bold cyan]Segmento: {seg_label}[/bold cyan]  ({len(sub)} FIIs com dados)")

        sub = _add_score(sub.copy(), _DEFAULT_WEIGHTS)
        sub = sub.sort_values("score", ascending=False).head(top).reset_index(drop=True)

        t = Table(show_header=True, header_style="bold", title=f"Top {len(sub)} -- {seg_label}")
        t.add_column("#",         justify="right", width=3)
        t.add_column("Ticker",    style="cyan",    width=8)
        t.add_column("Preco",     justify="right", width=9)
        t.add_column("P/VP",      justify="right", width=6)
        t.add_column("DY 12m",    justify="right", width=8)
        t.add_column("Spread",    justify="right", width=8)
        t.add_column("Liq 30d",   justify="right", width=10)
        t.add_column("Score",     justify="right", width=6)

        for i, r in sub.iterrows():
            t.add_row(
                str(i + 1),
                r["ticker"],
                f"R$ {r['preco']:.2f}"       if pd.notna(r.get("preco"))         else "--",
                f"{r['p_vp']:.2f}"           if pd.notna(r.get("p_vp"))          else "--",
                f"{r['dy_12m']:.1f}%"        if pd.notna(r.get("dy_12m"))        else "--",
                f"{r['spread_selic']:.1f}%"  if pd.notna(r.get("spread_selic"))  else "--",
                _fmt_reais(r.get("liquidez_30d")),
                f"{r['score']:.0f}"          if pd.notna(r.get("score"))         else "--",
            )
        console.print(t)

        # Medianas do segmento para contexto
        console.print("\n[dim]Medianas do segmento:[/dim]")
        mt = Table(show_header=False, box=None, padding=(0, 2))
        mt.add_column("Indicador", style="dim")
        mt.add_column("Mediana", style="bold")
        for col, label in [("dy_12m", "DY 12m"), ("p_vp", "P/VP"),
                            ("spread_selic", "Spread vs SELIC"), ("consistencia_dy", "Consist. DY")]:
            v = sub[col].median() if col in sub.columns else None
            if pd.notna(v):
                if col in ("dy_12m", "spread_selic", "consistencia_dy"):
                    mt.add_row(label, f"{v:.2f}%")
                else:
                    mt.add_row(label, f"{v:.3f}")
        console.print(mt)

    else:
        # Modo visao geral: uma linha por segmento com medianas
        console.print("\n[bold]Analise por segmento[/bold]")

        seg_stats = (
            df.groupby("segmento")
            .agg(
                n_fiis=("ticker", "count"),
                dy_med=("dy_12m", "median"),
                pvp_med=("p_vp", "median"),
                spread_med=("spread_selic", "median"),
                liq_med=("liquidez_30d", "median"),
            )
            .reset_index()
            .sort_values("dy_med", ascending=False)
        )

        t = Table(show_header=True, header_style="bold", title="Medianas por segmento")
        t.add_column("Segmento",     width=28)
        t.add_column("N",            justify="right", width=4)
        t.add_column("DY 12m med",   justify="right", width=10)
        t.add_column("P/VP med",     justify="right", width=9)
        t.add_column("Spread med",   justify="right", width=10)
        t.add_column("Liq med",      justify="right", width=11)

        for _, r in seg_stats.iterrows():
            t.add_row(
                str(r["segmento"])[:28],
                str(int(r["n_fiis"])),
                f"{r['dy_med']:.1f}%"       if pd.notna(r.get("dy_med"))      else "--",
                f"{r['pvp_med']:.3f}"       if pd.notna(r.get("pvp_med"))     else "--",
                f"{r['spread_med']:.1f}%"   if pd.notna(r.get("spread_med"))  else "--",
                _fmt_reais(r.get("liq_med")),
            )
        console.print(t)
        console.print(
            f"\n[dim]{len(seg_stats)} segmentos, {len(df)} FIIs com dados. "
            "Para detalhar um segmento: python main.py segment <nome>[/dim]"
        )


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def _print_scenario(label: str, sc, console) -> None:
    """Exibe os resultados de um ScenarioResult no terminal."""
    import pandas as pd

    console.print(f"\n[bold]{label}: {sc.ticker}[/bold]  (entrada: {sc.mes_inicio})")
    console.print(
        f"  Cotas: {sc.cotas:.2f}  |  "
        f"Preco entrada: R$ {sc.preco_entrada:.2f}  |  "
        f"Capital: R$ {sc.capital_investido:,.2f}"
    )

    preco_str = f"R$ {sc.preco_atual:.2f}" if sc.preco_atual is not None else "--"
    valor_str = f"R$ {sc.valor_atual:,.2f}" if sc.valor_atual is not None else "--"
    ret_str   = (
        f"{sc.total_return:+.2f}%"
        if sc.total_return is not None
        else "--"
    )
    cor_ret = "green" if (sc.total_return or 0) >= 0 else "red"

    console.print(f"  Preco atual ({label.lower()} mes fechado): {preco_str}")
    console.print(f"  Valor atual: {valor_str}")
    console.print(f"  Dividendos recebidos: R$ {sc.dividendos_total:,.2f}")
    console.print(f"  Retorno total: [{cor_ret}]{ret_str}[/{cor_ret}]")

    if not sc.dividendos_mensais.empty:
        console.print(f"\n  [dim]Dividendos mensais ({len(sc.dividendos_mensais)} meses):[/dim]")
        dt = Table(show_header=True, header_style="dim", box=None, padding=(0, 1))
        dt.add_column("Mes",          width=8)
        dt.add_column("DY mes",       justify="right", width=8)
        dt.add_column("Preco cota",   justify="right", width=10)
        dt.add_column("Div/cota",     justify="right", width=9)
        dt.add_column("Recebido",     justify="right", width=12)
        for _, dr in sc.dividendos_mensais.iterrows():
            dt.add_row(
                str(dr["mes"]),
                f"{dr['dy_mes']*100:.2f}%"     if pd.notna(dr.get("dy_mes"))           else "--",
                f"R$ {dr['preco_cota']:.2f}"   if pd.notna(dr.get("preco_cota"))       else "--",
                f"R$ {dr['dividendo_cota']:.4f}" if pd.notna(dr.get("dividendo_cota")) else "--",
                f"R$ {dr['dividendo_recebido']:.2f}" if pd.notna(dr.get("dividendo_recebido")) else "--",
            )
        console.print(dt)

    for aviso in sc.avisos:
        console.print(f"  [yellow]Aviso: {aviso}[/yellow]")


@backtest_app.command("swap")
def backtest_swap(
    ticker_out: str   = typer.Argument(...,  help="Ticker que seria vendido (ex: VISC11)"),
    ticker_in:  str   = typer.Argument(...,  help="Ticker que seria comprado (ex: HGLG11)"),
    mes:        str   = typer.Argument(...,  help="Mes hipotetico da troca (YYYY-MM)"),
    cotas:      float = typer.Option(None,   "--cotas", "-c", help="Cotas de ticker_out. Padrao: busca da carteira."),
):
    """
    Simula o que teria acontecido se voce tivesse trocado um FII por outro.

    Compara o cenario real (manter ticker_out) com o hipotetico (comprar ticker_in
    com o mesmo capital). Mostra dividendos recebidos e retorno total em ambos.

    Exemplo:
        python main.py backtest swap VISC11 HGLG11 2024-06
        python main.py backtest swap VISC11 HGLG11 2024-06 --cotas 200
    """
    from src.analysis.backtest import simular_swap, BacktestError

    try:
        resultado = simular_swap(ticker_out, ticker_in, mes, cotas=cotas)
    except BacktestError as e:
        console.print(f"[red]Erro: {e}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold cyan]Backtest -- Swap hipotetico[/bold cyan]  "
        f"{resultado.ticker_out} -> {resultado.ticker_in}  em {resultado.mes}"
    )
    console.print("[dim]Comparacao: manter o FII original vs. ter trocado pelo alternativo.[/dim]")

    _print_scenario("Real", resultado.real, console)
    _print_scenario("Simulado", resultado.simulado, console)

    # Resumo comparativo
    real = resultado.real
    sim  = resultado.simulado
    console.print("\n[bold]Comparacao:[/bold]")
    ct = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    ct.add_column("",              width=22)
    ct.add_column(real.ticker,     justify="right", width=14)
    ct.add_column(sim.ticker,      justify="right", width=14)
    ct.add_column("Delta",         justify="right", width=12)

    def _fmt_r(v):
        return f"R$ {v:,.2f}" if v is not None else "--"

    def _fmt_p(v):
        if v is None:
            return "--"
        cor = "green" if v >= 0 else "red"
        return f"[{cor}]{v:+.2f}%[/{cor}]"

    def _delta_r(a, b):
        if a is None or b is None:
            return "--"
        d = b - a
        cor = "green" if d >= 0 else "red"
        return f"[{cor}]{'+' if d >= 0 else ''}{d:,.2f}[/{cor}]"

    def _delta_p(a, b):
        if a is None or b is None:
            return "--"
        d = b - a
        cor = "green" if d >= 0 else "red"
        return f"[{cor}]{d:+.2f} p.p.[/{cor}]"

    ct.add_row("Capital investido",  _fmt_r(real.capital_investido),  _fmt_r(sim.capital_investido),  _delta_r(real.capital_investido,  sim.capital_investido))
    ct.add_row("Dividendos totais",  _fmt_r(real.dividendos_total),   _fmt_r(sim.dividendos_total),   _delta_r(real.dividendos_total,   sim.dividendos_total))
    ct.add_row("Valor atual",        _fmt_r(real.valor_atual),        _fmt_r(sim.valor_atual),        _delta_r(real.valor_atual,        sim.valor_atual))
    ct.add_row("Retorno total",      _fmt_p(real.total_return),       _fmt_p(sim.total_return),       _delta_p(real.total_return,       sim.total_return))

    console.print(ct)
    console.print("\n[dim]Custos operacionais (corretagem, IR) nao estao modelados.[/dim]")


@backtest_app.command("add")
def backtest_add(
    ticker:  str   = typer.Argument(..., help="Ticker do FII (ex: HGLG11)"),
    mes:     str   = typer.Argument(..., help="Mes hipotetico de compra (YYYY-MM)"),
    cotas:   float = typer.Option(None, "--cotas",   "-c", help="Numero de cotas"),
    capital: float = typer.Option(None, "--capital", "-k", help="Capital a investir em R$"),
):
    """
    Simula o que teria acontecido se voce tivesse comprado um FII em determinado mes.

    Informe --cotas OU --capital (nao ambos).

    Exemplos:
        python main.py backtest add HGLG11 2024-01 --cotas 100
        python main.py backtest add HGLG11 2024-01 --capital 16500
    """
    from src.analysis.backtest import simular_add, BacktestError

    try:
        resultado = simular_add(ticker, mes, cotas=cotas, capital=capital)
    except BacktestError as e:
        console.print(f"[red]Erro: {e}[/red]")
        raise typer.Exit(code=1)

    sc = resultado.simulado
    console.print(
        f"\n[bold cyan]Backtest -- Compra hipotetica[/bold cyan]  "
        f"{sc.ticker}  em {sc.mes_inicio}"
    )
    console.print("[dim]Simulacao: resultado se tivesse comprado o FII neste mes.[/dim]")

    _print_scenario("Simulado", sc, console)
    console.print("\n[dim]Custos operacionais (corretagem, IR) nao estao modelados.[/dim]")


if __name__ == "__main__":
    app()
