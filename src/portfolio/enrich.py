"""
Enriquecimento de relatorios gerenciais via FundosNet + Claude API.

Fluxo por fundo (carteira + watchlist):
  1. Busca o relatorio gerencial mais recente no FundosNet (por CNPJ)
  2. Baixa o PDF
  3. Envia ao Claude API (Haiku) com prompt estruturado
  4. Armazena vacancia, contratos, locatarios e alertas em relatorio_gerencial

Requer:
  - pip install anthropic>=0.40.0
  - variavel de ambiente ANTHROPIC_API_KEY

Custo estimado: < R$ 2,50/mes para 15 fundos (Claude Haiku 3).

Cache: nao re-processa se ja existe um relatorio do mesmo CNPJ no mes atual.
Escopo: apenas carteira ativa + watchlist (nao cobre toda a bolsa).
"""

from __future__ import annotations

import datetime
import json
import os

from src.storage.database import (
    connect, upsert_relatorio_gerencial, get_relatorio_gerencial
)
from src.collectors.fundosnet import buscar_relatorio_gerencial, baixar_pdf


_PROMPT = """Voce e um analista de fundos imobiliarios brasileiro.
Analise o relatorio gerencial abaixo e extraia as seguintes informacoes.
Responda APENAS com JSON valido, sem markdown, sem texto adicional.

{
  "vacancia": <numero em % ou null se nao encontrado>,
  "contratos": "<resumo dos vencimentos de contratos (1-2 sentencas) ou null>",
  "locatarios": "<top 3-5 locatarios com % da receita se disponivel, ou null>",
  "alertas": "<2-3 pontos de atencao ou destaques mencionados pelo gestor, ou null>"
}"""


class EnrichError(RuntimeError):
    """Erro durante o processo de enriquecimento."""
    pass


