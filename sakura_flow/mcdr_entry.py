import warnings

from mcdreforged.api.all import PluginServerInterface, CommandSource, CommandContext, RText, RColor, RStyle
from mcdreforged.api.command import Literal, Integer, GreedyText, Text

from .application import TodoApplication
from .constants import COMMAND_PREFIX, GT_TIERS, PROP_ALIASES, LIST_PROP_ALIASES
from .enums import Status, Tier, Priority
from .interface import UI
from .utils import Utils


def _parse_search_criteria(query_raw: str) -> dict:
    """Parse search query using shared alias dictionaries from constants."""
    criteria = {}
    list_field_map = {
        "collaborators": "collaborator",
        "labels": "label",
    }

    for part in query_raw.split():
        if '=' in part:
            key, val = part.split('=', 1)
            key = key.lower()

            scalar_prop = PROP_ALIASES.get(key)
            if scalar_prop in {"title", "status", "tier", "priority"}:
                criteria[scalar_prop] = val
                continue

            list_prop = LIST_PROP_ALIASES.get(key)
            mapped_list = list_field_map.get(list_prop)
            if mapped_list:
                criteria[mapped_list] = val
                continue

            # creator is search-only and not part of set/append aliases.
            if key == 'creator':
                criteria['creator'] = val
                continue

            # Keep unknown keys for dynamic custom-field search.
            criteria[key] = val
        else:
            criteria['title'] = part

    return criteria


