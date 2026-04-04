"""
Collector — BCB: Series Temporais (SELIC, CDI, IPCA)

API SGS do Banco Central do Brasil.
Sem autenticacao. Janela maxima por consulta: 10 anos.

Series coletadas:
  433  -> IPCA variacao mensal (%)
  4390 -> SELIC acumulada no mes (%)
  12   -> CDI acumulado no mes (%)  [serie 4391 se 12 nao retornar mensal]

Endpoint:
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json
  &dataInicial=DD/MM/AAAA&dataFinal=DD/MM/AAAA

Retorno JSON:
  [{"data": "01/01/2025", "valor": "1.23"}, ...]

Armazenamento:
  Tabela benchmarks: (data, selic_mes, cdi_mes, ipca_mes)
  data = primeiro dia do mes em ISO-8601 (YYYY-MM-DD)
"""

from datetime import date, datetime, timedelta

import requests
from rich.console import Console

console = Console()

_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"

# Codigos das series
_SERIE_IPCA  = 433   # IPCA variacao mensal (%)
_SERIE_SELIC = 4390  # SELIC acumulada no mes (%)
_SERIE_CDI   = 4391  # CDI acumulado no mes (%)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_serie(serie: int, data_ini: str, data_fim: str) -> dict[str, float]:
    """
    Baixa uma serie do BCB e retorna dict {data_iso: valor}.

    Args:
        serie:     codigo da serie SGS.
        data_ini:  data inicial no formato DD/MM/AAAA.
        data_fim:  data final no formato DD/MM/AAAA.

    Returns:
        dict mapeando data ISO-8601 (YYYY-MM-DD) para float.
    """
    url = _BASE_URL.format(serie=serie)
    params = {"formato": "json", "dataInicial": data_ini, "dataFinal": data_fim}

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        console.print(f"[red]    Erro serie {serie}: {e}[/red]")
        return {}

    result = {}
    for item in data:
        raw_date = item.get("data", "")
        raw_val  = item.get("valor", "")
        try:
            dt = datetime.strptime(raw_date, "%d/%m/%Y").date()
            val = float(str(raw_val).replace(",", "."))
            result[dt.isoformat()] = val
        except (ValueError, TypeError):
            continue

    return result


def _date_range(months: int) -> tuple[str, str]:
    """Retorna (data_ini, data_fim) como strings DD/MM/AAAA para os ultimos N meses."""
    today = date.today()
    ini = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 1):
        ini = (ini - timedelta(days=1)).replace(day=1)
    return ini.strftime("%d/%m/%Y"), today.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def fetch(months: int = 24) -> list[dict]:
    """
    Baixa SELIC, CDI e IPCA mensais dos ultimos N meses.

    Args:
        months: numero de meses de historico (padrao: 24).

    Returns:
        lista de dicts para upsert_benchmarks().
        Cada dict: {data, selic_mes, cdi_mes, ipca_mes}
    """
    data_ini, data_fim = _date_range(months)
    console.print(
        f"[cyan]  -> BCB -- SELIC / CDI / IPCA "
        f"({data_ini} a {data_fim})[/cyan]"
    )

    selic = _fetch_serie(_SERIE_SELIC, data_ini, data_fim)
    cdi   = _fetch_serie(_SERIE_CDI,   data_ini, data_fim)
    ipca  = _fetch_serie(_SERIE_IPCA,  data_ini, data_fim)

    # Une todas as datas encontradas em qualquer serie
    all_dates = sorted(set(selic) | set(cdi) | set(ipca))

    records = [
        {
            "data":      d,
            "selic_mes": selic.get(d),
            "cdi_mes":   cdi.get(d),
            "ipca_mes":  ipca.get(d),
        }
        for d in all_dates
    ]

    console.print(
        f"[dim]    SELIC: {len(selic)} | CDI: {len(cdi)} | "
        f"IPCA: {len(ipca)} meses[/dim]"
    )
    return records
