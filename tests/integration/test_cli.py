"""
CLI集成测试

测试 webis run 命令是否正确集成了 IntelligentPipeline
"""

import sys
import logging
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from webis.cli import cmd_run

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_cli():
    print("="*70)
    print("测试 CLI 集成 (IntelligentPipeline)")
    print("="*70)
    
    # 模拟运行 "webis run"
    # 使用一个小任务测试
    task = "Python 3.12 新特性"
    limit = 3
    
    try:
        cmd_run(task, limit)
        print("\n✅ CLI 运行成功!")
    except Exception as e:
        print(f"\n❌ CLI 运行失败: {e}")
        raise e

if __name__ == "__main__":
    test_cli()
