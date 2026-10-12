import os
import glob
import asyncio
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from src.entrega_7.config import settings
from src.entrega_7.logging_config import rag_logger


class SimpleLocalVectorStore:
    """Fallback in-memory vector store with cosine similarity calculation when Pinecone is unavailable."""
    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.documents: List[Document] = []
        self.vectors: List[List[float]] = []

    async def aadd_documents(self, docs: List[Document]):
        texts = [doc.page_content for doc in docs]
        embeds = await asyncio.to_thread(self.embeddings.embed_documents, texts)
        self.documents.extend(docs)
        self.vectors.extend(embeds)
        rag_logger.info(f"LocalVectorStore: Agregados {len(docs)} documentos al almacenamiento local/en memoria.")

    async def asimilarity_search(self, query: str, k: int = 4) -> List[Document]:
        if not self.documents:
            return []
        query_embed = await asyncio.to_thread(self.embeddings.embed_query, query)

        # Compute cosine similarity
        scores = []
        for i, vec in enumerate(self.vectors):
            dot = sum(q * v for q, v in zip(query_embed, vec))
            norm_q = sum(q * q for q in query_embed) ** 0.5
            norm_v = sum(v * v for v in vec) ** 0.5
            sim = dot / (norm_q * norm_v) if norm_q and norm_v else 0.0
            scores.append((sim, self.documents[i]))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = [doc for _, doc in scores[:k]]
        rag_logger.info(f"LocalVectorStore: Búsqueda de similitud para '{query}' retornó {len(results)} resultados.")
        return results


class RAGService:
    def __init__(self):
        self.embeddings = self._init_embeddings()
        self.vectorstore = None
        self._init_vectorstore()

    def _init_embeddings(self):
        rag_logger.info(f"Inicializando embeddings con modelo: {settings.EMBEDDING_MODEL_NAME}")
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
        except Exception as e:
            rag_logger.warning(f"Error al cargar HuggingFaceEmbeddings ({e}). Usando FakeEmbeddings fallback.")
            from langchain_community.embeddings import FakeEmbeddings
            return FakeEmbeddings(size=384)

    def _init_vectorstore(self):
        if settings.PINECONE_API_KEY and settings.PINECONE_INDEX_NAME:
            try:
                from pinecone import Pinecone
                from langchain_pinecone import PineconeVectorStore
                pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                self.vectorstore = PineconeVectorStore.from_existing_index(
                    index_name=settings.PINECONE_INDEX_NAME,
                    embedding=self.embeddings
                )
                rag_logger.info("VectorStore Pinecone inicializado exitosamente.")
                return
            except Exception as e:
                rag_logger.warning(f"No se pudo conectar a Pinecone: {e}. Usando fallback local/en memoria.")

        rag_logger.info("Usando SimpleLocalVectorStore como almacenamiento vectorial fallback.")
        self.vectorstore = SimpleLocalVectorStore(self.embeddings)

    async def ingest_directory(self, data_dir: str = None) -> int:
        target_dir = data_dir or settings.DATA_DIR
        rag_logger.info(f"Iniciando ingesta de documentos desde: {target_dir}")
        md_files = sorted(list(set(glob.glob(os.path.join(target_dir, "**/*.md"), recursive=True))))

        if not md_files:
            rag_logger.warning(f"No se encontraron archivos .md en {target_dir}")
            return 0

        docs = []
        for file_path in md_files:
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["source"] = os.path.basename(file_path)
                docs.extend(loaded)
            except Exception as e:
                rag_logger.error(f"Error cargando archivo {file_path}: {e}")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        split_docs = text_splitter.split_documents(docs)

        if hasattr(self.vectorstore, "aadd_documents"):
            await self.vectorstore.aadd_documents(split_docs)
        else:
            await asyncio.to_thread(self.vectorstore.add_documents, split_docs)

        rag_logger.info(f"Ingesta completada: {len(split_docs)} chunks procesados e indexados.")
        return len(split_docs)

    async def search(self, query: str, k: int = 4) -> List[Document]:
        rag_logger.info(f"Ejecutando búsqueda RAG para consulta: '{query}'")
        if hasattr(self.vectorstore, "asimilarity_search"):
            return await self.vectorstore.asimilarity_search(query, k=k)
        else:
            return await asyncio.to_thread(self.vectorstore.similarity_search, query, k=k)


rag_service = RAGService()
