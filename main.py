"""
Brick by Brick -- CLI principal

Uso:
    python main.py update                  # atualiza todas as fontes
    python main.py update cadastro         # apenas o cadastro de FIIs (CVM)
    python main.py update inf-mensal       # apenas informe mensal (CVM)
    python main.py update cotahist         # apenas cotacoes historicas (B3)
    python main.py update benchmarks       # apenas SELIC/CDI/IPCA (BCB)
    python main.py status                  # estado do banco local
    python main.py --help
"""

import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Força UTF-8 no Windows para evitar UnicodeEncodeError com rich/typer
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

app = typer.Typer(
    name="brick",
    help="Brick by Brick -- Analise de Fundos Imobiliarios",
    add_completion=False,
)
console = Console()

_SOURCES_AVAILABLE = ["cadastro", "inf-mensal", "cotahist", "benchmarks"]


@app.command()
def update(
    source: str = typer.Argument(
        "all",
        help="Fonte: all | cadastro | inf-mensal | cotahist | benchmarks",
    ),
):
    """
    Baixa dados das fontes primarias (CVM, B3, BCB) e salva no banco local.

    Sem argumentos atualiza todas as fontes. Idempotente.
    """
    from src.storage.database import (
        init_db, upsert_fiis, upsert_inf_mensal, update_fiis_metadata,
        upsert_cotacoes, upsert_benchmarks,
    )
    from src.collectors import cvm_cadastro, cvm_inf_mensal

    console.print(Panel.fit("Brick by Brick -- Atualizacao de dados", style="bold blue"))
    init_db()
    console.print("[dim]  Banco:[/dim] data/brickbybrick.sqlite\n")

    targets = _SOURCES_AVAILABLE if source == "all" else [source]

    for t in targets:
        if t not in _SOURCES_AVAILABLE:
            console.print(
                f"[red]Fonte desconhecida: '{t}'. "
                f"Disponiveis: {', '.join(_SOURCES_AVAILABLE)}[/red]"
            )
            raise typer.Exit(code=1)

    results: list[tuple[str, int]] = []

    # 1.1 Cadastro de FIIs (CVM)
    if "cadastro" in targets:
        records = cvm_cadastro.fetch()
        results.append(("Cadastro CVM", upsert_fiis(records)))

    # 1.2 Informe Mensal (CVM)
    if "inf-mensal" in targets:
        inf_records, meta_records = cvm_inf_mensal.fetch()
        results.append(("Informe Mensal CVM", upsert_inf_mensal(inf_records)))
        results.append(("  segmento/mandato", update_fiis_metadata(meta_records)))

    # 1.4 Cotacoes historicas B3 (COTAHIST)
    if "cotahist" in targets:
        from src.collectors import b3_cotahist
        results.append(("COTAHIST B3", upsert_cotacoes(b3_cotahist.fetch())))

    # 1.5 Benchmarks BCB
    if "benchmarks" in targets:
        from src.collectors import bcb_series
        results.append(("Benchmarks BCB (24m)", upsert_benchmarks(bcb_series.fetch(months=24))))

    console.print()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Fonte", style="cyan")
    table.add_column("Registros", justify="right", style="green")
    for label, count in results:
        table.add_row(label, str(count))
    console.print(table)


@app.command()
def status():
    """Exibe o estado atual do banco de dados local."""
    import sqlite3
    from src.config import DB_PATH

    if not DB_PATH.exists():
        console.print("[yellow]Banco nao encontrado. Rode: python main.py update[/yellow]")
        raise typer.Exit()

    conn = sqlite3.connect(DB_PATH)
    table = Table(title="Estado do banco", show_header=True, header_style="bold")
    table.add_column("Tabela", style="cyan")
    table.add_column("Registros", justify="right")

    for t in ["fiis", "cotacoes", "cota_oficial", "inf_mensal", "benchmarks",
              "carteira", "movimentacoes"]:
        try:
            (count,) = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        except Exception:
            count = "?"
        table.add_row(t, str(count))

    conn.close()
    console.print(table)


if __name__ == "__main__":
    app()
