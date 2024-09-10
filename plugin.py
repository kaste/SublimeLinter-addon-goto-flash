from functools import partial
import threading

import sublime
import sublime_plugin

from SublimeLinter import highlight_view
from SublimeLinter.lint import persist, util

try:
    from SublimeLinter.lint.util import canonical_filename
except ImportError:
    canonical_filename = util.get_filename  # type: ignore[attr-defined]


MYPY = False
if MYPY:
    from typing import Callable, Dict, List, Optional, Set, Tuple, TypedDict

    Task = Tuple[Callable, object, ...]  # type: ignore[misc]
    State_ = TypedDict(
        'State_',
        {
            'cursor_position_pre': Optional[Tuple[sublime.ViewId, int]],
            'temporary_squiggles_after_jumping': Set[sublime.ViewId],
            'temporary_squiggles_after_panel': Set[sublime.ViewId],
            'just_drawn_a_phantom': Set[sublime.ViewId],
            'resurrect_tasks': List[Task],
            'await_load': Dict[sublime.ViewId, Callable[[], None]],
        },
    )


HIGHLIGHT_REGION_KEY = 'SL.flash_jump_position.{}'
State = {
    'cursor_position_pre': None,
    'temporary_squiggles_after_jumping': set(),
    'temporary_squiggles_after_panel': set(),
    'just_drawn_a_phantom': set(),
    'resurrect_tasks': [],
    'await_load': {},
}  # type: State_

PANEL_NAME = "SublimeLinter"
OUTPUT_PANEL = "output." + PANEL_NAME

GOTO_COMMANDS = {
    'sublime_linter_goto_error',
    'sublime_linter_panel_next',
    'sublime_linter_panel_previous',
}


class GotoCommandListener(sublime_plugin.EventListener):
    # `on_load` is a lie, the `sel()` is still not updated
    def on_load_async(self, view):
        try:
            callback = State['await_load'][view.id()]
        except KeyError:
            ...
        else:
            callback()

    def on_text_command(self, view, command_name, args):
        # type: (sublime.View, str, Dict) -> None
        if command_name in GOTO_COMMANDS:
            # `view` can be the panel
            # (for `sublime_linter_panel_next/previous`), so read
            # out the `active_view` here
            window = view.window()
            if not window:
                return
            active_view = window.active_view()
            if not active_view:
                return
            cursor = active_view.sel()[0].begin()
            State['cursor_position_pre'] = (active_view.id(), cursor)

    def on_post_text_command(self, view, command_name, args):
        # type: (sublime.View, str, Dict) -> None
        if command_name in GOTO_COMMANDS:
            pre_cursor = State['cursor_position_pre']
            if pre_cursor is None:
                return

            window = view.window()
            if not window:
                return
            active_view = window.active_view()
            if not active_view:
                return

            def side_effect():
                State['cursor_position_pre'] = None
                cursor = active_view.sel()[0].begin()
                if pre_cursor != (active_view.id(), cursor):
                    cursor_jumped(active_view, cursor)

            if active_view.is_loading():
                State['await_load'][active_view.id()] = side_effect
            else:
                side_effect()

    def on_window_command(self, window, command_name, args):
        # type: (sublime.Window, str, Optional[Dict]) -> None
        if command_name == 'sublime_linter_toggle_highlights':
            active_view = window.active_view()
            if not active_view:
                return
            vid = active_view.id()
            State["just_drawn_a_phantom"].discard(vid)
            State['temporary_squiggles_after_jumping'].discard(vid)
            State['temporary_squiggles_after_panel'].discard(vid)

        elif command_name == 'hide_panel':
            if window.active_panel() == OUTPUT_PANEL:
                active_view = window.active_view()
                if not active_view:
                    return

                vid = active_view.id()
                if vid in State['temporary_squiggles_after_panel']:
                    window.run_command('sublime_linter_toggle_highlights', {
                        "what": toggle_squiggles()
                    })

        elif command_name == 'show_panel':
            if args and args.get('panel') == OUTPUT_PANEL:
                active_view = window.active_view()
                if not active_view:
                    return
                if not view_has_no_squiggles_drawn(active_view):
                    return

                settings = sublime.load_settings(
                    'SublimeLinter-addon-goto-flash.sublime-settings'
                )
                if not settings.get('jump_out_of_quiet'):
                    return

                what = toggle_squiggles()
                if what:
                    window.run_command('sublime_linter_toggle_highlights', {
                        "what": what
                    })
                    State['temporary_squiggles_after_panel'].add(active_view.id())


class JumpIntoQuietModeAgain(sublime_plugin.EventListener):
    def on_modified_async(self, view):
        window = view.window()
        if window:
            vid = view.id()
            if (
                (vid in State['temporary_squiggles_after_jumping'] and toggle_squiggles())
                or vid in State["just_drawn_a_phantom"]
            ):
                window.run_command('sublime_linter_toggle_highlights', {
                    "what": toggle_mode()
                })


