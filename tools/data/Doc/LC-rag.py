import os
import pathlib
from typing import List
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA

# LLM 适配：OpenAI 或 Ollama
def get_llm():
    use_openai = os.getenv("USE_OPENAI", "0") == "1"
    if use_openai and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        print("使用 OpenAI LLM（可通过 USE_OPENAI=0 改回本地）")
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    else:
        from langchain_ollama import ChatOllama
        # 需本地已安装并运行 ollama，且已 pull 对应模型
        print("使用本地 Ollama（默认模型：llama3）")
        return ChatOllama(model="llama3", temperature=0)

INPUT_DIR = "docs"
PERSIST_DIR = "storage"

def load_docs(root: str):
    files = []
    for r, _, fns in os.walk(root):
        for fn in fns:
            ext = pathlib.Path(fn).suffix.lower()
            if ext in {".docx", ".pdf", ".md", ".txt"}:
                files.append(os.path.join(r, fn))
    if not files:
        raise RuntimeError(f"在 {root}/ 未找到文档（支持 .docx/.pdf/.md/.txt）")

    all_docs = []
    for fp in files:
        ext = pathlib.Path(fp).suffix.lower()
        if ext == ".docx":
            docs = Docx2txtLoader(fp).load()
        elif ext == ".pdf":
            docs = PyPDFLoader(fp).load()
        else:
            docs = TextLoader(fp, encoding="utf-8").load()
        # 标注来源，方便回溯
        for d in docs:
            d.metadata = d.metadata or {}
            d.metadata["source"] = fp
        all_docs.extend(docs)
    return all_docs

def build_or_load_vectorstore():
    # 嵌入模型：体积小、中文友好
    embed = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh")
    if os.path.isdir(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        print(f"发现持久化向量库，加载：{PERSIST_DIR}/")
        vs = Chroma(persist_directory=PERSIST_DIR, embedding_function=embed)
        return vs

    print("首次构建向量库：加载文档…")
    docs = load_docs(INPUT_DIR)
    print(f"共加载 {len(docs)} 条文档片段（未切分）")

    # 切分
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    chunks = splitter.split_documents(docs)
    print(f"切分后共 {len(chunks)} 个块")

    # 构建 & 持久化
    vs = Chroma.from_documents(chunks, embedding=embed, persist_directory=PERSIST_DIR)
    print(f"已持久化到：{PERSIST_DIR}/")
    return vs

def main():
    llm = get_llm()
    vectorstore = build_or_load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True,
    )

    print("\nRAG 已就绪。输入问题开始检索问答；输入 `exit` 退出。\n")
    while True:
        q = input("你：").strip()
        if q.lower() in {"exit", "quit"}:
            break
        out = qa.invoke({"query": q})
        print("\n—— 回答 ——")
        print(out["result"].strip())
        print("\n—— 参考来源 ——")
        for i, sd in enumerate(out.get("source_documents", []), 1):
            src = sd.metadata.get("source", "unknown")
            page = sd.metadata.get("page", None)
            page_info = f" (page {page})" if page is not None else ""
            print(f"{i}. {src}{page_info}")
        print()

if __name__ == "__main__":
    main()