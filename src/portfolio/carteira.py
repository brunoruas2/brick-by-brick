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


def export_template(path: str) -> None:
    """
    Salva um arquivo Excel com o template de importacao de carteira.

    Colunas: ticker | tipo | data | cotas | preco
    Inclui linhas de exemplo e validacao de lista suspensa para 'tipo'.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "carteira"

    # Cabecalho
    headers = ["ticker", "tipo", "data", "cotas", "preco"]
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Linhas de exemplo
    exemplos = [
        ["HGLG11", "compra", "2024-06-15", 100, 165.50],
        ["MXRF11", "compra", "2024-08-10", 500,   9.85],
        ["XPLG11", "compra", "2024-09-20", 200, 103.20],
        ["MXRF11", "venda",  "2026-04-01", 100,  10.20],
    ]
    example_fill = PatternFill("solid", fgColor="D9E1F2")
    for row_idx, row_data in enumerate(exemplos, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill = example_fill
            if col_idx == 5:
                cell.number_format = "#,##0.00"

    # Validacao de lista suspensa para coluna 'tipo' (B)
    dv = DataValidation(type="list", formula1='"compra,venda"', allow_blank=False)
    dv.sqref = "B2:B10000"
    ws.add_data_validation(dv)

    # Largura das colunas
    ws.column_dimensions["A"].width = 12  # ticker
    ws.column_dimensions["B"].width = 10  # tipo
    ws.column_dimensions["C"].width = 14  # data
    ws.column_dimensions["D"].width = 8   # cotas
    ws.column_dimensions["E"].width = 12  # preco

    # Aba de instrucoes
    wi = wb.create_sheet("instrucoes")
    instrucoes = [
        ("Campo",  "Formato",        "Exemplo",     "Obrigatorio"),
        ("ticker", "Texto maiusculo", "HGLG11",      "Sim"),
        ("tipo",   "compra ou venda", "compra",      "Sim"),
        ("data",   "YYYY-MM-DD",      "2024-06-15",  "Sim"),
        ("cotas",  "Numero inteiro",  "100",         "Sim"),
        ("preco",  "Preco por cota",  "165.50",      "Sim"),
    ]
    hf = Font(bold=True)
    for r, row in enumerate(instrucoes, start=1):
        for c, val in enumerate(row, start=1):
            cell = wi.cell(row=r, column=c, value=val)
            if r == 1:
                cell.font = hf
    wi.column_dimensions["A"].width = 10
    wi.column_dimensions["B"].width = 20
    wi.column_dimensions["C"].width = 16
    wi.column_dimensions["D"].width = 12

    wb.save(path)


def import_from_excel(path: str, dry_run: bool = False) -> tuple[int, list[str]]:
    """
    Le o arquivo Excel (aba 'carteira') e registra as operacoes.

    Retorna:
        (n_sucesso, lista_de_erros)

    Erros nao interrompem o processamento: linhas validas sao inseridas
    mesmo que outras contenham erros.
    """
    df = pd.read_excel(path, sheet_name="carteira", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"ticker", "tipo", "data", "cotas", "preco"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no arquivo: {', '.join(sorted(missing))}")

    erros: list[str] = []
    n_sucesso = 0

    for i, row in df.iterrows():
        linha = i + 2  # +2 porque cabecalho e index 0-based

        # Ignora linhas completamente vazias
        if all(pd.isna(row[c]) or str(row[c]).strip() == "" for c in required):
            continue

        # Valida campos obrigatorios
        valores: dict = {}
        ok = True
        for campo in required:
            v = str(row.get(campo, "")).strip()
            if not v or v.lower() == "nan":
                erros.append(f"Linha {linha}: campo '{campo}' vazio")
                ok = False
        if not ok:
            continue

        ticker = str(row["ticker"]).strip().upper()
        tipo   = str(row["tipo"]).strip().lower()
        data   = str(row["data"]).strip()

        if tipo not in ("compra", "venda"):
            erros.append(f"Linha {linha} ({ticker}): tipo '{tipo}' invalido — use 'compra' ou 'venda'")
            continue

        try:
            cotas = int(float(str(row["cotas"]).strip()))
            if cotas <= 0:
                raise ValueError
        except (ValueError, TypeError):
            erros.append(f"Linha {linha} ({ticker}): 'cotas' deve ser inteiro positivo")
            continue

        try:
            preco = float(str(row["preco"]).strip().replace(",", "."))
            if preco <= 0:
                raise ValueError
        except (ValueError, TypeError):
            erros.append(f"Linha {linha} ({ticker}): 'preco' deve ser numero positivo")
            continue

        # Valida formato da data
        try:
            pd.Timestamp(data)
            # Normaliza para YYYY-MM-DD independente do formato de entrada
            data = pd.Timestamp(data).strftime("%Y-%m-%d")
        except Exception:
            erros.append(f"Linha {linha} ({ticker}): data '{data}' invalida — use YYYY-MM-DD")
            continue

        if dry_run:
            n_sucesso += 1
            continue

        try:
            if tipo == "compra":
                add_compra(ticker, cotas, preco, data)
            else:
                add_venda(ticker, cotas, preco, data)
            n_sucesso += 1
        except Exception as e:
            erros.append(f"Linha {linha} ({ticker}): {e}")

    return n_sucesso, erros


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
