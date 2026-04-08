"""Core retrieval-augmented generation pipeline using LangChain + FAISS."""

from pathlib import Path

from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

RUNBOOK_DIR = Path(__file__).parent.parent / "runbooks"

PROMPT_TEMPLATE = """You are an expert SRE assistant. Use the following runbook context to answer
the incident response question. If the answer is not in the context, say so clearly.
Do not hallucinate procedures that are not in the runbooks.

Context:
{context}

Question: {question}

Answer:"""


def load_runbooks(runbook_dir: Path = RUNBOOK_DIR) -> list[Document]:
    documents: list[Document] = []
    headers_to_split_on = [("#", "Header1"), ("##", "Header2"), ("###", "Header3")]
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)

    for runbook_path in sorted(runbook_dir.glob("*.md")):
        raw_text = runbook_path.read_text(encoding="utf-8")
        header_splits = header_splitter.split_text(raw_text)
        chunks = text_splitter.split_documents(header_splits)
        for chunk in chunks:
            chunk.metadata["source"] = runbook_path.name
        documents.extend(chunks)

    return documents


def build_vectorstore(
    documents: list[Document],
    embedding_model: str,
    persist_path: str = "faiss_index",
) -> FAISS:
    embeddings = OpenAIEmbeddings(model=embedding_model)
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(persist_path)
    return vectorstore


def load_vectorstore(embedding_model: str, persist_path: str = "faiss_index") -> FAISS:
    embeddings = OpenAIEmbeddings(model=embedding_model)
    return FAISS.load_local(persist_path, embeddings, allow_dangerous_deserialization=True)


def build_rag_chain(vectorstore: FAISS, model: str = "gpt-4o-mini", k: int = 4) -> RetrievalQA:
    llm = ChatOpenAI(model=model, temperature=0)
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})
    prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def query(chain: RetrievalQA, question: str) -> dict:
    result = chain.invoke({"query": question})
    source_documents = result.get("source_documents", [])
    sources = sorted({doc.metadata.get("source", "unknown") for doc in source_documents})
    retrieved_contexts = [doc.page_content for doc in source_documents]
    return {
        "question": question,
        "answer": result["result"],
        "sources": sources,
        "num_chunks_retrieved": len(source_documents),
        "contexts": retrieved_contexts,
    }


def initialize_pipeline(
    force_rebuild: bool = False,
    persist_path: str = "faiss_index",
    model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-small",
    top_k: int = 4,
    runbook_dir: Path = RUNBOOK_DIR,
) -> RetrievalQA:
    if not force_rebuild and Path(persist_path).exists():
        vectorstore = load_vectorstore(embedding_model=embedding_model, persist_path=persist_path)
    else:
        documents = load_runbooks(runbook_dir=runbook_dir)
        if not documents:
            raise ValueError(f"No runbooks found in {runbook_dir}. Add .md files to /runbooks.")
        vectorstore = build_vectorstore(
            documents=documents,
            embedding_model=embedding_model,
            persist_path=persist_path,
        )

    return build_rag_chain(vectorstore=vectorstore, model=model, k=top_k)