# Webis：AI 驱动的数据管道

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Webis** 是一个模块化、插件化的框架，旨在为下一代 AI 应用提供动力。它通过稳健的采集、处理与抽取流水线，将多样数据源（Web、SaaS、数据库等）连接到大语言模型（LLM）。

## 🚀 主要特性

* **插件优先架构**：一切皆插件（Source、Processor、Extractor、Model）。
* **智能爬虫代理**：使用 LLM 动态选择最佳数据源并生成查询。
* **RAG 就绪**：内置清洗、切分与 RAG 准备能力。
* **LLM 抽取**：把非结构化 PDF/网页转为结构化 JSON（支持动态 Schema）。
* **统一 CLI**：用一个 `webis` 命令完成所有操作。

## 📦 安装

```bash
cd webis
pip install -e .
```

## 🛠️ 使用

Webis 主要通过 `webis` CLI 运行。

### 1. 端到端执行

执行完整流水线：识别数据源 -> 抓取 -> 清洗 -> 抽取 -> 可视化报告。

```bash
# 示例：查找过去三个月关于北京大学的新闻并生成报告
webis run "Find news about Peking University in the last three months and generate a report" --limit 3
```

* `report.html`：美观的 HTML 报告（抽取成功时）。
* `result.json`：结构化抽取结果。
* `documents.json`：所有抓取文档的**原始与清洗内容**（即使抽取失败也会保存）。

## ⚠️ 配置

必须在 `.env` 中配置 API Key，Agent 功能才能正常工作。

### 2. 仅抓取

只抓取相关数据。

```bash
webis crawl "Python 3.13 new features" --limit 5 
```

* `output/{timestamp}/documents.json`：结构化抽取结果。
* `output/{timestamp}/result.json`：所有抓取文档的**原始与清洗内容**（即使抽取失败也会保存）。


### 3. 仅抽取

使用 LLM 从本地文件抽取结构化数据。

```bash
# 从 PDF 抽取
webis extract ./report.pdf --task "Extract financial summary"

# 使用指定 Schema 抽取
webis extract ./cv.pdf --schema ./schemas/resume.json
```

### 4. 生成 HTML 报告

基于已有的 `result.json`（可选 `documents.json`）生成 `report.html`。

```bash
webis html-report ./output/20260204_113243/result.json --documents ./output/20260204_113243/documents.json
```

默认输出到 `result.json` 所在目录。

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
