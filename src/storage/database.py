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
"""


def init_db() -> None:
    """Cria todas as tabelas se não existirem. Seguro para rodar múltiplas vezes."""
    with connect() as conn:
        conn.executescript(_SCHEMA)


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
    Atualiza segmento e mandato na tabela fiis.
    Nao sobrescreve outros campos (ticker, gestor, etc.).
    """
    sql = """
        UPDATE fiis
        SET segmento = :segmento,
            mandato  = :mandato
        WHERE cnpj = :cnpj
    """
    with connect() as conn:
        conn.executemany(sql, records)
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
