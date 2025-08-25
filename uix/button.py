from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.button import Button

from consts import FONT_SIZE_MEDIUM
from tools.utils import minmax


class ButtonColored(Button):
    def __init__(self, **kwargs):
        kwargs['font_size'] = kwargs.get('font_size', FONT_SIZE_MEDIUM)
        kwargs['color'] = kwargs.get('color', (1, 1, 1, 1))
        kwargs['background_color'] = kwargs.get('background_color', (0.9, 0.1, 0.1, 1))
        kwargs['background_normal'] = kwargs.get('background_normal', '')
        kwargs['background_down'] = kwargs.get('background_down', '')
        super().__init__(**kwargs)
        self.default_background_color = self.background_color
        self.pressed_background_color = [minmax(value -0.25, 0, 1)
                                         for value in self.background_color[:-1]] + [self.background_color[-1]]

    def on_press(self):
        self._update_background(True)

    def on_release(self):
        self._update_background(False)

    def _update_background(self, pressed=False):
        self.background_color = self.pressed_background_color if pressed else self.default_background_color


class SwitchButtonColored(ButtonColored):
    active = BooleanProperty(False)
    active_text = StringProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.default_text = self.text
        self.active_text = self.active_text or self.text

    def on_release(self):
        self.active = not self.active

    def deactivate(self, *_):
        self.active = False

    def on_active(self, _, value):
        if value:
            self.text = self.active_text
            self._update_background(True)
        else:
            self.text = self.default_text
            self._update_background(False)


class ButtonImage(Button):
    def __init__(self, image, **kwargs):
        kwargs.setdefault('border', (1, 1, 1, 1))
        super().__init__(**kwargs)
        self.set_image(image)

    def set_image(self, image):
        self.background_normal = image
        self.background_down = image
        self.background_disabled_normal = image
        self.background_disabled_down = image

    def on_press(self, *_):
        self.background_color = (*self.background_color[:3], 0.5)

    def on_release(self, *_):
        self.background_color = (*self.background_color[:3], 1)

    def on_disabled(self, _, disabled):
        if disabled:
            self.opacity = 0.3
        else:
            self.opacity = 1.0


__all__ = ['ButtonColored', 'SwitchButtonColored', 'ButtonImage']
