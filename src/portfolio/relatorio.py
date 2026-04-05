"""
Relatorios de carteira para o terminal (rich).

show_posicoes()       -- visao rapida das posicoes com P&L de capital
relatorio_mensal()    -- relatorio mensal detalhado: posicoes + proventos + benchmarks
"""

from datetime import date

import pandas as pd
from rich.console import Console
from rich.table import Table

from src.portfolio.carteira import get_posicoes, get_movimentacoes, get_historico_dividendos
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
            f"{r['dy_mes']*100:.2f}%" if pd.notna(r.get("dy_mes")) else "--",
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

    df = get_posicoes(month=month)
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


# ---------------------------------------------------------------------------
# Historico de dividendos
# ---------------------------------------------------------------------------

def relatorio_dividendos(
    ticker: str | None = None,
    desde: str | None = None,
    resumo: bool = False,
) -> None:
    """
    Exibe historico de dividendos recebidos pela carteira.

    ticker: filtra por ativo (opcional)
    desde:  YYYY-MM -- mostra apenas a partir deste mes (opcional)
    resumo: True => exibe apenas o sumario consolidado, sem detalhe mensal
    """
    df = get_historico_dividendos(ticker=ticker, desde=desde)

    if df.empty:
        console.print(
            "[yellow]Sem historico de dividendos. "
            "Verifique se a carteira tem movimentacoes e se os dados estao atualizados.[/yellow]"
        )
        return

    # Avisa sobre meses sem DY (dados nao baixados para aquele periodo)
    sem_dy = df["dy_mes"].isna().sum()
    total  = len(df)
    if sem_dy > 0:
        mes_min = df.loc[df["dy_mes"].isna(), "mes"].min()
        console.print(
            f"[yellow]Aviso: {sem_dy}/{total} mes(es) sem DY disponivel "
            f"(primeiro: {mes_min}). "
            f"Para baixar dados mais antigos: "
            f"python main.py update inf-mensal --desde-ano {mes_min[:4]}[/yellow]"
        )

    tickers = df["ticker"].unique().tolist()

    # Anomalias de grupamento para os tickers da carteira
    from src.portfolio.grupamentos import detectar_anomalias
    anomalias = detectar_anomalias(tickers=tickers)
    if anomalias:
        console.print()
        console.print("[bold yellow]Possiveis grupamentos detectados:[/bold yellow]")
        at = Table(show_header=True, header_style="yellow")
        at.add_column("Ticker",    style="cyan", width=8)
        at.add_column("Mes",       width=8)
        at.add_column("Fator est.", justify="right", width=10)
        at.add_column("Confianca", width=8)
        at.add_column("Sinais")
        for a in anomalias:
            cor = "green" if a["confianca"] == "alta" else "yellow" if a["confianca"] == "media" else "dim"
            at.add_row(
                a["ticker"],
                a["mes"],
                f"{a['fator_estimado']}:1",
                f"[{cor}]{a['confianca']}[/{cor}]",
                a["sinais"],
            )
        console.print(at)
        console.print(
            "[dim]Para registrar um grupamento confirmado: "
            "python main.py portfolio add-split TICKER YYYY-MM FATOR[/dim]"
        )
        console.print()

    # ------------------------------------------------------------------
    # Detalhe mensal por ativo (omitido em modo resumo)
    # ------------------------------------------------------------------
    if not resumo:
        for t in tickers:
            sub = df[df["ticker"] == t].sort_values("mes")
            console.print(f"\n[bold cyan]{t}[/bold cyan] -- dividendos mensais")

            dt = Table(show_header=True, header_style="bold")
            dt.add_column("Mes",       width=8)
            dt.add_column("Cotas",     justify="right", width=7)
            dt.add_column("P. Cota",   justify="right", width=11)
            dt.add_column("DY mes",    justify="right", width=8)
            dt.add_column("Div/cota",  justify="right", width=11)
            dt.add_column("Recebido",  justify="right", width=12)
            dt.add_column("YoC mes",   justify="right", width=8)

            for _, r in sub.iterrows():
                preco_str = f"R$ {r['preco_cota']:.2f}" if pd.notna(r.get("preco_cota")) else "--"
                dy_str    = f"{r['dy_mes']*100:.2f}%"    if pd.notna(r.get("dy_mes"))    else "--"
                dcota_str = f"R$ {r['dividendo_cota']:.4f}" if pd.notna(r.get("dividendo_cota")) else "--"
                rec_str   = f"R$ {r['dividendo_recebido']:.2f}" if pd.notna(r.get("dividendo_recebido")) else "--"
                yoc_str   = f"{r['yoc_mes']:.4f}%"      if pd.notna(r.get("yoc_mes"))   else "--"

                dt.add_row(
                    str(r["mes"])[:7],
                    str(int(r["cotas"])),
                    preco_str,
                    dy_str,
                    dcota_str,
                    rec_str,
                    yoc_str,
                )

            console.print(dt)

    # ------------------------------------------------------------------
    # Sumario por ativo
    # ------------------------------------------------------------------
    console.print("\n[bold]Sumario por ativo[/bold]")
    st = Table(show_header=True, header_style="bold")
    st.add_column("Ticker",        style="cyan",    width=8)
    st.add_column("Custo medio",   justify="right", width=13)
    st.add_column("Meses",         justify="right", width=7)
    st.add_column("Recebido total",justify="right", width=14)
    st.add_column("YoC acum.",     justify="right", width=10)
    st.add_column("Vol. mensal",   justify="right", width=11)
    st.add_column("Payback est.",  justify="right", width=11)

    total_recebido_geral  = 0.0
    total_custo_geral     = 0.0
    total_div_media_geral = 0.0

    for t in tickers:
        sub = df[df["ticker"] == t].dropna(subset=["dividendo_recebido"])
        if sub.empty:
            continue

        custo_total  = sub["custo_total"].iloc[-1]           # ultimo mes = posicao atual
        meses        = len(sub)
        recebido     = sub["dividendo_recebido"].sum()
        yoc_acum     = (recebido / custo_total * 100) if custo_total > 0 else None

        # Payback em meses: custo_total / media dos ultimos 6 meses com dados
        ultimos   = sub.tail(6)["dividendo_recebido"]
        div_media = ultimos.mean() if len(ultimos) > 0 else None
        if div_media and div_media > 0 and custo_total > 0:
            payback_meses = custo_total / div_media
        else:
            payback_meses = None

        total_recebido_geral  += recebido
        total_custo_geral     += custo_total
        total_div_media_geral += div_media if div_media else 0.0

        vol_renda   = sub["dividendo_recebido"].std()
        yoc_str     = f"{yoc_acum:.2f}%"         if yoc_acum      is not None else "--"
        vol_str     = f"R$ {vol_renda:.2f}"       if pd.notna(vol_renda)       else "--"
        payback_str = f"~{payback_meses:.0f} m"   if payback_meses is not None else "--"

        st.add_row(
            t,
            f"R$ {custo_total:,.2f}",
            str(meses),
            f"R$ {recebido:,.2f}",
            yoc_str,
            vol_str,
            payback_str,
        )

    console.print(st)

    # ------------------------------------------------------------------
    # Total geral
    # ------------------------------------------------------------------
    if total_custo_geral > 0:
        yoc_geral = total_recebido_geral / total_custo_geral * 100
        console.print()
        gt = Table(show_header=False, box=None, padding=(0, 2))
        gt.add_column("Label", style="dim")
        gt.add_column("Valor", style="bold")
        gt.add_row("Total recebido em dividendos", f"R$ {total_recebido_geral:,.2f}")
        gt.add_row(
            "YoC acumulado",
            _color_pl(yoc_geral - 0.001, f"{yoc_geral:.2f}% do custo total recuperado"),
        )
        if total_div_media_geral > 0:
            payback_geral = total_custo_geral / total_div_media_geral
            gt.add_row(
                "Payback estimado",
                f"~{payback_geral:.0f} meses ({payback_geral / 12:.1f} anos) no ritmo atual",
            )
        console.print(gt)


