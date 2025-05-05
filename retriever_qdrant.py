from pathlib import Path
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant as QdrantStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Initialize Qdrant
qdrant = QdrantClient(host="localhost", port=6333)
embeddings = OpenAIEmbeddings()

def extract_repo_documents(repo_path: Path) -> list[Document]:
    docs = []
    for filepath in repo_path.rglob("*"):
        if filepath.suffix in [".py", ".md", ".txt"]:
            try:
                content = filepath.read_text(encoding="utf-8")
                docs.append(Document(page_content=content, metadata={"source": str(filepath)}))
            except Exception as e:
                print(f"Failed to read {filepath}: {e}")
    return docs

def index_repo(repo_path: Path, collection_name: str):
    docs = extract_repo_documents(repo_path)
    print("Resolved path:", repo_path)
    print("Exists:", repo_path.exists(), "Is dir:", repo_path.is_dir())
    print(f"Found {len(docs)} documents")
    chunks = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64).split_documents(docs)

    qdrant.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )

   # Create Qdrant vector store reference (no actual insert yet)
    vectorstore = QdrantStore(
        client=qdrant,
        collection_name=collection_name,
        embeddings=embeddings
    )

# Add documents (this avoids pickling issues)
    vectorstore.add_documents(chunks)

def search_repo(query: str, collection_name: str, k: int = 10):
    retriever = QdrantStore(client=qdrant, collection_name=collection_name, embeddings=embeddings)
    results = retriever.similarity_search(query, k=k)
    return [{"source": r.metadata["source"], "content": r.page_content} for r in results]
