import os
import pathlib
from typing import List
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader

INPUTDIR = "docs"
OUTPUTDIR = "outputs"

def load_one(path: str):
    ext = pathlib.Path(path).suffix.lower()
    if ext == ".docx":
        return Docx2txtLoader(path).load()
    elif ext == ".pdf":
        return PyPDFLoader(path).load()
    elif ext in [".md", ".txt"]:
        # autodetect encoding=False -> tries utf-8; set to None to guess
        return TextLoader(path, encoding="utf-8").load()
    else:
        return []

def get_allfiles(root: str) -> List[str]:
    exts = {".docx", ".pdf", ".md", ".txt"}
    files = []
    for r, _, fns in os.walk(root):
        for fn in fns:
            if pathlib.Path(fn).suffix.lower() in exts:
                files.append(os.path.join(r, fn))
    return files

def main():
    os.makedirs(OUTPUTDIR, exist_ok=True)
    files = get_allfiles(INPUTDIR)
    if not files:
        print(f"在 {INPUTDIR}/ 下未发现可处理的文件（支持 .docx/.pdf/.md/.txt）")
        return

    for fp in files:
        docs = load_one(fp)
        if not docs:
            print(f"跳过不支持的文件：{fp}")
            continue

        text = "\n".join(d.page_content for d in docs).strip()

        # 生成输出文件名：原名去后缀 + .txt
        p = pathlib.Path(fp)
        out_name = p.with_suffix(".txt").name
        out_path = os.path.join(OUTPUTDIR, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)

        print("=" * 40)
        print(f"已输出：{out_path}")
        print("内容预览：")
        print(text[:600])
        if len(text) > 600:
            print("...（已截断）")

if __name__ == "__main__":
    main()
