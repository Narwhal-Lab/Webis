# Webis Visualizer

📊 **NotebookLM风格的可视化界面，用于Webis AI数据管道**

## 🌟 功能特性

- **双数据源支持**：支持互联网爬取和本地上传（同一页面）
- **Pipeline可视化**：清晰呈现数据获取、清洗与结构化知识库生成
- **结构化数据展示**：JSON结构化结果与统计信息
- **AI对话分析**：Notebook风格助手，结合来源与上下文提示
- **数据导出**：支持JSON、CSV格式

## 🚀 快速开始

### 1. 安装依赖

```bash
cd src/webis_visualizer
pip install -r requirements.txt
```

### 2. 运行可视化界面

```bash
# 从项目根目录运行
streamlit run src/webis_visualizer/app.py

# 或直接运行
cd src/webis_visualizer
streamlit run app.py
```

也可以使用脚本：

```bash
bash src/webis_visualizer/run_visualizer.sh
```

### 3. 使用流程

#### 步骤1：添加数据源

**互联网爬取**：
1. 在左侧边栏输入搜索关键词
2. 设置获取数量
3. 点击"开始爬取"（搜索引擎由Agent自动选择）

**本地上传**：
1. 在左侧边栏选择文件（PDF、HTML、TXT、CSV、MD等）
2. 点击"处理文件"

#### 步骤2：运行Pipeline

1. 在文档列表中确认已添加的数据
2. 点击"运行 Pipeline"按钮
3. 等待Pipeline完成数据获取、清洗和结构化提取

#### 步骤3：查看结构化数据

1. 切换到"结构化数据"标签
2. 查看提取的数据JSON与统计指标
3. 使用导出功能下载数据

#### 步骤4：AI对话分析

1. 切换到"AI助手"标签
2. 基于结构化数据提出问题
3. 查看AI回复（右侧展示来源与上下文）

## 📁 项目结构

```
src/webis_visualizer/
├── app.py                    # 主应用入口
├── components/               # UI组件
│   ├── __init__.py
│   ├── data_source_panel.py  # 数据源管理面板
│   ├── pipeline_panel.py     # Pipeline可视化面板
│   ├── structured_data_panel.py  # 结构化数据面板
│   └── chat_panel.py         # AI对话面板
├── utils/                    # 工具函数
│   └── helpers.py
├── requirements.txt          # 依赖列表
└── README.md                 # 本文档
```

## 🔧 依赖说明

| 包名 | 版本要求 | 说明 |
|------|----------|------|
| streamlit | >=1.28.0 | 主框架 |
| streamlit-chat | >=0.1.0 | 对话组件 |
| streamlit-aggrid | >=0.3.0 | 高级表格 |
| plotly | >=5.17.0 | 数据可视化 |
| pyvis | >=0.3.0 | 网络图可视化 |
| networkx | >=3.2.0 | 图算法 |
| pandas | >=1.5.0,<2.0.0 | 数据处理 |
| openpyxl | >=3.1.0 | Excel支持 |

## 📝 使用示例

### 示例1：爬取新闻并分析

```python
# 在界面中操作
1. 关键词: "AI machine learning 2024"
2. 数量: 10
3. 运行Pipeline
4. 在AI助手提问: "分析这些新闻的主要话题"
```

### 示例2：分析本地上传文件

```python
# 在界面中操作
1. 上传PDF报告文件
2. 运行Pipeline提取结构化数据
3. 在AI助手提问: "总结这份报告的主要发现"
```

## ⚠️ 注意事项

1. **API密钥**：确保在`.env`文件中配置了必要的API密钥
2. **文件大小**：大文件可能需要较长的处理时间
3. **网络爬取**：请遵守网站的robots.txt和使用条款

## 🔮 未来计划

- [ ] 支持更多文件格式（DOCX、PPTX等）
- [ ] 增强的PDF解析（表格、图表提取）
- [ ] 多语言支持
- [ ] 项目保存和加载功能
- [ ] 团队协作功能

## 📄 许可证

本项目遵循Webis项目的Apache 2.0许可证。
