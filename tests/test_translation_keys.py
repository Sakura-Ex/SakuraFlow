import os
import json
import re
import pytest

# 定义项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_FILE = os.path.join(PROJECT_ROOT, 'lang', 'zh_cn.json')
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'sakura_flow')

def get_defined_keys():
    """读取语言文件并返回所有定义的键"""
    if not os.path.exists(LANG_FILE):
        pytest.fail(f"语言文件不存在: {LANG_FILE}")
    
    with open(LANG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(data.keys())

def scan_used_keys():
    """扫描源代码中使用的翻译键"""
    used_keys = set()
    # 匹配形如 'sakuraflow.xxx' 或 "sakuraflow.xxx" 的字符串
    # 假设翻译键都以 sakuraflow. 开头
    pattern = re.compile(r'["\'](sakuraflow\.[a-zA-Z0-9_.]+)["\']')
    
    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    for match in matches:
                        used_keys.add(match)
    return used_keys

def test_translation_keys_exist():
    """测试代码中引用的所有翻译键是否都在语言文件中定义"""
    defined_keys = get_defined_keys()
    used_keys = scan_used_keys()
    
    missing_keys = used_keys - defined_keys
    
    # 过滤掉一些可能的动态键或误报
    # 如果有已知的动态生成的键前缀，可以在这里过滤
    # 例如: sakuraflow.msg.{variable} 这种无法静态检测，但如果代码里写了 'sakuraflow.msg.' 可能会被匹配到
    # 这里假设代码里写的都是完整的键
    
    if missing_keys:
        pytest.fail(f"发现 {len(missing_keys)} 个未定义的翻译键:\n" + "\n".join(missing_keys))

def test_unused_keys():
    """(可选) 测试是否有未使用的翻译键"""
    # 这个测试通常作为警告而不是错误，因为有些键可能只在动态生成时使用
    defined_keys = get_defined_keys()
    used_keys = scan_used_keys()
    
    unused = defined_keys - used_keys
    # 这里我们只打印警告，不让测试失败
    if unused:
        print(f"\n警告: 发现 {len(unused)} 个可能未使用的翻译键 (可能是动态调用):")
        # 只打印前10个
        for k in list(unused)[:10]:
            print(f"  - {k}")
        if len(unused) > 10:
            print("  ...")
