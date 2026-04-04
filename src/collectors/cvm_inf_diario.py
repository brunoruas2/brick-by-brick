"""
ATENÇÃO: Este collector NÃO é utilizado no pipeline de FIIs.

O arquivo inf_diario_fi (CVM) contém apenas FI, FIF e FAPI — fundos
convencionais. FIIs não publicam informe diário na CVM; seu preço de mercado
diário vem exclusivamente do COTAHIST da B3 (etapa 1.4).

Este arquivo é mantido apenas para referência futura caso o projeto expanda
para análise de outros tipos de fundos.

---
Collector — CVM: Informe Diario de Fundos de Investimento (NÃO-FII)

Fonte: https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{YYYYMM}.zip
Atualizacao: diaria para M e M-1; semanal para M-2 a M-11.
Sem autenticacao. Encoding: latin-1. Separador: ;

Campos coletados:
  CNPJ_FUNDO, DT_COMPTC  -> chave (cnpj, data)
  VL_QUOTA               -> valor da cota oficial (NAV)
  VL_PATRIM_LIQ          -> patrimonio liquido diario
  NR_COTST               -> numero de cotistas

Observacoes:
  - O arquivo contem TODOS os fundos (FI, FIA, FIDC, FII...). Filtramos pelo
    CNPJ dos FIIs que ja estao na tabela fiis do banco.
  - Por padrao baixa os ultimos 6 meses (suficiente para P/VP e DY recentes).
  - Para carga historica completa, passe months=24 ou mais.
"""

import io
import zipfile
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import pandas as pd
import requests
from rich.console import Console

console = Console()

_BASE_URL = (
    "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/"
    "inf_diario_fi_{yyyymm}.zip"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_cnpj(s: pd.Series) -> pd.Series:
    return (
        s.fillna("").astype(str)
        .apply(lambda x: "".join(c for c in x if c.isdigit()).zfill(14))
    )


def _to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.fillna("").astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.fillna("").astype(str).str.strip(), errors="coerce")


def _months_to_fetch(months: int) -> list[str]:
    """Retorna lista de strings YYYYMM dos ultimos N meses (mais antigo primeiro)."""
    today = date.today()
    result = []
    for i in range(months - 1, -1, -1):
        d = today - relativedelta(months=i)
        result.append(d.strftime("%Y%m"))
    return result


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _download_month(yyyymm: str, fii_cnpjs: set[str]) -> list[dict]:
    """
    Baixa o informe diario de um mes, filtra apenas FIIs e retorna registros.

    Args:
        yyyymm:     mes no formato YYYYMM.
        fii_cnpjs:  conjunto de CNPJs conhecidos como FII (filtro).
    """
    url = _BASE_URL.format(yyyymm=yyyymm)
    console.print(f"[cyan]  -> CVM -- informe diario {yyyymm}[/cyan]")

    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 404:
            console.print(f"[dim]    {yyyymm} nao disponivel[/dim]")
            return []
        r.raise_for_status()
    except requests.RequestException as e:
        console.print(f"[red]    Erro {yyyymm}: {e}[/red]")
        return []

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            return []
        raw = zf.read(csv_names[0])

    df = pd.read_csv(
        io.BytesIO(raw),
        sep=";",
        dtype=str,
        encoding="latin-1",
    )

    # Normaliza CNPJ e filtra apenas FIIs conhecidos
    df["cnpj"] = _normalize_cnpj(df.get("CNPJ_FUNDO", pd.Series(dtype=str)))
    df = df[df["cnpj"].isin(fii_cnpjs)].copy()

    if df.empty:
        console.print(f"[dim]    0 FIIs no arquivo[/dim]")
        return []

    out = pd.DataFrame({
        "cnpj":                  df["cnpj"],
        "data":                  df["DT_COMPTC"].fillna("").str.strip(),
        "vl_quota":              _to_float(df.get("VL_QUOTA",       pd.Series(dtype=str))),
        "vl_patrimonio_liquido": _to_float(df.get("VL_PATRIM_LIQ",  pd.Series(dtype=str))),
        "nr_cotistas":           _to_int(  df.get("NR_COTST",       pd.Series(dtype=str))),
    })

    # Remove linhas sem data ou CNPJ
    out = out[(out["cnpj"].str.len() == 14) & (out["data"] != "")]

    console.print(f"[dim]    {len(out)} registros de FIIs[/dim]")
    return out.to_dict("records")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def fetch(months: int = 6) -> list[dict]:
    """
    Baixa o informe diario dos ultimos N meses e retorna registros para cota_oficial.

    Args:
        months: quantos meses baixar (padrao: 6).

    Returns:
        lista de dicts para upsert_cota_oficial().
    """
    from src.storage.database import connect

    # Carrega CNPJs de FIIs ja cadastrados para usar como filtro
    with connect() as conn:
        rows = conn.execute("SELECT cnpj FROM fiis").fetchall()
    fii_cnpjs = {r["cnpj"] for r in rows}

    if not fii_cnpjs:
        console.print(
            "[yellow]  Nenhum FII no cadastro. "
            "Rode primeiro: python main.py update cadastro[/yellow]"
        )
        return []

    console.print(f"[dim]  Filtrando por {len(fii_cnpjs)} CNPJs de FIIs conhecidos[/dim]")

    all_records: list[dict] = []
    for yyyymm in _months_to_fetch(months):
        records = _download_month(yyyymm, fii_cnpjs)
        all_records.extend(records)

    return all_records
