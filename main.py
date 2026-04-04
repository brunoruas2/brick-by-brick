"""
🧱 Brick by Brick — CLI principal

Uso:
    python main.py update                  # atualiza todas as fontes disponíveis
    python main.py update cadastro         # apenas o cadastro de FIIs (CVM)
    python main.py --help
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="brick",
    help="🧱 Brick by Brick — Análise de Fundos Imobiliários",
    add_completion=False,
)
console = Console()

# Fontes implementadas por etapa do M1
# Adicionamos aqui à medida que cada collector for concluído
_SOURCES_AVAILABLE = ["cadastro", "inf-mensal"]


@app.command()
def update(
    source: str = typer.Argument(
        "all",
        help=(
            "Fonte a atualizar: "
            + " | ".join(["all"] + _SOURCES_AVAILABLE)
        ),
    ),
):
    """
    Baixa dados das fontes primárias (CVM, B3, BCB) e salva no banco local.

    Rodar sem argumentos atualiza todas as fontes disponíveis.
    Idempotente: pode ser executado múltiplas vezes sem duplicar dados.
    """
    from src.storage.database import (
        init_db, upsert_fiis, upsert_inf_mensal, update_fiis_metadata,
    )
    from src.collectors import cvm_cadastro, cvm_inf_mensal

    console.print(
        Panel.fit("Brick by Brick -- Atualizacao de dados", style="bold blue")
    )

    init_db()
    console.print("[dim]  Banco:[/dim] data/brickbybrick.sqlite\n")

    targets = _SOURCES_AVAILABLE if source == "all" else [source]

    for t in targets:
        if t not in _SOURCES_AVAILABLE:
            console.print(
                f"[red]Fonte desconhecida: '{t}'. "
                f"Disponíveis: {', '.join(_SOURCES_AVAILABLE)}[/red]"
            )
            raise typer.Exit(code=1)

    results: list[tuple[str, int]] = []

    # --- Etapa 1.1: Cadastro de FIIs (CVM) ---
    if "cadastro" in targets:
        records = cvm_cadastro.fetch()
        n = upsert_fiis(records)
        results.append(("Cadastro CVM", n))

    # --- Etapa 1.2: Informe Mensal (CVM) ---
    if "inf-mensal" in targets:
        inf_records, meta_records = cvm_inf_mensal.fetch()
        n_inf = upsert_inf_mensal(inf_records)
        n_meta = update_fiis_metadata(meta_records)
        results.append(("Informe Mensal CVM", n_inf))
        results.append(("  segmento/mandato atualizados", n_meta))

    # --- Etapas futuras (adicionadas aqui conforme implementacao) ---
    # if "inf-diario" in targets:   ...  (etapa 1.3)
    # if "cotahist"   in targets:   ...  (etapa 1.4)
    # if "benchmarks" in targets:   ...  (etapa 1.5)

    console.print()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Fonte", style="cyan")
    table.add_column("Registros salvos", justify="right", style="green")
    for label, count in results:
        table.add_row(label, str(count))
    console.print(table)


@app.command()
def status():
    """Exibe o estado atual do banco de dados local."""
    import sqlite3
    from src.config import DB_PATH

    if not DB_PATH.exists():
        console.print("[yellow]Banco não encontrado. Rode: python main.py update[/yellow]")
        raise typer.Exit()

    conn = sqlite3.connect(DB_PATH)
    table = Table(title="Estado do banco", show_header=True, header_style="bold")
    table.add_column("Tabela", style="cyan")
    table.add_column("Registros", justify="right")

    tables = [
        "fiis", "cotacoes", "cota_oficial",
        "inf_mensal", "benchmarks", "carteira", "movimentacoes",
    ]
    for t in tables:
        try:
            (count,) = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        except Exception:
            count = "—"
        table.add_row(t, str(count))

    conn.close()
    console.print(table)


if __name__ == "__main__":
    app()
