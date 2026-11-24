import glob
import os
import chromadb
from google import genai
from google.genai import types

client=genai.Client()

# Creats a local folder ./chroma_db that persists on disk
db=chromadb.PersistentClient(path="./chroma_db")
collection=db.get_or_create_collection(
    name="my_notes",
    metadata={"hnsw:space":"cosine"},
                                       )
def chunk_text(text:str,chunk_size: int=600,overlap: int=100) -> list[str]:
    chunks=[]
    start=0
    while start<len(text):
        end=start+chunk_size
        chunks.append(text[start:end].strip())
        start+=chunk_size-overlap
    return [c for c in chunks if c]

ids,documents,metadatas=[],[],[]

for filepath in glob.glob("notes/*.*"):
    filename=os.path.basename(filepath)
    with open(filepath,"r",encoding="utf-8") as f:
        content=f.read()
    for idx,chunk in enumerate(chunk_text(content)):
        ids.append(f"{filename}::chunk_{idx}")
        documents.append(chunk)
        metadatas.append({"source":filename,"chunk":idx})

# Generate embeddings specifically optimized for stored documents
embed_res=client.models.embed_content(
    model="gemini-embedding-001",
    contents=documents,
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
)
embeddings= [e.values for e in embed_res.embeddings]

# Upsert = insert if new, overwrite if ID already exists
collection.upsert(
    ids=ids,
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
)

print(f"Indexed {len(documents)} chunks from {len(glob.glob('notes/*.*'))} files into ./chroma_db")
