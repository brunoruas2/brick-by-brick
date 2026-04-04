"""
Collector — B3: Series Historicas de Cotacoes (COTAHIST)

Fonte: https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ANO}.ZIP
Atualizacao: diaria. Sem autenticacao.

Formato: arquivo de largura fixa, 245 bytes por linha.
Tipos de registro:
  00 = Header
  01 = Cotacao diaria
  99 = Trailer

Para filtrar FIIs: CODBDI == "12" (posicoes 11-12, base 1)

Layout oficial:
  https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf

Campos extraidos (posicoes base 1, inclusive):
  DATPRE  03-10   Data do pregao (AAAAMMDD)
  CODBDI  11-12   Codigo BDI ("12" = FII)
  CODNEG  13-24   Ticker (ex: HGLG11)
  PREABE  57-69   Preco de abertura  (inteiro, dividir por 100)
  PREMAX  70-82   Preco maximo       (inteiro, dividir por 100)
  PREMIN  83-95   Preco minimo       (inteiro, dividir por 100)
  PREMED  96-108  Preco medio        (inteiro, dividir por 100)
  PREULT 109-121  Preco de fechamento (inteiro, dividir por 100)
  TOTNEG 148-152  Numero de negocios
  QUATOT 153-170  Quantidade total negociada
  VOLTOT 171-188  Volume financeiro total (inteiro, dividir por 100)

Estrategia de anos:
  - Por padrao baixa o ano atual e o anterior.
  - Pode-se passar anos especificos via parametro.
"""

import io
import zipfile
from datetime import date

import pandas as pd
import requests
from rich.console import Console

console = Console()

_BASE_URL = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"
)

# Posicoes no arquivo de largura fixa (base 0, exclusive no slice)
_FIELDS = {
    "tipreg": (0,   2),    # tipo de registro
    "datpre": (2,   10),   # data do pregao AAAAMMDD
    "codbdi": (10,  12),   # codigo BDI
    "codneg": (12,  24),   # ticker
    "preabe": (56,  69),   # preco abertura
    "premax": (69,  82),   # preco maximo
    "premin": (82,  95),   # preco minimo
    "premed": (95,  108),  # preco medio
    "preult": (108, 121),  # preco fechamento
    "totneg": (147, 152),  # numero de negocios
    "quatot": (152, 170),  # quantidade negociada
    "voltot": (170, 188),  # volume financeiro
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_lines(lines: list[bytes]) -> tuple[list[dict], list[dict]]:
    """
    Parseia as linhas do arquivo COTAHIST e retorna registros de FIIs.
    Apenas linhas com tipreg=='01' e codbdi=='12' (FII) sao processadas.

    Returns:
        (cotacoes_records, isin_ticker_records)
    """
    records = []
    isin_ticker_records: dict[str, str] = {}  # isin -> ticker (deduplica)

    for line in lines:
        if len(line) < 245:
            continue

        tipreg = line[0:2].decode("latin-1").strip()
        if tipreg != "01":
            continue

        codbdi = line[10:12].decode("latin-1").strip()
        if codbdi != "12":
            continue

        def field(s, e):
            return line[s:e].decode("latin-1").strip()

        def price(s, e):
            raw = field(s, e)
            return int(raw) / 100 if raw.isdigit() else None

        def integer(s, e):
            raw = field(s, e)
            return int(raw) if raw.isdigit() else None

        # Data: AAAAMMDD -> YYYY-MM-DD
        raw_date = field(2, 10)
        try:
            data = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8])).isoformat()
        except (ValueError, IndexError):
            continue

        ticker = field(12, 24).rstrip()
        if not ticker:
            continue

        isin = line[230:242].decode("latin-1").strip()
        if isin:
            isin_ticker_records[isin] = ticker

        records.append({
            "ticker":    ticker,
            "data":      data,
            "abertura":  price(56, 69),
            "maxima":    price(69, 82),
            "minima":    price(82, 95),
            "fechamento": price(108, 121),
            "volume":    price(170, 188),
            "negocios":  integer(147, 152),
        })

    isin_ticker_list = [{"isin": k, "ticker": v} for k, v in isin_ticker_records.items()]
    return records, isin_ticker_list


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _download_year(year: int) -> tuple[list[dict], list[dict]]:
    """
    Baixa COTAHIST_{year}.ZIP e retorna (cotacoes, isin_ticker) de FIIs.
    """
    url = _BASE_URL.format(year=year)
    console.print(f"[cyan]  -> B3 -- COTAHIST {year}[/cyan]")

    try:
        r = requests.get(url, timeout=300, stream=True)
        if r.status_code == 404:
            console.print(f"[dim]    {year} nao disponivel[/dim]")
            return [], []
        r.raise_for_status()
    except requests.RequestException as e:
        console.print(f"[red]    Erro {year}: {e}[/red]")
        return [], []

    content = r.content
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        txt_names = [n for n in zf.namelist() if n.upper().endswith(".TXT")]
        if not txt_names:
            console.print("[red]    Arquivo TXT nao encontrado no ZIP[/red]")
            return [], []
        raw = zf.read(txt_names[0])

    lines = raw.split(b"\n")
    records, isin_ticker = _parse_lines(lines)
    console.print(f"[dim]    {len(records)} cotacoes de FIIs | {len(isin_ticker)} ISINs mapeados[/dim]")
    return records, isin_ticker


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def fetch(years: list[int] | None = None) -> tuple[list[dict], list[dict]]:
    """
    Baixa o COTAHIST da B3 para os anos indicados.

    Args:
        years: lista de anos. Padrao: ano atual + ano anterior.

    Returns:
        (cotacoes_records, isin_ticker_records)
    """
    if years is None:
        today = date.today()
        years = sorted({today.year - 1, today.year})

    all_cotacoes: list[dict] = []
    all_isin_ticker: list[dict] = []
    for year in years:
        cotacoes, isin_ticker = _download_year(year)
        all_cotacoes.extend(cotacoes)
        all_isin_ticker.extend(isin_ticker)

    return all_cotacoes, all_isin_ticker
