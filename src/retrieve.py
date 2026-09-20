"""Vector search over documentation.json.

Returns nothing rather than an irrelevant passage (Build Spec §03 Retrieve).
Identifiers are corpus `doc_id` values so citations can be verified (A4, A6).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_DIR,
    EMBEDDING_MODEL,
    RETRIEVAL_BACKEND,
    RETRIEVAL_MIN_SCORE,
    RETRIEVAL_TOP_K,
)

COLLECTION = "cloudserve_docs"


def _load_docs(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or (DATA_DIR / "documentation.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _split_articles(docs: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    texts: list[str] = []
    metas: list[dict[str, Any]] = []
    for doc in docs:
        content = doc.get("content") or ""
        chunks = splitter.split_text(content)
        if not chunks:
            chunks = [content[:CHUNK_SIZE] or doc.get("title", "")]
        title = doc.get("title") or ""
        for i, chunk in enumerate(chunks):
            texts.append(f"{title}\n{chunk}")
            metas.append(
                {
                    "doc_id": doc["doc_id"],
                    "title": doc.get("title", ""),
                    "category": doc.get("category", ""),
                    "chunk_index": i,
                    "passage_id": f"{doc['doc_id']}#c{i}",
                }
            )
    return texts, metas


class Retriever:
    def __init__(self) -> None:
        self._ready = False
        self._embeddings = None
        self._collection = None
        self._client = None

    def _embedder(self):
        if self._embeddings is None:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            self._embeddings = SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
        return self._embeddings

    def build(self, docs_path: Path | None = None, persist_dir: str | None = None) -> int:
        import chromadb

        persist_dir = persist_dir or CHROMA_PATH
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        docs = _load_docs(docs_path)
        texts, metas = _split_articles(docs)
        ids = [m["passage_id"] for m in metas]
        self._client = chromadb.PersistentClient(path=persist_dir)
        try:
            self._client.delete_collection(COLLECTION)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=self._embedder(),
            metadata={"hnsw:space": "cosine"},
        )
        # chroma 0.5 batches
        batch = 64
        for i in range(0, len(texts), batch):
            self._collection.add(
                ids=ids[i : i + batch],
                documents=texts[i : i + batch],
                metadatas=metas[i : i + batch],
            )
        self._ready = True
        return len(texts)

    def ensure(self) -> None:
        import chromadb

        if self._ready and self._collection is not None:
            return
        persist_dir = CHROMA_PATH
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        existing = [c.name for c in self._client.list_collections()]
        if COLLECTION not in existing:
            self.build()
            return
        self._collection = self._client.get_collection(
            name=COLLECTION, embedding_function=self._embedder()
        )
        if self._collection.count() == 0:
            self.build()
            return
        self._ready = True

    def search(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        min_score = RETRIEVAL_MIN_SCORE if min_score is None else min_score
        top_k = top_k or RETRIEVAL_TOP_K
        if not (query or "").strip():
            return []
        try:
            self.ensure()
            result = self._collection.query(
                query_texts=[query],
                n_results=max(top_k, 1),
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]
        hits: list[dict[str, Any]] = []
        for i, text in enumerate(docs):
            dist = float(distances[i]) if i < len(distances) else 1.0
            # cosine distance: 0 is identical. Convert to similarity.
            score = 1.0 - dist
            if score < min_score:
                continue
            meta = metas[i] if i < len(metas) else {}
            hits.append(
                {
                    "doc_id": meta.get("doc_id"),
                    "title": meta.get("title"),
                    "category": meta.get("category"),
                    "passage_id": meta.get("passage_id") or (ids[i] if i < len(ids) else ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "text": text,
                    "score": round(score, 4),
                }
            )
        return hits[:top_k]


class LexicalRetriever:
    """TF-IDF fallback used in CI and when Chroma/embeddings cannot load (A11)."""

    def __init__(self) -> None:
        self._vectorizer = None
        self._matrix = None
        self._texts: list[str] = []
        self._metas: list[dict[str, Any]] = []
        self._ready = False

    def build(self, docs_path: Path | None = None, persist_dir: str | None = None) -> int:
        from sklearn.feature_extraction.text import TfidfVectorizer

        docs = _load_docs(docs_path)
        self._texts, self._metas = _split_articles(docs)
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._texts)
        self._ready = True
        return len(self._texts)

    def ensure(self) -> None:
        if not self._ready:
            self.build()

    def search(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        min_score = RETRIEVAL_MIN_SCORE if min_score is None else min_score
        top_k = top_k or RETRIEVAL_TOP_K
        if not (query or "").strip():
            return []
        self.ensure()
        q = self._vectorizer.transform([query])
        scores = (self._matrix @ q.T).toarray().ravel()
        order = scores.argsort()[::-1][: max(top_k * 3, top_k)]
        hits = []
        for idx in order:
            score = float(scores[idx])
            if score < min_score:
                continue
            meta = self._metas[idx]
            hits.append(
                {
                    "doc_id": meta.get("doc_id"),
                    "title": meta.get("title"),
                    "category": meta.get("category"),
                    "passage_id": meta.get("passage_id"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "text": self._texts[idx],
                    "score": round(score, 4),
                }
            )
            if len(hits) >= top_k:
                break
        return hits


_default = None


def get_retriever():
    global _default
    if _default is None:
        if RETRIEVAL_BACKEND == "lexical":
            _default = LexicalRetriever()
        else:
            try:
                _default = Retriever()
                _default.ensure()
            except Exception:
                _default = LexicalRetriever()
    return _default


def retrieve(query: str, **kwargs: Any) -> list[dict[str, Any]]:
    return get_retriever().search(query, **kwargs)


def article_preview(doc_id: str, limit: int = 280) -> str:
    """Resolve a doc_id to corpus text for citation checks (A4/A6)."""
    for doc in _load_docs():
        if doc.get("doc_id") == doc_id:
            content = re.sub(r"\s+", " ", doc.get("content") or "")
            return content[:limit]
    return ""