def cursor_jumped(view, cursor):
    # type: (sublime.View, int) -> None
    settings = sublime.load_settings(
        'SublimeLinter-addon-goto-flash.sublime-settings'
    )

    currently_quiet = view_has_no_squiggles_drawn(view)
    if currently_quiet and settings.get('jump_out_of_quiet'):
        window = view.window()
        what = toggle_squiggles()
        if window and what:
            window.run_command('sublime_linter_toggle_highlights', {
                "what": what
            })
            State['temporary_squiggles_after_jumping'].add(view.id())

    if (
        (view_has_no_phantoms_drawn(view) or view.id() in State["just_drawn_a_phantom"])
        and not error_panel_is_visible(view)
        and settings.get('jump_out_of_quiet')
    ):
        filename = canonical_filename(view)
        touching_errors = [
            error
            for error in persist.file_errors[filename]
            if error['region'].begin() == cursor
        ]
        phantoms = highlight_view.prepare_phantoms(view, touching_errors)
        if phantoms:
            highlight_view.update_phantoms(view, phantoms)
            State["just_drawn_a_phantom"].add(view.id())
            highlight_view.State['views_without_phantoms'].discard(view.id())

    if currently_quiet or not settings.get('only_if_quiet'):
        try:
            touching_errors
        except NameError:
            filename = canonical_filename(view)
            touching_errors = [
                error
                for error in persist.file_errors[filename]
                if error['region'].begin() == cursor
            ]
        if touching_errors:
            highlight_jump_position(view, touching_errors, settings)


def toggle_mode():
    # type: () -> List[str]
    start_hidden = persist.settings.get('highlights.start_hidden') or []
    if start_hidden is True:
        return ["phantoms", "squiggles"]
    return start_hidden


def toggle_squiggles():
    # type: () -> List[str]
    modes = toggle_mode()
    return ["squiggles"] if "squiggles" in modes else []


def view_has_no_squiggles_drawn(view):
    return view.id() in highlight_view.State['quiet_views']


def view_has_no_phantoms_drawn(view):
    return view.id() in highlight_view.State['views_without_phantoms']


def error_panel_is_visible(view):
    window = view.window()
    if not window:
        return False
    return window.active_panel() == "output.SublimeLinter"


def highlight_jump_position(view, touching_errors, settings):
    while State['resurrect_tasks']:
        undo_task = State['resurrect_tasks'].pop(0)
        throttled(*undo_task)()

    widest_region = max(
        (error['region'] for error in touching_errors),
        key=lambda region: region.end(),
    )

    region_key = HIGHLIGHT_REGION_KEY.format('flash')
    scope = settings.get('scope')
    flags = highlight_view.MARK_STYLES[settings.get('style')]
    view.add_regions(region_key, [widest_region], scope=scope, flags=flags)

    sublime.set_timeout(
        throttled(erase_regions, view, region_key),
        settings.get('duration') * 1000,
    )

    undo_task = dehighlight_linter_errors(view, touching_errors, settings)
    State['resurrect_tasks'].append(undo_task)
    sublime.set_timeout(
        throttled(*undo_task),
        settings.get('duration') * 1000,
    )


def erase_regions(view, region_key):
    # type: (sublime.View, str) -> None
    view.erase_regions(region_key)


def dehighlight_linter_errors(view, touching_errors, settings):
    # type: (...) -> Task
    touching_error_uids = {error['uid'] for error in touching_errors}

    touching_regions = []
    for key in highlight_view.get_regions_keys(view):
        if not isinstance(key, highlight_view.Squiggle):
            continue

        if not key.visible():
            continue

        if key.uid in touching_error_uids:
            regions = view.get_regions(key)
            if regions:
                touching_regions.append((key, regions))

    for key, regions in touching_regions:
        if key.scope and getattr(key, "annotation", None):
            annotations = {
                "annotations": [key.annotation],
                "annotation_color":
                    view.style_for_scope(key.scope)["foreground"],
            }
        else:
            annotations = {}
        view.add_regions(key, regions, '', key.icon, key.flags, **annotations)

        # Both `erase_view_region` and `draw_squiggle_invisible` would
        # also erase the annotation.
        # highlight_view.erase_view_region(view, key)
        # highlight_view.draw_squiggle_invisible(view, key, regions)

    return (resurrect_regions, view, touching_regions)


def resurrect_regions(view, touching_regions):
    for key, regions in touching_regions:
        highlight_view.redraw_squiggle(view, key, regions)


THROTTLED_CACHE = {}
THROTTLED_LOCK = threading.Lock()


def throttled(fn, *args, **kwargs):
    # type: (...) -> Callable[[], None]
    token = (fn,)
    action = partial(fn, *args, **kwargs)
    with THROTTLED_LOCK:
        THROTTLED_CACHE[token] = action

    def task():
        with THROTTLED_LOCK:
            ok = THROTTLED_CACHE[token] == action
        if ok:
            action()

    return task
