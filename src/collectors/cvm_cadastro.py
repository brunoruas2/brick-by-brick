"""
Collector — CVM: Cadastro de Fundos de Investimento (cad_fi.csv)

Fonte: https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv
Atualização: terça a sábado, às 08h
Sem autenticação. Encoding: latin-1. Separador: ;

O que coletamos:
  - CNPJ, nome, situação, gestor, administrador, taxa de adm, data de início
  - Filtro: TP_FUNDO == "FII"

O que NÃO está aqui:
  - Ticker (vem do COTAHIST da B3 — etapa 1.4)
  - Segmento / mandato (vem do informe mensal — etapa 1.2)
"""

import io
from datetime import datetime

import pandas as pd
import requests
from rich.console import Console

console = Console()

_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Retorna a coluna ou uma série vazia se não existir no DataFrame."""
    return df[name] if name in df.columns else pd.Series("", index=df.index, dtype=str)


def _normalize_cnpj(s: pd.Series) -> pd.Series:
    """Remove formatação do CNPJ → 14 dígitos numéricos zerados à esquerda."""
    return (
        s.fillna("")
        .astype(str)
        .apply(lambda x: "".join(c for c in x if c.isdigit()).zfill(14))
    )


def _to_float(s: pd.Series) -> pd.Series:
    """Converte coluna com decimal brasileiro (vírgula) para float."""
    return pd.to_numeric(
        s.fillna("").astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _clean_str(s: pd.Series) -> pd.Series:
    """Strip e substitui strings vazias por None."""
    cleaned = s.fillna("").astype(str).str.strip()
    return cleaned.where(cleaned != "", other=None)


def fetch() -> list[dict]:
    """
    Baixa cad_fi.csv da CVM e retorna lista de dicts prontos para upsert.

    Raises:
        requests.HTTPError: se o download falhar.
    """
    console.print("[cyan]  -> CVM -- cadastro (cad_fi.csv)[/cyan]")

    response = requests.get(_URL, timeout=60)
    response.raise_for_status()

    df = pd.read_csv(
        io.StringIO(response.content.decode("latin-1")),
        sep=";",
        dtype=str,
    )

    fiis = df[df["TP_FUNDO"] == "FII"].copy()
    console.print(f"[dim]    {len(fiis)} FIIs encontrados no cadastro[/dim]")

    out = pd.DataFrame({
        "cnpj":          _normalize_cnpj(_col(fiis, "CNPJ_FUNDO")),
        "nome":          _clean_str(_col(fiis, "DENOM_SOCIAL")),
        "situacao":      _clean_str(_col(fiis, "SIT")),
        "gestor":        _clean_str(_col(fiis, "GESTOR")),
        "administrador": _clean_str(_col(fiis, "ADMIN")),
        "taxa_adm":      _to_float(_col(fiis, "TAXA_ADM")),
        "data_inicio":   _clean_str(_col(fiis, "DT_INI_ATIV")),
        "atualizado_em": datetime.now().isoformat(),
    })

    # Remove linhas sem CNPJ válido
    out = out[out["cnpj"].str.len() == 14]

    return out.to_dict("records")
