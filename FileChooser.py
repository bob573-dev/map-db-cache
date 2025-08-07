from pathlib import Path

from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup


class FileChooserPopup(Popup):
    selected_dir = StringProperty(None)
    selected_file = StringProperty(None)
    entry_height = 40
    __events__ = ['on_submit']

    def __init__(self, path: str, **kwargs):
        super().__init__(**kwargs)
        self.title='Choose directory'
        self._build_content(path or '.')

    def _build_content(self, path: str):
        content = BoxLayout(orientation='vertical')
        self.filechooser = FileChooserListView(path=path, dirselect=True, filters = ['*.mbtiles'], size_hint_y=0.9)
        self.filechooser.bind(
            on_entry_added=self._update_entry_height,
            on_subentry_to_entry=self._update_entry_height,
        )
        self.selected_dir = self.filechooser.path
        self.submit_btn = Button(
            text='Select',
            on_release=self._submit,
            size_hint_y=0.1
        )
        content.add_widget(self.filechooser)
        content.add_widget(self.submit_btn)
        self.content = content

    def _update_entry_height(self, _, entry, __):
        entry.height = self.entry_height

    def _submit(self, *_):
        selection = self.filechooser.selection
        if selection:
            path = Path(selection[0])
            if path.is_dir():
                self.selected_dir = str(path)
                self.selected_file = ''
            else:
                self.selected_dir = str(path.parent)
                self.selected_file = str(path.name)
        else:
            self.selected_dir = self.filechooser.path
            self.selected_file = ''
        self.dispatch('on_submit')

    def on_submit(self, *_):
        self.dismiss()
