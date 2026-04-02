import os

from mcdreforged.api.all import PluginServerInterface

from .application import TodoApplication
from .config_loader import apply_custom_field_definitions
from .constants import COMMAND_PREFIX
from .manager import TodoManager
from .mcdr_entry import register_mcdr_commands

manager = None
service = None


def on_load(server: PluginServerInterface, _prev):
    """Initialize the plugin, load custom fields, and register commands.

    Args:
        server: MCDR plugin server interface.
        _prev: Previous plugin state provided by MCDR.
    """
    global manager, service
    # 初始化管理器
    # 数据存放到 MCDR 根目录下的 sf_tasks 目录
    data_dir = os.path.join(os.getcwd(), 'sf_tasks')
    db_path = os.path.join(data_dir, 'tasks.db')
    legacy_json_path = os.path.join(data_dir, 'tasks.json')
    config_path = os.path.join(os.getcwd(), 'config', 'sakura_flow', 'custom_fields.yml')
    manager = TodoManager(db_path, legacy_json_path=legacy_json_path)
    if manager.startup_warning:
        server.logger.warning(manager.startup_warning)

    for warning in apply_custom_field_definitions(manager, config_path):
        server.logger.warning(f"[sakura_flow config] {warning}")

    # 初始化后端服务
    service = TodoApplication(manager)

    # 注册指令帮助条目
    server.register_help_message(COMMAND_PREFIX, "任务管理")

    # 注册 MCDR 指令
    register_mcdr_commands(server, service)
