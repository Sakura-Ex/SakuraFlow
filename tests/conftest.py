import pytest
from unittest.mock import MagicMock
from mcdreforged.api.all import PluginServerInterface

@pytest.fixture
def mock_server():
    server = MagicMock(spec=PluginServerInterface)
    # 模拟 register_command，避免报错
    server.register_command = MagicMock()
    return server

@pytest.fixture
def mock_controller():
    # 模拟 TodoController
    # 这里不需要引入真实的 Controller 类，只需要一个有相应方法的 Mock 对象
    # 这样可以解耦测试
    controller = MagicMock()
    return controller
