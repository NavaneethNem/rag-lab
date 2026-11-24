import chromadb
from google import genai
from google.genai import types

client=genai.Client()
db=chromadb.PersistentClient(path="./chroma_db/")
collection=db.get_collection(name="my_notes")

# Cosine distance cutoff: 0.0 is an exact match, 1.0 is unrelated.
# Anything above ~0.55 usually means your notes don't cover the topic.

from google.genai import errors

MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
MAX_DISTANCE = 0.5  # Tightened for gemini-embedding-001's cosine range

def ask(question: str):
    # 1. Embed the user's question
    q_embed = client.models.embed_content(
        model="gemini-embedding-001",
        contents=question,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    ).embeddings[0].values

    # 2. Query ChromaDB for top 3 chunks
    results = collection.query(
        query_embeddings=[q_embed],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    # Show retrieval results immediately so you can inspect the search step
    print("\nRetrieved chunks:")
    for meta, dist in zip(metas, distances):
        print(f"  - {meta['source']} (chunk {meta['chunk']}, cosine distance: {dist:.3f})")

    # 3. Guardrail: bail out if even the closest chunk is too far away
    if not docs or distances[0] > MAX_DISTANCE:
        print(f"\nAnswer: I couldn't find anything relevant in your notes (closest distance: {distances[0]:.3f}).\n")
        return

    # 4. Build context with source citations
    context_blocks = [
        f" | Distance: {dist:.3f}]\n{doc}"
        for doc, meta, dist in zip(docs, metas, distances)
    ]
    context = "\n\n---\n\n".join(context_blocks)

    # 5. Generate answer with automatic fallback if a model returns 503
    for model_name in MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"Context:\n{context}\n\nQuestion: {question}",
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "Answer the user's question using ONLY the provided context. "
                        "Cite the source filename in brackets like [filename.md]. "
                        "If the context does not contain the answer, say 'I don't know based on the provided notes.'"
                    ),
                    temperature=0.2,
                ),
            )
            print(f"\nAnswer (via {model_name}):\n{response.text}\n")
            return
        except errors.ServerError as e:
            print(f"  [!] {model_name} busy ({e.code}), trying fallback...")

    print("\nAll fallback models are temporarily overloaded. Try again in a few seconds.\n")

if __name__ == "__main__":
    while True:
        q = input("\nAsk your notes (or 'exit'): ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        if q:
            ask(q)
