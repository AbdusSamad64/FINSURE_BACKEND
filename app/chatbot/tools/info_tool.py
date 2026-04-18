"""RAG tool for the FINSURE assistant.

Loads FINSURE_GUIDE.pdf once, chunks it, builds a FAISS index using a lightweight
HuggingFace embedding model, and exposes a LangChain tool that returns the most
relevant chunks for a user question.
"""

from functools import lru_cache
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings

GUIDE_PATH = Path(__file__).parent / "FINSURE_GUIDE.pdf"
EMBED_MODEL = "sentence-transformers/paraphrase-MiniLM-L3-v2"


@lru_cache(maxsize=1)
def _get_retriever():
    if not GUIDE_PATH.exists():
        raise FileNotFoundError(
            f"{GUIDE_PATH} not found. Generate it with: "
            f"python app/chatbot/build_guide.py"
        )

    loader = PyPDFLoader(str(GUIDE_PATH))
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(pages)

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    store = FAISS.from_documents(chunks, embeddings)
    return store.as_retriever(search_kwargs={"k": 6})


@tool("finsure_guide_lookup")
def finsure_guide_lookup(query: str) -> str:
    """Look up information about the FINSURE app - features, navigation, how-to,
    report types, security and FAQs - from the official FINSURE product guide.
    Use this for any user question about what FINSURE is or how to use it.
    """
    retriever = _get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant section found in the FINSURE guide."
    return "\n\n---\n\n".join(d.page_content.strip() for d in docs)


def warmup() -> None:
    """Call at startup to build the FAISS index before the first user query."""
    _get_retriever()
