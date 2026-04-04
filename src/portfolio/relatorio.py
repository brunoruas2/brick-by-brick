"""
Relatorios de carteira para o terminal (rich).

show_posicoes()       -- visao rapida das posicoes com P&L de capital
relatorio_mensal()    -- relatorio mensal detalhado: posicoes + proventos + benchmarks
"""

from datetime import date

import pandas as pd
from rich.console import Console
from rich.table import Table

from src.portfolio.carteira import get_posicoes, get_movimentacoes
from src.storage.database import connect

console = Console()


def _fmt_brl(v) -> str:
    if v is None or (hasattr(v, "__class__") and pd.isna(v)):
        return "--"
    return f"R$ {float(v):,.2f}"


def _fmt_pct(v, decimals: int = 2) -> str:
    if v is None or (hasattr(v, "__class__") and pd.isna(v)):
        return "--"
    return f"{float(v):.{decimals}f}%"


def _color_pl(v, fmt: str) -> str:
    """Envolve uma string de valor em markup de cor verde/vermelho."""
    if v is None or (hasattr(v, "__class__") and pd.isna(v)):
        return "--"
    color = "green" if float(v) >= 0 else "red"
    sign = "+" if float(v) >= 0 else ""
    return f"[{color}]{sign}{fmt}[/{color}]"


# ---------------------------------------------------------------------------
# Visao rapida das posicoes
# ---------------------------------------------------------------------------

def show_posicoes() -> None:
    """
    Exibe tabela rapida das posicoes ativas com preco atual e P&L de capital.
    """
    df = get_posicoes()
    if df.empty:
        console.print(
            "[yellow]Carteira vazia. "
            "Use: python main.py portfolio add TICKER COTAS PRECO DATA[/yellow]"
        )
        return

    t = Table(show_header=True, header_style="bold", title="Carteira atual")
    t.add_column("Ticker",   style="cyan",    min_width=7)
    t.add_column("Cotas",    justify="right", min_width=6)
    t.add_column("P. Medio", justify="right", min_width=9)
    t.add_column("Custo",    justify="right", min_width=12)
    t.add_column("P. Atual", justify="right", min_width=9)
    t.add_column("Valor",    justify="right", min_width=12)
    t.add_column("P&L",      justify="right", min_width=12)
    t.add_column("P&L %",    justify="right", min_width=7)
    t.add_column("DY mes",   justify="right", min_width=7)

    total_custo  = 0.0
    total_valor  = 0.0
    total_pl     = 0.0
    has_prices   = False

    for _, r in df.iterrows():
        total_custo += float(r["custo_total"] or 0)
        if pd.notna(r.get("valor_atual")):
            total_valor += float(r["valor_atual"])
            total_pl    += float(r.get("pl_capital") or 0)
            has_prices   = True

        # P&L com cor
        pl_str  = _color_pl(r.get("pl_capital"), f"R$ {abs(float(r['pl_capital'])):.2f}")  \
                  if pd.notna(r.get("pl_capital")) else "--"
        pct_str = _color_pl(r.get("pl_pct"), f"{abs(float(r['pl_pct'])):.1f}%") \
                  if pd.notna(r.get("pl_pct")) else "--"

        t.add_row(
            r["ticker"],
            str(int(r["cotas"])),
            f"R$ {r['preco_medio']:.2f}",
            f"R$ {r['custo_total']:,.2f}",
            f"R$ {r['preco_atual']:.2f}" if pd.notna(r.get("preco_atual")) else "--",
            f"R$ {r['valor_atual']:,.2f}" if pd.notna(r.get("valor_atual")) else "--",
            pl_str,
            pct_str,
            _fmt_pct(r.get("dy_mes")),
        )

    console.print(t)

    # Rodape de totais
    console.print()
    st = Table(show_header=False, box=None, padding=(0, 2))
    st.add_column("Label", style="dim")
    st.add_column("Valor", style="bold")
    st.add_row("Custo total", f"R$ {total_custo:,.2f}")
    if has_prices:
        st.add_row("Valor atual", f"R$ {total_valor:,.2f}")
        pct_total = (total_pl / total_custo * 100) if total_custo > 0 else 0
        st.add_row(
            "P&L total",
            _color_pl(total_pl, f"R$ {abs(total_pl):,.2f}  ({abs(pct_total):.1f}%)"),
        )
    console.print(st)


# ---------------------------------------------------------------------------
# Relatorio mensal
# ---------------------------------------------------------------------------

