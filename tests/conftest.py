from unittest.mock import MagicMock

import pytest
from mcdreforged.api.all import PluginServerInterface


@pytest.fixture
def mock_server():
    server = MagicMock(spec=PluginServerInterface)
    # 模拟 register_command，避免报错
    server.register_command = MagicMock()
    return server

@pytest.fixture
def mock_service():
    # 模拟应用服务
    # 这里不需要引入真实的服务类，只需要一个有相应方法的 Mock 对象
    # 这样可以解耦测试
    service = MagicMock()
    return service
