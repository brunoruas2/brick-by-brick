"""
Modulo de backtest: simulacoes hipoteticas (what-if) para a carteira de FIIs.

Permite responder perguntas como:
  - "Se eu tivesse trocado VISC11 por HGLG11 em 2024-06, qual seria o resultado hoje?"
  - "Se eu tivesse comprado 100 cotas de HGLG11 em 2024-01, qual seria o resultado hoje?"

Limitacoes da v1:
  - Splits: detectados mas nao corrigidos no cenario simulado. Um aviso e emitido.
  - Custos operacionais (corretagem, IOF, IR) nao sao modelados.
  - O cenario "real" do swap usa get_historico_dividendos(), que ja tem correcao de splits.
"""

from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field

from src.storage.database import connect
from src.portfolio.grupamentos import get_fatores_por_ticker


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Resultado de um cenario (real ou simulado) para um unico ticker."""
    ticker:           str
    mes_inicio:       str           # YYYY-MM
    cotas:            float
    preco_entrada:    float         # preco usado para calcular o capital investido
    capital_investido: float
    dividendos_mensais: pd.DataFrame  # colunas: mes, dy_mes, preco_cota, dividendo_cota, dividendo_recebido
    dividendos_total: float
    preco_atual:      float | None
    valor_atual:      float | None
    total_return:     float | None  # (valor_atual + dividendos_total - capital) / capital * 100
    avisos:           list[str] = field(default_factory=list)


@dataclass
class SwapResult:
    """Resultado da simulacao de troca entre dois tickers."""
    ticker_out: str
    ticker_in:  str
    mes:        str  # YYYY-MM
    real:       ScenarioResult
    simulado:   ScenarioResult


@dataclass
class AddResult:
    """Resultado da simulacao de compra adicional."""
    simulado: ScenarioResult


class BacktestError(ValueError):
    """Erro de validacao no backtest."""
    pass


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _ultimo_mes_fechado() -> str:
    """Retorna o ultimo mes ja fechado (mes atual - 1) em formato YYYY-MM."""
    hoje = pd.Timestamp.today()
    return str((hoje.to_period("M") - 1))


def _get_preco_mes(ticker: str, mes: str) -> float | None:
    """
    Retorna o preco de fechamento do ultimo pregao do mes indicado.
    mes: YYYY-MM
    """
    with connect() as conn:
        row = conn.execute(
            """
            SELECT fechamento FROM cotacoes
            WHERE ticker = ? AND strftime('%Y-%m', data) = ?
            ORDER BY data DESC LIMIT 1
            """,
            (ticker.upper(), mes),
        ).fetchone()
    return float(row["fechamento"]) if row else None


def _get_vpa_mes(ticker: str, mes: str) -> float | None:
    """Retorna o VPA (valor_patrimonial_cota) do mes indicado."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT im.valor_patrimonial_cota
            FROM inf_mensal im
            JOIN fiis f ON f.cnpj = im.cnpj
            WHERE f.ticker = ? AND strftime('%Y-%m', im.data_referencia) = ?
            LIMIT 1
            """,
            (ticker.upper(), mes),
        ).fetchone()
    return float(row["valor_patrimonial_cota"]) if row and row["valor_patrimonial_cota"] else None


def _get_dy_mensal(ticker: str, mes_inicio: str, mes_fim: str) -> pd.DataFrame:
    """
    Retorna serie mensal de dy_mes e preco_fechamento para o ticker
    entre mes_inicio e mes_fim (inclusive). Inclui VPA como fallback.

    Colunas: mes, dy_mes, preco_cota, vpa
    """
    with connect() as conn:
        # DY e VPA do inf_mensal
        im_rows = conn.execute(
            """
            SELECT strftime('%Y-%m', im.data_referencia) AS mes,
                   im.dy_mes,
                   im.valor_patrimonial_cota AS vpa
            FROM inf_mensal im
            JOIN fiis f ON f.cnpj = im.cnpj
            WHERE f.ticker = ?
              AND im.dy_mes IS NOT NULL
              AND strftime('%Y-%m', im.data_referencia) >= ?
              AND strftime('%Y-%m', im.data_referencia) <= ?
            ORDER BY mes
            """,
            (ticker.upper(), mes_inicio, mes_fim),
        ).fetchall()

        # Ultimo fechamento por mes
        cot_rows = conn.execute(
            """
            SELECT c.mes, c.preco_cota FROM (
                SELECT strftime('%Y-%m', data) AS mes, fechamento AS preco_cota,
                       ROW_NUMBER() OVER (PARTITION BY strftime('%Y-%m', data) ORDER BY data DESC) AS rn
                FROM cotacoes
                WHERE ticker = ?
                  AND strftime('%Y-%m', data) >= ?
                  AND strftime('%Y-%m', data) <= ?
            ) c WHERE c.rn = 1
            """,
            (ticker.upper(), mes_inicio, mes_fim),
        ).fetchall()

    im_df  = pd.DataFrame([dict(r) for r in im_rows])  if im_rows  else pd.DataFrame(columns=["mes", "dy_mes", "vpa"])
    cot_df = pd.DataFrame([dict(r) for r in cot_rows]) if cot_rows else pd.DataFrame(columns=["mes", "preco_cota"])

    if im_df.empty:
        return pd.DataFrame(columns=["mes", "dy_mes", "preco_cota", "vpa"])

    df = im_df.merge(cot_df, on="mes", how="left")
    # fallback: usa VPA quando nao ha preco de mercado
    df["preco_cota"] = df["preco_cota"].fillna(df["vpa"])
    return df.sort_values("mes").reset_index(drop=True)


def _check_splits_in_range(ticker: str, mes_inicio: str, mes_fim: str) -> list[str]:
    """Retorna avisos para splits do ticker dentro do intervalo."""
    fatores = get_fatores_por_ticker([ticker])
    avisos: list[str] = []
    for mes_split, fator, tipo in fatores.get(ticker.upper(), []):
        if mes_inicio <= mes_split <= mes_fim:
            avisos.append(
                f"Atencao: {tipo} de {ticker.upper()} em {mes_split} "
                f"(fator {fator:.0f}x) nao foi ajustado no cenario simulado."
            )
    return avisos


def _simular_cenario(
    ticker:        str,
    mes_inicio:    str,
    cotas:         float,
    preco_entrada: float,
    mes_fim:       str | None = None,
) -> ScenarioResult:
    """
    Simula a evolucao de uma posicao hipotetica.

    ticker:        FII a simular
    mes_inicio:    mes de entrada (YYYY-MM)
    cotas:         quantidade de cotas
    preco_entrada: preco unitario de entrada (usado apenas para calcular capital investido)
    mes_fim:       mes de encerramento (padrao: ultimo mes fechado)
    """
    ticker = ticker.upper()
    if mes_fim is None:
        mes_fim = _ultimo_mes_fechado()

    capital = round(cotas * preco_entrada, 2)
    avisos: list[str] = []

    # Verifica se ha dados para o ticker
    with connect() as conn:
        existe = conn.execute(
            "SELECT ticker FROM fiis WHERE ticker = ?", (ticker,)
        ).fetchone()
    if not existe:
        raise BacktestError(
            f"Ticker '{ticker}' nao encontrado no banco. "
            "Verifique o ticker ou rode: python main.py update"
        )

    # Verifica se o mes de inicio tem dados
    preco_entry_real = _get_preco_mes(ticker, mes_inicio)
    if preco_entry_real is None:
        preco_entry_real = _get_vpa_mes(ticker, mes_inicio)
    if preco_entry_real is None:
        raise BacktestError(
            f"Sem dados de preco/VPA para {ticker} em {mes_inicio}. "
            "Tente um mes mais recente ou rode: python main.py update --desde-ano 2020"
        )

    # Valida que mes_inicio <= mes_fim
    if mes_inicio > mes_fim:
        raise BacktestError(
            f"mes_inicio ({mes_inicio}) nao pode ser posterior ao mes_fim ({mes_fim})"
        )

    # Dividendos mes a mes
    serie = _get_dy_mensal(ticker, mes_inicio, mes_fim)

    avisos += _check_splits_in_range(ticker, mes_inicio, mes_fim)

    if serie.empty:
        avisos.append(
            f"Sem dados de DY para {ticker} no periodo {mes_inicio}–{mes_fim}."
        )
        divs_df = pd.DataFrame(columns=["mes", "dy_mes", "preco_cota", "dividendo_cota", "dividendo_recebido"])
        divs_total = 0.0
    else:
        serie["dividendo_cota"]     = (serie["dy_mes"] * serie["preco_cota"]).round(4)
        serie["dividendo_recebido"] = (cotas * serie["dividendo_cota"]).round(2)
        divs_df    = serie[["mes", "dy_mes", "preco_cota", "dividendo_cota", "dividendo_recebido"]].copy()
        divs_total = round(float(divs_df["dividendo_recebido"].sum()), 2)

    # Preco atual (ultimo mes fechado)
    preco_atual = _get_preco_mes(ticker, mes_fim)
    if preco_atual is None:
        preco_atual = _get_vpa_mes(ticker, mes_fim)
        if preco_atual is not None:
            avisos.append(f"Preco atual de {ticker} em {mes_fim} nao disponivel; usando VPA.")

    valor_atual  = round(cotas * preco_atual, 2) if preco_atual is not None else None
    total_return = (
        round((valor_atual + divs_total - capital) / capital * 100, 2)
        if valor_atual is not None and capital > 0
        else None
    )

    return ScenarioResult(
        ticker=ticker,
        mes_inicio=mes_inicio,
        cotas=cotas,
        preco_entrada=preco_entrada,
        capital_investido=capital,
        dividendos_mensais=divs_df,
        dividendos_total=divs_total,
        preco_atual=preco_atual,
        valor_atual=valor_atual,
        total_return=total_return,
        avisos=avisos,
    )


def _df_historico_to_scenario(
    ticker:       str,
    mes_inicio:   str,
    cotas:        float,
    preco_entrada: float,
    hist_df:      pd.DataFrame,
) -> ScenarioResult:
    """
    Converte um DataFrame do get_historico_dividendos() em ScenarioResult.
    Usado para o cenario "real" no swap (aproveita correcao de splits ja feita).
    """
    ticker = ticker.upper()
    mes_fim = _ultimo_mes_fechado()

    df = hist_df[hist_df["mes"] >= mes_inicio].copy()
    df = df[df["ticker"] == ticker]

    if df.empty:
        divs_df    = pd.DataFrame(columns=["mes", "dy_mes", "preco_cota", "dividendo_cota", "dividendo_recebido"])
        divs_total = 0.0
    else:
        cols = [c for c in ["mes", "dy_mes", "preco_cota", "dividendo_cota", "dividendo_recebido"] if c in df.columns]
        divs_df    = df[cols].copy().reset_index(drop=True)
        divs_total = round(float(df["dividendo_recebido"].sum()), 2) if "dividendo_recebido" in df.columns else 0.0

    capital     = round(cotas * preco_entrada, 2)
    preco_atual = _get_preco_mes(ticker, mes_fim)

    avisos: list[str] = []
    if preco_atual is None:
        preco_atual = _get_vpa_mes(ticker, mes_fim)
        if preco_atual is not None:
            avisos.append(f"Preco atual de {ticker} em {mes_fim} nao disponivel; usando VPA.")

    valor_atual  = round(cotas * preco_atual, 2) if preco_atual is not None else None
    total_return = (
        round((valor_atual + divs_total - capital) / capital * 100, 2)
        if valor_atual is not None and capital > 0
        else None
    )

    return ScenarioResult(
        ticker=ticker,
        mes_inicio=mes_inicio,
        cotas=cotas,
        preco_entrada=preco_entrada,
        capital_investido=capital,
        dividendos_mensais=divs_df,
        dividendos_total=divs_total,
        preco_atual=preco_atual,
        valor_atual=valor_atual,
        total_return=total_return,
        avisos=avisos,
    )


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def simular_swap(
    ticker_out: str,
    ticker_in:  str,
    mes:        str,
    cotas:      int | float | None = None,
) -> SwapResult:
    """
    Simula o impacto de ter trocado ticker_out por ticker_in em um dado mes.

    Cenario real:   manteve ticker_out desde mes_inicio ate hoje.
    Cenario simulado: vendeu ticker_out no inicio do mes e comprou ticker_in
                      com o mesmo capital, pelo preco de mercado daquele mes.

    ticker_out: FII que estava (ou esta) na carteira
    ticker_in:  FII hipotetico que teria sido comprado
    mes:        mes da troca hipotetica (YYYY-MM)
    cotas:      cotas de ticker_out naquele mes. Se None, tenta buscar da carteira ativa.

    Raises BacktestError se nao houver dados suficientes.
    """
    ticker_out = ticker_out.upper()
    ticker_in  = ticker_in.upper()

    # Valida formato do mes
    try:
        pd.Period(mes, freq="M")
    except Exception:
        raise BacktestError(f"Formato de mes invalido: '{mes}'. Use YYYY-MM.")

    mes_fim = _ultimo_mes_fechado()

    if mes > mes_fim:
        raise BacktestError(
            f"O mes de referencia ({mes}) ainda nao fechou. "
            f"Use um mes ate {mes_fim}."
        )

    # Determina cotas no cenario real
    if cotas is None:
        # Reconstroi posicao a partir do historico de movimentacoes
        with connect() as conn:
            movs = conn.execute(
                """SELECT tipo, quantidade FROM movimentacoes
                   WHERE ticker = ? AND strftime('%Y-%m', data) <= ?
                   AND tipo IN ('compra','venda')
                   ORDER BY data, id""",
                (ticker_out, mes),
            ).fetchall()
        cotas_calc = 0
        for m in movs:
            if m["tipo"] == "compra":
                cotas_calc += int(m["quantidade"])
            else:
                cotas_calc = max(0, cotas_calc - int(m["quantidade"]))
        if cotas_calc <= 0:
            raise BacktestError(
                f"Nao foi encontrada posicao de {ticker_out} na carteira em {mes}. "
                "Informe --cotas explicitamente."
            )
        cotas = float(cotas_calc)

    # Preco de entrada do ticker_out no mes indicado (para recalcular capital)
    preco_out = _get_preco_mes(ticker_out, mes)
    if preco_out is None:
        preco_out = _get_vpa_mes(ticker_out, mes)
    if preco_out is None:
        raise BacktestError(
            f"Sem dados de preco para {ticker_out} em {mes}. "
            "Rode: python main.py update --desde-ano 2020"
        )

    capital = round(float(cotas) * preco_out, 2)

    # Preco de entrada do ticker_in no mesmo mes
    preco_in = _get_preco_mes(ticker_in, mes)
    if preco_in is None:
        preco_in = _get_vpa_mes(ticker_in, mes)
    if preco_in is None:
        raise BacktestError(
            f"Sem dados de preco para {ticker_in} em {mes}. "
            "Rode: python main.py update --desde-ano 2020"
        )

    cotas_in = capital / preco_in

    # Cenario real: usa get_historico_dividendos para aproveitar correcao de splits
    from src.portfolio.carteira import get_historico_dividendos
    hist = get_historico_dividendos(ticker=ticker_out, desde=mes)
    real = _df_historico_to_scenario(ticker_out, mes, float(cotas), preco_out, hist)

    # Cenario simulado
    simulado = _simular_cenario(ticker_in, mes, cotas_in, preco_in, mes_fim)

    return SwapResult(
        ticker_out=ticker_out,
        ticker_in=ticker_in,
        mes=mes,
        real=real,
        simulado=simulado,
    )


def simular_add(
    ticker:  str,
    mes:     str,
    cotas:   int | float | None = None,
    capital: float | None = None,
) -> AddResult:
    """
    Simula o impacto de ter comprado um FII em determinado mes.

    ticker:  FII hipotetico
    mes:     mes de entrada (YYYY-MM)
    cotas:   quantidade de cotas (use cotas OU capital, nao ambos)
    capital: capital a investir em R$ (calcula cotas automaticamente pelo preco do mes)

    Raises BacktestError se parametros forem invalidos.
    """
    ticker = ticker.upper()

    try:
        pd.Period(mes, freq="M")
    except Exception:
        raise BacktestError(f"Formato de mes invalido: '{mes}'. Use YYYY-MM.")

    mes_fim = _ultimo_mes_fechado()
    if mes > mes_fim:
        raise BacktestError(
            f"O mes de referencia ({mes}) ainda nao fechou. "
            f"Use um mes ate {mes_fim}."
        )

    if cotas is None and capital is None:
        raise BacktestError("Informe --cotas ou --capital.")
    if cotas is not None and capital is not None:
        raise BacktestError("Informe apenas --cotas OU --capital, nao ambos.")

    # Preco de entrada
    preco_entrada = _get_preco_mes(ticker, mes)
    if preco_entrada is None:
        preco_entrada = _get_vpa_mes(ticker, mes)
    if preco_entrada is None:
        raise BacktestError(
            f"Sem dados de preco para {ticker} em {mes}. "
            "Rode: python main.py update --desde-ano 2020"
        )

    if capital is not None:
        cotas = capital / preco_entrada

    resultado = _simular_cenario(ticker, mes, float(cotas), preco_entrada, mes_fim)
    return AddResult(simulado=resultado)
