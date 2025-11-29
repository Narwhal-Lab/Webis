# Webis - 多模态数据提取框架

[English](README.md) | [中文](README_CN.md)

![Python Version](https://img.shields.io/badge/Python-3.9+-blue)  

![License](https://img.shields.io/badge/License-Open%20Source-green) 

## 概述

Webis是一条从网络数据爬取、多模态清洗到专题知识库构建的全链路高效流水线，该框架集成**文档、PDF、图片、HTML网页**等多模态数据的清洗工具，可以自动识别文件类型并快速调用不同工具，批量清洗各类文件并提供**结构化输出**。当前Webis已集成四种模态数据处理工具，其中**Webis_HTML**工具为我们独立开发的网页数据提取工具，使用 AI 技术自动识别网页上的有价值信息。Webis_HTML已作为一个独立依赖包同步上传至PyPi。

## 目录

- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [接口说明](#接口说明)
- [使用示例](#使用示例)
- [支持的文件类型](#支持的文件类型)
- [功能特性](#功能特性)
- [开发与扩展](#开发与扩展)
- [常见问题](#常见问题)
- [许可证与贡献](#许可证与贡献)

## 快速开始

### 前提条件

- Python 3.9+
- Conda环境 或 uv环境

### 环境配置

#### 方式一：自动配置脚本（推荐）

```
# 运行自动配置脚本
bash setup/conda_setup.sh
# 如果是uv环境
bash setup/uv_setup.sh
```

#### 方式二：手动配置

```
# 创建并激活Conda环境
conda create -n webis python=3.9 -y
conda activate webis

# 安装依赖包
pip install -r setup/requirements.txt
```

#### 方式三：使用 Homebrew (macOS)

```
# 安装 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python

# 验证安装
python3 --version
pip3 --version

# 安装依赖
pip install -r setup/requirements.txt
```

### 基础使用

```
# 激活环境
conda activate webis

# 处理单个文件
python process_file.py tools/data/pdf/example.pdf

# 运行完整演示
python examples/demo.py

# 运行爬虫知识库演示
python examples/crawler_demo.py "关键词" --limit 5
```

## 接口说明

### 1. 单独处理器接口

#### DocumentProcessor - 文档处理器

```
from file_processor import DocumentProcessor

processor = DocumentProcessor()

# 检查是否支持文件类型
if processor.can_process("test.docx"):
    # 提取文本
    result = processor.extract_text("test.docx")
    if result["success"]:
        print(result["text"])
    else:
        print(f"错误: {result['error']}")
```

#### PDFProcessor - PDF处理器

```
from file_processor import PDFProcessor

processor = PDFProcessor()

# 提取PDF文本
result = processor.extract_text("document.pdf")
if result["success"]:
    print(result["text"])  # 包含分页信息
```

#### ImageProcessor - 图片OCR处理器

```
from file_processor import ImageProcessor

processor = ImageProcessor()

# OCR识别图片
result = processor.extract_text("image.png")
if result["success"]:
    print(result["text"])
```

> **提示**: 第一次使用图片处理器时，会自动下载 EasyOCR 开源模型，会耗费一些时间，请耐心等待，后续使用将直接加载已下载的模型。如果下载失败，建议尝试使用科学上网工具。

#### HTMLProcessor - HTML处理器

**Webis_HTML** 是一个为 Webis 开发的独立的 HTML 网页数据提取工具，`html_processor.py`通过直接调用 `webis-html`Python 库实现。

- **安装方式**: 通过 `pip install webis-html`安装，已包含在 `requirements.txt`中
- **无需启动服务器**: `webis-html`库会自动处理 HTML 内容提取，无需启动额外的服务器

**使用示例**:

```
from file_processor import HTMLProcessor

processor = HTMLProcessor()

# 提取HTML文本
result = processor.extract_text("example.html")
if result["success"]:
    print(result["text"])
```

**API 密钥配置**（HTML处理必需）:

- **获取 API Key**: 请访问 [SiliconFlow](https://www.siliconflow.com/) 注册账号并获取 API 密钥
- **配置环境变量**: 
  ```bash
  export DEEPSEEK_API_KEY="your-siliconflow-api-key"
  # 或
  export LLM_PREDICTOR_API_KEY="your-siliconflow-api-key"
  ```
- **Conda 环境配置**（推荐）:
  ```bash
  conda env config vars set DEEPSEEK_API_KEY="your-siliconflow-api-key" -n webis
  conda activate webis  # 重新激活环境使配置生效
  ```

> **注意**: HTML 处理功能需要通过 SiliconFlow API 进行内容过滤优化，需要配置相应的 API 密钥。请从 [SiliconFlow](https://www.siliconflow.com/) 获取 API 密钥。不配置 API 密钥则无法使用 HTML 处理功能。

### 2. 统一处理器接口

#### UnifiedFileProcessor - 统一处理器

```
from file_processor import UnifiedFileProcessor

processor = UnifiedFileProcessor()

# 自动判断文件类型并处理
result = processor.extract_text("any_file.pdf")
print(f"文件类型: {result['file_type']}")
print(f"文本内容: {result['text']}")
```

### 3. 便捷函数接口

#### 单文件处理

```
from file_processor import extract_text_from_file

# 最简单的使用方式
result = extract_text_from_file("file.pdf")
if result["success"]:
    print(f"文件类型: {result['file_type']}")
    print(f"文本长度: {len(result['text'])}")
    print(result["text"])
```

#### 批量文件处理

```
from file_processor import batch_extract_text

# 批量处理多个文件
file_paths = ["doc1.pdf", "doc2.docx", "image1.png"]
results = batch_extract_text(file_paths)

for file_path, result in results.items():
    if result["success"]:
        print(f"{file_path}: {len(result['text'])} 字符")
    else:
        print(f"{file_path}: {result['error']}")
```

## 使用示例

### 命令行使用

```
# 处理单个文件
python3 file_processor.py document.pdf

# 查看支持的文件类型
python3 file_processor.py
```

### Python脚本使用

```
#!/usr/bin/env python3
from file_processor import extract_text_from_file

def main():
    # 处理不同类型的文件
    files = [
        "pdf/示例.pdf",
        "Doc/demo.pdf", 
        "Pic/demo.pdf"
    ]
    
    for file_path in files:
        print(f"\n处理文件: {file_path}")
        result = extract_text_from_file(file_path)
        
        if result["success"]:
            print(f"文件类型: {result['file_type']}")
            print(f"文本长度: {len(result['text'])} 字符")
            print("文本预览:")
            print(result["text"][:300] + "...")
        else:
            print(f"处理失败: {result['error']}")

if __name__ == "__main__":
    main()
```

### 代码中集成使用

```
# 添加工具路径
import sys
sys.path.append('tools')

from file_processor import extract_text_from_file

# 处理文件
result = extract_text_from_file('your_file.pdf')
if result['success']:
    print(result['text'])
```

### 爬虫知识库演示

`crawler_demo.py` 是一个完整的网络爬虫示例，可以自动搜索、下载并处理网络上的文档材料，生成知识库。

**功能特点**：
- 使用 DuckDuckGo 搜索引擎自动搜索相关材料（PDF、DOC、DOCX、PPT、PPTX、HTML等）
- 自动下载找到的文件到本地
- 使用 Webis UnifiedFileProcessor 自动处理下载的文件
- 生成结构化的知识库 JSON 文件

**使用方法**：

```
# 基本用法：搜索关键词并下载处理前5个结果
python examples/crawler_demo.py "Python教程" --limit 5

# 搜索更多结果
python examples/crawler_demo.py "机器学习" --limit 10

# 指定文件类型搜索（在关键词中包含 filetype:）
python examples/crawler_demo.py "深度学习 filetype:pdf" --limit 3
```

**输出结果**：
- 下载的文件保存在 `examples/outputs/downloaded_materials/` 目录
- 知识库文件保存在 `examples/outputs/knowledge_base.json`
- 知识库包含每个文件的处理结果、提取的文本内容、文件类型等信息

**知识库格式**：

```json
[
  {
    "source_file": "example.pdf",
    "file_type": "pdf",
    "processed_time": "2025-11-27 14:00:00",
    "content": "提取的文本内容...",
    "status": "success",
    "error": ""
  }
]
```

**注意事项**：
- 需要配置 `DEEPSEEK_API_KEY` 环境变量，请从 [SiliconFlow](https://www.siliconflow.com/) 获取 API 密钥（用于 HTML 处理优化）
- 搜索功能依赖网络连接，某些网站可能无法访问
- 下载的文件会保存在 `examples/outputs/downloaded_materials/` 目录
- 建议使用 `--limit` 参数限制结果数量，避免下载过多文件

## 支持的文件类型

###  可识别文件

| 类型 | 扩展名                                   | 处理工具   | 说明                                   |
| :--- | :--------------------------------------- | :--------- | :------------------------------------- |
| 文档 | `.txt`, `.md`, `.docx`                   | LangChain  | 直接文本提取                           |
| PDF  | `.pdf`                                   | PyPDF      | 按页提取，保留页码信息                 |
| 图片 | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff` | EasyOCR    | 光学字符识别                           |
| HTML | `.html`                                  | Webis_HTML | 使用自主设计的微调模型提取清洗网页数据 |

###  返回结果格式

所有处理器都返回统一的结果格式：

```
{
    "success": bool,        # 是否处理成功
    "text": str,           # 提取的文本内容
    "error": str,          # 错误信息 (失败时)
    "file_type": str       # 文件类型 (仅统一接口)
}
```

## 功能特性

- **自动文件类型识别**: 根据扩展名自动选择合适的处理工具
- **统一接口**: 提供一致的API接口处理不同类型文件
- **批量处理**: 支持批量处理多个文件
- **错误处理**: 完善的错误处理和日志记录
- **中文支持**: 完全支持中文文档和OCR
- **可扩展**: 易于添加新的文件类型支持
- **模块化设计**: 各处理器独立，便于维护和扩展
- **结构化输出**: 所有处理器返回统一的结果格式

## 开发与扩展

### 如何添加新的文件处理类型

1. 在 `tools/processors/`中创建新的处理器类（继承 `BaseFileProcessor`）
2. 在 `tools/processors/__init__.py`中导入并注册新处理器
3. 在 `tools/file_processor.py`的 `UnifiedFileProcessor`中注册新类型
4. 更新支持的扩展名列表和文档

### 性能优化建议

1. **批量处理**: 使用 `batch_extract_text()`处理多文件
2. **延迟加载**: 图片处理器采用延迟加载，避免不必要的模型初始化
3. **缓存结果**: 对于重复处理的文件，建议缓存结果
4. **并行处理**: 对于大量文件，可考虑多进程并行处理

## 常见问题

### Q: 安装依赖时出现错误？

A: 确保使用正确的Python版本 (3.8+)，可能需要使用 `pip3`而不是 `pip`

### Q: EasyOCR 第一次运行很慢？

A: EasyOCR 首次使用会下载模型文件，请耐心等待

### Q: 图片识别准确率不高？

A: 可以尝试：

- 提高图片分辨率
- 确保文字清晰
- 调整置信度阈值 (代码中的 confidence > 0.5)

### Q: PDF 无法提取文本？

A: 可能是扫描版PDF，建议先转换为图片再用OCR处理

## 许可证与贡献

### 许可证

本项目采用开源许可证，具体许可证信息请查看项目根目录下的 LICENSE 文件。

### 贡献

欢迎贡献！请在 GitHub上提交问题或拉取请求。如需支持，请通过 GitHub Issues 联系我们。