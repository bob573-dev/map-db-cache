from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label

from consts import TEXT_COLOR, FONT_SIZE_SMALL


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


class ProviderLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        kwargs.setdefault('color', TEXT_COLOR)
        kwargs.setdefault('font_size', FONT_SIZE_SMALL)
        super(ProviderLabel, self).__init__(**kwargs)
        self.bind(width=self._update_text_size)

    def _update_text_size(self, *_):
        self.text_size = (self.width, None)


__all__ = ['LabelAutoresized', 'ProviderLabel']
