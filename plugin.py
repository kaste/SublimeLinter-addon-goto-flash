import uuid

import sublime
import sublime_plugin

from SublimeLinter.highlight_view import get_regions_keys
from SublimeLinter.lint import persist, queue


State = {'cursor_position_pre': None}


class GotoCommandListener(sublime_plugin.EventListener):
    def on_window_command(self, window, command_name, args):
        if command_name == 'sublime_linter_goto_error':
            view = window.active_view()
            if not view:
                return

            cursor = view.sel()[0].begin()
            State['cursor_position_pre'] = cursor

    def on_post_window_command(self, window, command_name, args):
        if command_name == 'sublime_linter_goto_error':
            view = window.active_view()
            if not view:
                return

            pre_cursor = State['cursor_position_pre']
            if pre_cursor is None:
                return

            cursor = view.sel()[0].begin()
            State['cursor_position_pre'] = None

            if pre_cursor != cursor:
                highlight_jump_position(view, cursor)


HIGHLIGHT_REGION_KEY = 'SL.flash_jump_position.{}'
HIGHLIGHT_TIME = 0.8  # [sec]
HIGHLIGHT_SCOPE = 'markup.bold'
HIGHLIGHT_FLAGS = sublime.DRAW_NO_FILL
RESURRECT_KEY_TMPL = 'sl-goto-flash-{}'


def highlight_jump_position(view, point):
    bid = view.buffer_id()
    touching_errors = [
        error for error in persist.errors[bid] if error['region'].contains(point)
    ]
    touching_error_uids = {error['uid'] for error in touching_errors}

    # First dehighlight lint errors
    touching_regions = []
    for key in get_regions_keys(view):
        if '.Highlights.' not in key:
            continue

        namespace, uid, scope, flags = key.split('|')
        if uid in touching_error_uids:
            touching_regions.append(
                (key, view.get_regions(key), scope, int(flags))
            )

    for key, _, _, _ in touching_regions:
        view.erase_regions(key)

    def resurrect_regions():
        for key, regions, scope, flags in touching_regions:
            view.add_regions(key, regions, scope=scope, flags=flags)

    queue.debounce(
        resurrect_regions,
        delay=HIGHLIGHT_TIME,
        key=RESURRECT_KEY_TMPL.format(view.id()),
    )

    # Now highlight the jump position
    widest_region = max(
        (error['region'] for error in touching_errors),
        key=lambda region: region.end(),
    )

    region_key = HIGHLIGHT_REGION_KEY.format(uuid.uuid4())
    view.add_regions(
        region_key, [widest_region], scope=HIGHLIGHT_SCOPE, flags=HIGHLIGHT_FLAGS
    )

    queue.debounce(
        lambda: view.erase_regions(region_key),
        delay=HIGHLIGHT_TIME,
        key=region_key,
    )
