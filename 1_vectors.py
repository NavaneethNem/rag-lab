import numpy as np
from google import genai
from google.genai import types

client=genai.Client()

sentences=["Why is the sky blue?","Sunlight scatters off atmospheric gases via Rayleigh scattering.","Bicycles typically have two wheels and a chain drive.",]

#Turn all three sentences into coordinate arrays in one API call
response=client.models.embed_content(model="gemini-embedding-001",contents=sentences,config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),)

vectors=[np.array(e.values) for e in response.embeddings]

print(f"Vector dimensions: {len(vectors[0])}")
print(f"First 5 numbers of sentence 1: {vectors[0][:5]}\n")

def cosine_similarity(a,b):
    return np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))

print("Sky question vs. Rayleigh scattering:",round(cosine_similarity(vectors[0],vectors[1]),4))
print("Sky question vs. Bicycles:",round(cosine_similarity(vectors[0],vectors[2]),4))


