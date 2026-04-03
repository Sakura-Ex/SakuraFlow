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
    service = MagicMock()
    return service
