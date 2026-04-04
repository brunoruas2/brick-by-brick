"""
Modulo de indicadores -- calcula P/VP, DY 12m, liquidez, spread vs SELIC.

Todos os calculos partem de dados ja armazenados no banco local.
Nenhuma chamada de rede aqui.
"""
import sqlite3
import pandas as pd
from src.config import DB_PATH


def get_all_indicators() -> pd.DataFrame:
    """
    Retorna DataFrame com indicadores calculados para todos os FIIs ativos
    que possuem ticker vinculado.

    Colunas retornadas:
      ticker, cnpj, nome, segmento, gestor, taxa_adm,
      preco, data_preco,
      vpa, data_vpa,
      p_vp,
      dy_12m, dy_mes_atual,
      liquidez_30d,
      selic_12m, spread_selic,
      consistencia_dy   (desvio padrao dos DY mensais, 12 meses)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- Preco mais recente (B3) ---
    preco_df = pd.read_sql("""
        SELECT ticker, fechamento AS preco, data AS data_preco
        FROM cotacoes
        WHERE (ticker, data) IN (
            SELECT ticker, MAX(data) FROM cotacoes GROUP BY ticker
        )
    """, conn)

    # --- VPA mais recente (CVM) ---
    vpa_df = pd.read_sql("""
        SELECT cnpj, valor_patrimonial_cota AS vpa, data_referencia AS data_vpa
        FROM inf_mensal
        WHERE (cnpj, data_referencia) IN (
            SELECT cnpj, MAX(data_referencia) FROM inf_mensal GROUP BY cnpj
        )
    """, conn)

    # --- DY mensal dos ultimos 13 meses (12 completos + eventual mes atual) ---
    dy_df = pd.read_sql("""
        SELECT cnpj, data_referencia, dy_mes
        FROM inf_mensal
        WHERE data_referencia >= date('now', '-13 months')
          AND dy_mes IS NOT NULL
        ORDER BY cnpj, data_referencia
    """, conn)

    # --- Liquidez media 30 dias (B3) ---
    liq_df = pd.read_sql("""
        SELECT ticker, AVG(volume) AS liquidez_30d
        FROM cotacoes
        WHERE data >= date('now', '-30 days')
          AND volume IS NOT NULL
        GROUP BY ticker
    """, conn)

    # --- SELIC acumulada 12 meses (BCB) ---
    selic_row = conn.execute("""
        SELECT SUM(selic_mes) AS selic_12m
        FROM benchmarks
        WHERE data >= date('now', '-12 months')
          AND selic_mes IS NOT NULL
    """).fetchone()
    selic_12m = selic_row["selic_12m"] if selic_row else None

    # --- Cadastro base ---
    fiis_df = pd.read_sql("""
        SELECT cnpj, ticker, nome, segmento, gestor, taxa_adm, situacao
        FROM fiis
        WHERE ticker IS NOT NULL
          AND situacao = 'EM FUNCIONAMENTO NORMAL'
    """, conn)

    conn.close()

    if fiis_df.empty:
        return pd.DataFrame()

    # --- Calculos de DY em pandas (SQLite nao tem STDEV) ---
    dy_agg = (
        dy_df.sort_values("data_referencia")
        .groupby("cnpj")
        .agg(
            dy_12m=("dy_mes", "sum"),
            dy_mes_atual=("dy_mes", "last"),
            consistencia_dy=("dy_mes", "std"),
        )
        .reset_index()
    )

    # --- Juncao de tudo ---
    df = (
        fiis_df
        .merge(preco_df, on="ticker", how="left")
        .merge(vpa_df, on="cnpj", how="left")
        .merge(dy_agg, on="cnpj", how="left")
        .merge(liq_df, on="ticker", how="left")
    )

    # --- Indicadores calculados ---
    df["p_vp"] = (df["preco"] / df["vpa"]).round(4)
    df["selic_12m"] = selic_12m
    df["spread_selic"] = (df["dy_12m"] - selic_12m).round(4)

    # Ordena e limpa
    cols = [
        "ticker", "cnpj", "nome", "segmento", "gestor", "taxa_adm", "situacao",
        "preco", "data_preco",
        "vpa", "data_vpa",
        "p_vp",
        "dy_mes_atual", "dy_12m",
        "liquidez_30d",
        "selic_12m", "spread_selic",
        "consistencia_dy",
    ]
    return df[[c for c in cols if c in df.columns]].sort_values("ticker").reset_index(drop=True)


def get_indicators_for(tickers: list[str]) -> pd.DataFrame:
    """Retorna indicadores apenas para os tickers solicitados."""
    df = get_all_indicators()
    return df[df["ticker"].isin([t.upper() for t in tickers])].reset_index(drop=True)


def get_dy_history(ticker: str, months: int = 12) -> pd.DataFrame:
    """Retorna historico de DY mensal de um ticker."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT im.data_referencia, im.dy_mes, im.valor_patrimonial_cota AS vpa,
               im.patrimonio_liquido, im.nr_cotistas
        FROM inf_mensal im
        JOIN fiis f ON f.cnpj = im.cnpj
        WHERE f.ticker = ?
          AND im.data_referencia >= date('now', ? || ' months')
        ORDER BY im.data_referencia
    """, conn, params=(ticker.upper(), f"-{months}"))
    conn.close()
    return df
