"""
Gerencia a conexão e o schema do banco SQLite local.

Regra: todas as operações de escrita usam upsert (INSERT ... ON CONFLICT DO UPDATE),
garantindo que rodar o update duas vezes não duplique dados.
"""

import sqlite3
from contextlib import contextmanager
from src.config import DB_PATH


@contextmanager
def connect():
    """Context manager que abre, comita ou faz rollback e fecha a conexão."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # melhor performance em leituras concorrentes
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fiis (
    cnpj          TEXT PRIMARY KEY,   -- 14 dígitos sem formatação
    ticker        TEXT,               -- preenchido pelo collector B3 (etapa 1.4)
    isin          TEXT,               -- preenchido pelo informe mensal (ISIN do fundo)
    nome          TEXT NOT NULL,
    situacao      TEXT,               -- ex: "EM FUNCIONAMENTO NORMAL"
    segmento      TEXT,               -- preenchido pelo informe mensal (etapa 1.2)
    mandato       TEXT,               -- preenchido pelo informe mensal (etapa 1.2)
    gestor        TEXT,
    administrador TEXT,
    taxa_adm      REAL,
    data_inicio   TEXT,               -- ISO-8601
    atualizado_em TEXT NOT NULL       -- ISO-8601 timestamp da última ingestão
);

CREATE TABLE IF NOT EXISTS isin_ticker (
    isin   TEXT PRIMARY KEY,
    ticker TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cotacoes (
    ticker    TEXT NOT NULL,
    data      TEXT NOT NULL,          -- ISO-8601 (YYYY-MM-DD)
    abertura  REAL,
    maxima    REAL,
    minima    REAL,
    fechamento REAL,
    volume    REAL,
    negocios  INTEGER,
    PRIMARY KEY (ticker, data)
);

CREATE TABLE IF NOT EXISTS cota_oficial (
    cnpj                  TEXT NOT NULL,
    data                  TEXT NOT NULL,  -- ISO-8601
    vl_quota              REAL,
    vl_patrimonio_liquido REAL,
    nr_cotistas           INTEGER,
    PRIMARY KEY (cnpj, data)
);

CREATE TABLE IF NOT EXISTS inf_mensal (
    cnpj                          TEXT NOT NULL,
    data_referencia               TEXT NOT NULL,  -- ISO-8601 (YYYY-MM-DD)
    dy_mes                        REAL,
    rentabilidade_efetiva_mes     REAL,
    rentabilidade_patrimonial_mes REAL,
    patrimonio_liquido            REAL,
    cotas_emitidas                REAL,
    valor_patrimonial_cota        REAL,           -- VPA
    nr_cotistas                   INTEGER,
    taxa_adm                      REAL,
    rendimentos_a_distribuir      REAL,
    imoveis_renda                 REAL,
    cri                           REAL,
    lci                           REAL,
    contas_receber_aluguel        REAL,
    PRIMARY KEY (cnpj, data_referencia)
);

CREATE TABLE IF NOT EXISTS benchmarks (
    data      TEXT PRIMARY KEY,  -- ISO-8601 (YYYY-MM-DD, primeiro dia do mês)
    selic_mes REAL,
    cdi_mes   REAL,
    ipca_mes  REAL
);

CREATE TABLE IF NOT EXISTS carteira (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT NOT NULL,
    cnpj         TEXT,
    cotas        INTEGER NOT NULL,
    preco_medio  REAL NOT NULL,
    data_entrada TEXT NOT NULL,  -- ISO-8601
    ativa        INTEGER NOT NULL DEFAULT 1  -- 1 = ativa, 0 = encerrada
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker         TEXT NOT NULL,
    tipo           TEXT NOT NULL,   -- 'compra' | 'venda' | 'provento'
    data           TEXT NOT NULL,   -- ISO-8601
    quantidade     INTEGER,
    preco_unitario REAL,
    valor_total    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS grupamentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj            TEXT NOT NULL,
    ticker          TEXT,
    data_grupamento TEXT NOT NULL,   -- ISO-8601, primeiro dia do mes (YYYY-MM-01)
    fator           REAL NOT NULL,   -- ex: 10.0 significa 10 cotas antigas = 1 nova
    origem          TEXT NOT NULL,   -- 'manual' | 'auto'
    observacao      TEXT,
    criado_em       TEXT NOT NULL,
    UNIQUE(cnpj, data_grupamento)
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Aplica migracoes incrementais ao schema existente."""
    try:
        conn.execute("ALTER TABLE fiis ADD COLUMN isin TEXT")
        conn.commit()
    except Exception:
        pass  # coluna ja existe
    # Adiciona coluna tipo na tabela grupamentos (bancos criados antes desta versao)
    try:
        conn.execute(
            "ALTER TABLE grupamentos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'grupamento'"
        )
        conn.commit()
    except Exception:
        pass  # coluna ja existe


