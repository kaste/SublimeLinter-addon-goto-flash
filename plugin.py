import uuid

import sublime
import sublime_plugin

from SublimeLinter.highlight_view import get_regions_keys, MARK_STYLES
from SublimeLinter.lint import persist, queue


MYPY = False
if MYPY:
    from typing import Optional, Set
    from mypy_extensions import TypedDict

    State_ = TypedDict(
        'State_',
        {
            'cursor_position_pre': Optional[int],
            'previous_quiet_views': Set[sublime.ViewId],
        },
    )


HIGHLIGHT_REGION_KEY = 'SL.flash_jump_position.{}'
State = {
    'cursor_position_pre': None,
    'previous_quiet_views': set(),
}  # type: State_


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
                cursor_jumped(view, cursor)


def cursor_jumped(view, cursor):
    bid = view.buffer_id()
    touching_errors = [
        error
        for error in persist.errors[bid]
        if error['region'].begin() == cursor
    ]
    settings = sublime.load_settings(
        'SublimeLinter-addon-goto-flash.sublime-settings'
    )

    highlight_jump_position(view, touching_errors, settings)
    dehighlight_linter_errors(view, touching_errors, settings)


def highlight_jump_position(view, touching_errors, settings):
    widest_region = max(
        (error['region'] for error in touching_errors),
        key=lambda region: region.end(),
    )

    region_key = HIGHLIGHT_REGION_KEY.format(uuid.uuid4())
    scope = settings.get('scope')
    flags = MARK_STYLES[settings.get('style')]
    view.add_regions(region_key, [widest_region], scope=scope, flags=flags)

    queue.debounce(
        lambda: view.erase_regions(region_key),
        delay=settings.get('duration'),
        key=region_key,
    )


def dehighlight_linter_errors(view, touching_errors, settings):
    touching_error_uids = {error['uid'] for error in touching_errors}

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
        resurrect_regions, delay=settings.get('duration'), key=uuid.uuid4()
    )