# ---------------------------------------------------------------------------
# Alocacao da carteira
# ---------------------------------------------------------------------------

def relatorio_alocacao() -> None:
    """Mostra alocacao da carteira por ativo e por segmento."""
    from src.analysis.indicadores import get_indicators_for

    df = get_posicoes()
    if df.empty:
        console.print(
            "[yellow]Carteira vazia. "
            "Use: python main.py portfolio add TICKER COTAS PRECO DATA[/yellow]"
        )
        return

    tickers = df["ticker"].tolist()
    ind_all = get_indicators_for(tickers)
    if not ind_all.empty and "segmento" in ind_all.columns:
        ind = ind_all[["ticker", "segmento"]]
        df = df.merge(ind, on="ticker", how="left")
    else:
        df["segmento"] = None

    if "segmento" not in df.columns:
        df["segmento"] = None

    # valor_atual da posicao ou custo como fallback
    df["valor_ref"] = df["valor_atual"].fillna(df["custo_total"])
    total = df["valor_ref"].sum()
    if total == 0:
        console.print("[yellow]Sem dados de preco para calcular alocacao.[/yellow]")
        return

    df["peso"] = df["valor_ref"] / total * 100
    df = df.sort_values("peso", ascending=False).reset_index(drop=True)

    # --- Por ativo ---
    console.print("\n[bold]Alocacao por ativo[/bold]")
    t = Table(show_header=True, header_style="bold")
    t.add_column("#",        justify="right",  width=3)
    t.add_column("Ticker",   style="cyan",     width=8)
    t.add_column("Segmento",                   width=16)
    t.add_column("Cotas",    justify="right",  width=6)
    t.add_column("P. Atual", justify="right",  width=9)
    t.add_column("Valor",    justify="right",  width=12)
    t.add_column("Peso",     justify="right",  width=6)
    t.add_column("",                           width=15)

    for i, r in df.iterrows():
        barra_len = max(1, int(r["peso"] * 20 / 100))
        barra = "[cyan]" + "#" * barra_len + "[/cyan]"
        t.add_row(
            str(i + 1),
            r["ticker"],
            str(r.get("segmento") or "--")[:20],
            str(int(r["cotas"])),
            f"R$ {r['preco_atual']:.2f}" if pd.notna(r.get("preco_atual")) else "--",
            f"R$ {r['valor_ref']:,.2f}",
            f"{r['peso']:.1f}%",
            barra,
        )
    console.print(t)

    # --- Por segmento ---
    console.print("\n[bold]Alocacao por segmento[/bold]")
    seg = (
        df.assign(segmento=df["segmento"].fillna("Outros"))
        .groupby("segmento")
        .agg(valor=("valor_ref", "sum"), n_ativos=("ticker", "count"))
        .reset_index()
    )
    seg["peso"] = seg["valor"] / total * 100
    seg = seg.sort_values("peso", ascending=False)

    st = Table(show_header=True, header_style="bold")
    st.add_column("Segmento", width=25)
    st.add_column("Ativos",   justify="right", width=7)
    st.add_column("Valor",    justify="right", width=13)
    st.add_column("Peso",     justify="right", width=7)
    st.add_column("",                          width=20)

    for _, r in seg.iterrows():
        barra_len = max(1, int(r["peso"] * 20 / 100))
        barra = "[green]" + "#" * barra_len + "[/green]"
        st.add_row(
            str(r["segmento"])[:25],
            str(int(r["n_ativos"])),
            f"R$ {r['valor']:,.2f}",
            f"{r['peso']:.1f}%",
            barra,
        )
    console.print(st)
    console.print(f"\n[dim]Total carteira: R$ {total:,.2f}[/dim]")


