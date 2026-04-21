from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.properties import NumericProperty, BooleanProperty, ObjectProperty, ListProperty
from kivy.uix.bubble import Bubble
from kivy.uix.textinput import TextInput

from consts import DEFAULT_LAT, DEFAULT_LON, INPUT_INCREASE_PNG, INPUT_DECREASE_PNG, FONT_SIZE_SMALL, \
    MIN_CENTER_LATITUDE, MAX_CENTER_LONGITUDE, MAX_CENTER_LATITUDE, MIN_CENTER_LONGITUDE, ERROR_COLOR
from localization import _
from tools.binding_manager import BindingManager
from . import BoxLayoutAutoresized
from .button import ButtonImage, ButtonColored


class BubbleButtonColored(ButtonColored):
    def __init__(self, **kwargs):
        kwargs.setdefault('halign', 'left')
        kwargs.setdefault('valign', 'center')
        kwargs.setdefault('padding', [12, 0, 0, 0])
        super().__init__(**kwargs)
        self.background_color[3] = self.background_color[3] * 0.8

    def on_size(self, *args):
        self.text_size = self.size


class CPBubble(Bubble):
    def __init__(self, textinput, touch_pos, selection_from, selection_to, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('width', 140)
        kwargs.setdefault('show_arrow', True)
        kwargs.setdefault('arrow_pos', 'top_left')
        super().__init__(**kwargs)
        self.textinput: TextInput = textinput
        self.touch_pos = touch_pos
        self.selection_from = selection_from
        self.selection_to = selection_to
        self._button_size = (self.width, 32)
        self._bindings = BindingManager()
        self._root_widget = None
        self._trigger_restore_selection = Clock.create_trigger(self._restore_selection, 0.15)

        content = BoxLayoutAutoresized(orientation='vertical', spacing=1, padding=1)
        content.bind(size=self.setter('size'))
        self.add_widget(content)
        self._select_all_btn = BubbleButtonColored(text=_('Select all'), on_release=self.select_all, size_hint=(None, None), size=self._button_size)
        self._cut_btn = BubbleButtonColored(text=_('Cut'), on_release=self.cut, size_hint=(None, None), size=self._button_size)
        self._copy_btn = BubbleButtonColored(text=_('Copy'), on_release=self.copy, size_hint=(None, None), size=self._button_size)
        self._paste_btn = BubbleButtonColored(text=_('Paste'), on_release=self.paste, size_hint=(None, None), size=self._button_size)

    def select_all(self, *args):
        self.selection_from = 0
        self.selection_to = len(self.textinput.text)
        self._trigger_restore_selection()

    def cut(self, *args):
        self.textinput.cut()
        self.hide()

    def copy(self, *args):
        self.textinput.copy()
        self.hide()

    def paste(self, *args):
        self.textinput.paste()
        self.hide()

    def hide(self, *args):
        if self.parent:
            self.textinput.cancel_selection()
            self.parent.remove_widget(self)
            self._bindings.unbind_items()

    def show(self):
        if not self.parent:
            self._root_widget = root = self.textinput.get_root_window()
            root.add_widget(self)
            self._trigger_restore_selection()
            self._bindings.bind_item(root, 'on_touch_down', self._on_touch_down_root)
            self._bindings.bind_item(root, 'size', self.hide)
            self._update_buttons()

    def _update_buttons(self, *args):
        self.opacity = 0
        self.content.clear_widgets()
        text_available = bool(self.textinput.text)
        text_selected = (
            text_available
            and self.selection_from is not None
            and self.selection_to is not None
            and self.selection_from - self.selection_to != 0
        )
        all_text_selected = text_selected and abs(self.selection_from - self.selection_to) == len(self.textinput.text)
        if text_available and not all_text_selected:
            self.content.add_widget(self._select_all_btn)
        if text_selected:
            if not self.textinput.readonly:
                self.content.add_widget(self._cut_btn)
            self.content.add_widget(self._copy_btn)
        if not self.textinput.readonly:
            self.content.add_widget(self._paste_btn)
        Clock.schedule_once(self._update_pos)

    def _restore_selection(self, *_):
        if self.selection_from is None or self.selection_to is None:
            return
        self.textinput.select_text(min(self.selection_from, self.selection_to), max(self.selection_from, self.selection_to))
        self._update_buttons()

    def _on_touch_down_root(self, root, touch):
        if not self.collide_point(*touch.pos):
            self.hide()

    def _update_pos(self, *args):
        touch_x, touch_y = self.touch_pos
        arrow_relative_x, arrow_relative_y = 15, 8
        pos_x, pos_y = touch_x - arrow_relative_x, touch_y - self.content.height - arrow_relative_y
        arrow_vertical = 'top'
        arrow_horizontal = 'left'

        if pos_x + self.content.width > self.parent.width:
            pos_x = touch_x - self.content.width + arrow_relative_x
            arrow_horizontal = 'right'

        if pos_y < 0:
            pos_y = touch_y + arrow_relative_y
            arrow_vertical = 'bottom'

        self.pos = (pos_x, pos_y)
        self.arrow_pos = f'{arrow_vertical}_{arrow_horizontal}'
        self.opacity = 1


class TextInputUnderlined(TextInput):
    invalid = BooleanProperty(False)

    def  __init__(self, **kwargs):
        kwargs.setdefault('font_size', FONT_SIZE_SMALL)
        kwargs.setdefault('cursor_color', (0.3, 0.3, 0.3, 1))
        kwargs.setdefault('use_bubble', False)  # turn off default for mobile
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)

        with self.canvas.after:
            self._line_color = Color(0, 0, 0, 0.8)
            self._underline = Line(points=[])

        self._trigger_update_underline = Clock.create_trigger(self._update_underline)
        self.bind(
            pos=self._trigger_update_underline,
            size=self._trigger_update_underline,
            invalid=self._trigger_update_underline,
        )
        self._trigger_update_underline()
        self.__bubble = None
        self._saved_selection = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if 'button' in touch.profile and touch.button == 'right':
                self._saved_selection = (
                    self.selection_from,
                    self.selection_to,
                )
                self._show_copy_paste_bubble(self.to_window(*touch.pos))
                return True
        return super().on_touch_down(touch)

    def _show_copy_paste_bubble(self, touch_pos):
        if self.__bubble:
            self.__bubble.hide()
        self.__bubble = CPBubble(
            self,
            touch_pos=touch_pos,
            selection_from=self._saved_selection[0],
            selection_to=self._saved_selection[1],
        )
        self.__bubble.show()

    def _update_underline(self, *_):
        self._line_color.rgba = ERROR_COLOR if self.invalid else (0, 0, 0, 0.8)
        x, y = self.x, self.y
        self._underline.points = [x + self.padding[0], y, x + self.width - self.padding[2], y]


