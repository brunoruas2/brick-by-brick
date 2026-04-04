"""
Deteccao de anomalias e registro de grupamentos de cotas de FIIs.

Grupamento (reverse split): N cotas antigas viram 1 cota nova.
Exemplo: fator=10 -> 10 cotas de R$16 viraram 1 cota de R$160.

Fluxo:
  1. detectar_anomalias()    -- varre inf_mensal buscando quedas em cotas_emitidas
  2. usuario pesquisa o fato relevante do fundo
  3. add_grupamento()        -- registra o fator confirmado
  4. get_fatores_por_ticker() -- retorna fatores para aplicar no calculo historico
"""

import datetime as _dt

import pandas as pd

from src.storage.database import connect, upsert_grupamento, get_grupamentos


# ---------------------------------------------------------------------------
# Anomalias (deteccao automatica para avisar o usuario)
# ---------------------------------------------------------------------------

def detectar_anomalias(
    tickers: list[str] | None = None,
    fator_minimo: float = 1.8,
    tolerancia_pl: float = 0.10,
) -> list[dict]:
    """
    Varre inf_mensal buscando meses com queda abrupta em cotas_emitidas,
    caracteristica de um grupamento.

    Sinal triplo (maior confianca quando todos satisfeitos):
      1. cotas_emitidas[t-1] / cotas_emitidas[t] >= fator_minimo
      2. variacao do patrimonio_liquido < tolerancia_pl  (PL nao muda no grupamento)
      3. valor_patrimonial_cota[t] / valor_patrimonial_cota[t-1] ~= fator  (VPA sobe)

    Retorna lista de dicts com:
      ticker, cnpj, mes, fator_estimado, confianca ('alta'|'media'), sinais
    """
    with connect() as conn:
        if tickers:
            ph = ",".join("?" * len(tickers))
            rows = conn.execute(
                f"""SELECT f.ticker, im.cnpj, im.data_referencia,
                           im.cotas_emitidas, im.patrimonio_liquido,
                           im.valor_patrimonial_cota
                    FROM inf_mensal im
                    JOIN fiis f ON f.cnpj = im.cnpj
                    WHERE f.ticker IN ({ph})
                      AND im.cotas_emitidas IS NOT NULL
                    ORDER BY f.ticker, im.data_referencia""",
                tickers,
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT f.ticker, im.cnpj, im.data_referencia,
                          im.cotas_emitidas, im.patrimonio_liquido,
                          im.valor_patrimonial_cota
                   FROM inf_mensal im
                   JOIN fiis f ON f.cnpj = im.cnpj
                   WHERE im.cotas_emitidas IS NOT NULL
                   ORDER BY f.ticker, im.data_referencia"""
            ).fetchall()

        # Grupamentos ja registrados (para nao re-avisar)
        ja_registrados: set[tuple] = set()
        gr_rows = conn.execute(
            "SELECT ticker, data_grupamento FROM grupamentos"
        ).fetchall()
        for r in gr_rows:
            ja_registrados.add((r["ticker"], r["data_grupamento"][:7]))

    if not rows:
        return []

    df = pd.DataFrame([dict(r) for r in rows])
    df["data_referencia"] = pd.to_datetime(df["data_referencia"])
    df = df.sort_values(["ticker", "data_referencia"])

    anomalias: list[dict] = []

    for ticker, grupo in df.groupby("ticker"):
        grupo = grupo.reset_index(drop=True)
        for i in range(1, len(grupo)):
            prev = grupo.iloc[i - 1]
            curr = grupo.iloc[i]

            cotas_prev = float(prev["cotas_emitidas"])
            cotas_curr = float(curr["cotas_emitidas"])

            if cotas_curr <= 0 or cotas_prev <= 0:
                continue

            fator_raw = cotas_prev / cotas_curr
            if fator_raw < fator_minimo:
                continue

            mes_str = curr["data_referencia"].strftime("%Y-%m")

            # Ja tem grupamento registrado para esse mes?
            if (ticker, mes_str) in ja_registrados:
                continue

            sinais = [f"cotas: {cotas_prev:,.0f} -> {cotas_curr:,.0f} (fator ~{fator_raw:.1f}x)"]
            confianca = "media"

            # Sinal 2: PL estavel
            pl_ok = False
            if pd.notna(prev["patrimonio_liquido"]) and pd.notna(curr["patrimonio_liquido"]):
                pl_prev = float(prev["patrimonio_liquido"])
                pl_curr = float(curr["patrimonio_liquido"])
                if pl_prev > 0:
                    var_pl = abs(pl_curr / pl_prev - 1)
                    pl_ok = var_pl < tolerancia_pl
                    sinais.append(
                        f"PL {'estavel' if pl_ok else 'variou'} "
                        f"({var_pl * 100:.1f}%)"
                    )

            # Sinal 3: VPA proporcional ao fator
            vpa_ok = False
            if pd.notna(prev["valor_patrimonial_cota"]) and pd.notna(curr["valor_patrimonial_cota"]):
                vpa_prev = float(prev["valor_patrimonial_cota"])
                vpa_curr = float(curr["valor_patrimonial_cota"])
                if vpa_prev > 0:
                    ratio_vpa = vpa_curr / vpa_prev
                    vpa_ok = abs(ratio_vpa / fator_raw - 1) < 0.08
                    sinais.append(
                        f"VPA: R${vpa_prev:.2f} -> R${vpa_curr:.2f} "
                        f"({'proporcional' if vpa_ok else 'nao proporcional'})"
                    )

            if pl_ok and vpa_ok:
                confianca = "alta"
            elif pl_ok or vpa_ok:
                confianca = "media"
            else:
                confianca = "baixa"

            # Arredonda para fator inteiro mais proximo
            fator_estimado = round(fator_raw)
            if fator_estimado < 2:
                fator_estimado = 2

            anomalias.append({
                "ticker":          str(ticker),
                "cnpj":            str(curr["cnpj"]),
                "mes":             mes_str,
                "fator_estimado":  fator_estimado,
                "fator_raw":       round(fator_raw, 2),
                "confianca":       confianca,
                "sinais":          " | ".join(sinais),
            })

    return anomalias


# ---------------------------------------------------------------------------
# Registro de grupamento confirmado
# ---------------------------------------------------------------------------

def add_grupamento(
    ticker: str,
    mes: str,           # YYYY-MM
    fator: float,
    observacao: str | None = None,
) -> None:
    """
    Registra um grupamento de cotas confirmado manualmente.

    ticker:     ex. 'HGLG11'
    mes:        ex. '2021-10'  (mes em que o grupamento foi efetivado)
    fator:      ex. 10.0       (10 cotas antigas viraram 1 nova)
    observacao: texto livre (opcional)

    Raises ValueError se o ticker nao for encontrado no banco.
    """
    ticker = ticker.upper()

    with connect() as conn:
        row = conn.execute(
            "SELECT cnpj FROM fiis WHERE ticker = ?", (ticker,)
        ).fetchone()

    if not row:
        raise ValueError(
            f"Ticker '{ticker}' nao encontrado. "
            "Verifique o ticker ou rode: python main.py update"
        )

    cnpj = row["cnpj"]
    data_grupamento = f"{mes}-01"

    upsert_grupamento({
        "cnpj":            cnpj,
        "ticker":          ticker,
        "data_grupamento": data_grupamento,
        "fator":           float(fator),
        "origem":          "manual",
        "observacao":      observacao,
        "criado_em":       _dt.datetime.now().isoformat(timespec="seconds"),
    })


# ---------------------------------------------------------------------------
# Lookup de fatores para correcao historica
# ---------------------------------------------------------------------------

def get_fatores_por_ticker(tickers: list[str]) -> dict[str, list[tuple[str, float]]]:
    """
    Retorna dict: ticker -> [(data_grupamento_YYYY-MM, fator), ...] ordenado por data.

    Apenas grupamentos confirmados (origem='manual').
    Usado em get_historico_dividendos() para corrigir cotas historicas.
    """
    rows = get_grupamentos(tickers)
    result: dict[str, list[tuple[str, float]]] = {}
    for r in rows:
        t = r["ticker"]
        mes = r["data_grupamento"][:7]   # YYYY-MM
        fator = float(r["fator"])
        result.setdefault(t, []).append((mes, fator))
    # Garante ordem cronologica por ticker
    for t in result:
        result[t].sort(key=lambda x: x[0])
    return result
