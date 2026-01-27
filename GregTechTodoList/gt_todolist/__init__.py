from mcdreforged.api.all import *
from mcdreforged.api.command import SimpleCommandBuilder, Text, GreedyText
import os

from .manager import TodoManager
from .commands import register_commands

manager = None


def on_load(server: PluginServerInterface, _prev):
    global manager
    # 初始化管理器
    data_path = os.path.join(server.get_data_folder(), 'tasks.json')
    manager = TodoManager(data_path)

    # 注册指令帮助条目
    server.register_help_message("!!todo", "格雷科技任务管理")

    # 构建指令系统
    builder = SimpleCommandBuilder()

    # 定义参数节点
    builder.arg("id", Text)
    builder.arg("title", GreedyText)
    builder.arg("prop", Text)
    builder.arg("list_prop", Text)
    builder.arg("value", GreedyText)
    builder.arg("content", GreedyText)

    # 注册回调逻辑 (传入 manager 实例)
    register_commands(builder, manager, server)

    # 注册到服务器
    builder.register(server)
