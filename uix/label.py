from kivy.properties import BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label

from consts import TEXT_COLOR, FONT_SIZE_SMALL, ERROR_COLOR


class LabelAutoresized(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault('color', TEXT_COLOR)
        kwargs.setdefault('font_size', FONT_SIZE_SMALL)
        if 'size_hint' not in kwargs:
            kwargs['size_hint_x'] = kwargs.get('size_hint_x')
            kwargs['size_hint_y'] = kwargs.get('size_hint_y')

        super(LabelAutoresized, self).__init__(**kwargs)
        self.bind(
            texture_size=self.setter('size'),
            width=self._update_text_size,
        )

    def _update_text_size(self, *_):
        self.text_size = (self.width, None)


class LabelValidatedAutoresized(LabelAutoresized):
    invalid = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(LabelValidatedAutoresized, self).__init__(**kwargs)
        self.default_color = self.color
        self.bind(invalid=self._update_color)

    def _update_color(self, *args):
        self.color = ERROR_COLOR if self.invalid else self.default_color


class DropdownLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        kwargs.setdefault('color', TEXT_COLOR)
        kwargs.setdefault('font_size', FONT_SIZE_SMALL)
        super(DropdownLabel, self).__init__(**kwargs)
        self.bind(width=self._update_text_size)

    def _update_text_size(self, *_):
        self.text_size = (self.width, None)


__all__ = [
    'LabelAutoresized',
    'LabelValidatedAutoresized',
    'DropdownLabel',
]