# ---------------------------------------------------------------------------
# Renda mensal da carteira
# ---------------------------------------------------------------------------

def relatorio_income(meses: int = 12, projecao: int = 0) -> None:
    """
    Mostra a renda mensal gerada pela carteira nos ultimos N meses.

    projecao: se > 0, projeta os proximos N meses usando a media dos ultimos 6 meses
              com dados reais. Claramente rotulado como estimativa.
    """
    df = get_historico_dividendos()

    if df.empty:
        console.print(
            "[yellow]Sem historico de dividendos. "
            "Verifique se a carteira tem movimentacoes e se os dados estao atualizados.[/yellow]"
        )
        return

    monthly = (
        df.dropna(subset=["dividendo_recebido"])
        .groupby("mes")
        .agg(renda=("dividendo_recebido", "sum"), n_ativos=("ticker", "nunique"))
        .reset_index()
        .sort_values("mes")
        .tail(meses)
    )

    if monthly.empty:
        console.print("[yellow]Sem dados de dividendos para exibir.[/yellow]")
        return

    # Calcula media dos ultimos 6 meses reais para projecao
    media_proj = float(monthly.tail(6)["renda"].mean()) if len(monthly) >= 1 else 0.0
    n_ativos_proj = int(monthly["n_ativos"].iloc[-1]) if not monthly.empty else 0

    # Gera linhas de projecao
    proj_rows: list[dict] = []
    if projecao > 0 and media_proj > 0:
        ultimo_mes = pd.Period(monthly["mes"].iloc[-1], freq="M")
        for i in range(1, projecao + 1):
            prox = str(ultimo_mes + i)
            proj_rows.append({"mes": prox, "renda": media_proj, "n_ativos": n_ativos_proj, "projetado": True})

    titulo = f"Renda mensal -- {len(monthly)} meses reais"
    if projecao > 0:
        titulo += f" + {projecao} projetados"
    console.print(f"\n[bold]{titulo}[/bold]")

    max_renda = max(monthly["renda"].max(), media_proj if proj_rows else 0)
    t = Table(show_header=True, header_style="bold")
    t.add_column("Mes",    width=10)
    t.add_column("Ativos", justify="right", width=7)
    t.add_column("Renda",  justify="right", width=13)
    t.add_column("",                        width=30)

    for _, r in monthly.iterrows():
        barra_len = max(1, int(r["renda"] / max_renda * 30)) if max_renda > 0 else 1
        barra = "[green]" + "#" * barra_len + "[/green]"
        t.add_row(
            str(r["mes"])[:7],
            str(int(r["n_ativos"])),
            f"R$ {r['renda']:,.2f}",
            barra,
        )

    for r in proj_rows:
        barra_len = max(1, int(r["renda"] / max_renda * 30)) if max_renda > 0 else 1
        barra = "[dim]" + "-" * barra_len + "[/dim]"
        t.add_row(
            f"[dim]{r['mes'][:7]}*[/dim]",
            f"[dim]{r['n_ativos']}[/dim]",
            f"[dim]R$ {r['renda']:,.2f}[/dim]",
            barra,
        )

    console.print(t)

    if proj_rows:
        console.print(
            f"[dim]* Estimativa: media dos ultimos 6 meses reais (R$ {media_proj:,.2f}/mes). "
            "Nao considera variacao de cotas ou DY.[/dim]"
        )

    media   = monthly["renda"].mean()
    maxima  = monthly["renda"].max()
    minima  = monthly["renda"].min()
    total_r = monthly["renda"].sum()

    console.print()
    gt = Table(show_header=False, box=None, padding=(0, 2))
    gt.add_column("Label", style="dim")
    gt.add_column("Valor", style="bold")
    gt.add_row("Media mensal (real)",     f"R$ {media:,.2f}")
    gt.add_row("Melhor mes",              f"R$ {maxima:,.2f}")
    gt.add_row("Menor mes",               f"R$ {minima:,.2f}")
    gt.add_row(f"Total {len(monthly)}m",  f"R$ {total_r:,.2f}")
    if projecao > 0 and media_proj > 0:
        gt.add_row(
            f"Projecao {projecao}m (estimativa)",
            f"R$ {media_proj * projecao:,.2f}  (R$ {media_proj:,.2f}/mes)",
        )
    console.print(gt)
