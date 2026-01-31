"""
AI Chat Panel Component - NotebookLM-style chat interface for data analysis
"""

import streamlit as st
import json
from typing import List, Dict, Any, Optional
from webis.core.llm.base import get_default_router

def render_chat_panel(
    structured_result: Optional[Dict[str, Any]],
    documents: List[Any],
    chat_history: List[Dict[str, str]]
):
    """
    Render the AI chat panel for data analysis
    
    Args:
        structured_result: Current structured data result
        documents: List of source documents
        chat_history: List of chat messages
    """
    st.header("💬 AI 分析助手")
    
    # Check if data is available
    if not structured_result:
        st.info("📝 请先运行Pipeline获取结构化数据，然后开始AI分析")
        return
    
    # Chat history container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        if not chat_history:
            # Welcome message
            st.chat_message("assistant").markdown(
                "👋 您好！我是Webis AI助手。\n\n"
                "我已经完成了对您数据的结构化处理，现在可以帮您：\n"
                "- 📊 分析结构化数据的特征和规律\n"
                "- 🔍 根据您的需求进行数据查询和筛选\n"
                "- 📈 生成数据可视化和统计摘要\n"
                "- 💡 提供基于数据的洞察和建议\n\n"
                "请在下方输入您的问题或分析需求。"
            )
        
        # Display existing messages
        for message in chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display references if available
                if "references" in message and message["references"]:
                    with st.expander("📚 引用文档"):
                        for ref in message["references"]:
                            st.markdown(f"- [{ref.get('title', '文档')}]({ref.get('url', '#')})")
    
    # Chat input
    if prompt := st.chat_input("基于结构化数据提问或请求分析..."):
        # Add user message to history
        chat_history.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("💭 AI正在思考..."):
                try:
                    # Build context
                    context = build_chat_context(structured_result, documents)
                    
                    # Call LLM
                    router = get_default_router()
                    response = router.chat([
                        {
                            "role": "system",
                            "content": get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": f"上下文信息:\n{context}\n\n用户问题: {prompt}"
                        }
                    ])
                    
                    # Extract references
                    references = extract_references(response.content, documents)
                    
                    # Display response
                    st.markdown(response.content)
                    
                    # Store response with references
                    assistant_message = {
                        "role": "assistant",
                        "content": response.content,
                        "references": references
                    }
                    chat_history.append(assistant_message)
                    
                    # Show references if available
                    if references:
                        with st.expander("📚 引用文档"):
                            for ref in references:
                                st.markdown(f"- [{ref.get('title', '文档')}]({ref.get('url', '#')})")
                
                except Exception as e:
                    st.error(f"❌ AI回复生成失败: {str(e)}")
                    
                    # Add error message to history
                    error_msg = {
                        "role": "assistant",
                        "content": "抱歉，处理您的问题时出现了错误。请检查网络连接或稍后重试。"
                    }
                    chat_history.append(error_msg)


def build_chat_context(structured_result: Dict[str, Any], documents: List[Any]) -> str:
    """Build context for AI chat"""
    context_parts = []
    
    # Structured data summary
    data = structured_result.get("data", [])
    stats = structured_result.get("stats", {})
    
    context_parts.append("【结构化数据摘要】")
    context_parts.append(f"数据项数: {len(data) if isinstance(data, list) else 1}")
    context_parts.append(f"接受文档数: {stats.get('accepted_count', 0)}")
    context_parts.append(f"迭代次数: {stats.get('iterations', 0)}")
    
    # Data structure
    if isinstance(data, list) and data:
        if isinstance(data[0], dict):
            context_parts.append(f"字段: {', '.join(data[0].keys())}")
    elif isinstance(data, dict):
        context_parts.append(f"字段: {', '.join(data.keys())}")
    
    context_parts.append("")
    
    # Source document information
    context_parts.append("【源文档信息】")
    
    for i, doc in enumerate(documents[:5]):  # Limit to 5 documents
        doc_info = {
            "id": doc.id if hasattr(doc, 'id') else str(i),
            "title": getattr(doc.meta, 'title', None) or f"文档 {i+1}",
            "type": getattr(doc.doc_type, 'value', str(doc.doc_type)) if hasattr(doc.doc_type, 'value') else str(doc.doc_type),
            "url": getattr(doc.meta, 'url', None) or "本地文件"
        }
        context_parts.append(f"- 文档{i+1}: {doc_info['title']} ({doc_info['type']})")
    
    return "\n".join(context_parts)


