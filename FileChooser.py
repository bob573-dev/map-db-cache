from pathlib import Path
from os.path import sep
from weakref import ref

from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.label import Label

from localization import _


class FileChooserListViewCurrentDir(FileChooserListView):
    def _generate_file_entries(self, *args, **kwargs):
        path = kwargs.get('path', self.path)
        if kwargs.get('parent', None) is None:
            pardir = self._create_entry_widget(dict(
                name='.' + sep, size='', path=Path(path).absolute(), controller=ref(self),
                isdir=False, parent=None, sep=sep,
                get_nice_size=lambda: ''))
            yield 0, 1, pardir

        yield from super()._generate_file_entries(*args, **kwargs)


class FileChooserPopup(Popup):
    selected_dir = StringProperty('')
    selected_file = StringProperty('')
    entry_height = 40
    __events__ = ['on_submit']

    def __init__(self, path: str, **kwargs):
        super().__init__(**kwargs)
        self.title = _('Choose directory')
        self._build_content(path or '.')

    def _build_content(self, path: str):
        content = BoxLayout(orientation='vertical')

        path_container = BoxLayout(
            padding=(10, 5, 0, 0),
            size_hint_y=None,
            height=40,
        )
        self.path_label = Label(
            text=path,
            halign='left',
            valign='middle',
        )
        self.path_label.bind(
            size=lambda *_: setattr(self.path_label, 'text_size', self.path_label.size),
        )
        def _update_path_label_text_size(*_):
            self.path_label.text_size = self.path_label.size
        _update_path_label_text_size()
        path_container.add_widget(self.path_label)

        self.filechooser = FileChooserListViewCurrentDir(path=path, dirselect=True, filters=['*.mbtiles'], size_hint_y=0.9)
        self.filechooser.bind(
            on_entry_added=self._update_entry_height,
            on_subentry_to_entry=self._update_entry_height,
            path=self._on_path_change,
            selection=self._on_selection_change,
        )
        self.selected_dir = self.filechooser.path
        self.submit_btn = Button(text=_('Select'), on_release=self._submit, size_hint_y=0.1)

        content.add_widget(path_container)
        content.add_widget(self.filechooser)
        content.add_widget(self.submit_btn)
        self.content = content

    def _on_path_change(self, _, path):
        self.path_label.text = path

    def _on_selection_change(self, _, selection):
        if selection:
            self.path_label.text = selection[0]

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
