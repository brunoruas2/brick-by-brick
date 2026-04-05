"""
Coletor FundosNet (B3/CVM) -- Documentos de FIIs.

Fonte publica, sem autenticacao. Retorna JSON com metadados e links de PDFs.

Endpoint principal:
  GET https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados
  Parametros relevantes:
    d=1                -- draw (paginacao DataTables)
    s=0                -- start (offset)
    l=10               -- length (quantidade de resultados)
    f[tipoFundo]=FII
    f[cnpjFundo]=XX.XXX.XXX/XXXX-XX  (CNPJ formatado)
    f[tipoDocumento]=41               (Relatorio Gerencial)

O campo 'id' do resultado permite montar a URL de download do PDF:
  https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id={id}
"""

import requests

_BASE_URL    = "https://fnet.bmfbovespa.com.br/fnet/publico"
_SEARCH_URL  = f"{_BASE_URL}/pesquisarGerenciadorDocumentosDados"
_DOWNLOAD_URL = f"{_BASE_URL}/exibirDocumento"

# Tipo de documento: 41 = Relatorio Gerencial
# Outros tipos uteis: 40 = Informe Mensal, 12 = Fato Relevante
_TIPO_RELATORIO_GERENCIAL = 41

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": f"{_BASE_URL}/abrirGerenciadorDocumentosCVM",
}

_TIMEOUT = 30


def _fmt_cnpj(cnpj: str) -> str:
    """Formata CNPJ de 14 digitos para XX.XXX.XXX/XXXX-XX."""
    c = cnpj.strip().replace(".", "").replace("/", "").replace("-", "")
    if len(c) != 14:
        return cnpj
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}"


def buscar_relatorio_gerencial(cnpj: str, max_results: int = 5) -> list[dict]:
    """
    Busca os ultimos relatorios gerenciais de um FII no FundosNet.

    cnpj: string com 14 digitos (com ou sem formatacao)

    Retorna lista de dicts com chaves:
      id, dataEntrega (YYYY-MM-DD), descricao, url
    Ordenada do mais recente para o mais antigo.

    Raises:
      requests.RequestException em caso de falha de rede.
      ValueError se a resposta nao for JSON valido.
    """
    cnpj_fmt = _fmt_cnpj(cnpj)

    params = {
        "d": 1,
        "s": 0,
        "l": max_results,
        "f[tipoFundo]": "FII",
        "f[cnpjFundo]": cnpj_fmt,
        "f[tipoDocumento]": _TIPO_RELATORIO_GERENCIAL,
    }

    resp = requests.get(_SEARCH_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()

    data = resp.json()
    documentos = data.get("data", [])

    resultado: list[dict] = []
    for doc in documentos:
        doc_id = doc.get("id")
        if not doc_id:
            continue
        resultado.append({
            "id":           doc_id,
            "dataEntrega":  str(doc.get("dataEntrega", ""))[:10],  # YYYY-MM-DD
            "descricao":    str(doc.get("descricao") or ""),
            "url":          f"{_DOWNLOAD_URL}?id={doc_id}",
        })

    # Ordena por data decrescente
    resultado.sort(key=lambda x: x["dataEntrega"], reverse=True)
    return resultado


def baixar_pdf(url: str) -> bytes:
    """
    Baixa o conteudo binario de um PDF do FundosNet.

    Raises:
      requests.RequestException em caso de falha de rede.
    """
    resp = requests.get(url, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.content