def get_system_prompt() -> str:
    """Get system prompt for the AI assistant"""
    return """你是Webis AI数据分析助手，专注于帮助用户理解和使用结构化的知识数据。

你的主要职责：
1. 基于提供的结构化数据回答用户问题
2. 清晰解释数据中的关键信息和规律
3. 提取引用的文档来源，方便用户追溯
4. 提供数据驱动的洞察和建议

回复要求：
1. 语言简洁、专业
2. 使用中文回复
3. 如有引用，在回复末尾列出参考文档
4. 如数据无法回答问题，明确说明
5. 避免编造信息，严格基于提供的上下文

回复格式：
- 先直接回答问题
- 如有必要，给出详细解释
- 最后列出引用来源（如果有）
"""


def extract_references(response: str, documents: List[Any]) -> List[Dict[str, str]]:
    """
    Extract document references from response and documents
    
    Args:
        response: AI response text
        documents: List of source documents
    
    Returns:
        List of reference dictionaries
    """
    references = []
    
    # Simple reference extraction based on document indices in response
    # Looking for patterns like [1], [doc1], 文档1, etc.
    
    import re
    
    # Common reference patterns
    patterns = [
        r'\[(\d+)\]',  # [1], [2]
        r'文档\s*(\d+)',  # 文档1
        r'doc\s*(\d+)',  # doc1
    ]
    
    matched_indices = set()
    for pattern in patterns:
        matches = re.findall(pattern, response)
        for match in matches:
            try:
                idx = int(match) - 1  # Convert to 0-based index
                if 0 <= idx < len(documents):
                    matched_indices.add(idx)
            except ValueError:
                continue
    
    # Create references for matched documents
    for idx in matched_indices:
        doc = documents[idx]
        references.append({
            "id": doc.id if hasattr(doc, 'id') else str(idx),
            "title": getattr(doc.meta, 'title', None) or f"文档 {idx+1}",
            "url": getattr(doc.meta, 'url', None) or "本地文件",
            "type": getattr(doc.doc_type, 'value', str(doc.doc_type)) if hasattr(doc.doc_type, 'value') else str(doc.doc_type)
        })
    
    # If no references found, include all documents
    if not references and documents:
        for idx, doc in enumerate(documents[:3]):  # Limit to 3 references
            references.append({
                "id": doc.id if hasattr(doc, 'id') else str(idx),
                "title": getattr(doc.meta, 'title', None) or f"文档 {idx+1}",
                "url": getattr(doc.meta, 'url', None) or "本地文件",
                "type": getattr(doc.doc_type, 'value', str(doc.doc_type)) if hasattr(doc.doc_type, 'value') else str(doc.doc_type)
            })
    
    return references


def generate_quick_analysis_prompts(structured_result: Dict[str, Any]) -> List[str]:
    """Generate quick analysis prompt suggestions"""
    prompts = []
    
    data = structured_result.get("data", [])
    
    # Basic analysis prompts
    prompts.append("分析这些数据的主要特征和规律")
    prompts.append("总结数据结构，找出关键指标")
    prompts.append("这些数据有什么异常或特殊情况？")
    
    # Data-specific prompts
    if isinstance(data, list) and data:
        if isinstance(data[0], dict):
            # Get field names
            fields = list(data[0].keys())
            
            if len(fields) > 0:
                prompts.append(f"分析 '{fields[0]}' 字段的分布和趋势")
            
            if len(fields) > 1:
                prompts.append(f"'{fields[0]}' 和 '{fields[1]}' 之间有什么关系？")
            
            if len(fields) > 2:
                prompts.append("给出所有字段的综合分析报告")
    
    # Visualization prompts
    prompts.append("建议如何可视化这些数据？")
    prompts.append("哪些数据适合制作图表？")
    
    return prompts[:5]  # Return top 5 suggestions