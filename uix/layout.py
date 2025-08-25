from kivy.event import EventDispatcher
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout

from consts import DOWNLOAD_PANEL_BACKGROUND


class ColoredLayout(EventDispatcher):
    def __init__(
            self,
            background: tuple = DOWNLOAD_PANEL_BACKGROUND,
            **kwargs,
    ):
        super().__init__(**kwargs)

        if background:
            with self.canvas.before:
                Color(*background)
                self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *_):
        self.rect.size = self.size
        self.rect.pos = self.pos


class BoxLayoutColored(ColoredLayout, BoxLayout):
    pass


class BoxLayoutShort(BoxLayoutColored):
    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter('height'))


class BoxLayoutAutoresized(BoxLayoutColored):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.bind(
            minimum_height=self.setter('height'),
            minimum_width=self.setter('width'),
        )


__all__ = ['ColoredLayout', 'BoxLayoutColored', 'BoxLayoutShort', 'BoxLayoutAutoresized']