def register_mcdr_commands(server: PluginServerInterface, service: TodoApplication):
    # --- Command Callbacks ---

    def on_welcome(source: CommandSource):
        source.reply(UI.render_welcome(server))

    def on_help(source: CommandSource):
        source.reply(UI.render_help(server))

    def on_list(source: CommandSource, context: CommandContext):
        page = context.get("page", 1)
        # 使用 search_tasks 获取非 Done 任务
        tasks = service.search_tasks({'status': '!Done'})
        UI.render_paged_list(source, tasks, service.get_tasks(include_done=True), 'sakuraflow.list.header',
                             'sakuraflow.list.empty',
                             input_page=page, cmd_prefix="list")

    def on_archive(source: CommandSource, context: CommandContext):
        page = context.get("page", 1)
        # 使用 search_tasks 获取 Done 任务
        tasks = service.search_tasks({'status': 'Done'})
        UI.render_paged_list(source, tasks, service.get_tasks(include_done=True), 'sakuraflow.archive.header',
                             'sakuraflow.archive.empty',
                             input_page=page, cmd_prefix="archive")

    def on_search(source: CommandSource, context: CommandContext):
        query_raw = context['query']
        player_key = source.player if source.is_player else "Console"
        
        # 尝试判断是否为纯数字（翻页）
        is_page = False
        page = 1
        if query_raw.isdigit():
            is_page = True
            page = int(query_raw)
        
        results = None
        
        if is_page:
            # 尝试从缓存获取
            results = service.get_cached_search(player_key)
            if results is None:
                # 缓存过期或不存在，提示用户重新搜索
                source.reply(Utils.error_msg(server, 'sakuraflow.search.cache_expired'))
                return
        else:
            # 执行新搜索
            criteria = _parse_search_criteria(query_raw)

            # 执行搜索并缓存
            results = service.search_tasks(criteria, cache_key=player_key)
            page = 1 # 新搜索重置为第一页

        # 渲染搜索结果
        UI.render_paged_list(source, results, service.get_tasks(include_done=True), 'sakuraflow.search.header',
                             'sakuraflow.search.empty',
                             input_page=page, cmd_prefix="search")


    def on_add(source: CommandSource, context: CommandContext):
        creator = source.player if source.is_player else "Console"
        tid = service.add_task(context['title'], creator)
        tid_text = RText(f"#{tid}", color=RColor.green, styles=RStyle.bold)
        source.reply(Utils.info_msg(server, 'sakuraflow.msg.add_success', tid_text))

    def on_info(source: CommandSource, context: CommandContext):
        tid = str(context['id'])
        task = service.get_task(tid)
        if not task:
            source.reply(Utils.error_msg(server, 'sakuraflow.msg.not_found'))
            return
        source.reply(UI.render_task_info(tid, task, service.get_tasks(include_done=True), server))

    def on_set(source: CommandSource, context: CommandContext):
        editor = source.player if source.is_player else "Console"
        success, val, err = service.set_property(str(context['id']), context['prop'], context['value'], editor)
        
        if not success:
            if err == 'sakuraflow.msg.invalid_tier':
                tier_list = Utils.list_to_rtext([Tier.get_rtext(t.value) for t in Tier])
                source.reply(Utils.error_msg(server, err, len(GT_TIERS) - 1, tier_list))
            elif err == 'sakuraflow.msg.invalid_priority':
                prio_list = Utils.list_to_rtext([Priority.get_rtext(p.value) for p in Priority])
                source.reply(Utils.error_msg(server, err, prio_list))
            elif err == 'sakuraflow.msg.invalid_status':
                status_list = Utils.list_to_rtext([Status.get_rtext(s.value) for s in Status])
                source.reply(Utils.error_msg(server, err, status_list))
            else:
                source.reply(Utils.error_msg(server, err or 'sakuraflow.msg.unknown_error', context.get('prop')))
            return

        # 成功后的 UI 反馈
        # 需要重新获取 real_prop 对应的显示文本，这里稍微有点 hack，因为服务层已经处理了逻辑
        # 简单起见，我们直接用 context['prop'] 作为显示，或者让服务层返回 real_prop
        # 为了更好的体验，这里简单处理：
        rval = RText(val)
        # 尝试美化显示
        if Tier.validate(val): rval = Tier.get_rtext(val)
        elif Priority.validate(val): rval = Priority.get_rtext(val, server)
        elif Status.validate(val): rval = Status.get_rtext(val, server)
        
        source.reply(Utils.info_msg(server, 'sakuraflow.msg.set_success', context['id'], context['prop'], rval))

    def on_append(source: CommandSource, context: CommandContext):
        editor = source.player if source.is_player else "Console"
        success, err, error_detail = service.append_list_property(
            str(context['id']),
            context['list_prop'],
            str(context['value']),
            editor,
        )
        
        if not success:
            if err == 'sakuraflow.msg.dep_not_found':
                source.reply(Utils.error_msg(server, err, context['value']))
            elif err == 'sakuraflow.msg.self_dependency':
                source.reply(Utils.error_msg(server, err, context['id']))
            elif err == 'sakuraflow.msg.circular_dependency':
                source.reply(Utils.error_msg(server, err, error_detail or context['value']))
            else:
                source.reply(Utils.error_msg(server, err or 'sakuraflow.msg.unknown_error', context['list_prop']))
            return
            
        source.reply(Utils.info_msg(server, 'sakuraflow.msg.append_success', context['id'], context['list_prop'], context['value']))

    def on_remove(source: CommandSource, context: CommandContext):
        editor = source.player if source.is_player else "Console"
        success, err = service.remove_list_property(str(context['id']), context['list_prop'], str(context['value']),
                                                    editor)
        
        if not success:
             source.reply(Utils.error_msg(server, 'sakuraflow.msg.remove_failed', context['value']))
             return
             
        source.reply(Utils.info_msg(server, 'sakuraflow.msg.remove_success', context['id'], context['list_prop'], context['value']))

    def on_note(source: CommandSource, context: CommandContext):
        author = source.player if source.is_player else "Console"
        if service.add_note(str(context['id']), context['content'], author):
            source.reply(Utils.info_msg(server, 'sakuraflow.msg.note_success', context['id']))

    def on_status_change(source: CommandSource, context: CommandContext, status: Status, msg_key: str):
        editor = source.player if source.is_player else "Console"
        if service.update_status(str(context['id']), status, editor):
            source.reply(Utils.info_msg(server, msg_key, context['id']))

    def on_default_tier(source: CommandSource, context: CommandContext):
        warnings.warn(
            "!!todo default_tier is deprecated; use field-definition defaults.",
            DeprecationWarning,
            stacklevel=2,
        )
        if service.set_default_tier(context['tier']):
             source.reply(Utils.info_msg(server, 'sakuraflow.msg.default_tier_success', context['tier']))
        else:
             tier_list = Utils.list_to_rtext([Tier.get_rtext(t.value) for t in Tier])
             source.reply(Utils.error_msg(server, 'sakuraflow.msg.invalid_tier', len(GT_TIERS) - 1, tier_list))


    # --- Command Tree Definition ---
    
    # Nodes
    node_root = Literal(COMMAND_PREFIX).runs(on_welcome)
    
    node_help = Literal('help').runs(on_help)
    
    node_list = Literal('list').runs(on_list).then(Integer('page').runs(on_list))
    node_list_alias = Literal('l').runs(on_list).then(Integer('page').runs(on_list))
    
    node_archive = Literal('archive').runs(on_archive).then(Integer('page').runs(on_archive))
    node_archive_alias = Literal('ar').runs(on_archive).then(Integer('page').runs(on_archive))
    
    node_search = Literal('search').then(GreedyText('query').runs(on_search))
    node_search_alias = Literal('find').then(GreedyText('query').runs(on_search))

    node_add = Literal('add').then(GreedyText('title').runs(on_add))
    node_add_alias = Literal('a').then(GreedyText('title').runs(on_add))
    
    node_info = Literal('info').then(Text('id').runs(on_info))
    node_info_alias = Literal('i').then(Text('id').runs(on_info))
    
    node_set = Literal('set').then(
        Text('id').then(
            Text('prop').then(
                GreedyText('value').runs(on_set)
            )
        )
    )
    node_set_alias = Literal('s').then(Text('id').then(Text('prop').then(GreedyText('value').runs(on_set))))

    node_append = Literal('append').then(Text('id').then(Text('list_prop').then(GreedyText('value').runs(on_append))))
    node_append_alias = Literal('ap').then(Text('id').then(Text('list_prop').then(GreedyText('value').runs(on_append))))

    node_remove = Literal('remove').then(Text('id').then(Text('list_prop').then(GreedyText('value').runs(on_remove))))
    node_remove_alias = Literal('rm').then(Text('id').then(Text('list_prop').then(GreedyText('value').runs(on_remove))))

    node_note = Literal('note').then(Text('id').then(GreedyText('content').runs(on_note)))
    node_note_alias = Literal('n').then(Text('id').then(GreedyText('content').runs(on_note)))

    node_complete = Literal('complete').then(Text('id').runs(lambda s, c: on_status_change(s, c, Status.DONE, 'sakuraflow.msg.complete_success')))
    node_pause = Literal('pause').then(Text('id').runs(lambda s, c: on_status_change(s, c, Status.ON_HOLD, 'sakuraflow.msg.pause_success')))
    node_resume = Literal('resume').then(Text('id').runs(lambda s, c: on_status_change(s, c, Status.IN_PROGRESS, 'sakuraflow.msg.resume_success')))
    node_restore = Literal('restore').then(Text('id').runs(lambda s, c: on_status_change(s, c, Status.IN_PROGRESS, 'sakuraflow.msg.restore_success')))

    node_default_tier = Literal('default_tier').then(Text('tier').runs(on_default_tier))

    # Assembly
    node_root.then(node_help)
    node_root.then(node_list).then(node_list_alias)
    node_root.then(node_archive).then(node_archive_alias)
    node_root.then(node_search).then(node_search_alias)
    node_root.then(node_add).then(node_add_alias)
    node_root.then(node_info).then(node_info_alias)
    node_root.then(node_set).then(node_set_alias)
    node_root.then(node_append).then(node_append_alias)
    node_root.then(node_remove).then(node_remove_alias)
    node_root.then(node_note).then(node_note_alias)
    node_root.then(node_complete).then(node_pause).then(node_resume).then(node_restore)
    node_root.then(node_default_tier)

    server.register_command(node_root)
