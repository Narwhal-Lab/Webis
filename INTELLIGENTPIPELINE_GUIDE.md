# IntelligentPipeline 工作流程说明文档

## 目录
1. [概述](#概述)
2. [架构设计](#架构设计)
3. [核心工作流程](#核心工作流程)
4. [组件详解](#组件详解)
5. [数据流转](#数据流转)
6. [使用示例](#使用示例)

---

## 概述

**IntelligentPipeline** 是一个智能网络爬虫管道系统，集成了多个agent（代理）来智能地爬取、清理和验证网络文档。它通过以下特性来确保获取高质量的相关文档：

- ✅ **智能工具选择** - 使用LLM自动选择最适合的数据源
- ✅ **自动重新爬取** - 当文档不足或质量不达标时自动重新爬取
- ✅ **LLM驱动的验证** - 使用LLM判断文档的相关性和质量
- ✅ **LLM清理内容** - 使用LLM从HTML中提取主要内容
- ✅ **失败工具跟踪** - 记录失败的工具，避免重复尝试

---

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│          IntelligentPipeline (主编排器)              │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┐
        │                    │              │
        ▼                    ▼              ▼
   CrawlerAgent    ValidationAgent  HTMLCleanerPlugin
   (爬虫代理)        (验证代理)        (HTML清理)
        │                    │              │
        ├─ LLMRouter        ├─ LLMRouter   └─ LLMRouter
        │  (工具选择)         │              (内容提取)
        │                    │ (相关性判断)
        ├─ PluginRegistry   │
        │  (数据源注册)       │
        │                    │
        └─ SourcePlugins    │
           (DuckDuckGo,      │
            GitHub,GNews等)  │
```

**核心组件：**

| 组件 | 职责 | 依赖 |
|------|------|------|
| **IntelligentPipeline** | 编排整个工作流，管理迭代循环 | CrawlerAgent, ValidationAgent, HTMLCleanerPlugin |
| **CrawlerAgent** | 选择数据源、执行爬取任务 | LLMRouter, PluginRegistry |
| **ValidationAgent** | 验证文档质量和相关性 | LLMRouter |
| **HTMLCleanerPlugin** | 从HTML中提取主要内容 | LLMRouter |
| **AgentState** | 追踪爬取和验证的状态 | - |

---

## 核心工作流程

### 总体流程图

```
开始
  │
  ├─► 初始化Pipeline、Agent、State
  │
  └─► 进入迭代循环 (最多 max_iterations 次)
        │
        ├─► [第1步] 数量检查
        │   ├─ 已接受文档数 >= min_count? ✓ 结束
        │   └─ 否则 → 继续
        │
        ├─► [第2步] 爬取文档
        │   ├─ CrawlerAgent.run()
        │   │  ├─ 获取可用数据源列表
        │   │  ├─ 用LLM选择最佳工具
        │   │  └─ 执行爬取任务
        │   └─ 返回原始文档列表
        │
        ├─► [第3步] 清理文档
        │   ├─ HTMLCleanerPlugin.process()
        │   │  ├─ 用BeautifulSoup提取可见文本
        │   │  ├─ 用LLM识别主要内容
        │   │  └─ 返回clean_content
        │   └─ 返回已清理文档列表
        │
        ├─► [第4步] 验证相关性
        │   └─ for each doc:
        │      ├─ ValidationAgent.check_relevance()
        │      │  ├─ 构建验证提示
        │      │  ├─ 调用LLM判断相关性
        │      │  └─ 返回 (是否相关, 置信度, 理由)
        │      │
        │      ├─ if 相关 && 置信度 >= threshold:
        │      │  └─ state.add_decision(doc, "ACCEPT")
        │      └─ else:
        │         └─ state.add_decision(doc, "REJECT")
        │
        ├─► [第5步] 状态检查
        │   └─ 返回第1步继续迭代
        │
└──► 返回最终结果
     ├─ documents: 已接受的文档列表
     ├─ rejected: 已拒绝的文档列表
     └─ stats: 统计信息
```

### 详细步骤说明

#### 步骤1: 数量检查
```python
is_sufficient, shortage = validation_agent.check_quantity(
    state.current_docs,
    state.required_count
)
```
- 检查已接受的文档数是否满足要求
- 如果满足，结束迭代
- 如果不足，计算缺少的文档数 (shortage)

#### 步骤2: 爬取文档
```python
raw_docs = crawler_agent.run(
    task=query,
    limit=crawl_limit,  # shortage + 5 (预留余量)
    context=context,
    excluded_tools=state.failed_tools  # 排除之前失败的工具
)
```

**CrawlerAgent 内部流程：**
1. 获取所有可用数据源插件 (DuckDuckGo, GitHub, GNews等)
2. 过滤已排除的工具
3. 构建提示词，让LLM选择最佳工具：
   ```
   用户任务: "{query}"
   可用工具: [列表]
   已排除工具: [列表]
   
   → LLM回复: 按优先级返回3个最佳工具和改进的查询词
   ```
4. 按顺序执行选定的工具，直到达到文档数量限制
5. 返回原始文档列表

#### 步骤3: 清理文档
```python
cleaned_docs = pipeline._clean_documents(raw_docs, context)
```

**HTMLCleanerPlugin 内部流程：**
1. 用 BeautifulSoup 解析HTML，移除脚本/样式标签
2. 提取所有可见文本
3. 调用LLM清理：
   ```
   系统提示: "提取网页主要内容，忽略导航菜单、页脚、广告等"
   用户输入: 前8000字符的页面文本
   
   → LLM回复: 
   {
     "main_text": "清理后的内容",
     "reason": "提取理由"
   }
   ```
4. 返回带 clean_content 的文档对象

#### 步骤4: 验证相关性
对每个清理后的文档：

```python
is_relevant, score, reason = validation_agent.check_relevance(
    doc, query, intent
)
```

**ValidationAgent 内部流程：**
1. 构建验证提示词：
   ```
   用户查询: "{query}"
   用户意图: {intent}
   
   文档内容: "{doc_content[:2000]}"
   
   → LLM回复:
   {
     "is_relevant": true/false,
     "confidence": 0.0-1.0,
     "reason": "判断理由",
     "verdict": "ACCEPT" or "REJECT"
   }
   ```
2. 解析LLM响应，提取是否相关和置信度
3. 如果相关且置信度 >= relevance_threshold：
   - 接受文档 → state.current_docs
4. 否则：
   - 拒绝文档 → state.rejected_docs

---

## 组件详解

### 1. IntelligentPipeline (主编排器)

**职责：** 协调整个工作流程，管理迭代循环

**主要方法：**

```python
def run(query, requirements, context) -> Dict[str, Any]:
    """
    执行智能管道
    
    Args:
        query: 用户查询
        requirements: 要求配置
            - min_count: 最少文档数 (默认10)
            - relevance_threshold: 相关性阈值 (默认0.7)
            - max_iterations: 最大迭代次数 (默认3)
        context: 管道上下文
    
    Returns:
        {
            "documents": [已接受文档],
            "rejected": [已拒绝文档],
            "stats": {
                "accepted_count": int,
                "rejected_count": int,
                "iterations": int,
                "success": bool
            }
        }
    """
```

**状态管理：**
- 使用 `AgentState` 跟踪：
  - 已接受的文档
  - 已拒绝的文档
  - 失败的工具
  - 当前迭代次数

### 2. CrawlerAgent (爬虫代理)

**职责：** 智能选择数据源并执行爬取

**关键算法：**

```python
def run(task, limit, context, excluded_tools):
    # 1. 获取可用工具
    sources = [s for s in all_sources if s not in excluded_tools]
    
    # 2. LLM选择最佳工具
    prompt = f"""
    选择最佳的3个工具来完成任务: "{task}"
    可用工具: {tool_list}
    已排除工具: {excluded_tools}
    返回JSON格式的执行计划
    """
    response = llm.chat(prompt)
    plan = parse_json(response)  # [{"tool": ..., "query": ..., "reason": ...}]
    
    # 3. 按顺序执行工具
    all_docs = []
    for step in plan:
        if len(all_docs) >= limit:
            break
        docs = execute_tool(step["tool"], step["query"])
        all_docs.extend(docs)
    
    return all_docs
```

**降级策略：**
- 如果LLM选择失败，使用默认工具列表：DuckDuckGo → Google → Baidu
- 如果工具执行失败，标记为 failed_tool，下次迭代跳过

### 3. ValidationAgent (验证代理)

**职责：** 判断文档质量和相关性

**两个核心方法：**

```python
def check_quantity(documents, required_count) -> (bool, int):
    """检查文档数量是否足够"""
    return len(documents) >= required_count, max(0, required_count - len(documents))

def check_relevance(document, query, intent) -> (bool, float, str):
    """
    判断文档相关性
    
    Returns:
        is_relevant: 是否相关
        confidence: 置信度 (0.0-1.0)
        reason: 判断理由
    """
```

**相关性判断标准（在LLM提示中定义）：**
- ✓ ACCEPT: 直接回答查询、提供最新信息、有实质内容
- ✗ REJECT: 内容过时、无关、重复模板文本、只有链接

### 4. HTMLCleanerPlugin (HTML清理插件)

**职责：** 从HTML中提取主要内容

**处理流程：**

```python
def process(doc, context):
    # 1. 解析HTML
    soup = BeautifulSoup(doc.content, "html.parser")
    
    # 2. 移除非内容标签
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    
    # 3. 提取可见文本
    page_text = soup.get_text(separator="\n", strip=True)
    
    # 4. LLM清理
    clean_text = llm_clean(page_text)
    
    # 5. 更新文档
    doc.clean_content = clean_text
    return doc
```

**LLM清理指令：**
```
提取主要内容，排除：
❌ 导航菜单、面包屑、页眉/页脚
❌ 广告、登录提示、推荐链接
❌ 网站搜索框、版权声明、评论
❌ 社交按钮、Cookie横幅、重复文本
✅ 文章正文、产品描述、新闻内容
```

### 5. AgentState (状态追踪)

**职责：** 维护爬取过程中的状态

```python
@dataclass
class AgentState:
    query: str                          # 用户查询
    intent: Dict[str, Any]              # 解析的意图
    required_count: int                 # 所需文档数
    current_docs: List[WebisDocument]   # ✓ 已接受文档
    rejected_docs: List[WebisDocument]  # ✗ 已拒绝文档
    attempts: int                       # 当前迭代数
    max_attempts: int                   # 最大迭代数
    failed_tools: List[str]             # 失败的工具 (下次跳过)
```

---

## 数据流转

### 数据对象规范

**WebisDocument** - 网络文档对象
```
{
  id: str                          # 唯一标识
  content: str                     # 原始HTML内容
  clean_content: str               # [由HTMLCleaner填充] 清理后的文本
  meta: {
    url: str                       # 来源URL
    title: str                     # 页面标题
    source_plugin: str             # 来源插件名称
  }
  metadata: dict                   # 附加元数据
}
```

### 数据流转路径

```
数据源插件 (DuckDuckGo/GitHub等)
    │
    ├─ 返回: WebisDocument (仅content + meta)
    │
    ▼
HTMLCleanerPlugin._clean_documents()
    │
    ├─ 处理每个文档
    ├─ 提取可见文本
    ├─ LLM识别主要内容
    │
    ├─ 返回: WebisDocument (content + clean_content + meta)
    │
    ▼
ValidationAgent.check_relevance()
    │
    ├─ 读取 clean_content
    ├─ LLM判断相关性
    │
    ├─ 返回: (is_relevant, confidence, reason)
    │
    ▼
AgentState (decision)
    │
    ├─ 如果相关: → current_docs ✓
    └─ 否则: → rejected_docs ✗
```

---

## 使用示例

### 基础使用

```python
from webis.core.intelligent_pipeline import IntelligentPipeline

# 初始化管道
pipeline = IntelligentPipeline()

# 运行管道
result = pipeline.run(
    query="Python 3.12 新特性",
    requirements={
        'min_count': 5,              # 至少5篇文档
        'relevance_threshold': 0.6,  # 相关性阈值
        'max_iterations': 2           # 最多2次迭代
    }
)

# 获取结果
print(f"✓ 已接受: {len(result['documents'])} 篇")
print(f"✗ 已拒绝: {len(result['rejected'])} 篇")
print(f"迭代次数: {result['stats']['iterations']}")

# 处理已接受的文档
for doc in result['documents']:
    print(f"- {doc.meta.title}")
    print(f"  来源: {doc.meta.url}")
    print(f"  插件: {doc.meta.source_plugin}")
    print(f"  内容长度: {len(doc.clean_content)} 字符")
```

### 与RAGPipeline集成

```python
from webis.core.rag.pipeline import RAGPipeline
from webis.core.intelligent_pipeline import IntelligentPipeline

# 创建管道
rag_pipeline = RAGPipeline()
intelligent_pipeline = IntelligentPipeline()

# 运行IntelligentPipeline获取高质量文档
result = intelligent_pipeline.run(
    query="AI芯片最新进展",
    requirements={
        'min_count': 5,
        'relevance_threshold': 0.65,
        'max_iterations': 2
    }
)

# 将结果转换为RAG格式
rag_documents = []
for doc in result['documents']:
    rag_documents.append({
        'content': doc.clean_content,
        'source': doc.meta.url,
        'title': doc.meta.title,
        'metadata': {
            'source_plugin': doc.meta.source_plugin,
            'webis_validation': 'passed'
        }
    })

# 存储到RAG
rag_pipeline.process_and_store_documents(rag_documents, query="AI芯片最新进展")

# 检索相关文档
retrieval = rag_pipeline.retrieve("AI芯片性能比较")
```

### 自定义配置

```python
from webis.core.agent.crawler_agent import CrawlerAgent
from webis.core.agent.validation_agent import ValidationAgent
from webis.core.intelligent_pipeline import IntelligentPipeline

# 创建自定义Agent
crawler = CrawlerAgent(
    router=custom_llm_router,
    registry=custom_plugin_registry
)
validator = ValidationAgent(router=custom_llm_router)

# 初始化管道（使用自定义Agent）
pipeline = IntelligentPipeline(
    crawler_agent=crawler,
    validation_agent=validator
)

# 运行
result = pipeline.run(
    query="最新技术新闻",
    requirements={
        'min_count': 10,
        'relevance_threshold': 0.75,
        'max_iterations': 3
    }
)
```

---

## 关键设计特性

### 1. 失败工具追踪

```python
# 某个工具失败 → 记录在state.failed_tools
if not raw_docs:
    failed = crawler_agent.last_used_tools
    state.failed_tools.extend(failed)

# 下次迭代跳过失败工具
raw_docs = crawler_agent.run(
    task=query,
    excluded_tools=state.failed_tools  # 排除
)
```

### 2. 自动重爬取

```python
# 第1次迭代: 5篇文档 → 3篇被接受，2篇被拒绝
# shortage = min_count - len(current_docs) = 5 - 3 = 2

# 第2次迭代: 爬取 2 + 5 = 7 篇 (加5是预留)
crawl_limit = shortage + 5
```

### 3. LLM智能选择

```python
# LLM不是随机选择，而是根据任务性质
# - 代码相关 → GitHub优先
# - 新闻相关 → GNews优先
# - 通用查询 → DuckDuckGo优先
```

### 4. 严格的错误处理

```python
# HTMLCleanerPlugin: 严格模式，LLM失败直接异常
# → 确保returned content是LLM验证过的

# 其他错误: 优雅降级
# → 保证整个管道不会因单文档失败而中断
```

---

## 性能指标

| 指标 | 说明 |
|------|------|
| **min_count** | 目标文档数量 |
| **relevance_threshold** | 相关性置信度阈值 (0.0-1.0) |
| **max_iterations** | 最多重复多少次爬取周期 |
| **crawl_limit** | 每次迭代的爬取数量 |
| **LLM调用次数** | ~(爬取数量 × 迭代数) 次 |

---

## 故障排查

### 问题1: 文档质量不高

**原因：** relevance_threshold 设置过低

**解决：** 提高阈值
```python
requirements={
    'relevance_threshold': 0.75,  # 从0.6提升到0.75
}
```

### 问题2: 爬取速度慢

**原因：** 多次LLM调用（验证每个文档）

**解决：** 
- 增加 max_iterations（减少爬取次数）
- 提高 min_count（更快达成目标）
- 优化LLM模型

### 问题3: 爬不到足够的文档

**原因：** 工具选择不当或数据源缺乏

**解决：**
- 降低 relevance_threshold
- 增加 max_iterations
- 注册更多数据源插件

---

## 总结

IntelligentPipeline通过以下创新设计实现高质量文档爬取：

1. **智能工具选择** - LLM根据任务选择最适合的数据源
2. **LLM驱动清理** - 从HTML中准确提取主要内容
3. **LLM验证相关性** - 确保只保留相关文档
4. **自动重爬取** - 不足时自动获取更多文档
5. **失败追踪** - 避免重复尝试失败的策略
6. **优雅降级** - 单个失败不影响整体流程

这使其成为一个**可靠、灵活、智能**的网络爬虫解决方案。
