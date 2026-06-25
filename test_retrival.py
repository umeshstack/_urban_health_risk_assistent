from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

db = FAISS.load_local("faiss_index",embeddings=embedding,allow_dangerous_deserialization=True)

query = "what are the effects of PM2.5"

results = db.similarity_search(query,k=3)

for i, doc in enumerate(results):
    print(f"\nResult {i+1}")
    print(doc.page_content[:1000])