from langchain_community import vectorstores
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
#from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


load_dotenv()

loader = PyMuPDFLoader("data/who_air_quality.pdf")

docs = loader.load()

print(f"the number pages : {len(docs)}")


#embedding = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

#text_splitter = SemanticChunker(embedding)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = text_splitter.split_documents(docs)

print(f"the number of chunks :{len(chunks)}")

embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

print("Creating FAISS Vector Store...")

vectorstore = FAISS.from_documents(chunks,embedding=embedding)

print("Saving FAISS Index...")

vectorstore.save_local("faiss_index")

print("FAISS Index Saved Successfully!")

