"""
Data-source Agent (LangChain):
- 用 LLM 做工具路由（选择 tool + 生成 tool_task）
- 然后在主线程同步执行 tool.run(...)，避免 Scrapy/Twisted 在线程池里运行触发 signal 报错

用法（推荐包方式运行）：
  cd Webis_v3/Webis
  python -m crawler.agent "帮我搜索 llm 相关文件" --limit 20
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import re
import sys
from typing import Dict, List, Optional, Tuple

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:
    find_dotenv = None
    load_dotenv = None

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError as exc:  # noqa: BLE001
    raise ImportError("缺少 LangChain 相关依赖，请安装：`pip install langchain langchain-openai`。") from exc

if not __package__:
    sys.path.append(str(pathlib.Path(__file__).resolve().parent))
    from hn_tool import HackerNewsTool  # type: ignore  # noqa: E402
    from tool_base import BaseTool, ToolResult  # type: ignore  # noqa: E402
else:
    from .hn_tool import HackerNewsTool  # noqa: F401
    from .tool_base import BaseTool, ToolResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _load_env() -> None:
    """加载项目根目录下 `.env` / `.env.local`（如果安装了 python-dotenv）。"""
    if not find_dotenv or not load_dotenv:
        return

    project_root = pathlib.Path(__file__).resolve().parents[1]
    for fname in (".env", ".env.local"):
        direct = project_root / fname
        if direct.exists():
            load_dotenv(str(direct), override=False)
            logger.info("Loaded environment from %s", direct)
            return

    for fname in (".env", ".env.local"):
        path = find_dotenv(fname, usecwd=True)
        if path:
            load_dotenv(path, override=False)
            logger.info("Loaded environment from %s", path)
            return


class LangChainDataSourceAgent:
    """
    数据源获取 Agent：
    - LLM 只负责做工具选择（输出 JSON）
    - 真正抓取在本进程主线程同步执行
    """

    def __init__(self, llm, tools: Optional[List[BaseTool]] = None, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose
        self.tools: Dict[str, BaseTool] = {}
        if tools:
            for tool in tools:
                self.register_tool(tool)
        self.last_choice: Optional[dict] = None

    def register_tool(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def available_tools(self) -> List[str]:
        return list(self.tools.keys())

    def run(self, task: str, limit: int = 5, max_rounds: int = 10, **kwargs) -> ToolResult:
        """
        总调度：
        - 目标：尽量拿到 limit 条数据（文件），不足则自动继续尝试
        - 如果某工具失败/返回为空，自动切换其他工具
        """
        if not self.tools:
            return ToolResult(name="agent", success=False, error="未注册任何 tools。")

        collected: List[str] = []
        used_tools: List[dict] = []

        file_exts = self._detect_file_exts(task)

        for round_idx in range(1, max_rounds + 1):
            remaining = max(0, int(limit) - len(collected))
            if remaining == 0:
                break

            # 规则优先：如果任务明确要下载 PDF/文档，第一轮先走“可下载文件”的通用抓取工具，
            # 避免模型误选只抓 HTML 的通用搜索工具。
            if round_idx == 1 and file_exts and "hackernews" in self.tools:
                tool_name = "hackernews"
                tool_task = self._build_file_query(task, file_exts)
                tool_kwargs = {"limit": remaining}
                selection = "rule_based_file_download"
            else:
                tool_name, tool_task, tool_kwargs = self._choose_tool(
                    user_task=task,
                    remaining=remaining,
                    already_have=len(collected),
                    history=used_tools,
                    extra_kwargs=kwargs,
                )
                selection = "llm"
            self.last_choice = {"tool_name": tool_name, "tool_task": tool_task, "tool_kwargs": tool_kwargs}

            tool = self.tools.get(tool_name)
            if tool is None:
                fallback = next(iter(self.tools.values()))
                logger.warning("LLM chose unknown tool '%s', fallback to '%s'", tool_name, fallback.name)
                tool = fallback
                tool_name = tool.name

            merged_kwargs = dict(tool_kwargs)
            merged_kwargs.setdefault("limit", remaining)
            merged_kwargs.update({k: v for k, v in kwargs.items() if v is not None})

            if self.verbose:
                logger.info("Round %s/%s", round_idx, max_rounds)
                logger.info("Tool chosen: %s", tool_name)
                logger.info("Tool task: %s", tool_task)
                logger.info("Tool kwargs: %s", merged_kwargs)

            try:
                result = tool.run(task=tool_task, **merged_kwargs)
            except Exception as exc:  # noqa: BLE001
                result = ToolResult(
                    name=tool_name,
                    success=False,
                    error=str(exc),
                    meta={"tool_task": tool_task, "tool_kwargs": merged_kwargs},
                )

            new_files = [f for f in (result.files or []) if f and f not in collected]
            collected.extend(new_files)

            used_tools.append(
                {
                    "round": round_idx,
                    "tool": tool_name,
                    "tool_task": tool_task,
                    "tool_kwargs": merged_kwargs,
                    "selection": selection,
                    "success": result.success,
                    "error": result.error,
                    "got": len(result.files or []),
                    "new": len(new_files),
                    "meta": result.meta,
                }
            )

            # 如果这轮没拿到任何新文件，下一轮让模型换个工具；但最多重试 max_rounds 次

        success = len(collected) > 0
        err: Optional[str] = None
        if len(collected) < int(limit):
            err = f"仅获取到 {len(collected)}/{limit} 条数据"

        return ToolResult(
            name="agent",
            success=success,
            files=collected,
            output_dir=None,
            meta={"requested": limit, "collected": len(collected), "history": used_tools},
            error=err if err else (None if success else "未获取到任何数据"),
        )

    def _choose_tool(
        self,
        user_task: str,
        remaining: int,
        already_have: int,
        history: List[dict],
        extra_kwargs: dict,
    ) -> Tuple[str, str, dict]:
        """
        用一次 LLM 调用做“下一步动作”决策。
        需要具备泛化性：识别语言、是否需要翻译、工具失败后切换、补齐 remaining。
        """
        # 1) 如果缺少某 tool 的 key，严格不让模型选择它（不出现在列表里）
        # 2) 优先展示 specialized，其次 general（通用引擎）
        specialized_ok: List[str] = []
        general_ok: List[str] = []
        for t in self.tools.values():
            required = getattr(t, "required_env_vars", []) or []
            missing = [k for k in required if not os.environ.get(k)]
            if missing:
                continue

            kind = getattr(t, "tool_kind", "specialized")
            caps = getattr(t, "capabilities", []) or []
            line = f"- {t.name} [{kind}] caps={caps}: {t.description}"
            if kind == "general":
                general_ok.append(line)
            else:
                specialized_ok.append(line)

        system = (
            "你是一个“任务总调度数据源获取 Agent”。你要做的是：为用户任务选择工具并生成工具参数，"
            "以尽量拿到足量的数据源文件。\n"
            "注意：用户的任务可能是中文或英文；不同工具可能需要不同语言的查询词、甚至需要你把查询词翻译成英文。\n"
            "你必须根据工具描述自行判断是否需要翻译/改写查询词，并通过 tool_task / tool_kwargs 表达出来。\n\n"
            "工具选择优先级：\n"
            "1) 优先选择 specialized 工具（当其能力标签 caps 与任务明显匹配，例如 news/academic/github）。\n"
            "2) 若 specialized 不适用或连续无结果，再选择 general 工具（通用搜索/通用爬虫引擎）兜底。\n\n"
            "文件型任务规则（很重要）：\n"
            "- 如果用户明确提到 PDF/Word/PPT/文档/文件下载/附件，请优先选择 caps 包含 download_files 的工具；\n"
            "- SerpApi/百度 MCP 主要用于抓取 HTML 页面，本身不负责下载 PDF。\n\n"
            "你必须输出一个 JSON 对象，不能输出其他任何文字。\n"
            "JSON 格式：\n"
            '{\n  "tool_name": "xxx",\n  "tool_task": "给工具的更具体查询词（可翻译/改写）",\n  "tool_kwargs": {\n    "limit": 2,\n    "lang": "en"\n  }\n}\n'
            "规则：\n"
            "1) tool_name 必须来自下面的工具列表（列表已过滤缺少 key 的工具）。\n"
            "2) tool_kwargs.limit 必须等于 remaining。\n"
            "3) 如果之前某工具连续失败/无结果，优先切换别的工具。\n"
            "4) tool_task 不要太长，尽量是搜索关键词串。\n\n"
            f"当前目标：还需要获取 remaining={remaining} 条（已获取 {already_have} 条）。\n"
            f"历史执行记录（可能为空）：{json.dumps(history, ensure_ascii=False)}\n"
            "specialized 工具列表：\n"
            f"{chr(10).join(specialized_ok) if specialized_ok else '(none)'}\n"
            "general 工具列表：\n"
            f"{chr(10).join(general_ok) if general_ok else '(none)'}\n"
        )
        user = f"用户任务：{user_task}"

        resp = self.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = getattr(resp, "content", "") or ""
        data = self._safe_json_loads(content) or {}

        tool_name = str(data.get("tool_name") or "").strip()
        tool_task = str(data.get("tool_task") or user_task).strip() or user_task
        tool_kwargs = data.get("tool_kwargs") if isinstance(data.get("tool_kwargs"), dict) else {}
        tool_kwargs["limit"] = remaining

        if not tool_name:
            # 兜底：优先选 specialized，其次 general（且必须 key 齐全）
            ok_tools = [
                t
                for t in self.tools.values()
                if not getattr(t, "required_env_vars", [])
                or all(os.environ.get(k) for k in getattr(t, "required_env_vars", []))
            ]
            ok_tools_sorted = sorted(
                ok_tools,
                key=lambda t: 0 if getattr(t, "tool_kind", "specialized") == "specialized" else 1,
            )
            tool_name = (ok_tools_sorted[0].name if ok_tools_sorted else next(iter(self.tools.keys())))

        return tool_name, tool_task, tool_kwargs

    @staticmethod
    def _detect_file_exts(task: str) -> List[str]:
        """
        从用户任务里粗略识别“文件下载意图”。
        返回需要的文件后缀列表（无则为空）。
        """
        t = (task or "").lower()
        exts: List[str] = []
        if "pdf" in t or "论文" in task or "文献" in task:
            exts.append("pdf")
        if "docx" in t or "doc" in t or "word" in t:
            exts.extend(["doc", "docx"])
        if "ppt" in t or "pptx" in t:
            exts.extend(["ppt", "pptx"])
        # 去重保序
        out: List[str] = []
        for e in exts:
            if e not in out:
                out.append(e)
        return out

    @staticmethod
    def _build_file_query(task: str, exts: List[str]) -> str:
        """
        给“可下载文件”的工具构造更强的查询关键词。
        注意：不强制绑定 filetype（因为不同引擎语法不一），但会显式加入扩展名关键词。
        """
        base = (task or "").strip()
        if not base:
            return ""
        suffix = " ".join([f".{e}" for e in exts]) if exts else ""
        # 加一个 “filetype:pdf” 作为通用提示词（即便引擎不支持也通常不会坏）
        hint = " ".join([f"filetype:{e}" for e in exts]) if exts else ""
        return " ".join([base, suffix, hint]).strip()

    @staticmethod
    def _safe_json_loads(text: str) -> Optional[dict]:
        text = (text or "").strip()
        if not text:
            return None
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
        candidate = fenced.group(1) if fenced else text
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except Exception:  # noqa: BLE001
            pass
        m = re.search(r"(\{.*\})", candidate, re.S)
        if not m:
            return None
        try:
            obj = json.loads(m.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:  # noqa: BLE001
            return None


def cli() -> None:
    parser = argparse.ArgumentParser(description="Data-source agent demo.")
    parser.add_argument("task", help="Natural-language task to fetch data for.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", type=str, default="deepseek-ai/DeepSeek-V3.2")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--output", type=str, default="outputs")
    args = parser.parse_args()

    _load_env()

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("需要安装 langchain-openai：`pip install langchain-openai`") from exc

    api_key = args.api_key or os.getenv("SILICONFLOW_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 SiliconFlow API Key，请设置 SILICONFLOW_API_KEY")

    llm = ChatOpenAI(
        model=args.model,
        temperature=0,
        base_url="https://api.siliconflow.cn/v1",
        api_key=api_key,
    )

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    tools: List[BaseTool] = [HackerNewsTool(output_dir=str(output_dir))]
    # 这些 tool 可能依赖额外 API key；CLI 里尽量“能用就注册”，不可用也不影响基础工具。
    try:
        if __package__:
            from .baidu_mcp_tool import BaiduAiSearchMcpTool  # type: ignore
            from .gnews_tool import GNewsTool  # type: ignore
            from .github_api_tools import GitHubSearchTool  # type: ignore
            from .hn_tool import HackerNewsTool  # type: ignore
            from .semantic_scholar import SemanticScholarTool  # type: ignore
            from .serpapi_tool import SerpApiSearchTool  # type: ignore
        else:
            from baidu_mcp_tool import BaiduAiSearchMcpTool  # type: ignore
            from gnews_tool import GNewsTool  # type: ignore
            from github_api_tools import GitHubSearchTool  # type: ignore
            from hn_tool import HackerNewsTool  # type: ignore
            from semantic_scholar import SemanticScholarTool  # type: ignore
            from serpapi_tool import SerpApiSearchTool  # type: ignore

        tools.extend(
            [
                BaiduAiSearchMcpTool(output_dir=str(output_dir)),
                GNewsTool(output_dir=str(output_dir)),
                SemanticScholarTool(output_dir=str(output_dir)),
                GitHubSearchTool(output_dir=str(output_dir)),
                HackerNewsTool(output_dir=str(output_dir)),
                SerpApiSearchTool(output_dir=str(output_dir)),
            ]
        )
    except Exception:
        pass

    agent = LangChainDataSourceAgent(llm=llm, tools=tools, verbose=True)
    result = agent.run(task=args.task, limit=args.limit)

    if result.success:
        print(f"✓ Agent finished using tool: {result.name}")
        if result.output_dir:
            print(f"Output dir: {result.output_dir}")
        print("Files:")
        for f in result.files:
            print(f" - {f}")
    else:
        print(f"✗ Agent failed: {result.error}")


if __name__ == "__main__":
    cli()
