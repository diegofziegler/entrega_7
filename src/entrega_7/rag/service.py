import asyncio
import hashlib
import glob
import math
import os
import re
from pathlib import Path
from collections import Counter

from langchain_core.documents import Document
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from entrega_7.config import settings
from entrega_7.logging_config import rag_logger


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


class RAGService:
    """Pinecone-backed hybrid retriever: dense Pinecone results + lexical RRF."""

    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self._documents: list[Document] = []
        self._initialize_lock = asyncio.Lock()

    async def initialize(self) -> None:
        if self.vectorstore is not None:
            return
        async with self._initialize_lock:
            if self.vectorstore is not None:
                return
            if not settings.PINECONE_API_KEY or not settings.PINECONE_INDEX_NAME:
                raise RuntimeError("PINECONE_API_KEY y PINECONE_INDEX_NAME son obligatorios para RAG.")
            await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        from langchain_openai import OpenAIEmbeddings
        from langchain_pinecone import PineconeVectorStore

        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY es obligatoria para generar embeddings compatibles con Pinecone.")
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            dimensions=1536,
            api_key=settings.OPENAI_API_KEY,
        )
        self.vectorstore = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            pinecone_api_key=settings.PINECONE_API_KEY,
            embedding=self.embeddings,
            namespace=settings.PINECONE_NAMESPACE or None,
            text_key="text",
        )
        rag_logger.info("Conexión a Pinecone preparada para búsqueda híbrida.")

    async def ingest_directory(self, data_dir: str | None = None) -> int:
        await self.initialize()
        target_dir = data_dir or settings.DATA_DIR
        md_files = sorted(glob.glob(os.path.join(target_dir, "**", "*.md"), recursive=True))
        if not md_files:
            rag_logger.warning("No se encontraron documentos Markdown en %s", target_dir)
            self._documents = []
            return 0

        docs: list[Document] = []
        for file_path in md_files:
            content = await asyncio.to_thread(Path(file_path).read_text, encoding="utf-8")
            docs.append(Document(
                page_content=content,
                metadata={"source": os.path.basename(file_path), "path": os.path.relpath(file_path, target_dir)},
            ))

        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        chunks = splitter.split_documents(docs)
        ids = []
        for index, doc in enumerate(chunks):
            doc.metadata["chunk_id"] = index
            ids.append(hashlib.sha256(f"{doc.metadata['path']}:{doc.page_content}".encode("utf-8")).hexdigest())
        await self.vectorstore.aadd_documents(chunks, ids=ids)
        self._documents = chunks
        rag_logger.info("Ingestados %d chunks en Pinecone.", len(chunks))
        return len(chunks)

    async def search(self, query: str, k: int = 4) -> list[Document]:
        if k < 1:
            return []
        await self.initialize()
        from opentelemetry import trace

        with trace.get_tracer("entrega_7.rag").start_as_current_span("rag.hybrid_search") as span:
            span.set_attribute("retrieval.strategy", "pinecone_dense+bm25_lexical_rrf")
            span.set_attribute("retrieval.top_k", k)
            dense_results = await self.vectorstore.asimilarity_search(query, k=max(k * 3, 10))
            lexical_results = await asyncio.to_thread(self._lexical_search, query, max(k * 3, 10))

            # Reciprocal Rank Fusion combines Pinecone's dense ranking and BM25-style lexical ranking.
            scores: dict[tuple[str, str], float] = {}
            documents: dict[tuple[str, str], Document] = {}
            for result_list in (dense_results, lexical_results):
                for rank, doc in enumerate(result_list, start=1):
                    key = (str(doc.metadata.get("source", "")), doc.page_content)
                    documents[key] = doc
                    scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
            results = [documents[key] for key in sorted(scores, key=scores.get, reverse=True)[:k]]
            span.set_attribute("retrieval.pinecone.result_count", len(dense_results))
            span.set_attribute("retrieval.lexical.result_count", len(lexical_results))
            span.set_attribute("retrieval.fused.result_count", len(results))
            rag_logger.info("Búsqueda híbrida completada: dense=%d lexical=%d fused=%d", len(dense_results), len(lexical_results), len(results))
            return results

    def _lexical_search(self, query: str, k: int) -> list[Document]:
        query_terms = _tokens(query)
        if not query_terms or not self._documents:
            return []
        documents = [(doc, _tokens(doc.page_content)) for doc in self._documents]
        avg_length = sum(len(words) for _, words in documents) / max(len(documents), 1)
        doc_frequency = Counter(term for term in set(query_terms) for _, words in documents if term in words)
        ranked = []
        for doc, words in documents:
            frequencies = Counter(words)
            score = 0.0
            for term in query_terms:
                tf = frequencies[term]
                if tf:
                    idf = math.log(1 + (len(documents) - doc_frequency[term] + 0.5) / (doc_frequency[term] + 0.5))
                    score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * len(words) / max(avg_length, 1)))
            if score:
                ranked.append((score, doc))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in ranked[:k]]


rag_service = RAGService()
