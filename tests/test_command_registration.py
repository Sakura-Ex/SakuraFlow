import pytest
from sakura_flow.mcdr_entry import register_mcdr_commands
from mcdreforged.api.command import Literal

def test_command_registration(mock_server, mock_controller):
    """
    测试命令注册流程是否正常，确保命令树构建没有语法错误
    """
    try:
        register_mcdr_commands(mock_server, mock_controller)
    except Exception as e:
        pytest.fail(f"命令注册失败: {e}")

    # 验证是否调用了 server.register_command
    assert mock_server.register_command.called, "未调用 server.register_command"
    
    # 获取注册的命令节点
    # call_args[0][0] 是第一个位置参数，即 node_root
    node_root = mock_server.register_command.call_args[0][0]
    
    # 验证根节点是否正确
    assert isinstance(node_root, Literal)
    
    # 由于 MCDR 的 CommandNode 内部结构可能随版本变化且不一定公开 children 属性，
    # 这里我们只验证根节点对象存在且类型正确。
    # 如果命令树构建逻辑有误（如 .then() 链式调用错误），上面的 register_mcdr_commands 通常会直接抛出异常。
