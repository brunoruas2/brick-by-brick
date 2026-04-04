"""
Screener -- filtra e ranqueia FIIs com base em criterios configuráveis.
"""
import pandas as pd
from src.analysis.indicadores import get_all_indicators


_DEFAULT_WEIGHTS = {
    "dy_12m":          0.30,
    "spread_selic":    0.25,
    "p_vp":            0.20,
    "liquidez_30d":    0.15,
    "consistencia_dy": 0.10,
}


def screen(
    dy_min: float | None = None,
    pvp_max: float | None = None,
    liq_min: float | None = None,
    spread_min: float | None = None,
    segmento: str | None = None,
    top_n: int = 20,
    weights: dict | None = None,
) -> pd.DataFrame:
    """
    Filtra e ranqueia FIIs.

    Args:
        dy_min:     DY 12m minimo em % (ex: 8.0)
        pvp_max:    P/VP maximo (ex: 1.10)
        liq_min:    Liquidez 30d minima em R$ (ex: 500_000)
        spread_min: Spread vs SELIC minimo em % (ex: -5.0)
        segmento:   Filtro parcial de segmento (ex: "logistica")
        top_n:      Numero de resultados
        weights:    Pesos para o score (usa _DEFAULT_WEIGHTS se None)

    Returns:
        DataFrame com coluna extra 'score' (0-100), ordenado por score desc.
    """
    df = get_all_indicators()
    if df.empty:
        return df

    # Filtros
    if dy_min is not None:
        df = df[df["dy_12m"].fillna(0) >= dy_min]
    if pvp_max is not None:
        df = df[df["p_vp"].fillna(999) <= pvp_max]
    if liq_min is not None:
        df = df[df["liquidez_30d"].fillna(0) >= liq_min]
    if spread_min is not None:
        df = df[df["spread_selic"].fillna(-999) >= spread_min]
    if segmento:
        df = df[df["segmento"].fillna("").str.lower().str.contains(segmento.lower())]

    if df.empty:
        return df

    # Score normalizado 0-100
    w = weights or _DEFAULT_WEIGHTS
    df = _add_score(df.copy(), w)

    return df.sort_values("score", ascending=False).head(top_n).reset_index(drop=True)


def _add_score(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Calcula score ponderado (0-100) para cada FII."""
    scores = pd.Series(0.0, index=df.index)

    def _norm(s: pd.Series, higher_is_better: bool = True) -> pd.Series:
        """Normaliza serie para [0, 1]. NaN vira 0."""
        s = s.fillna(s.median()).fillna(0)
        rng = s.max() - s.min()
        if rng == 0:
            return pd.Series(0.5, index=s.index)
        n = (s - s.min()) / rng
        return n if higher_is_better else (1 - n)

    if "dy_12m" in df.columns and "dy_12m" in weights:
        scores += _norm(df["dy_12m"], higher_is_better=True) * weights["dy_12m"]

    if "spread_selic" in df.columns and "spread_selic" in weights:
        scores += _norm(df["spread_selic"], higher_is_better=True) * weights["spread_selic"]

    if "p_vp" in df.columns and "p_vp" in weights:
        scores += _norm(df["p_vp"], higher_is_better=False) * weights["p_vp"]

    if "liquidez_30d" in df.columns and "liquidez_30d" in weights:
        scores += _norm(df["liquidez_30d"], higher_is_better=True) * weights["liquidez_30d"]

    if "consistencia_dy" in df.columns and "consistencia_dy" in weights:
        scores += _norm(df["consistencia_dy"], higher_is_better=False) * weights["consistencia_dy"]

    df["score"] = (scores * 100).round(1)
    return df
