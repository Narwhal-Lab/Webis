# Webis Crawler Framework

This folder contains a simple framework for data-source crawling tools plus a LangChain-based agent that can route natural-language tasks to them. The agent uses SiliconFlow (base URL `https://api.siliconflow.cn/v1`) with model `deepseek-ai/DeepSeek-V3.2`.

## Files
- `agent.py`: LangChain agent that picks a tool for a task. Register future tools here.
- `tool_base.py`: Shared tool interface and result dataclass.

## Quick start
```bash
cd crawler
# 安装依赖（匹配当前 agent，建议 langchain>=1.1）
pip install "scrapy" "langchain>=1.1" "langchain-openai>=1.1"

# LangChain agent demo (requires langchain + langchain-openai; needs SILICONFLOW_API_KEY)
python agent.py "帮我搜索LLM相关pdf文件" --limit 5 --model deepseek-ai/DeepSeek-V3.2
```
Outputs are saved under `crawler/outputs/<keyword_timestamp>/`. HTML pages are stored as numbered `.html` files; downloaded documents go into the same folder (or `full/` when saved by Scrapy's pipeline).

## Adding new tools
1. Implement `BaseTool.run` and return a `ToolResult`.
2. Register the tool when constructing `LangChainDataSourceAgent` (see `agent.py`), and add/update descriptions so the LLM knows when to use it.
3. Keep the interface stable so existing callers (e.g., the agent or other workflows) can swap tools without changing code.
