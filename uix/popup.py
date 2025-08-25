from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup


class InfoPopup(Popup):
    text = StringProperty('')
    __events__ = ['on_ok']

    def __init__(self, **kwargs):
        kwargs.setdefault('title', 'Info')
        super().__init__(**kwargs)
        self._build_content()

    def _build_content(self):
        container = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(
            text=self.text,
            halign='center',
            valign='middle',
            size_hint=(1, 0.8),
        )
        label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
        self.bind(text=label.setter('text'))

        ok_button = Button(text="OK", size_hint_y=0.2)
        ok_button.bind(on_release=self._make_ok)

        container.add_widget(label)
        container.add_widget(ok_button)
        self.content = container

    def _make_ok(self, *_):
        self.dispatch('on_ok')
        self.dismiss()

    def on_ok(self, *_):
        pass


class FileExistsPopup(Popup):
    text = StringProperty('')
    __events__ = ['on_cancel', 'on_overwrite', 'on_copy']

    def __init__(self, **kwargs):
        kwargs.setdefault('title', 'Make a choice')
        super().__init__(**kwargs)
        self._build_content()

    def _build_content(self):
        container = BoxLayout(orientation='vertical', padding=10, spacing=10)

        label = Label(
            text=self.text,
            halign='center',
            valign='middle',
            size_hint=(1, 0.8),
        )
        label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))
        self.bind(text=label.setter('text'))

        control_buttons_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)

        cancel_button = Button(text="Cancel", size_hint_x=0.3)
        cancel_button.bind(on_release=self._make_cancel)

        overwrite_button = Button(text="Overwrite", size_hint_x=0.3)
        overwrite_button.bind(on_release=self._make_overwrite)

        ok_button = Button(text="Save copy", size_hint_x=0.3)
        ok_button.bind(on_release=self._make_copy)

        control_buttons_layout.add_widget(cancel_button)
        control_buttons_layout.add_widget(overwrite_button)
        control_buttons_layout.add_widget(ok_button)

        container.add_widget(label)
        container.add_widget(control_buttons_layout)
        self.content = container

    def _make_cancel(self, *_):
        self.dispatch('on_cancel')
        self.dismiss()

    def on_cancel(self, *_):
        pass

    def _make_overwrite(self, *_):
        self.dispatch('on_overwrite')
        self.dismiss()

    def on_overwrite(self, *_):
        pass

    def _make_copy(self, *_):
        self.dispatch('on_copy')
        self.dismiss()

    def on_copy(self, *_):
        pass


__all__ = ['InfoPopup', 'FileExistsPopup']
