"""
Gestao de posicoes e movimentacoes da carteira de FIIs.

Logica de preco medio:
  Compra: preco_medio = (cotas_antigas * pm_antigo + cotas_novas * preco) / total_cotas
  Venda: preco_medio permanece inalterado (apenas reduz cotas)
"""

import pandas as pd
from src.storage.database import connect


def add_compra(ticker: str, cotas: int, preco: float, data: str) -> None:
    """
    Registra uma compra e atualiza a posicao na carteira.
    Calcula preco medio ponderado se ja existir posicao ativa.
    """
    ticker = ticker.upper()
    valor_total = cotas * preco

    with connect() as conn:
        # Registra movimentacao
        conn.execute(
            """
            INSERT INTO movimentacoes (ticker, tipo, data, quantidade, preco_unitario, valor_total)
            VALUES (?, 'compra', ?, ?, ?, ?)
            """,
            (ticker, data, cotas, preco, valor_total),
        )

        # Busca CNPJ do ticker
        row = conn.execute(
            "SELECT cnpj FROM fiis WHERE ticker = ?", (ticker,)
        ).fetchone()
        cnpj = row["cnpj"] if row else None

        # Atualiza ou insere posicao na carteira
        existing = conn.execute(
            "SELECT id, cotas, preco_medio FROM carteira WHERE ticker = ? AND ativa = 1",
            (ticker,),
        ).fetchone()

        if existing:
            old_cotas = existing["cotas"]
            old_pm = existing["preco_medio"]
            new_cotas = old_cotas + cotas
            new_pm = (old_cotas * old_pm + cotas * preco) / new_cotas
            conn.execute(
                "UPDATE carteira SET cotas = ?, preco_medio = ? WHERE id = ?",
                (new_cotas, new_pm, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO carteira (ticker, cnpj, cotas, preco_medio, data_entrada, ativa)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (ticker, cnpj, cotas, preco, data),
            )


def add_venda(ticker: str, cotas: int, preco: float, data: str) -> None:
    """
    Registra uma venda. Reduz cotas da posicao ativa.
    Se todas as cotas forem vendidas, marca ativa = 0.

    Raises:
        ValueError: se nao houver posicao ativa ou cotas insuficientes.
    """
    ticker = ticker.upper()
    valor_total = cotas * preco

    with connect() as conn:
        existing = conn.execute(
            "SELECT id, cotas FROM carteira WHERE ticker = ? AND ativa = 1",
            (ticker,),
        ).fetchone()

        if not existing:
            raise ValueError(f"Posicao ativa nao encontrada para {ticker}")
        if cotas > existing["cotas"]:
            raise ValueError(
                f"Cotas insuficientes: posicao tem {existing['cotas']}, venda requer {cotas}"
            )

        conn.execute(
            """
            INSERT INTO movimentacoes (ticker, tipo, data, quantidade, preco_unitario, valor_total)
            VALUES (?, 'venda', ?, ?, ?, ?)
            """,
            (ticker, data, cotas, preco, valor_total),
        )

        new_cotas = existing["cotas"] - cotas
        if new_cotas == 0:
            conn.execute(
                "UPDATE carteira SET cotas = 0, ativa = 0 WHERE id = ?",
                (existing["id"],),
            )
        else:
            conn.execute(
                "UPDATE carteira SET cotas = ? WHERE id = ?",
                (new_cotas, existing["id"]),
            )


def get_posicoes() -> pd.DataFrame:
    """
    Retorna DataFrame com posicoes ativas enriquecidas com dados de mercado.

    Colunas:
      ticker, cotas, preco_medio, custo_total,
      nome, segmento,
      preco_atual, valor_atual,
      pl_capital, pl_pct,
      dy_mes, vpa, provento_est (cotas * vpa * dy_mes / 100)
    """
    with connect() as conn:
        rows = conn.execute("""
            SELECT
                c.ticker,
                c.cotas,
                c.preco_medio,
                ROUND(c.cotas * c.preco_medio, 2)          AS custo_total,
                f.nome,
                f.segmento,
                cot.fechamento                              AS preco_atual,
                ROUND(c.cotas * cot.fechamento, 2)         AS valor_atual,
                ROUND((cot.fechamento - c.preco_medio) * c.cotas, 2)          AS pl_capital,
                CASE WHEN c.preco_medio > 0
                     THEN ROUND((cot.fechamento - c.preco_medio) / c.preco_medio * 100, 2)
                     ELSE NULL END                         AS pl_pct,
                im.dy_mes,
                im.valor_patrimonial_cota                  AS vpa,
                ROUND(c.cotas * im.valor_patrimonial_cota * im.dy_mes / 100, 2) AS provento_est
            FROM carteira c
            LEFT JOIN fiis f ON c.ticker = f.ticker
            LEFT JOIN (
                SELECT c1.ticker, c1.fechamento
                FROM cotacoes c1
                INNER JOIN (
                    SELECT ticker, MAX(data) AS max_data
                    FROM cotacoes GROUP BY ticker
                ) c2 ON c1.ticker = c2.ticker AND c1.data = c2.max_data
            ) cot ON c.ticker = cot.ticker
            LEFT JOIN (
                SELECT f2.cnpj, im2.dy_mes, im2.valor_patrimonial_cota
                FROM inf_mensal im2
                INNER JOIN (
                    SELECT cnpj, MAX(data_referencia) AS max_ref
                    FROM inf_mensal GROUP BY cnpj
                ) latest ON im2.cnpj = latest.cnpj AND im2.data_referencia = latest.max_ref
                JOIN fiis f2 ON f2.cnpj = im2.cnpj
            ) im ON f.cnpj = im.cnpj
            WHERE c.ativa = 1
            ORDER BY c.ticker
        """).fetchall()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([dict(r) for r in rows])


def get_movimentacoes(ticker: str | None = None) -> pd.DataFrame:
    """Retorna historico de movimentacoes, opcionalmente filtrado por ticker."""
    with connect() as conn:
        if ticker:
            rows = conn.execute(
                "SELECT * FROM movimentacoes WHERE ticker = ? ORDER BY data DESC, id DESC",
                (ticker.upper(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM movimentacoes ORDER BY data DESC, id DESC"
            ).fetchall()

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])
