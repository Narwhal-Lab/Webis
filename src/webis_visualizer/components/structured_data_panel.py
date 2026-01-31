"""
Structured Data Panel Component - Displays and manages structured data
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List, Optional
from io import BytesIO
try:
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

def render_structured_data_panel(
    structured_result: Optional[Dict[str, Any]],
    documents: List[Any]
):
    """
    Render the structured data display panel
    
    Args:
        structured_result: Current structured data result
        documents: List of source documents
    """
    st.header("💾 结构化数据")
    
    if not structured_result:
        st.info("📝 暂无结构化数据，请运行Pipeline处理文档")
        return
    
    # Extract data from result
    data = structured_result.get("data", [])
    stats = structured_result.get("stats", {})
    
    # Data overview
    render_data_overview(data, stats)
    
    # Data display
    render_data_display(data)
    
    # Data export
    render_data_export(data)


def render_data_overview(data: Any, stats: Dict[str, Any]):
    """Render data overview section"""
    st.subheader("📊 数据概览")
    
    # Determine data structure
    if isinstance(data, list):
        item_count = len(data)
        if data and isinstance(data[0], dict):
            field_count = len(data[0].keys())
            fields = list(data[0].keys())
        elif data:
            field_count = 1
            fields = ["value"]
        else:
            field_count = 0
            fields = []
    elif isinstance(data, dict):
        item_count = 1
        field_count = len(data.keys())
        fields = list(data.keys())
    else:
        item_count = 1
        field_count = 1
        fields = ["data"]
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    col1.metric("数据项数", item_count)
    col2.metric("字段数", field_count)
    col3.metric("文档来源", stats.get("accepted_count", 0))
    
    # Display field names
    if fields:
        st.write("**字段列表:**")
        st.write(", ".join([f"`{f}`" for f in fields[:10]]))
        if len(fields) > 10:
            st.caption(f"还有 {len(fields) - 10} 个字段...")


def render_data_display(data: Any):
    """Render data display section with multiple view options"""
    st.subheader("👀 数据视图")
    
    view_options = ["表格视图", "JSON视图", "原始数据"]
    selected_view = st.radio("选择视图", view_options, horizontal=True)
    
    if selected_view == "表格视图":
        render_table_view(data)
    elif selected_view == "JSON视图":
        render_json_view(data)
    else:
        render_raw_view(data)


def render_table_view(data: Any):
    """Render table view of the data"""
    try:
        # Convert to DataFrame
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                df = pd.DataFrame(data)
            elif data:
                df = pd.DataFrame([{"value": d} for d in data])
            else:
                df = pd.DataFrame()
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame([{"value": str(data)}])
        
        if not df.empty:
            # Display DataFrame with basic styling
            st.dataframe(df, use_container_width=True, height=400)
            
            # Column selection for detailed view
            if len(df.columns) > 1:
                selected_col = st.selectbox("选择字段查看详情", df.columns)
                
                if pd.api.types.is_numeric_dtype(df[selected_col]):
                    # Show statistics for numeric columns
                    st.write(f"**{selected_col} 统计:**")
                    st.write(df[selected_col].describe())
                    
                    # Simple chart
                    st.line_chart(df[selected_col])
        else:
            st.warning("⚠️ 数据为空或无法转换为表格")
            
    except Exception as e:
        st.error(f"❌ 表格渲染失败: {str(e)}")


def render_json_view(data: Any):
    """Render JSON view of the data"""
    try:
        if isinstance(data, (list, dict)):
            st.json(data, expanded=False)
        else:
            st.json({"data": data})
    except Exception as e:
        st.error(f"❌ JSON渲染失败: {str(e)}")


def render_raw_view(data: Any):
    """Render raw text view of the data"""
    try:
        if isinstance(data, (list, dict)):
            raw_text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            raw_text = str(data)
        
        st.text_area("原始数据", raw_text, height=400)
    except Exception as e:
        st.error(f"❌ 原始数据渲染失败: {str(e)}")


def render_data_export(data: Any):
    """Render data export section"""
    st.subheader("⬇️ 导出数据")
    
    col1, col2, col3 = st.columns(3)
    
    # JSON Export
    with col1:
        json_data = json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (list, dict)) else json.dumps({"data": data})
        st.download_button(
            label="📦 导出 JSON",
            data=json_data,
            file_name="structured_data.json",
            mime="application/json",
            use_container_width=True
        )
    
    # CSV Export
    with col2:
        try:
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([{"value": d} for d in data])
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame([{"value": str(data)}])
            
            csv_data = df.to_csv(index=False, encoding="utf-8")
            st.download_button(
                label="📊 导出 CSV",
                data=csv_data,
                file_name="structured_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.button("📊 导出 CSV", disabled=True, use_container_width=True)
            st.caption("CSV导出不可用")
    
    # Markdown Export
    with col3:
        try:
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([{"value": d} for d in data])
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame([{"value": str(data)}])
            
            md_data = df.to_markdown(index=False)
            st.download_button(
                label="📄 导出 Markdown",
                data=md_data,
                file_name="structured_data.md",
                mime="text/markdown",
                use_container_width=True
            )
        except Exception as e:
            st.button("📄 导出 Markdown", disabled=True, use_container_width=True)
            st.caption("Markdown导出不可用")
    
    # Excel Export (optional)
    with st.expander("高级导出选项"):
        st.write("### 高级导出")
        st.info("💡 Excel导出功能需要安装 openpyxl 库")
        st.code("pip install openpyxl", language="bash")