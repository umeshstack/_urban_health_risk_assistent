# load environment variable
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

_retriever = None
_llm = None


def _get_rag_components():
    global _retriever, _llm

    if _retriever is None:
        embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        db = FAISS.load_local(
            "faiss_index",
            embeddings=embedding,
            allow_dangerous_deserialization=True,
        )
        _retriever = db.as_retriever(search_kwargs={"k": 3})

    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    return _retriever, _llm


# user input
def get_answer(question: str):
    """
    Retrieves relevant chunks from FAISS, then asks Gemini.
    Returns (answer_text, list_of_source_snippets).
    """
    retriever, llm = _get_rag_components()
    docs = retriever.invoke(question)

    context = "\n\n".join(doc.page_content for doc in docs)

    prompt = f"""You are an urban Health Assistant.
                      Answer the question only using the provided Context.

    If the answer is not available in the context,
    say "I could not find this information in the documents."

    Context:  {context}

    Question: {question}"""

    response = llm.invoke(prompt)

    sources = [
        {
            "snippet": doc.page_content[:300].strip() + ("..." if len(doc.page_content) > 300 else ""),
            "page": doc.metadata.get("page", doc.metadata.get("page_number")),
            "source": doc.metadata.get("source"),
        }
        for doc in docs
    ]
    return response.content, sources