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


@app.command()
def update(
    source: str = typer.Argument(
        "all",
        help="Fonte: all | cadastro | inf-mensal | cotahist | benchmarks",
    ),
):
    """
    Baixa dados das fontes primarias (CVM, B3, BCB) e salva no banco local.

    Sem argumentos atualiza todas as fontes. Idempotente.
    """
    from src.storage.database import (
        init_db, upsert_fiis, upsert_inf_mensal, update_fiis_metadata,
        upsert_cotacoes, upsert_benchmarks, update_fiis_isin,
        upsert_isin_ticker, link_tickers,
    )
    from src.collectors import cvm_cadastro, cvm_inf_mensal

    console.print(Panel.fit("Brick by Brick -- Atualizacao de dados", style="bold blue"))
    init_db()
    console.print("[dim]  Banco:[/dim] data/brickbybrick.sqlite\n")

    targets = _SOURCES_AVAILABLE if source == "all" else [source]

    for t in targets:
        if t not in _SOURCES_AVAILABLE:
            console.print(
                f"[red]Fonte desconhecida: '{t}'. "
                f"Disponiveis: {', '.join(_SOURCES_AVAILABLE)}[/red]"
            )
            raise typer.Exit(code=1)

    results: list[tuple[str, int]] = []

    # 1.1 Cadastro de FIIs (CVM)
    if "cadastro" in targets:
        records = cvm_cadastro.fetch()
        results.append(("Cadastro CVM", upsert_fiis(records)))

    # 1.2 Informe Mensal (CVM)
    if "inf-mensal" in targets:
        inf_records, meta_records = cvm_inf_mensal.fetch()
        results.append(("Informe Mensal CVM", upsert_inf_mensal(inf_records)))
        results.append(("  segmento/mandato", update_fiis_metadata(meta_records)))
        update_fiis_isin(meta_records)

    # 1.4 Cotacoes historicas B3 (COTAHIST)
    if "cotahist" in targets:
        from src.collectors import b3_cotahist
        cotacao_records, isin_ticker_records = b3_cotahist.fetch()
        results.append(("COTAHIST B3", upsert_cotacoes(cotacao_records)))
        upsert_isin_ticker(isin_ticker_records)

    # 1.5 Benchmarks BCB
    if "benchmarks" in targets:
        from src.collectors import bcb_series
        results.append(("Benchmarks BCB (24m)", upsert_benchmarks(bcb_series.fetch(months=24))))

    # Vincula tickers a CNPJs via ISIN
    n_linked = link_tickers()
    results.append(("  tickers vinculados a CNPJs", n_linked))

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


if __name__ == "__main__":
    app()
