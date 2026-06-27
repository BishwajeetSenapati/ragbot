import os
from django.conf import settings

# ── Document Loading ──────────────────────────────────────────────────────────

def load_document(file_path: str):
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        Docx2txtLoader,
    )
    ext = os.path.splitext(file_path)[-1].lower()

    if ext == ".pdf":
        from langchain_core.documents import Document
        import pytesseract
        from pdf2image import convert_from_path

        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        loader = PyPDFLoader(file_path)
        docs   = loader.load()

        if len(docs) > 50:
            print(f"Large PDF ({len(docs)} pages) → skipping OCR check")
            needs_ocr = False
        else:
            needs_ocr = any(
                len(doc.page_content.strip()) < 100
                for doc in docs
            )

        if not needs_ocr:
            print(f"Normal PDF → skipping OCR")
            return docs

        print(f"Mixed/scanned PDF → converting pages to images")
        images = convert_from_path(
            file_path,
            poppler_path=settings.POPPLER_PATH,
            dpi=150,
            thread_count=4,
        )

        final_docs = []
        for i, doc in enumerate(docs):
            page_text = doc.page_content.strip()
            if len(page_text) >= 100:
                print(f"Page {i+1}: text ({len(page_text)} chars)")
                final_docs.append(doc)
            else:
                print(f"Page {i+1}: running OCR...")
                if i < len(images):
                    ocr_text = pytesseract.image_to_string(
                        images[i], lang='eng'
                    ).strip()
                    if ocr_text:
                        final_docs.append(Document(
                            page_content=ocr_text,
                            metadata={
                                "source":      file_path,
                                "page":        i,
                                "total_pages": len(docs),
                                "ocr":         True,
                            }
                        ))
                        print(f"Page {i+1}: OCR → {len(ocr_text)} chars")
                    else:
                        print(f"Page {i+1}: blank, skipping")

        print(f"Done: {len(final_docs)}/{len(docs)} pages indexed")
        return final_docs

    elif ext == ".txt":
        loader = TextLoader(file_path)
    elif ext == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return loader.load()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_documents(documents):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_documents(documents)


# ── Pinecone Client ───────────────────────────────────────────────────────────

def get_pinecone_index():
    from pinecone import Pinecone
    pc    = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX)
    return index


def get_pinecone_client():
    from pinecone import Pinecone
    return Pinecone(api_key=settings.PINECONE_API_KEY)


# ── Embeddings via Pinecone Inference API ─────────────────────────────────────

def embed_passages(texts: list) -> list:
    """Embed document passages using llama-text-embed-v2."""
    pc = get_pinecone_client()
    result = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=texts,
        parameters={"input_type": "passage", "truncate": "END"},
    )
    return [item.values for item in result.data]


def embed_query(question: str) -> list:
    """Embed a search query using llama-text-embed-v2."""
    pc = get_pinecone_client()
    result = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[question],
        parameters={"input_type": "query", "truncate": "END"},
    )
    return result.data[0].values


# ── Index Document ────────────────────────────────────────────────────────────

def index_document(file_path: str, user_id, doc_id) -> int:
    import uuid
    import tempfile

    is_temp = file_path.startswith(tempfile.gettempdir())

    print(f"Loading document...")
    docs   = load_document(file_path)
    print(f"Loaded {len(docs)} pages → chunking...")
    chunks = chunk_documents(docs)
    print(f"Created {len(chunks)} chunks → embedding via Pinecone...")

    index = get_pinecone_index()
    texts = [c.page_content for c in chunks]

    batch_size  = 96
    all_vectors = []

    for i in range(0, len(texts), batch_size):
        batch   = texts[i:i + batch_size]
        vectors = embed_passages(batch)
        all_vectors.extend(vectors)
        print(f"Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")

    upload_batch = 100
    for i in range(0, len(chunks), upload_batch):
        batch_chunks  = chunks[i:i + upload_batch]
        batch_vectors = all_vectors[i:i + upload_batch]

        pinecone_vectors = []
        for chunk, vector in zip(batch_chunks, batch_vectors):
            pinecone_vectors.append({
                "id":     str(uuid.uuid4()),
                "values": vector,
                "metadata": {
                    "user_id": str(user_id),
                    "doc_id":  str(doc_id),
                    "page":    int(chunk.metadata.get("page", 0)),
                    "text":    chunk.page_content[:1000],
                }
            })

        index.upsert(vectors=pinecone_vectors)
        print(f"Uploaded batch {i//upload_batch + 1}")

    # Clean up temp file if downloaded from Cloudinary
    if is_temp and os.path.exists(file_path):
        os.unlink(file_path)
        print(f"Cleaned up temp file ✅")

    print(f"Indexing complete ✅ ({len(chunks)} chunks)")
    return len(chunks)


# ── Answer Question ───────────────────────────────────────────────────────────

def answer_question(question: str, user_id, doc_ids=None) -> dict:

    print(f"Embedding question...")
    question_vector = embed_query(question)

    index = get_pinecone_index()

    # Build filter
    if doc_ids and len(doc_ids) > 0:
        pinecone_filter = {
            "user_id": {"$eq": str(user_id)},
            "doc_id":  {"$in": [str(d) for d in doc_ids]},
        }
        print(f"Searching selected docs: {doc_ids}")
    else:
        pinecone_filter = {
            "user_id": {"$eq": str(user_id)},
        }
        print(f"Searching all docs for user {user_id}")

    # Search Pinecone
    results = index.query(
        vector=question_vector,
        filter=pinecone_filter,
        top_k=8,
        include_metadata=True,
    )

    if not results.matches:
        return {
            "answer":  "I couldn't find relevant information in your documents. Please make sure you have uploaded documents first.",
            "sources": []
        }

    print(f"Found {len(results.matches)} matches")

    # Build context
    context = "\n\n".join([
        f"[Page {m.metadata.get('page', '?')}]: {m.metadata.get('text', '')}"
        for m in results.matches
    ])

    prompt = f"""You are a helpful document assistant.
Use the context below to answer the question as accurately as possible.
If the exact answer is not stated, use the closest related information from the context.
Only say "I don't have enough information" if the topic is completely absent from the context.
Always mention the page number if available.

Context:
{context}

Question: {question}

Answer:"""

    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    sources = []
    for match in results.matches:
        sources.append({
            "page":    match.metadata.get("page", 0),
            "snippet": match.metadata.get("text", "")[:200],
        })

    return {
        "answer":  completion.choices[0].message.content,
        "sources": sources,
    }


# ── Delete Document Chunks ────────────────────────────────────────────────────

def delete_document_chunks(user_id, doc_id):
    try:
        index = get_pinecone_index()
        index.delete(
            filter={
                "user_id": {"$eq": str(user_id)},
                "doc_id":  {"$eq": str(doc_id)},
            }
        )
        print(f"Deleted chunks for doc_{doc_id} from Pinecone ✅")
    except Exception as e:
        print(f"Error deleting from Pinecone: {e}")


# ── Document Summary ──────────────────────────────────────────────────────────

def summarize_document(file_path: str) -> str:
    from groq import Groq

    docs          = load_document(file_path)
    chunks        = chunk_documents(docs)
    sample_chunks = chunks[:5]
    context       = "\n\n".join([c.page_content for c in sample_chunks])

    prompt = f"""You are a document summarizer.
Read the following text and write a clear, concise summary in 3-4 sentences.
The summary should tell the reader:
- What this document is about
- What main topics it covers
- Who would find it useful

Text:
{context}

Summary:"""

    client = Groq(api_key=settings.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return completion.choices[0].message.content.strip()
