from math import floor

from kivy.graphics import Color, Line
from kivy.properties import NumericProperty, BooleanProperty, ObjectProperty, ListProperty
from kivy.uix.textinput import TextInput

from consts import DEFAULT_LAT, DEFAULT_LON, INPUT_INCREASE_PNG, INPUT_DECREASE_PNG, FONT_SIZE_SMALL, \
    MIN_CENTER_LATITUDE, MAX_CENTER_LONGITUDE, MAX_CENTER_LATITUDE, MIN_CENTER_LONGITUDE
from .button import ButtonImage


class TextInputUnderlined(TextInput):
    def  __init__(self, **kwargs):
        kwargs.setdefault('font_size', FONT_SIZE_SMALL)
        kwargs.setdefault('cursor_color', (0.3, 0.3, 0.3, 1))
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)

        with self.canvas.after:
            self._line_color = Color(0, 0, 0, 0.8)
            self._underline = Line(points=[])

        self.bind(
            pos=self._update_underline,
            size=self._update_underline,
        )

    def _update_underline(self, *_):
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

        kwargs['hint_text'] = kwargs.get('hint_text', f"example: {DEFAULT_LAT if is_lat else DEFAULT_LON}")
        kwargs['cursor_color'] = kwargs.get('cursor_color', (0.3, 0.3, 0.3, 1))
        kwargs['min_value'] = kwargs.get('min_value', MIN_CENTER_LATITUDE if is_lat else MIN_CENTER_LONGITUDE)
        kwargs['max_value'] = kwargs.get('max_value', MAX_CENTER_LATITUDE if is_lat else MAX_CENTER_LONGITUDE)
        super().__init__(**kwargs)



__all__ = ['TextInputUnderlined', 'TextInputRanged', 'TextInputRangedUnderlined', 'TextInputCoord']
