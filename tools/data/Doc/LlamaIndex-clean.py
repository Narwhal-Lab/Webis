import os
from llama_index.core import SimpleDirectoryReader

def main():
    inputdir = "docs"
    outputdir = "outputs"

    os.makedirs(outputdir, exist_ok=True)

    # 读取目录下所有文档
    documents = SimpleDirectoryReader(inputdir).load_data()


    for i, doc in enumerate(documents):
        filename = f"document_{i+1}.txt"
        filepath = os.path.join(outputdir, filename)

        # 保存文本
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(doc.text)

        print("=" * 40)
        print(f"文档 {i+1} 已保存为: {filepath}")
        print("内容预览:\n")
        print(doc.text[:500])  # 打印前500字符
        print("\n...（已截断）")

if __name__ == "__main__":
    main()
