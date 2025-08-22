from services.embedder import get_model, build_faiss_index
import numpy as np

def retrieve_chunks(index, texts, question, top_k=15):
    model = get_model()
    q_embedding = model.encode([question], convert_to_numpy=True, normalize_embeddings=True)[0]
    scores, indices = index.search(np.array([q_embedding]), top_k)
    return [texts[i] for i in indices[0]]
