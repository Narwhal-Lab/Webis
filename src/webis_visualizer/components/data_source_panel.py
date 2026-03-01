"""
Data Source Panel Component - Handles data source selection and management
"""

import streamlit as st
from typing import List, Callable, Optional
from webis.core.agent.crawler_agent import CrawlerAgent
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, DocumentStatus
import time

def render_data_source_panel(
    on_documents_updated: Callable[[List[WebisDocument]], None],
    current_documents: List[WebisDocument]
):
    """
    Render the data source management panel
    
    Args:
        on_documents_updated: Callback function when documents are updated
        current_documents: Current list of documents
    """
    st.sidebar.markdown(
        "<div class=\"sidebar-title\">📁 数据源管理</div>",
        unsafe_allow_html=True
    )
    
    # Single page for all data sources
    render_web_crawling_section(on_documents_updated)
    st.sidebar.markdown("---")
    # render_local_upload_section(on_documents_updated)
    
    # ======================
    # Document List
    # ======================
    render_document_list(current_documents)


def render_web_crawling_section(
    on_documents_updated: Callable[[List[WebisDocument]], None]
):
    """Render web crawling configuration section"""
    st.markdown("### 🔍 互联网数据爬取")
    
    query = st.text_input(
        "搜索关键词",
        placeholder="输入您想获取的内容...",
        key="crawl_query"
    )
    
    st.caption("搜索引擎由 Agent 自动选择")
    
    limit = st.slider(
        "获取数量",
        min_value=1,
        max_value=20,
        value=5,
        key="crawl_limit"
    )
    
    advanced_expander = st.expander("高级选项", expanded=False)
    
    with advanced_expander:
        date_filter = st.selectbox(
            "时间过滤",
            options=["不限", "过去24小时", "过去7天", "过去30天", "过去1年"]
        )
        language = st.selectbox(
            "语言",
            options=["不限", "英文", "中文", "日文", "韩文"]
        )
    
    if st.button("🚀 开始爬取", key="crawl_btn", use_container_width=True):
        if not query:
            st.error("❌ 请输入搜索关键词")
            return
        
        source_label = "Agent自动选择"
        with st.spinner("正在获取数据..."):
            try:
                # Use CrawlerAgent
                agent = CrawlerAgent()
                docs = agent.run(query, limit=limit)
                
                # Update document status
                for doc in docs:
                    if hasattr(doc.status, 'value'):
                        doc.status = DocumentStatus.COMPLETED
                    else:
                        doc.status = DocumentStatus.COMPLETED
                    doc.meta.source_plugin = source_label
                
                # Call callback
                on_documents_updated(docs)
                
                st.success(f"✅ 成功获取 {len(docs)} 条数据")
                
            except Exception as e:
                st.error(f"❌ 爬取失败: {str(e)}")


def render_local_upload_section(
    on_documents_updated: Callable[[List[WebisDocument]], None]
):
    """Render local file upload section"""
    st.markdown("### 📤 本地文件上传")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "选择文件",
        accept_multiple_files=True,
        type=["pdf", "html", "txt", "csv", "md", "json", "docx"],
        key="local_file_uploader"
    )
    
    # File type info
    st.caption("支持的格式: PDF, HTML, TXT, CSV, MD, JSON, DOCX")
    
    # Show selected files
    if uploaded_files:
        st.markdown("#### 已选择的文件:")
        for file in uploaded_files:
            file_size = file.size / 1024  # KB
            st.markdown(f"📄 **{file.name}** ({file_size:.1f} KB)")
    
    # Process button
    if st.button("📋 处理文件", key="process_files_btn", use_container_width=True):
        if not uploaded_files:
            st.error("❌ 请先选择文件")
            return
        
        with st.spinner("正在处理文件..."):
            try:
                local_docs = []
                
                for file in uploaded_files:
                    # Detect file type and create document
                    doc = process_local_file(file)
                    if doc:
                        local_docs.append(doc)
                
                # Call callback with new documents
                on_documents_updated(local_docs)
                
                st.success(f"✅ 成功处理 {len(local_docs)} 个文件")
                
            except Exception as e:
                st.error(f"❌ 文件处理失败: {str(e)}")