def init_db() -> None:
    """Cria todas as tabelas se não existirem. Seguro para rodar múltiplas vezes."""
    with connect() as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)


# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------

def upsert_fiis(records: list[dict]) -> int:
    """
    Insere ou atualiza registros na tabela fiis.
    Preserva ticker, segmento e mandato se já preenchidos por outro collector.
    """
    sql = """
        INSERT INTO fiis (cnpj, nome, situacao, gestor, administrador,
                          taxa_adm, data_inicio, atualizado_em)
        VALUES (:cnpj, :nome, :situacao, :gestor, :administrador,
                :taxa_adm, :data_inicio, :atualizado_em)
        ON CONFLICT(cnpj) DO UPDATE SET
            nome          = excluded.nome,
            situacao      = excluded.situacao,
            gestor        = excluded.gestor,
            administrador = excluded.administrador,
            taxa_adm      = excluded.taxa_adm,
            data_inicio   = excluded.data_inicio,
            atualizado_em = excluded.atualizado_em
    """
    with connect() as conn:
        conn.executemany(sql, records)
    return len(records)


def upsert_cota_oficial(records: list[dict]) -> int:
    sql = """
        INSERT INTO cota_oficial (cnpj, data, vl_quota, vl_patrimonio_liquido, nr_cotistas)
        VALUES (:cnpj, :data, :vl_quota, :vl_patrimonio_liquido, :nr_cotistas)
        ON CONFLICT(cnpj, data) DO UPDATE SET
            vl_quota              = excluded.vl_quota,
            vl_patrimonio_liquido = excluded.vl_patrimonio_liquido,
            nr_cotistas           = excluded.nr_cotistas
    """
    with connect() as conn:
        conn.executemany(sql, records)
    return len(records)


def upsert_cotacoes(records: list[dict]) -> int:
    sql = """
        INSERT INTO cotacoes (ticker, data, abertura, maxima, minima,
                              fechamento, volume, negocios)
        VALUES (:ticker, :data, :abertura, :maxima, :minima,
                :fechamento, :volume, :negocios)
        ON CONFLICT(ticker, data) DO UPDATE SET
            abertura   = excluded.abertura,
            maxima     = excluded.maxima,
            minima     = excluded.minima,
            fechamento = excluded.fechamento,
            volume     = excluded.volume,
            negocios   = excluded.negocios
    """
    with connect() as conn:
        conn.executemany(sql, records)
    return len(records)


def upsert_inf_mensal(records: list[dict]) -> int:
    sql = """
        INSERT INTO inf_mensal (
            cnpj, data_referencia, dy_mes, rentabilidade_efetiva_mes,
            rentabilidade_patrimonial_mes, patrimonio_liquido, cotas_emitidas,
            valor_patrimonial_cota, nr_cotistas, taxa_adm,
            rendimentos_a_distribuir, imoveis_renda, cri, lci,
            contas_receber_aluguel
        )
        VALUES (
            :cnpj, :data_referencia, :dy_mes, :rentabilidade_efetiva_mes,
            :rentabilidade_patrimonial_mes, :patrimonio_liquido, :cotas_emitidas,
            :valor_patrimonial_cota, :nr_cotistas, :taxa_adm,
            :rendimentos_a_distribuir, :imoveis_renda, :cri, :lci,
            :contas_receber_aluguel
        )
        ON CONFLICT(cnpj, data_referencia) DO UPDATE SET
            dy_mes                        = excluded.dy_mes,
            rentabilidade_efetiva_mes     = excluded.rentabilidade_efetiva_mes,
            rentabilidade_patrimonial_mes = excluded.rentabilidade_patrimonial_mes,
            patrimonio_liquido            = excluded.patrimonio_liquido,
            cotas_emitidas                = excluded.cotas_emitidas,
            valor_patrimonial_cota        = excluded.valor_patrimonial_cota,
            nr_cotistas                   = excluded.nr_cotistas,
            taxa_adm                      = excluded.taxa_adm,
            rendimentos_a_distribuir      = excluded.rendimentos_a_distribuir,
            imoveis_renda                 = excluded.imoveis_renda,
            cri                           = excluded.cri,
            lci                           = excluded.lci,
            contas_receber_aluguel        = excluded.contas_receber_aluguel
    """
    with connect() as conn:
        conn.executemany(sql, records)
    return len(records)


