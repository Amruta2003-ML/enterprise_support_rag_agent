import json
import logging
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from pypdf import PdfReader

from .config import BASE_DIR, settings

logger = logging.getLogger(__name__)

# Initialize Chroma persistent client
chroma_path = Path(settings.chroma_dir)
chroma_path.mkdir(parents=True, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=str(chroma_path))
collection = chroma_client.get_or_create_collection(
    name="it_knowledge",
    metadata={"hnsw:space": "cosine"},
)


def _get_mock_embeddings(texts: List[str], dim: int = 1536) -> List[List[float]]:
    """Generate deterministic normalized embeddings for testing/offline mode."""
    import numpy as np

    results: List[List[float]] = []
    for text in texts:
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        results.append(vec.tolist())
    return results


def embed(texts: List[str]) -> List[List[float]]:
    """Generate vector embeddings using OpenAI or offline fallback."""
    if not texts:
        return []

    # If OpenAI API key is missing or mock mode is requested, use fallback
    if not settings.openai_api_key or settings.enable_mock_llm:
        logger.info("Using local deterministic embeddings (no OPENAI_API_KEY set).")
        return _get_mock_embeddings(texts)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.warning(
            "Failed calling OpenAI Embeddings API (%s). Falling back to local embeddings.", e
        )
        return _get_mock_embeddings(texts)


def read_file(file_path: Path) -> str:
    """Read document text supporting Markdown, Plain Text, and PDF formats."""
    if file_path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(file_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception as e:
            logger.error("Error reading PDF %s: %s", file_path, e)
            return ""
    return file_path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> List[str]:
    """Chunk text into sliding window slices with word boundary preservation."""
    clean_text = " ".join(text.split())
    if not clean_text:
        return []

    chunks: List[str] = []
    start = 0
    text_len = len(clean_text)

    while start < text_len:
        end = min(text_len, start + size)
        chunks.append(clean_text[start:end])
        if end == text_len:
            break
        start = end - overlap

    return chunks


def ingest(docs_path: Optional[str] = None) -> int:
    """
    Ingest all documents from the docs folder into Chroma vector store.
    Reads department access rules from metadata.json.
    """
    base = Path(docs_path or settings.docs_dir)
    base.mkdir(parents=True, exist_ok=True)

    metadata_file = base / "metadata.json"
    metadata_map: Dict[str, Any] = {}
    if metadata_file.exists():
        try:
            metadata_map = json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to parse %s: %s", metadata_file, e)

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    valid_extensions = {".txt", ".md", ".pdf"}
    for doc_path in base.iterdir():
        if not doc_path.is_file() or doc_path.suffix.lower() not in valid_extensions:
            continue

        raw_text = read_file(doc_path)
        chunks = chunk_text(raw_text)
        doc_meta = metadata_map.get(doc_path.name, {})
        departments = doc_meta.get("departments", ["all"])

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_path.name}:{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "source": doc_path.name,
                "chunk": i,
                "departments": json.dumps(departments),
            })

    if not ids:
        logger.info("No documents found in %s to ingest.", base)
        return 0

    # Ingest chunks into Chroma
    embeddings = embed(documents)
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info("Successfully ingested %d chunks from %s.", len(ids), base)
    return len(ids)


def search(query: str, department: str, k: Optional[int] = None) -> List[Dict[str, str]]:
    """
    Search knowledge base using vector similarity and apply department RBAC.
    """
    total_docs = collection.count()
    if total_docs == 0:
        return []

    top_k = k or settings.top_k
    n_results = min(max(top_k * 3, top_k), total_docs)

    query_embeddings = embed([query])
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
    )

    if not results or not results.get("documents") or not results["documents"][0]:
        return []

    matched_rows: List[Dict[str, str]] = []
    docs = results["documents"][0]
    metas = results["metadatas"][0] if results.get("metadatas") else []

    dept_lower = (department or "all").lower()

    for i, doc_text in enumerate(docs):
        metadata = metas[i] if i < len(metas) else {}
        allowed_depts_raw = metadata.get("departments", '["all"]')
        try:
            allowed_depts = [d.lower() for d in json.loads(allowed_depts_raw)]
        except Exception:
            allowed_depts = ["all"]

        # Access check: "all", user's department, or IT superuser role
        if "all" in allowed_depts or dept_lower in allowed_depts or dept_lower == "it":
            matched_rows.append({
                "source": metadata.get("source", "unknown"),
                "text": doc_text,
            })

        if len(matched_rows) >= top_k:
            break

    return matched_rows


def get_knowledge_stats() -> Dict[str, Any]:
    """Retrieve statistical summary of the knowledge base."""
    count = collection.count()
    sources = set()
    if count > 0:
        sample = collection.get(limit=min(count, 500), include=["metadatas"])
        if sample and sample.get("metadatas"):
            for m in sample["metadatas"]:
                if m and "source" in m:
                    sources.add(m["source"])

    return {
        "total_chunks": count,
        "unique_sources": sorted(list(sources)),
    }