def render_document_list(documents: List[WebisDocument]):
    """Render document list with status and actions"""
    st.markdown("---")
    st.markdown("### 📋 文档列表")
    
    if not documents:
        st.info("📭 暂无文档，请添加数据源")
        return
    
    # Statistics
    st.markdown(f"**共 {len(documents)} 个文档**")
    
    # Document cards
    for idx, doc in enumerate(documents):
        render_document_card(doc, idx)


def render_document_card(doc: WebisDocument, index: int):
    """Render a single document card"""
    # Determine status and color
    status = getattr(doc.status, 'value', str(doc.status)) if hasattr(doc.status, 'value') else str(doc.status)
    
    status_config = {
        "completed": {"color": "🟢", "bg": "#E8F5E9"},
        "pending": {"color": "🟡", "bg": "#FFF8E1"},
        "failed": {"color": "🔴", "bg": "#FFEBEE"},
        "processing": {"color": "🔵", "bg": "#E3F2FD"}
    }
    
    status_info = status_config.get(status, {"color": "⚪", "bg": "#FAFAFA"})
    
    # Document title
    title = doc.meta.title or f"文档 #{index + 1}"
    
    with st.expander(f"{status_info['color']} {title}"):
        # Metadata
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**状态:** {status}")
            st.markdown(f"**类型:** {getattr(doc.doc_type, 'value', str(doc.doc_type))}")
        
        with col2:
            source = doc.meta.url or doc.meta.source_plugin or "本地"
            st.markdown(f"**来源:** {source}")
            if doc.meta.author:
                st.markdown(f"**作者:** {doc.meta.author}")
        
        # Content preview
        if doc.clean_content:
            preview_text = doc.clean_content[:300]
        elif doc.content:
            preview_text = doc.content[:300]
        else:
            preview_text = "无内容"
        
        st.text_area("内容预览", preview_text + "...", height=100, disabled=True, key=f"preview_{index}")
        
        # Action buttons
        col_reprocess, col_delete = st.columns(2)
        
        with col_reprocess:
            if st.button("🔄 重新处理", key=f"reprocess_{index}", use_container_width=True):
                st.info("重新处理功能将在下一版本实现")
        
        with col_delete:
            if st.button("🗑️ 删除", key=f"delete_{index}", use_container_width=True):
                if "on_delete" in st.session_state:
                    st.session_state.on_delete(index)
                st.experimental_rerun()


def process_local_file(file) -> Optional[WebisDocument]:
    """
    Process a local file and return a WebisDocument
    
    Args:
        file: Streamlit uploaded file object
    
    Returns:
        WebisDocument instance or None if processing fails
    """
    try:
        # Read file content
        file_content = file.read()
        
        # Detect file type
        file_name = file.name.lower()
        file_type = file.type
        
        # Determine document type
        if file_name.endswith('.pdf') or 'pdf' in file_type:
            doc_type = DocumentType.PDF
        elif file_name.endswith(('.html', '.htm')) or 'html' in file_type:
            doc_type = DocumentType.HTML
        elif file_name.endswith(('.txt', '.md')) or 'text' in file_type:
            doc_type = DocumentType.TEXT
        elif file_name.endswith('.csv'):
            doc_type = DocumentType.JSON  # Use JSON type for CSV
        else:
            doc_type = DocumentType.UNKNOWN
        
        # Create document
        doc = WebisDocument(
            id=f"local-{int(time.time())}-{hash(file_name) % 1000}",
            content=file_content.decode('utf-8', errors='ignore') if isinstance(file_content, bytes) else str(file_content),
            clean_content=None,
            doc_type=doc_type,
            meta=DocumentMetadata(
                title=file.name,
                url=None,
                source_plugin="local_upload",
                custom={
                    "filename": file.name,
                    "size": len(file_content),
                    "file_type": file_type
                }
            )
        )
        
        # Set status
        doc.status = DocumentStatus.COMPLETED
        
        return doc
        
    except Exception as e:
        st.error(f"处理文件 {file.name} 时出错: {str(e)}")
        return None