def update_fiis_metadata(records: list[dict]) -> int:
    """
    Garante que todos os CNPJs do inf_mensal existam em fiis, depois atualiza
    segmento, mandato e isin. FIIs ausentes do cadastro (nao retornados pela
    cvm_cadastro) sao criados com dados minimos para que os joins funcionem.
    """
    import datetime as _dt
    now = _dt.datetime.now().isoformat(timespec="seconds")

    with connect() as conn:
        # Garante registro minimo para CNPJs ainda nao presentes
        conn.executemany(
            """
            INSERT OR IGNORE INTO fiis (cnpj, nome, atualizado_em)
            VALUES (:cnpj, '[inf_mensal]', :now)
            """,
            [{**r, "now": now} for r in records],
        )
        # Atualiza segmento, mandato e isin (nao sobrescreve nome real se ja existir)
        conn.executemany(
            """
            UPDATE fiis
            SET segmento = :segmento,
                mandato  = :mandato,
                isin     = COALESCE(NULLIF(:isin,''), isin)
            WHERE cnpj = :cnpj
            """,
            records,
        )
    return len(records)


def upsert_benchmarks(records: list[dict]) -> int:
    sql = """
        INSERT INTO benchmarks (data, selic_mes, cdi_mes, ipca_mes)
        VALUES (:data, :selic_mes, :cdi_mes, :ipca_mes)
        ON CONFLICT(data) DO UPDATE SET
            selic_mes = excluded.selic_mes,
            cdi_mes   = excluded.cdi_mes,
            ipca_mes  = excluded.ipca_mes
    """
    with connect() as conn:
        conn.executemany(sql, records)
    return len(records)


def update_fiis_isin(records: list[dict]) -> int:
    """
    Atualiza o campo isin na tabela fiis.
    Recebe dicts com chaves: cnpj, isin (e possivelmente outros campos ignorados).
    """
    sql = "UPDATE fiis SET isin = :isin WHERE cnpj = :cnpj"
    valid = [r for r in records if r.get("isin")]
    with connect() as conn:
        conn.executemany(sql, valid)
    return len(valid)


def upsert_isin_ticker(records: list[dict]) -> int:
    """
    Insere ou atualiza mapeamento ISIN -> ticker na tabela isin_ticker.
    """
    sql = """
        INSERT INTO isin_ticker (isin, ticker)
        VALUES (:isin, :ticker)
        ON CONFLICT(isin) DO UPDATE SET ticker = excluded.ticker
    """
    valid = [r for r in records if r.get("isin") and r.get("ticker")]
    with connect() as conn:
        conn.executemany(sql, valid)
    return len(valid)


def upsert_grupamento(record: dict) -> None:
    """
    Insere ou atualiza um grupamento ou desdobramento de cotas.

    Chaves esperadas:
      cnpj, ticker, data_grupamento, fator, tipo, origem, observacao, criado_em
    tipo: 'grupamento' (reverse split) | 'desdobramento' (forward split)
    """
    sql = """
        INSERT INTO grupamentos
            (cnpj, ticker, data_grupamento, fator, tipo, origem, observacao, criado_em)
        VALUES
            (:cnpj, :ticker, :data_grupamento, :fator, :tipo, :origem, :observacao, :criado_em)
        ON CONFLICT(cnpj, data_grupamento) DO UPDATE SET
            fator      = excluded.fator,
            tipo       = excluded.tipo,
            ticker     = excluded.ticker,
            origem     = excluded.origem,
            observacao = excluded.observacao,
            criado_em  = excluded.criado_em
    """
    with connect() as conn:
        conn.execute(sql, record)


def get_grupamentos(tickers: list[str]) -> list[dict]:
    """Retorna grupamentos/desdobramentos registrados para os tickers, ordenados por data."""
    if not tickers:
        return []
    ph = ",".join("?" * len(tickers))
    with connect() as conn:
        rows = conn.execute(
            f"""SELECT g.cnpj, g.ticker, g.data_grupamento, g.fator,
                       COALESCE(g.tipo, 'grupamento') AS tipo,
                       g.origem, g.observacao
                FROM grupamentos g
                WHERE g.ticker IN ({ph})
                ORDER BY g.ticker, g.data_grupamento""",
            tickers,
        ).fetchall()
    return [dict(r) for r in rows]


def link_tickers() -> int:
    """
    Vincula tickers aos CNPJs atraves da tabela isin_ticker.
    1. Atualiza fiis.ticker usando fiis.isin como ponte (isin_ticker).
    2. Backfill de carteira.cnpj para posicoes com cnpj NULL.
    Retorna contagem de FIIs com ticker vinculado.
    """
    with connect() as conn:
        # 1. Popula fiis.ticker via isin
        conn.execute("""
            UPDATE fiis
            SET ticker = (
                SELECT ticker FROM isin_ticker
                WHERE isin_ticker.isin = fiis.isin
            )
            WHERE isin IS NOT NULL
        """)
        # 2. Backfill carteira.cnpj onde esta NULL
        conn.execute("""
            UPDATE carteira
            SET cnpj = (
                SELECT cnpj FROM fiis
                WHERE fiis.ticker = carteira.ticker
            )
            WHERE cnpj IS NULL
        """)
        row = conn.execute(
            "SELECT COUNT(*) FROM fiis WHERE ticker IS NOT NULL"
        ).fetchone()
    return row[0] if row else 0
