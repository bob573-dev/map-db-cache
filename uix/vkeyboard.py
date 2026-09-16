from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.textinput import TextInput
from kivy.uix.vkeyboard import VKeyboard

from consts import TEXT_COLOR, FONT_SIZE_MEDIUM, ACCENT_COLOR
from tools.binding_manager import BindingManager
from .textinput import CPBubble


class _PreviewTextInput(TextInput):
    def __init__(self, vkeyboard, **kwargs):
        super().__init__(**kwargs)
        self._vkeyboard = vkeyboard
        self._bubble = None
        self._touch_down_window_pos = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if 'button' in touch.profile and touch.button == 'right':
                self._open_bubble(self.to_window(*touch.pos))
                return True
            self._touch_down_window_pos = self.to_window(*touch.pos)
        return super().on_touch_down(touch)

    def long_touch(self, dt):
        self._long_touch_ev = None
        if self._selection_to != self._selection_from:
            return
        self._open_bubble(self._touch_down_window_pos)

    def _open_bubble(self, window_pos):
        target = self._vkeyboard.target
        if target is None:
            return
        if self._bubble:
            self._bubble.hide()
        self._bubble = CPBubble(
            target,
            touch_pos=window_pos,
            selection_from=self.selection_from,
            selection_to=self.selection_to,
        )
        self._bubble.show()


class TabletVKeyboard(VKeyboard):
    """Docked on-screen keyboard with an input preview strip above the
    keys, mirroring the text/cursor of whichever input currently owns
    the keyboard.

    A separate class rather than a kivy.uix.vkeyboard.VKeyboard patch;
    registered via Window.set_vkeyboard_class() in setup.py.
    """

    input_preview_height = 36
    input_preview_padding = 14
    input_preview_border_radius = 8
    input_preview_border_width = 1.2
    input_preview_edge_margin = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bindings = BindingManager()
        self._syncing = False

        with self.canvas.before:
            Color(0.93, 0.93, 0.93, 1)
            self._input_preview_bg = RoundedRectangle(radius=[self.input_preview_border_radius])
            Color(*ACCENT_COLOR)
            self._input_preview_border = Line(width=self.input_preview_border_width)

        self._input_preview = _PreviewTextInput(
            self,
            # 'managed' keeps this widget focusable (so it can register
            # into FocusBehavior.ignored_touch and keep the real target's
            # keyboard alive) without it ever calling
            # Window.request_keyboard() itself, which would otherwise
            # steal the single docked keyboard away from the real target
            keyboard_mode='managed',
            readonly=True,
            multiline=False,
            use_bubble=False,
            font_size=FONT_SIZE_MEDIUM,
            foreground_color=TEXT_COLOR,
            background_color=(0, 0, 0, 0),
            padding=[self.input_preview_padding, 6, self.input_preview_padding, 6],
        )
        self._input_preview.bind(cursor=self._on_preview_cursor)
        self.add_widget(self._input_preview)

        self.fbind('target', self._on_target)
        self._update_input_preview_layout()
        self._on_target(self, self.target)

    def collide_point(self, x, y):
        if super().collide_point(x, y):
            return True
        lx, ly = self.to_local(x, y)
        return 0 <= lx <= self.width and self.height <= ly <= self.height + self.input_preview_height

    def refresh(self, force=False):
        super().refresh(force)
        self.add_widget(self._input_preview)
        self._update_input_preview_layout()

    def _update_input_preview_layout(self, *_):
        inset = self.input_preview_edge_margin
        x = inset
        width = self.width - 2 * inset

        self._input_preview_bg.pos = (x, self.height)
        self._input_preview_bg.size = (width, self.input_preview_height)
        self._input_preview_border.rounded_rectangle = (
            x, self.height, width, self.input_preview_height, self.input_preview_border_radius
        )

        self._input_preview.pos = (x, self.height)
        self._input_preview.size = (width, self.input_preview_height)

    def _on_target(self, _, target):
        self._bindings.unbind_items()
        if target is not None:
            self._bindings.bind_item(target, 'text', self._sync_preview_from_target)
            self._bindings.bind_item(target, 'cursor', self._sync_preview_from_target)
            self._bindings.bind_item(target, 'selection_text', self._sync_preview_selection_from_target)
        self._sync_preview_from_target()
        self._sync_preview_selection_from_target()

        preview = self._input_preview
        preview.focus = target is not None
        if target is not None:
            self.reset_preview_cursor_to_end()

    def reset_preview_cursor_to_end(self):
        target = self.target
        if target is None:
            return
        Clock.schedule_once(lambda *_: self._reset_preview_cursor_to_end(target))

    def _reset_preview_cursor_to_end(self, target):
        if self.target is not target:
            return
        preview = self._input_preview
        preview.cancel_selection()
        preview.cursor = preview.get_cursor_from_index(len(preview.text))

    def _sync_preview_from_target(self, *_):
        target = self.target
        preview = self._input_preview
        self._syncing = True
        try:
            preview.text = target.text if target is not None else ''
            if target is not None:
                preview.cursor = preview.get_cursor_from_index(target.cursor_index())
        finally:
            self._syncing = False

    def _sync_preview_selection_from_target(self, *_):
        target = self.target
        preview = self._input_preview
        if (
            target is None
            or target.selection_from is None
            or target.selection_to is None
            or target.selection_from == target.selection_to
        ):
            preview.cancel_selection()
            return
        preview.select_text(min(target.selection_from, target.selection_to), max(target.selection_from, target.selection_to))

    def _on_preview_cursor(self, _, __):
        if self._syncing:
            return
        target = self.target
        if target is not None:
            target.cursor = target.get_cursor_from_index(self._input_preview.cursor_index())
            target.cancel_selection()


__all__ = ['TabletVKeyboard']