class TextInputRanged(TextInput):
    min_value = NumericProperty(defaultvalue=0)
    max_value = NumericProperty(defaultvalue=0)
    value = NumericProperty(defaultvalue=None, allownone=True)
    step_buttons = BooleanProperty(False)
    increase_button = ObjectProperty(None)
    decrease_button = ObjectProperty(None)
    buttons_size = ListProperty([13, 13])

    def __init__(self, step: int|float = 1, **kwargs):
        kwargs.setdefault('font_size', FONT_SIZE_SMALL)
        kwargs.setdefault('cursor_color', (0.3, 0.3, 0.3, 1))
        kwargs['input_filter'] = kwargs.get('input_filter', 'int')
        kwargs['multiline'] = kwargs.get('multiline', False)

        super().__init__(**kwargs)
        if self.input_filter == 'float':
            self._value_type = float
        else:
            self._value_type = int
        self._update_value()
        self.bind(
            text=self._update_value,
            min_value=self._update_value,
            max_value=self._update_value,
        )
        if self.step_buttons:
            self._init_step_buttons(step)

    def _update_value(self, *args):
        try:
            val = self._value_type(self.text)
            if val < self.min_value:
                self.set_text_normalized(self.min_value)
                self.scroll_x = 0
            elif val > self.max_value:
                self.set_text_normalized(self.max_value)
                self.scroll_x = 0
            self.value = self._value_type(self.text)
        except ValueError:
            if self.text == '':
                self.value = type(self).value.defaultvalue

    def _init_step_buttons(self, step: int|float):
        normalized_step = self._value_type(step)
        self.increase_button = increase_button = ButtonImage(
            image=INPUT_INCREASE_PNG,
            size_hint=(None, None),
            size=self.buttons_size,
        )
        self.decrease_button = decrease_button = ButtonImage(
            image=INPUT_DECREASE_PNG,
            size_hint=(None, None),
            size=self.buttons_size,
        )
        increase_button.bind(
            on_release=lambda *_: self.increase(normalized_step),
        )
        decrease_button.bind(
            on_release=lambda *_: self.decrease(normalized_step),
        )

        def _update_buttons(*_):
            increase_disabled = False
            decrease_disabled = False
            if self.value == self.min_value:
                decrease_disabled = True
            elif self.value == self.max_value:
                increase_disabled = True
            increase_button.disabled = increase_disabled
            decrease_button.disabled = decrease_disabled

        self.bind(
            value=_update_buttons,
            min_value=_update_buttons,
            max_value=_update_buttons,
        )

    def increase(self, step):
        if self.value != self.max_value:
            self._step(step)

    def decrease(self, step):
        if self.value != self.min_value:
            self._step(-step)

    def _step(self, step):
        if self.value is None:
            self.set_text_normalized(self.min_value if step < 0 else self.max_value)
        else:
            try:
                self.set_text_normalized(self._value_type(self.text) + step)
                self.scroll_x = 0
            except ValueError:
                self._update_value()

    def set_text_normalized(self, value: int|float):
        if value is not None:
            if int(value) == value:
                value = int(value)
            self.text = str(value)


class TextInputRangedUnderlined(TextInputRanged, TextInputUnderlined):
    pass


class TextInputCoord(TextInputRangedUnderlined):
    def __init__(self, is_lat: bool = True, **kwargs):
        kwargs['input_filter'] = kwargs.get('input_filter', 'float')

        kwargs['hint_text'] = kwargs.get('hint_text', _('example') + f": {DEFAULT_LAT if is_lat else DEFAULT_LON}")
        kwargs['cursor_color'] = kwargs.get('cursor_color', (0.3, 0.3, 0.3, 1))
        kwargs['min_value'] = kwargs.get('min_value', MIN_CENTER_LATITUDE if is_lat else MIN_CENTER_LONGITUDE)
        kwargs['max_value'] = kwargs.get('max_value', MAX_CENTER_LATITUDE if is_lat else MAX_CENTER_LONGITUDE)
        super().__init__(**kwargs)



__all__ = ['TextInputUnderlined', 'TextInputRanged', 'TextInputRangedUnderlined', 'TextInputCoord']
