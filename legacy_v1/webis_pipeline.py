#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end Webis pipeline (crawler -> tools cleaning -> structuring).

Usage:
  cd Webis_v3/Webis
  python webis_pipeline.py "帮我搜索最近金融相关人员新闻，并输出结构化数据" --limit 5 --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent


def _load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for fname in (".env", ".env.local"):
        p = PROJECT_ROOT / fname
        if p.exists():
            load_dotenv(p, override=False)
            return


def _init_llm():
    _load_env()
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise ImportError("需要安装 langchain-openai：`pip install langchain-openai`") from exc

    api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 LLM API key：请设置 SILICONFLOW_API_KEY（推荐）或 DEEPSEEK_API_KEY。")

    return ChatOpenAI(
        model="deepseek-ai/DeepSeek-V3.2",
        temperature=0,
        base_url="https://api.siliconflow.cn/v1",
        api_key=api_key,
    )


def _collect_crawl_files(output_dir: str) -> List[str]:
    out = pathlib.Path(output_dir)
    if not out.exists():
        return []

    exts = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".html", ".htm", ".txt", ".md", ".json"}
    files = []
    for p in out.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(str(p))
    return sorted(files)


def _extract_texts(
    file_paths: List[str], text_out_dir: pathlib.Path, workers: int = 1, verbose: bool = False
) -> Tuple[List[str], List[dict]]:
    """
    Use tools/ UnifiedFileProcessor to extract clean text.
    Returns (texts, per_file_results_for_manifest).
    """
    tools_dir = str(PROJECT_ROOT / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)

    from file_processor import UnifiedFileProcessor  # type: ignore

    texts: List[str] = []
    manifest_rows: List[dict] = []

    text_out_dir.mkdir(parents=True, exist_ok=True)

    def _one(idx: int, fp: str):
        # 为了线程安全与避免共享状态，每个任务单独创建 UnifiedFileProcessor
        processor = UnifiedFileProcessor()
        path = pathlib.Path(fp)
        result = processor.extract_text(str(path))
        return idx, path, result

    if workers < 1:
        workers = 1

    results_by_idx: dict[int, dict] = {}
    paths_by_idx: dict[int, pathlib.Path] = {}

    if workers == 1 or len(file_paths) <= 1:
        for idx, fp in enumerate(file_paths, start=1):
            i, path, result = _one(idx, fp)
            results_by_idx[i] = result
            paths_by_idx[i] = path
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_one, idx, fp) for idx, fp in enumerate(file_paths, start=1)]
            for fut in as_completed(futs):
                i, path, result = fut.result()
                results_by_idx[i] = result
                paths_by_idx[i] = path

    for idx in range(1, len(file_paths) + 1):
        path = paths_by_idx[idx]
        result = results_by_idx[idx]

        row = {
            "input": str(path),
            "success": bool(result.get("success")),
            "file_type": result.get("file_type"),
            "processor": result.get("processor"),
            "error": result.get("error", ""),
        }

        if result.get("success") and result.get("text"):
            content = result["text"]
            texts.append(content)
            out_file = text_out_dir / f"{idx:04d}_{path.stem}.txt"
            out_file.write_text(content, encoding="utf-8")
            row["text_file"] = str(out_file)
            row["text_len"] = len(content)

        manifest_rows.append(row)

    return texts, manifest_rows


def _run_visualization(output_path: pathlib.Path, log):
    try:
        from visualization import visual as visual_app
    except Exception as exc:  # pragma: no cover - best effort integration
        log(f"[4/4] visualization: skipped (import error: {exc})")
        return

    try:
        visual_app.main([str(output_path)])
        log(f"[4/4] visualization: 可视化完成，结果保存在 pipeline_outputs/output_HTML/ 目录下")
    except Exception as exc:  # pragma: no cover - external integration
        log(f"[4/4] visualization: 可视化失败 ({exc})")


