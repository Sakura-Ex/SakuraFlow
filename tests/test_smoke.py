import os
import pytest

# 定义项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_plugin_structure():
    """
    验证插件的基本结构和导入是否正常
    """
    try:
        import sakura_flow
    except ImportError as e:
        pytest.fail(f"无法导入 sakura_flow 插件: {e}")

    # 验证必要的入口函数是否存在
    assert hasattr(sakura_flow, 'on_load'), "插件缺少 on_load 入口函数"
    assert callable(sakura_flow.on_load), "on_load 必须是可调用的函数"

def test_metadata_exists():
    """
    验证插件元数据文件是否存在
    """
    metadata_file = os.path.join(PROJECT_ROOT, 'mcdreforged.plugin.json')
    assert os.path.exists(metadata_file), "缺少 mcdreforged.plugin.json 文件"
