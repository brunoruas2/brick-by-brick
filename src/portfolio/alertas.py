"""
Verificacao de alertas da carteira e oportunidades do screener.

Alertas de carteira:
  atencao  — spread_negativo: DY 12m abaixo da SELIC
  atencao  — pl_negativo:     P&L de capital abaixo do limiar configurado
  aviso    — pvp_alto:        P/VP acima do limiar configurado
  aviso    — dy_queda:        DY do mes < X% da media historica

Oportunidades (top 5 fora da carteira por score):
  oportunidade — score_alto: score >= score_min e ticker nao na carteira
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class Alerta:
    nivel: str    # "atencao" | "aviso" | "oportunidade"
    ticker: str
    tipo: str
    mensagem: str


_ORDEM = {"atencao": 0, "aviso": 1, "oportunidade": 2}


def check_alerts(
    pvp_max: float = 1.20,
    pl_pct_min: float = -15.0,
    dy_queda_pct: float = 0.80,
    score_min: float = 70.0,
) -> list[Alerta]:
    """
    Verifica alertas e retorna lista ordenada por urgencia.

    Args:
        pvp_max:       Limiar de P/VP para alerta (default 1.20)
        pl_pct_min:    Limite de P&L % para alerta de queda (default -15%)
        dy_queda_pct:  Fracao da media mensal 12m abaixo da qual alerta (default 0.80)
        score_min:     Score minimo para sugerir oportunidade (default 70)
    """
    from src.portfolio.carteira import get_posicoes
    from src.analysis.indicadores import get_all_indicators
    from src.analysis.screener import _add_score, _DEFAULT_WEIGHTS

    alertas: list[Alerta] = []

    posicoes    = get_posicoes()
    indicadores = get_all_indicators()

    tickers_carteira: set[str] = (
        set(posicoes["ticker"].tolist()) if not posicoes.empty else set()
    )

    # ------------------------------------------------------------------
    # Alertas de carteira
    # ------------------------------------------------------------------
    if not posicoes.empty and not indicadores.empty:
        ind_cols = ["ticker", "p_vp", "dy_12m", "dy_mes_atual", "selic_12m", "spread_selic"]
        cart = posicoes.merge(
            indicadores[[c for c in ind_cols if c in indicadores.columns]],
            on="ticker",
            how="left",
        )

        for _, r in cart.iterrows():
            tk = r["ticker"]

            # Spread negativo: DY 12m < SELIC
            if pd.notna(r.get("spread_selic")) and r["spread_selic"] < 0:
                alertas.append(Alerta(
                    nivel="atencao",
                    ticker=tk,
                    tipo="spread_negativo",
                    mensagem=(
                        f"DY 12m ({r['dy_12m']:.1f}%) abaixo da SELIC "
                        f"({r['selic_12m']:.1f}%) -- spread {r['spread_selic']:.1f}%"
                    ),
                ))

            # P&L de capital muito negativo
            if pd.notna(r.get("pl_pct")) and r["pl_pct"] < pl_pct_min:
                alertas.append(Alerta(
                    nivel="atencao",
                    ticker=tk,
                    tipo="pl_negativo",
                    mensagem=(
                        f"P&L de capital: {r['pl_pct']:.1f}% "
                        f"(limiar configurado: {pl_pct_min:.0f}%)"
                    ),
                ))

            # P/VP acima do limiar
            if pd.notna(r.get("p_vp")) and r["p_vp"] > pvp_max:
                alertas.append(Alerta(
                    nivel="aviso",
                    ticker=tk,
                    tipo="pvp_alto",
                    mensagem=f"P/VP {r['p_vp']:.2f} acima do limiar {pvp_max:.2f}",
                ))

            # DY do mes em queda em relacao a media historica
            if (
                pd.notna(r.get("dy_mes_atual"))
                and pd.notna(r.get("dy_12m"))
                and r["dy_12m"] > 0
            ):
                media_mensal = r["dy_12m"] / 12
                if r["dy_mes_atual"] < dy_queda_pct * media_mensal:
                    alertas.append(Alerta(
                        nivel="aviso",
                        ticker=tk,
                        tipo="dy_queda",
                        mensagem=(
                            f"DY do mes ({r['dy_mes_atual']:.2f}%) abaixo de "
                            f"{dy_queda_pct*100:.0f}% da media mensal 12m "
                            f"({media_mensal:.2f}%)"
                        ),
                    ))

    # ------------------------------------------------------------------
    # Oportunidades: FIIs fora da carteira com score alto
    # ------------------------------------------------------------------
    if not indicadores.empty:
        scored = _add_score(indicadores.copy(), _DEFAULT_WEIGHTS)
        oportunidades = (
            scored[
                (~scored["ticker"].isin(tickers_carteira))
                & (scored["score"] >= score_min)
            ]
            .sort_values("score", ascending=False)
            .head(5)
        )

        for _, r in oportunidades.iterrows():
            dy   = f"{r['dy_12m']:.1f}%"   if pd.notna(r.get("dy_12m"))  else "--"
            pvp  = f"{r['p_vp']:.2f}"       if pd.notna(r.get("p_vp"))    else "--"
            seg  = str(r.get("segmento") or "")[:20]
            alertas.append(Alerta(
                nivel="oportunidade",
                ticker=r["ticker"],
                tipo="score_alto",
                mensagem=f"Score {r['score']:.0f} | DY 12m {dy} | P/VP {pvp} | {seg}",
            ))

    # ------------------------------------------------------------------
    # Alertas de watchlist: preco_alvo atingido
    # ------------------------------------------------------------------
    try:
        from src.storage.database import get_watchlist
        from src.analysis.indicadores import get_indicators_for

        wl_items = get_watchlist()
        if wl_items:
            wl_tickers = [w["ticker"] for w in wl_items]
            wl_ind = get_indicators_for(wl_tickers)
            ind_map = {r["ticker"]: r for _, r in wl_ind.iterrows()} if not wl_ind.empty else {}

            for item in wl_items:
                tk   = item["ticker"]
                alvo = item.get("preco_alvo")
                if not alvo:
                    continue
                ind_r = ind_map.get(tk, {})
                preco = ind_r.get("preco") if ind_r else None
                if preco and pd.notna(preco) and float(preco) <= float(alvo):
                    dist = (float(preco) / float(alvo) - 1) * 100
                    alertas.append(Alerta(
                        nivel="oportunidade",
                        ticker=tk,
                        tipo="preco_alvo_watchlist",
                        mensagem=(
                            f"Preco R$ {float(preco):.2f} atingiu alvo "
                            f"R$ {float(alvo):.2f} ({dist:+.1f}%) -- watchlist"
                        ),
                    ))
    except Exception:
        pass  # watchlist opcional -- nao interrompe os demais alertas

    alertas.sort(key=lambda a: _ORDEM.get(a.nivel, 9))
    return alertas
