from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.widget import Widget

from uix import BoxLayoutShort, LabelAutoresized, TextInputRangedUnderlined, BoxLayoutColored


class TextInputRangedTitledLayout(BoxLayoutShort):
    min_value = NumericProperty(defaultvalue=0)
    max_value = NumericProperty(defaultvalue=0)
    value_setter = ObjectProperty(None)
    buttons_overheight = NumericProperty(20)
    increase_button = ObjectProperty(None)
    decrease_button = ObjectProperty(None)

    def __init__(
            self,
            title = '',
            hint_text = '',
            text = '',
            **kwargs
    ):
        super().__init__(**kwargs)
        left_container = BoxLayoutShort(orientation='vertical')
        left_container.bind(height=self._on_left_container_height)

        self.label = label = LabelAutoresized(text=title)
        self.textinput = textinput = TextInputRangedUnderlined(
            size_hint_y=None,
            text=text,
            hint_text=hint_text,
            step_buttons=True,
            min_value=self.min_value,
            max_value=self.max_value,
        )
        self.bind(
            min_value=textinput.setter('min_value'),
            max_value=textinput.setter('max_value'),
        )
        textinput.bind(minimum_height=textinput.setter('height'))
        if self.value_setter:
            textinput.bind(value=self.value_setter)

        self.increase_button = textinput.increase_button
        self.decrease_button = textinput.decrease_button

        self._buttons_container = buttons_container = BoxLayoutColored(
            orientation='vertical',
            size_hint=(None, None),
        )

        if self.buttons_overheight:
            left_container.add_widget(Widget(height=self.buttons_overheight/2, size_hint_y=None))
        left_container.add_widget(label)
        left_container.add_widget(textinput)
        if self.buttons_overheight:
            left_container.add_widget(Widget(height=self.buttons_overheight/2, size_hint_y=None))

        buttons_container.add_widget(textinput.increase_button)
        buttons_container.add_widget(textinput.decrease_button)

        self.add_widget(left_container)
        self.add_widget(buttons_container)

    def _on_left_container_height(self, _, height):
        self._buttons_container.size = (height / 2, height)
        self.increase_button.size = (self._buttons_container.width, self._buttons_container.height / 2)
        self.decrease_button.size = (self._buttons_container.width, self._buttons_container.height / 2)

    def disable(self, disable):
        self.textinput.readonly = disable
        self.increase_button.disabled = disable
        self.decrease_button.disabled = disable
