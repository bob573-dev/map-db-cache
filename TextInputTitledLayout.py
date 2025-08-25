from kivy.properties import ObjectProperty, StringProperty

from uix import BoxLayoutShort, LabelAutoresized, TextInputUnderlined, ButtonImage


class TextInputTitledLayout(BoxLayoutShort):
    value_setter = ObjectProperty(None)
    button = ObjectProperty(None)
    button_image = StringProperty('')

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
        self.textinput = textinput = TextInputUnderlined(
            size_hint_y=None,
            text=text,
            hint_text=hint_text,
        )
        textinput.bind(minimum_height=textinput.setter('height'))
        if self.value_setter:
            textinput.bind(value=self.value_setter)

        self.button = ButtonImage(
            image=self.button_image,
            size_hint=(None, None),
        )

        left_container.add_widget(label)
        left_container.add_widget(textinput)

        self.add_widget(left_container)
        self.add_widget(self.button)

    def _on_left_container_height(self, _, height):
        self.button.size = (height, height)

    def disable(self, disable):
        self.button.disabled = disable