def main():
    parser = argparse.ArgumentParser(description="Webis end-to-end pipeline (crawler -> clean -> structuring).")
    parser.add_argument("task", help="一句自然语言任务：既描述要抓取什么，也描述要结构化成什么。")
    parser.add_argument("--limit", type=int, default=5, help="crawler 最大抓取数量（默认 5）")
    parser.add_argument("--out", type=str, default=None, help="输出目录（默认 pipeline_outputs/<timestamp>/）")
    parser.add_argument("--verbose", action="store_true", help="打印每个文件的处理中间信息")
    parser.add_argument("--workers", type=int, default=4, help="tools 清洗并发数（默认 4）")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    def log(msg: str):
        print(msg, flush=True)

    llm = _init_llm()

    run_id = str(int(time.time()))
    run_dir = pathlib.Path(args.out).expanduser().resolve() if args.out else (PROJECT_ROOT / "pipeline_outputs" / run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1) Crawl
    log("\n[1/4] crawler：开始获取数据源…")
    from crawler.agent import LangChainDataSourceAgent  # local package import
    from crawler.baidu_mcp_tool import BaiduAiSearchMcpTool
    from crawler.gnews_tool import GNewsTool
    from crawler.semantic_scholar import SemanticScholarTool
    from crawler.github_api_tools import GitHubSearchTool
    from crawler.hn_tool import HackerNewsTool
    from crawler.serpapi_tool import SerpApiSearchTool

    crawler_agent = LangChainDataSourceAgent(
        llm=llm,
        tools=[
            BaiduAiSearchMcpTool(output_dir=str(run_dir)),
            GNewsTool(output_dir=str(run_dir)),
            SemanticScholarTool(output_dir=str(run_dir)),
            GitHubSearchTool(output_dir=str(run_dir)),
            HackerNewsTool(output_dir=str(run_dir)),
            SerpApiSearchTool(output_dir=str(run_dir)),
        ],
        verbose=args.verbose,
    )
    crawl_result = crawler_agent.run(task=args.task, limit=args.limit)
    if getattr(crawler_agent, "last_choice", None):
        log(f"[1/4] crawler：tool 选择={crawler_agent.last_choice}")

    crawl_meta = {
        "tool": crawl_result.name,
        "success": crawl_result.success,
        "output_dir": crawl_result.output_dir,
        "files": crawl_result.files,
        "error": crawl_result.error,
        "meta": crawl_result.meta,
    }

    if not crawl_result.success:
        log("[1/4] crawler：失败详情（用于排查）")
        log(json.dumps(crawl_meta, ensure_ascii=False, indent=2))
        (run_dir / "manifest.json").write_text(
            json.dumps({"task": args.task, "crawl": crawl_meta}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        raise SystemExit(f"crawler 失败：{crawl_result.error}")

    crawl_files = crawl_result.files or _collect_crawl_files(crawl_result.output_dir or "")
    log(f"[1/4] crawler：完成（{len(crawl_files)} 个文件） output_dir={crawl_result.output_dir}")
    if args.verbose and crawl_result.meta:
        log("[1/4] crawler：执行历史")
        log(json.dumps(crawl_result.meta, ensure_ascii=False, indent=2))
    if crawl_result.error:
        log(f"[1/4] crawler：未达目标：{crawl_result.error}")
    (run_dir / "crawl_files.json").write_text(json.dumps(crawl_files, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) Clean to texts
    log("\n[2/4] tools：开始清洗/抽取纯文本…")
    texts_dir = run_dir / "texts"
    texts, clean_rows = _extract_texts(crawl_files, texts_dir, workers=args.workers, verbose=args.verbose)
    ok = sum(1 for r in clean_rows if r.get("success"))
    bad = len(clean_rows) - ok
    log(f"[2/4] tools：完成（成功 {ok} / 失败 {bad}） texts_dir={texts_dir}")
    if args.verbose:
        for r in clean_rows:
            if r.get("success"):
                log(f"  ✓ {r.get('input')} -> {r.get('text_file')} ({r.get('text_len', 0)} chars)")
            else:
                log(f"  ✗ {r.get('input')}  error={r.get('error')}")
    elif bad:
        for r in clean_rows:
            if not r.get("success"):
                log(f"  ✗ {r.get('input')}  error={r.get('error')}")

    # 3) Structuring
    log("\n[3/4] structuring：开始结构化抽取…")
    from structuring.prompt_agent import PromptBuilderAgent
    from structuring.extract_agent import StructureExtractionAgent

    prompt_agent = PromptBuilderAgent(llm)
    extract_agent = StructureExtractionAgent(llm)

    prompt, output_format = prompt_agent.build_with_format(goal=args.task, texts=texts, schema=None, few_shots=[])
    log(f"[3/4] structuring：已生成抽取 Prompt（output_format={output_format}）")
    extraction = extract_agent.extract(prompt=prompt, text=texts, output_format=output_format)

    structured_dir = run_dir / "structured"
    structured_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = structured_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    if output_format == "json":
        out_path = structured_dir / "result.json"
        if extraction.success and extraction.parsed is not None:
            out_path.write_text(json.dumps(extraction.parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            out_path.write_text(extraction.raw, encoding="utf-8")
    else:
        out_path = structured_dir / "result.md"
        out_path.write_text(extraction.raw, encoding="utf-8")

    manifest = {
        "task": args.task,
        "run_dir": str(run_dir),
        "crawl": crawl_meta,
        "clean": {"text_dir": str(texts_dir), "files": clean_rows},
        "structuring": {
            "output_format": output_format,
            "prompt_file": str(prompt_path),
            "result_file": str(out_path),
            "success": extraction.success,
            "error": extraction.error,
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) Visualization
    log("\n[4/4] visualization: 开始进行可视化")
    _run_visualization(out_path, log)

    print(f"\n完成：{run_dir}")
    print(f"- crawl: {crawl_result.output_dir}")
    print(f"- texts: {texts_dir}")
    print(f"- prompt: {prompt_path}")
    print(f"- result: {out_path}")


if __name__ == "__main__":
    main()