import os

from mcdreforged.api.all import PluginServerInterface

from .application import TodoApplication
from .constants import COMMAND_PREFIX
from .manager import TodoManager
from .mcdr_entry import register_mcdr_commands

manager = None
service = None

def on_load(server: PluginServerInterface, _prev):
    global manager, service
    # 初始化管理器
    # 数据存放到 MCDR 根目录下的 sf_tasks 目录
    data_dir = os.path.join(os.getcwd(), 'sf_tasks')
    db_path = os.path.join(data_dir, 'tasks.db')
    legacy_json_path = os.path.join(data_dir, 'tasks.json')
    manager = TodoManager(db_path, legacy_json_path=legacy_json_path)
    if manager.startup_warning:
        server.logger.warning(manager.startup_warning)

    # 初始化后端服务
    service = TodoApplication(manager)

    # 注册指令帮助条目
    server.register_help_message(COMMAND_PREFIX, "任务管理")

    # 注册 MCDR 指令
    register_mcdr_commands(server, service)
