from mcdreforged.api.all import *
import os

from .manager import TodoManager
from .controller import TodoController
from .mcdr_entry import register_mcdr_commands
from .constants import COMMAND_PREFIX

manager = None
controller = None

def on_load(server: PluginServerInterface, _prev):
    global manager, controller
    # 初始化管理器
    # 数据存放到 MCDR 根目录下的 sf_tasks 目录
    data_path = os.path.join(os.getcwd(), 'sf_tasks', 'tasks.json')
    manager = TodoManager(data_path)
    
    # 初始化控制器
    controller = TodoController(manager)

    # 注册指令帮助条目
    server.register_help_message(COMMAND_PREFIX, "任务管理")

    # 注册 MCDR 指令
    register_mcdr_commands(server, controller)
