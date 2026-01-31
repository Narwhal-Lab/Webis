"""
Pipeline Panel Component - Visualizes and manages the data processing pipeline
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from webis.core.schema import WebisDocument
from webis.core.intelligent_pipeline import IntelligentPipeline
from webis.core.schema import PipelineContext
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# Pipeline step definitions
PIPELINE_STEPS = [
    {
        "name": "fetch",
        "label": "📥 数据获取",
        "description": "从互联网或本地获取原始数据",
        "color": "#4CAF50",
        "icon": "download"
    },
    {
        "name": "clean",
        "label": "🧹 数据清洗",
        "description": "清理HTML标签，提取文本内容",
        "color": "#2196F3",
        "icon": "cleaning_services"
    },
    {
        "name": "extract",
        "label": "🤖 结构提取",
        "description": "使用LLM提取结构化信息",
        "color": "#FF9800",
        "icon": "auto_awesome"
    },
    {
        "name": "store",
        "label": "💾 数据存储",
        "description": "保存到数据库和向量存储",
        "color": "#9C27B0",
        "icon": "storage"
    }
]


def render_pipeline_panel(
    documents: List[WebisDocument],
    structured_result: Optional[Dict[str, Any]],
    pipeline_status: Dict[str, Any],
    on_run_pipeline: callable
):
    """
    Render the pipeline visualization and management panel
    
    Args:
        documents: List of current documents
        structured_result: Current structured data result
        pipeline_status: Current pipeline status dictionary
        on_run_pipeline: Callback function to run the pipeline
    """
    st.header("🔧 数据处理 Pipeline")
    
    # Pipeline visualization
    render_pipeline_flowchart(pipeline_status)
    
    # Pipeline progress
    render_pipeline_progress(pipeline_status)
    
    # Pipeline controls
    render_pipeline_controls(documents, pipeline_status, on_run_pipeline)
    
    # Document statistics
    if documents:
        render_document_statistics(documents, pipeline_status)


def render_pipeline_flowchart(pipeline_status: Dict[str, Any]):
    """Render the pipeline flowchart visualization"""
    st.subheader("📊 Pipeline 流程图")
    
    # Create network graph
    G = nx.DiGraph()
    
    # Add nodes for each step
    for step in PIPELINE_STEPS:
        step_name = step["name"]
        status = pipeline_status.get(step_name, "idle")
        
        # Determine node color based on status
        if status == "completed":
            color = step["color"]
        elif status == "in_progress":
            color = "#FFC107"  # Amber for in progress
        elif status == "failed":
            color = "#F44336"  # Red for failed
        else:
            color = "#E0E0E0"  # Gray for idle
        
        G.add_node(
            step_name,
            label=step["label"],
            title=step["description"],
            color=color,
            shape="box"
        )
    
    # Add edges between steps
    for i in range(len(PIPELINE_STEPS) - 1):
        G.add_edge(PIPELINE_STEPS[i]["name"], PIPELINE_STEPS[i+1]["name"])
    
    # Create pyvis network
    net = Network(height="300px", directed=True, bgcolor="#ffffff", font_color="#333333")
    net.from_nx(G)
    
    # Customize physics
    net.set_options("""
    var options = {
        "nodes": {
            "font": {
                "size": 16,
                "face": "arial"
            },
            "borderWidth": 2,
            "shadow": true
        },
        "edges": {
            "color": {
                "inherit": true
            },
            "smooth": {
                "type": "continuous"
            }
        },
        "physics": {
            "enabled": false
        }
    }
    """)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
        net.save_graph(tmp.name)
        
        # Read and display
        with open(tmp.name, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Display in Streamlit
        st.components.v1.html(html_content, height=320)
        
        # Clean up
        os.unlink(tmp.name)
    
    # Legend
    st.markdown("""
    <div style="display: flex; gap: 20px; justify-content: center; margin-top: 10px;">
        <span style="display: flex; align-items: center;">
            <span style="width: 12px; height: 12px; background-color: #4CAF50; border-radius: 50%; margin-right: 5px;"></span>
            已完成
        </span>
        <span style="display: flex; align-items: center;">
            <span style="width: 12px; height: 12px; background-color: #FFC107; border-radius: 50%; margin-right: 5px;"></span>
            进行中
        </span>
        <span style="display: flex; align-items: center;">
            <span style="width: 12px; height: 12px; background-color: #E0E0E0; border-radius: 50%; margin-right: 5px;"></span>
            待执行
        </span>
    </div>
    """, unsafe_allow_html=True)


def render_pipeline_progress(pipeline_status: Dict[str, Any]):
    """Render pipeline progress bar"""
    st.subheader("📈 进度")
    
    progress = pipeline_status.get("progress", 0)
    progress_bar = st.progress(progress)
    st.caption(f"已完成 {progress}%")


def render_pipeline_controls(
    documents: List[WebisDocument],
    pipeline_status: Dict[str, Any],
    on_run_pipeline: callable
):
    """Render pipeline control buttons"""
    st.subheader("🎮 管道控制")
    
    col1, col2 = st.columns(2)
    
    with col1:
        run_button = st.button(
            "▶️ 运行 Pipeline",
            disabled=not documents or pipeline_status.get("progress", 0) == 100,
            use_container_width=True
        )
        
        if run_button:
            on_run_pipeline()
    
    with col2:
        reset_button = st.button(
            "🔄 重置",
            disabled=pipeline_status.get("progress", 0) == 0,
            use_container_width=True
        )
        
        if reset_button:
            if "on_reset" in st.session_state:
                st.session_state.on_reset()
            st.experimental_rerun()
    
    # Task description
    st.text_input(
        "Pipeline任务描述",
        value=st.session_state.get("pipeline_task", "提取结构化数据"),
        key="pipeline_task_input",
        disabled=pipeline_status.get("progress", 0) > 0
    )


def render_document_statistics(
    documents: List[WebisDocument],
    pipeline_status: Dict[str, Any]
):
    """Render document and pipeline statistics"""
    st.subheader("📊 统计信息")
    
    # Document statistics
    st.markdown("#### 文档统计")
    
    # Count by type
    type_counts = {}
    for doc in documents:
        doc_type = getattr(doc.doc_type, 'value', str(doc.doc_type))
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
    
    # Count by status
    status_counts = {}
    for doc in documents:
        status = getattr(doc.status, 'value', str(doc.status))
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    col1.metric("文档总数", len(documents))
    col2.metric("已处理", status_counts.get("completed", 0))
    col3.metric("待处理", status_counts.get("pending", 0))
    
    # Display type distribution
    if type_counts:
        st.write("类型分布:")
        for doc_type, count in type_counts.items():
            st.write(f"- {doc_type}: {count}")
    
    # Pipeline statistics (if available)
    if pipeline_status.get("completed"):
        st.markdown("#### Pipeline 统计")
        
        stats = pipeline_status.get("stats", {})
        
        col1, col2, col3 = st.columns(3)
        col1.metric("接受文档", stats.get("accepted_count", 0))
        col2.metric("拒绝文档", stats.get("rejected_count", 0))
        col3.metric("迭代次数", stats.get("iterations", 0))


def create_default_pipeline_status() -> Dict[str, Any]:
    """Create default pipeline status dictionary"""
    return {
        "fetch": "idle",
        "clean": "idle",
        "extract": "idle",
        "store": "idle",
        "progress": 0,
        "completed": False
    }