def relatorio_mensal(month: str | None = None) -> None:
    """
    Relatorio mensal detalhado: posicoes, proventos estimados, YoC e benchmarks.

    month: YYYY-MM. Padrao: mes corrente.
    """
    if month is None:
        month = date.today().strftime("%Y-%m")

    df = get_posicoes()
    if df.empty:
        console.print(
            "[yellow]Carteira vazia. "
            "Use: python main.py portfolio add TICKER COTAS PRECO DATA[/yellow]"
        )
        return

    # Benchmarks do mes
    with connect() as conn:
        bench = conn.execute(
            "SELECT selic_mes, ipca_mes FROM benchmarks WHERE strftime('%Y-%m', data) = ?",
            (month,),
        ).fetchone()
    selic_mes = float(bench["selic_mes"]) if bench and bench["selic_mes"] else None
    ipca_mes  = float(bench["ipca_mes"])  if bench and bench["ipca_mes"]  else None

    # Calcula YoC mensal por posicao
    def _yoc_mes(row):
        if pd.notna(row.get("provento_est")) and (row.get("custo_total") or 0) > 0:
            return round(float(row["provento_est"]) / float(row["custo_total"]) * 100, 4)
        return None

    df["yoc_mes"] = df.apply(_yoc_mes, axis=1)

    # Tabela de posicoes
    console.print(f"\n[bold]Relatorio mensal -- {month}[/bold]")
    t = Table(show_header=True, header_style="bold")
    t.add_column("Ticker",    style="cyan",    width=8)
    t.add_column("Cotas",     justify="right", width=7)
    t.add_column("P. Medio",  justify="right", width=10)
    t.add_column("P. Atual",  justify="right", width=10)
    t.add_column("Custo",     justify="right", width=13)
    t.add_column("Valor",     justify="right", width=13)
    t.add_column("P&L",       justify="right", width=13)
    t.add_column("Prov. est", justify="right", width=10)
    t.add_column("YoC mes",   justify="right", width=8)

    total_custo    = 0.0
    total_valor    = 0.0
    total_pl       = 0.0
    total_provento = 0.0
    has_prices     = False

    for _, r in df.iterrows():
        total_custo += float(r["custo_total"] or 0)
        if pd.notna(r.get("valor_atual")):
            total_valor += float(r["valor_atual"])
            total_pl    += float(r.get("pl_capital") or 0)
            has_prices   = True
        if pd.notna(r.get("provento_est")):
            total_provento += float(r["provento_est"])

        pl_str = _color_pl(r.get("pl_capital"), f"R$ {abs(float(r['pl_capital'])):.2f}") \
                 if pd.notna(r.get("pl_capital")) else "--"

        t.add_row(
            r["ticker"],
            str(int(r["cotas"])),
            f"R$ {r['preco_medio']:.2f}",
            f"R$ {r['preco_atual']:.2f}" if pd.notna(r.get("preco_atual")) else "--",
            f"R$ {r['custo_total']:,.2f}",
            f"R$ {r['valor_atual']:,.2f}" if pd.notna(r.get("valor_atual")) else "--",
            pl_str,
            f"R$ {r['provento_est']:.2f}" if pd.notna(r.get("provento_est")) else "--",
            _fmt_pct(r.get("yoc_mes")),
        )

    console.print(t)

    # Resumo consolidado
    console.print()
    st = Table(show_header=False, box=None, padding=(0, 2))
    st.add_column("Label", style="dim")
    st.add_column("Valor", style="bold")

    st.add_row("Custo total", f"R$ {total_custo:,.2f}")
    if has_prices:
        st.add_row("Valor atual", f"R$ {total_valor:,.2f}")
        pct_total = (total_pl / total_custo * 100) if total_custo > 0 else 0
        st.add_row(
            "P&L capital",
            _color_pl(total_pl, f"R$ {abs(total_pl):,.2f}  ({abs(pct_total):.1f}%)"),
        )

    if total_provento > 0:
        st.add_row("Proventos est. mes", f"R$ {total_provento:.2f}")
        if total_custo > 0:
            yoc_mes  = total_provento / total_custo * 100
            yoc_anual = yoc_mes * 12
            st.add_row("YoC mensal / anual", f"{yoc_mes:.2f}% / {yoc_anual:.2f}%")

    if selic_mes is not None:
        st.add_row("SELIC do mes", _fmt_pct(selic_mes))
        if total_provento > 0 and total_custo > 0:
            yoc = total_provento / total_custo * 100
            spread = yoc - selic_mes
            st.add_row(
                "Spread YoC vs SELIC",
                _color_pl(spread, f"{abs(spread):.2f}%"),
            )
    if ipca_mes is not None:
        st.add_row("IPCA do mes", _fmt_pct(ipca_mes))

    console.print(st)

    # Historico de movimentacoes do mes (se houver)
    movs = get_movimentacoes()
    if not movs.empty:
        movs_mes = movs[movs["data"].str.startswith(month)]
        if not movs_mes.empty:
            console.print(f"\n[bold]Movimentacoes em {month}:[/bold]")
            mt = Table(show_header=True, header_style="dim")
            mt.add_column("Data",    width=12)
            mt.add_column("Ticker",  style="cyan", width=8)
            mt.add_column("Tipo",    width=8)
            mt.add_column("Cotas",   justify="right", width=7)
            mt.add_column("Preco",   justify="right", width=10)
            mt.add_column("Total",   justify="right", width=13)
            for _, m in movs_mes.iterrows():
                mt.add_row(
                    str(m["data"]),
                    str(m["ticker"]),
                    str(m["tipo"]),
                    str(int(m["quantidade"])) if pd.notna(m.get("quantidade")) else "--",
                    f"R$ {m['preco_unitario']:.2f}" if pd.notna(m.get("preco_unitario")) else "--",
                    f"R$ {m['valor_total']:.2f}",
                )
            console.print(mt)
