from sentence_transformers import SentenceTransformer

# Load once when the server starts
model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def create_embedding(text: str) -> list[float]:
    """
    Convert text into a vector embedding.
    """
    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()