# Webis：AI 驱动的数据管道

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

**Webis** 是一个模块化、插件化的框架，旨在为下一代 AI 应用提供动力。它通过稳健的采集、处理与抽取流水线，将多样数据源（Web、SaaS、数据库等）连接到大语言模型（LLM）。

## 🚀 主要特性

* **插件优先架构**：一切皆插件（Source、Processor、Extractor、Model）。
* **智能爬虫代理**：使用 LLM 动态选择最佳数据源并生成查询。
* **RAG 就绪**：内置清洗、切分与 RAG 准备能力。
* **LLM 抽取**：把非结构化 PDF/网页转为结构化 JSON（支持动态 Schema）。
* **统一 CLI**：用一个 `webis` 命令完成所有操作。

## 📦 安装

### 在项目根目录下，使用一键安装脚本

#### 方式 1：Conda 安装

```bash
bash setup/conda_setup.sh
```

#### 方式 2：uv 安装

```bash
bash setup/uv_setup.sh
```

### 安装Webis CLI

```bash
pip install -e .
```

### 下载用于构建 RAG 知识库的嵌入模型

`sentence-transformers/all-MiniLM-L6-v2` 用于在构建 RAG 知识库时生成文本向量（Embedding）。

```bash
# 中国大陆网络可选镜像
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DOWNLOAD_TIMEOUT=120

hf download sentence-transformers/all-MiniLM-L6-v2
```

## 🛠️ 使用

Webis 主要通过 `webis` CLI 运行。

### 1. 端到端执行

执行完整流水线：识别数据源 -> 抓取 -> 清洗 -> 抽取 -> 构建 RAG 知识库。

```bash
# 示例：查找过去三个月关于北京大学的新闻并构建 RAG 知识库
webis run "Find news about Peking University in the last three months" --limit 3
```

* `result.json`：结构化抽取结果。
* `documents.json`：所有抓取文档的**原始与清洗内容**（即使抽取失败也会保存）。
* `rag_store.json`：基于 `documents.json` 构建的 RAG 知识库。

## ⚠️ 配置

必须在 `.env` 中配置 API Key，Agent 功能才能正常工作。

### 2. 仅抽取

使用 LLM 从本地文件抽取结构化数据。

```bash
# 从 PDF 抽取
webis extract ./report.pdf --task "Extract financial summary"

# 使用指定 Schema 抽取
webis extract ./cv.pdf --schema ./schemas/resume.json
```

### 3. 生成 HTML 报告

基于已有的 `result.json`（可选 `documents.json`）生成 `report.html`。

```bash
webis html-report ./output/20260204_113243/result.json --documents ./output/20260204_113243/documents.json
```

默认输出到 `result.json` 所在目录。

### 4. 从 RAG 知识库生成 Markdown 报告

基于已有的 `rag_store.json` 直接生成 Markdown 报告。

```bash
webis markdown-report ./output/20260208_105119/rag_store.json
```

可选：添加报告关注问题。

```bash
webis markdown-report ./output/20260208_105119/rag_store.json --query "近期关于北京大学新闻的趋势"
```

生成的 Markdown 报告会保存到 `rag_store.json` 的同一目录下。

## 🖥️ 可视化界面

### 1. 启动可视化

```bash
webis visualizer
```

### 2. 基本流程

* 在左侧栏添加数据源（Web 抓取或本地上传）。
* 运行流水线并等待完成。
* 在 UI 中查看结构化 JSON 与统计信息。
* 在 AI 助手标签中结合来源上下文进行分析。

## 🧩 架构

项目结构位于 `src/webis/`：

* **`core/`**：核心（Agents、Pipeline、Plugin Registry）。
* **`plugins/`**：
  * `sources/`：GNews、Google Search、GitHub 等。
  * `processors/`：PDF 解析、HTML 清洗等。
  * `extractors/`：LLMExtractor。
* **`plugin_sdk/`**：用于构建新插件的开发者友好接口。

## 🤝 贡献

欢迎贡献！如何使用 SDK 编写新插件，请参考 [CONTRIBUTING.md](CONTRIBUTING.md)。