def _get_anthropic_client():
    """Retorna cliente Anthropic. Falha explicitamente se nao instalado ou sem chave."""
    try:
        import anthropic
    except ImportError:
        raise EnrichError(
            "Dependencia ausente. Instale com: pip install anthropic>=0.40.0"
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnrichError(
            "Variavel de ambiente ANTHROPIC_API_KEY nao definida. "
            "Obtenha uma chave em console.anthropic.com e defina: "
            "set ANTHROPIC_API_KEY=sk-ant-..."
        )
    return anthropic.Anthropic(api_key=api_key)


def _extrair_via_claude(pdf_bytes: bytes, url: str) -> dict:
    """
    Envia o PDF ao Claude Haiku e retorna o JSON extraido como dict.

    Campos retornados (todos opcionais/nulos):
      vacancia (float|None), contratos (str|None),
      locatarios (str|None), alertas (str|None)
    """
    client = _get_anthropic_client()

    import base64
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": _PROMPT,
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Remove markdown code fences se presentes
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(l for l in lines if not l.startswith("```")).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise EnrichError(f"Claude retornou resposta nao-JSON: {raw[:200]}")


def _tickers_escopo() -> list[tuple[str, str]]:
    """
    Retorna lista de (ticker, cnpj) para carteira ativa + watchlist.
    Remove duplicatas (um ticker pode estar em ambos).
    """
    from src.storage.database import get_watchlist

    vistos: set[str] = set()
    resultado: list[tuple[str, str]] = []

    with connect() as conn:
        # Carteira ativa
        rows = conn.execute(
            "SELECT DISTINCT ticker, cnpj FROM carteira WHERE ativa = 1"
        ).fetchall()
        for r in rows:
            tk = r["ticker"]
            cnpj = r["cnpj"]
            if tk and cnpj and tk not in vistos:
                vistos.add(tk)
                resultado.append((tk, cnpj))

        # Watchlist
        wl_rows = conn.execute(
            """SELECT w.ticker, f.cnpj
               FROM watchlist w
               JOIN fiis f ON f.ticker = w.ticker"""
        ).fetchall()
        for r in wl_rows:
            tk = r["ticker"]
            cnpj = r["cnpj"]
            if tk and cnpj and tk not in vistos:
                vistos.add(tk)
                resultado.append((tk, cnpj))

    return resultado


def enriquecer(
    ticker: str | None = None,
    forcar: bool = False,
    verbose: bool = True,
) -> list[dict]:
    """
    Executa o enriquecimento para os fundos da carteira e watchlist.

    ticker: se informado, processa apenas esse fundo (deve estar na carteira ou watchlist)
    forcar: se True, re-processa mesmo que ja haja dado do mes atual
    verbose: imprime progresso no terminal

    Retorna lista de dicts com status por fundo:
      ticker, cnpj, status ('ok'|'cache'|'sem_pdf'|'erro'), mensagem
    """
    mes_atual = datetime.datetime.now().strftime("%Y-%m")

    escopo = _tickers_escopo()
    if not escopo:
        return [{"ticker": "--", "cnpj": "--", "status": "erro",
                 "mensagem": "Carteira e watchlist vazias."}]

    if ticker:
        ticker_upper = ticker.upper()
        escopo = [(t, c) for t, c in escopo if t == ticker_upper]
        if not escopo:
            return [{"ticker": ticker_upper, "cnpj": "--", "status": "erro",
                     "mensagem": f"{ticker_upper} nao encontrado na carteira ou watchlist."}]

    relatorios: list[dict] = []

    for tk, cnpj in escopo:
        if verbose:
            print(f"  Processando {tk} ({cnpj})...", end=" ", flush=True)

        # Cache: ja tem relatorio do mes atual?
        if not forcar:
            cached = get_relatorio_gerencial(cnpj, mes_atual)
            if cached:
                if verbose:
                    print("cache")
                relatorios.append({
                    "ticker": tk, "cnpj": cnpj,
                    "status": "cache",
                    "mensagem": f"Ja processado em {cached['extraido_em'][:10]}",
                })
                continue

        # Busca PDFs no FundosNet
        try:
            docs = buscar_relatorio_gerencial(cnpj, max_results=3)
        except Exception as e:
            if verbose:
                print(f"erro FundosNet: {e}")
            relatorios.append({
                "ticker": tk, "cnpj": cnpj,
                "status": "erro",
                "mensagem": f"FundosNet: {e}",
            })
            continue

        if not docs:
            if verbose:
                print("sem PDF")
            relatorios.append({
                "ticker": tk, "cnpj": cnpj,
                "status": "sem_pdf",
                "mensagem": "Nenhum relatorio gerencial encontrado no FundosNet",
            })
            continue

        doc = docs[0]  # mais recente
        url = doc["url"]
        competencia = doc["dataEntrega"][:7]  # YYYY-MM

        # Baixa PDF
        try:
            pdf_bytes = baixar_pdf(url)
        except Exception as e:
            if verbose:
                print(f"erro download: {e}")
            relatorios.append({
                "ticker": tk, "cnpj": cnpj,
                "status": "erro",
                "mensagem": f"Download PDF: {e}",
            })
            continue

        # Extrai via Claude
        try:
            dados = _extrair_via_claude(pdf_bytes, url)
        except EnrichError as e:
            if verbose:
                print(f"erro Claude: {e}")
            relatorios.append({
                "ticker": tk, "cnpj": cnpj,
                "status": "erro",
                "mensagem": str(e),
            })
            continue
        except Exception as e:
            if verbose:
                print(f"erro inesperado: {e}")
            relatorios.append({
                "ticker": tk, "cnpj": cnpj,
                "status": "erro",
                "mensagem": f"Claude API: {e}",
            })
            continue

        # Armazena
        vacancia = dados.get("vacancia")
        try:
            vacancia = float(vacancia) if vacancia is not None else None
        except (TypeError, ValueError):
            vacancia = None

        upsert_relatorio_gerencial({
            "cnpj":        cnpj,
            "competencia": competencia,
            "vacancia":    vacancia,
            "contratos":   dados.get("contratos"),
            "locatarios":  dados.get("locatarios"),
            "alertas":     dados.get("alertas"),
            "fonte_url":   url,
            "extraido_em": datetime.datetime.now().isoformat(timespec="seconds"),
        })

        if verbose:
            print(f"ok (competencia {competencia})")

        relatorios.append({
            "ticker": tk, "cnpj": cnpj,
            "status": "ok",
            "mensagem": f"Extraido de {url[:60]}",
        })

    return relatorios
