"""Run the full RAG pipeline (same logic as the notebook)."""
import pip_system_certs.bootstrap  # noqa: F401 – fixes SSL on filtered networks (NetFree)

import os
import re
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone, ServerlessSpec
import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PDF_PATH = PROJECT_ROOT / "data" / "cs229-notes2.pdf"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
INDEX_NAME = "cs229-notes2"

import re

def clean_text(text):
    text = re.sub(re.compile(r'\s+'), ' ', text)
    return text.strip()

def load_pdf(pdf_path):
    """Read a PDF using pdfplumber for better Hebrew text extraction."""
    full_text = ""
    char_page = []
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            page_text = clean_text(page_text) + "\n"
            full_text += page_text
            char_page.extend([page_num] * len(page_text))
            
    return full_text, char_page

def chunk_text(text, char_page, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    step = chunk_size - chunk_overlap
    chunks = []
    idx = 0
    start = 0
    while start < len(text):
        chunk_str = text[start : start + chunk_size].strip()
        if chunk_str:
            page = char_page[start] if start < len(char_page) else char_page[-1]
            chunks.append({"id": f"chunk-{idx}", "text": chunk_str, "page": page})
            idx += 1
        start += step
    return chunks


def main():
    print("=" * 70)
    print("RAG Project Run")
    print("=" * 70)

    if not GEMINI_API_KEY:
        sys.exit("ERROR: missing GEMINI_API_KEY in .env")
    if not PINECONE_API_KEY:
        sys.exit("ERROR: missing PINECONE_API_KEY in .env")

    print("\n[Step 2] Loading PDF and chunking...")
    full_text, char_page = load_pdf(PDF_PATH)
    chunks = chunk_text(full_text, char_page)
    print(f"  Pages: {char_page[-1] if char_page else 0}")
    print(f"  Characters: {len(full_text):,}")
    print(f"  Chunks: {len(chunks)}")

    print("\n[Step 3] Creating Gemini embeddings...")
    client = genai.Client(api_key=GEMINI_API_KEY)

    def embed_texts(texts, task_type="RETRIEVAL_DOCUMENT"):
        for attempt in range(3):
            try:
                result = client.models.embed_content(
                    model=EMBED_MODEL,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=EMBED_DIM,
                    ),
                )
                return [emb.values for emb in result.embeddings]
            except Exception as exc:
                if "429" in str(exc) and attempt < 2:
                    print("  Rate limit – waiting 35s...")
                    time.sleep(35)
                    continue
                raise

    sample = embed_texts([chunks[0]["text"]])[0]
    print(f"  Sample vector dim: {len(sample)}")

    all_vectors = embed_texts([c["text"] for c in chunks])
    for chunk, vector in zip(chunks, all_vectors):
        chunk["vector"] = vector
    print(f"  Embeddings created: {len(all_vectors)}")

    print("\n[Step 4] Upserting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = {idx.name for idx in pc.list_indexes()}
    if INDEX_NAME not in existing:
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"  Created index: {INDEX_NAME}")
    else:
        print(f"  Using existing index: {INDEX_NAME}")

    index = pc.Index(INDEX_NAME)
    records = [
        (
            c["id"],
            c["vector"],
            {"text": c["text"][:1000], "page": c["page"]},
        )
        for c in chunks
    ]
    index.upsert(vectors=records)
    stats = index.describe_index_stats()
    print(f"  Upserted: {len(records)} vectors")
    print(f"  Index stats: {stats}")

    print("\n[Step 5] Semantic search (5 questions)...")
    questions = [
       "What is the core difference between discriminative and generative learning algorithms?",
    "How is the multivariate normal distribution parameterized?",
    "Under what conditions does Gaussian Discriminant Analysis (GDA) provide a better fit than logistic regression?",
    "What is the fundamental assumption made by the Naive Bayes classifier?",
    ]

    for q in questions:
        q_vec = embed_texts([q], task_type="RETRIEVAL_QUERY")[0]
        results = index.query(vector=q_vec, top_k=3, include_metadata=True)
        print("\n" + "=" * 70)
        print("Question:", q)
        for i, match in enumerate(results.matches, start=1):
            page = match.metadata.get("page", "?")
            text = match.metadata.get("text", "")
            print(f"  #{i} score={match.score:.4f} page={page} id={match.id}")
            print(f"     {text[:200]}...")

    print("\n[Bonus] Comparing chunk configs...")
    test_q = "Why is Laplace smoothing used in text classification with Naive Bayes?"

    configs = {
        "A_default": (1000, 150),
        "B_small": (500, 80),
    }

    def cosine(a, b):
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    for name, (cs, co) in configs.items():
        cfg_chunks = chunk_text(full_text, char_page, cs, co)
        q_vec = embed_texts([test_q], task_type="RETRIEVAL_QUERY")[0]
        doc_vecs = embed_texts([c["text"] for c in cfg_chunks])
        scored = sorted(
            ((cosine(q_vec, v), c) for c, v in zip(cfg_chunks, doc_vecs)),
            key=lambda x: x[0],
            reverse=True,
        )[:3]
        print(f"\n  Config {name}: size={cs}, overlap={co}, chunks={len(cfg_chunks)}")
        for i, (score, chunk) in enumerate(scored, start=1):
            print(f"    #{i} score={score:.4f} page={chunk['page']}")
            print(f"       {chunk['text'][:150]}...")

    print("\n" + "=" * 70)
    print("DONE - all steps completed successfully")
    print("=" * 70)


if __name__ == "__main__":
    main()
