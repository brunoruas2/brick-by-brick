from pathlib import Path

# Raiz do projeto (um nível acima de src/)
ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DIR  = DATA_DIR / "raw"
DB_PATH  = DATA_DIR / "brickbybrick.sqlite"
