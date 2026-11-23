import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.rag import ingest

if __name__ == "__main__":
    count = ingest()
    print(f"Successfully ingested {count} chunks into Chroma vector database.")
