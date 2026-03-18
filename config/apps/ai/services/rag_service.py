import os
from langchain_postgres.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Singleton instance to avoid reloading embeddings model
_rag_service_instance = None

# Relevance threshold — documents above this cosine distance are considered irrelevant.
# PGVector returns L2 distance; lower = more similar.
# 0.0–0.4 = highly relevant, 0.4–0.65 = somewhat relevant, >0.65 = likely irrelevant
RELEVANCE_THRESHOLD = 0.65


class HybridRAGService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # Build connection string from env or hardcoded for demo
        db_user = os.environ.get("DB_USER", "postgres")
        db_pass = os.environ.get("DB_PASSWORD", "postgres")
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "voice_agent")

        self.conn_str = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        self.vector_db = PGVector(
            embeddings=self.embeddings,
            collection_name="knowledge_base",
            connection=self.conn_str,
        )

        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def load_documents(self, text_content, metadata=None):
        """
        Ingest text content into the vector database with proper chunking.

        Args:
            text_content: String content or list of Document objects
            metadata: Optional metadata dict to attach to all chunks
        """
        if isinstance(text_content, str):
            chunks = self.text_splitter.split_text(text_content)
            docs = [
                Document(page_content=chunk, metadata=metadata or {})
                for chunk in chunks
            ]
        elif isinstance(text_content, list):
            all_texts = []
            for doc in text_content:
                if isinstance(doc, Document):
                    texts = self.text_splitter.split_text(doc.page_content)
                    for text in texts:
                        meta = {**(doc.metadata or {}), **(metadata or {})}
                        all_texts.append(Document(page_content=text, metadata=meta))
                else:
                    texts = self.text_splitter.split_text(str(doc))
                    for text in texts:
                        all_texts.append(Document(page_content=text, metadata=metadata or {}))
            docs = all_texts
        else:
            chunks = self.text_splitter.split_text(str(text_content))
            docs = [
                Document(page_content=chunk, metadata=metadata or {})
                for chunk in chunks
            ]

        if docs:
            self.vector_db.add_documents(docs)
            print(f"Loaded {len(docs)} document chunks into PGVector.")
            return len(docs)
        return 0

    def retrieve(self, query, k=3):
        """
        Semantic similarity search with relevance filtering.
        Uses similarity_search_with_score to filter out irrelevant documents.

        Args:
            query: Search query string
            k: Number of documents to retrieve
        """
        try:
            print(f"🔎 Searching knowledge base for: '{query}'")

            # Use similarity_search_with_score to get distance values
            docs_with_scores = self.vector_db.similarity_search_with_score(query, k=k)
            print(f"📚 Found {len(docs_with_scores)} documents from vector DB")

            if not docs_with_scores:
                print("⚠️ No documents found in vector database")
                return "No relevant documents found."

            # Filter by relevance threshold (lower distance = more relevant)
            relevant_docs = []
            for doc, score in docs_with_scores:
                content = doc.page_content.strip()
                if not content:
                    continue
                preview = content[:80] + "..." if len(content) > 80 else content
                status = "✅" if score <= RELEVANCE_THRESHOLD else "❌ FILTERED"
                print(f"   📄 score={score:.3f} {status}: {preview}")
                if score <= RELEVANCE_THRESHOLD:
                    relevant_docs.append(doc)

            if not relevant_docs:
                print(f"⚠️ All {len(docs_with_scores)} docs exceeded relevance threshold ({RELEVANCE_THRESHOLD})")
                return "No relevant documents found."

            # Build context from relevant docs only (compact format to save tokens)
            context_parts = []
            for doc in relevant_docs:
                context_parts.append(doc.page_content.strip())

            result = "\n".join(context_parts)
            print(f"✅ Returning {len(result)} chars of relevant context from {len(relevant_docs)}/{len(docs_with_scores)} documents")
            return result

        except Exception as e:
            print(f"❌ Error during retrieval: {e}")
            import traceback
            traceback.print_exc()
            return f"Error retrieving from knowledge base: {str(e)}"


def get_rag_service():
    """
    Get or create a singleton instance of HybridRAGService.
    This avoids reloading the embeddings model on every request.
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = HybridRAGService()
    return _rag_service_instance
