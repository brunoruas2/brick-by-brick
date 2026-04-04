"""
Collector — CVM: Informe Mensal de FII

Fonte: https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ANO}.zip
Atualizacao: semanal. Sem autenticacao. Encoding: latin-1. Separador: ;

Cada ZIP contem 3 CSVs:
  _geral_         -> nome, segmento, mandato, tipo de gestao, ISIN
  _complemento_   -> DY, rentabilidade, PL, VPA, cotistas, taxas
  _ativo_passivo_ -> CRI, LCI, imoveis, contas a receber, rendimentos a distribuir

Estrategia:
  - Por padrao baixa o ano atual e o anterior (garante 12+ meses para calculo de DY)
  - _complemento_ + _ativo_passivo_ sao unidos por (cnpj, data_referencia) -> inf_mensal
  - _geral_ alimenta atualizacao de segmento/mandato na tabela fiis
"""

import io
import zipfile
from datetime import datetime

import pandas as pd
import requests
from rich.console import Console

console = Console()

_BASE_URL = (
    "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/"
    "inf_mensal_fii_{year}.zip"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Retorna coluna ou serie vazia se nao existir."""
    return df[name] if name in df.columns else pd.Series("", index=df.index, dtype=str)


def _normalize_cnpj(s: pd.Series) -> pd.Series:
    return (
        s.fillna("").astype(str)
        .apply(lambda x: "".join(c for c in x if c.isdigit()).zfill(14))
    )


def _to_float(s: pd.Series) -> pd.Series:
    """Converte coluna com decimal brasileiro (virgula) para float."""
    return pd.to_numeric(
        s.fillna("").astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.fillna("").astype(str).str.strip(), errors="coerce")


def _normalize_date(s: pd.Series) -> pd.Series:
    """Normaliza datas para ISO-8601 (YYYY-MM-DD). Suporta ambos os formatos da CVM."""
    def parse(v):
        v = str(v).strip()
        if not v or v.lower() in ("nan", "none", ""):
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                continue
        return v  # retorna como esta se nao reconhecer
    return s.apply(parse)


def _add_floats(a: pd.Series, b: pd.Series) -> pd.Series:
    """Soma dois float Series ignorando NaN (NaN + valor = valor)."""
    return _to_float(a).fillna(0) + _to_float(b).fillna(0)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _download_year(year: int) -> dict[str, pd.DataFrame] | None:
    """Baixa o ZIP do informe mensal de um ano e retorna os 3 DataFrames."""
    url = _BASE_URL.format(year=year)
    console.print(f"[cyan]  -> CVM -- informe mensal {year}[/cyan]")

    try:
        r = requests.get(url, timeout=180)
        if r.status_code == 404:
            console.print(f"[dim]    Arquivo {year} nao disponivel[/dim]")
            return None
        r.raise_for_status()
    except requests.RequestException as e:
        console.print(f"[red]    Erro ao baixar {year}: {e}[/red]")
        return None

    dfs: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            raw = zf.read(name)
            df = pd.read_csv(
                io.BytesIO(raw),
                sep=";",
                dtype=str,
                encoding="latin-1",
            )
            lower = name.lower()
            if "_geral_" in lower:
                dfs["geral"] = df
            elif "_complemento_" in lower:
                dfs["complemento"] = df
            elif "_ativo_passivo_" in lower:
                dfs["ativo_passivo"] = df

    console.print(f"[dim]    {', '.join(dfs.keys())} carregados[/dim]")
    return dfs or None


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------

def _build_inf_mensal(
    comp: pd.DataFrame, ap: pd.DataFrame
) -> list[dict]:
    """
    Une complemento + ativo_passivo e retorna registros para a tabela inf_mensal.
    """
    if comp.empty:
        return []

    # Padroniza colunas-chave
    comp = comp.copy()
    comp["cnpj"] = _normalize_cnpj(_col(comp, "CNPJ_Fundo_Classe"))
    comp["data_referencia"] = _normalize_date(_col(comp, "Data_Referencia"))

    # Versao do informe (pode haver reapresentacoes; fica com a mais recente)
    if "Versao" in comp.columns:
        comp = (
            comp.sort_values("Versao", ascending=True)
            .drop_duplicates(subset=["cnpj", "data_referencia"], keep="last")
        )

    if not ap.empty:
        ap = ap.copy()
        ap["cnpj"] = _normalize_cnpj(_col(ap, "CNPJ_Fundo_Classe"))
        ap["data_referencia"] = _normalize_date(_col(ap, "Data_Referencia"))
        if "Versao" in ap.columns:
            ap = (
                ap.sort_values("Versao", ascending=True)
                .drop_duplicates(subset=["cnpj", "data_referencia"], keep="last")
            )
        merged = comp.merge(
            ap[["cnpj", "data_referencia"]
               + [c for c in ap.columns if c not in comp.columns]],
            on=["cnpj", "data_referencia"],
            how="left",
        )
    else:
        merged = comp

    out = pd.DataFrame({
        "cnpj": merged["cnpj"],
        "data_referencia": merged["data_referencia"],
        # --- de _complemento_ ---
        "dy_mes":                        _to_float(_col(merged, "Percentual_Dividend_Yield_Mes")),
        "rentabilidade_efetiva_mes":     _to_float(_col(merged, "Percentual_Rentabilidade_Efetiva_Mes")),
        "rentabilidade_patrimonial_mes": _to_float(_col(merged, "Percentual_Rentabilidade_Patrimonial_Mes")),
        "patrimonio_liquido":            _to_float(_col(merged, "Patrimonio_Liquido")),
        "cotas_emitidas":                _to_float(_col(merged, "Cotas_Emitidas")),
        "valor_patrimonial_cota":        _to_float(_col(merged, "Valor_Patrimonial_Cotas")),
        "nr_cotistas":                   _to_int(_col(merged, "Total_Numero_Cotistas")),
        "taxa_adm":                      _to_float(_col(merged, "Percentual_Despesas_Taxa_Administracao")),
        # --- de _ativo_passivo_ ---
        "rendimentos_a_distribuir":  _to_float(_col(merged, "Rendimentos_Distribuir")),
        "imoveis_renda":             _add_floats(
                                         _col(merged, "Imoveis_Renda_Acabados"),
                                         _col(merged, "Imoveis_Renda_Construcao"),
                                     ),
        "cri":                       _to_float(_col(merged, "CRI")),
        "lci":                       _to_float(_col(merged, "LCI")),
        "contas_receber_aluguel":    _to_float(_col(merged, "Contas_Receber_Aluguel")),
    })

    # Remove linhas sem CNPJ ou data validos
    # Parênteses obrigatórios: & tem precedência maior que == em pandas
    out = out[
        (out["cnpj"].str.len() == 14)
        & (out["data_referencia"].notna())
    ]

    return out.to_dict("records")


def _build_fii_updates(geral: pd.DataFrame) -> list[dict]:
    """
    Extrai segmento, mandato e ISIN do _geral_ para atualizar a tabela fiis.
    Retorna apenas o registro mais recente por CNPJ.
    """
    if geral.empty:
        return []

    g = geral.copy()
    g["cnpj"] = _normalize_cnpj(_col(g, "CNPJ_Fundo_Classe"))
    g["data_referencia"] = _normalize_date(_col(g, "Data_Referencia"))

    # Fica com a entrada mais recente por fundo
    g = g.sort_values("data_referencia", ascending=True).drop_duplicates(
        subset=["cnpj"], keep="last"
    )

    out = pd.DataFrame({
        "cnpj":     g["cnpj"],
        "segmento": g["Segmento_Atuacao"].fillna("").str.strip()
                    if "Segmento_Atuacao" in g.columns
                    else pd.Series("", index=g.index),
        "mandato":  g["Mandato"].fillna("").str.strip()
                    if "Mandato" in g.columns
                    else pd.Series("", index=g.index),
        "isin":     _col(g, "Codigo_ISIN").str.strip(),
    })

    out = out[out["cnpj"].str.len() == 14]
    out = out.replace("", None)

    return out.to_dict("records")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def fetch(years: list[int] | None = None) -> tuple[list[dict], list[dict]]:
    """
    Baixa o informe mensal da CVM para os anos indicados.

    Args:
        years: lista de anos. Padrao: ano atual + ano anterior.

    Returns:
        (inf_mensal_records, fii_updates)
        inf_mensal_records -> upsert_inf_mensal()
        fii_updates        -> update_fiis_metadata()
    """
    if years is None:
        now = datetime.now()
        years = sorted({now.year - 1, now.year})

    all_inf: list[dict] = []
    all_meta: list[dict] = []

    for year in years:
        dfs = _download_year(year)
        if dfs is None:
            continue

        inf = _build_inf_mensal(
            dfs.get("complemento", pd.DataFrame()),
            dfs.get("ativo_passivo", pd.DataFrame()),
        )
        meta = _build_fii_updates(dfs.get("geral", pd.DataFrame()))

        console.print(f"[dim]    {len(inf)} registros mensais | {len(meta)} fundos com segmento[/dim]")

        all_inf.extend(inf)
        all_meta.extend(meta)

    return all_inf, all_meta
