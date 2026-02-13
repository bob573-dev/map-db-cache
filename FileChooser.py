from pathlib import Path
from os.path import sep
from typing import Optional
from weakref import ref

from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.text import Label as CoreLabel
from kivy.logger import Logger

from localization import _
from tools.utils import check_filepath_valid
from uix import ErrorPopup


class FileChooserListViewCurrentDir(FileChooserListView):
    def _generate_file_entries(self, *args, **kwargs):
        path = kwargs.get('path', self.path)
        if kwargs.get('parent', None) is None:
            pardir = self._create_entry_widget(
                dict(
                    name='.' + sep,
                    size='',
                    path=Path(path).absolute(),
                    controller=ref(self),
                    isdir=False,
                    parent=None,
                    sep=sep,
                    get_nice_size=lambda: '',
                )
            )
            yield 0, 1, pardir

        yield from super()._generate_file_entries(*args, **kwargs)


class FileChooserPopup(Popup):
    selected_dir = StringProperty('')
    selected_file = StringProperty('')
    clicked_path = StringProperty('')
    entry_height = 40
    __events__ = ['on_submit']

    def __init__(self, path: str, **kwargs):
        kwargs.setdefault('auto_dismiss', False)
        super().__init__(**kwargs)
        self.title = _('Choose directory')
        self._build_content(path or '.')

    def _build_content(self, path: str):
        content = BoxLayout(orientation='vertical')

        self.header_container = BoxLayout(
            padding=(10, 5, 0, 0),
            size_hint_y=None,
            size_hint_x=1,
            height=self.entry_height,
            spacing=5,
        )

        self.path_label = path_label = Label(
            text=path,
            halign='left',
            valign='middle',
        )

        def _update_path_label_text_size(*_):
            path_label.text_size = path_label.size

        _update_path_label_text_size()
        path_label.bind(size=_update_path_label_text_size)
        path_label.bind(size=self._update_path_label_text)
        self.bind(clicked_path=self._update_path_label_text)
        self.header_container.add_widget(path_label)

        new_folder_layout = self._build_new_folder_layout()
        self.header_container.add_widget(new_folder_layout)

        self.filechooser = FileChooserListViewCurrentDir(
            path=path,
            dirselect=True,
            filters=['*.mbtiles'],
            size_hint_y=0.9,
        )
        self.filechooser.bind(
            on_entry_added=self._update_entry_height,
            on_subentry_to_entry=self._update_entry_height,
            path=self._on_path_change,
            selection=self._on_selection_change,
        )
        self.selected_dir = self.filechooser.path
        self.clicked_path = self.filechooser.path

        buttons_container = BoxLayout(size_hint_y=0.1)
        cancel_btn = Button(text=_('Cancel'), on_release=self.dismiss, size_hint_x=0.5)
        submit_btn = Button(text=_('OK'), on_release=self._submit, size_hint_x=0.5)
        buttons_container.add_widget(cancel_btn)
        buttons_container.add_widget(submit_btn)

        content.add_widget(self.header_container)
        content.add_widget(self.filechooser)
        content.add_widget(buttons_container)
        self.content = content

    def _build_new_folder_layout(self):
        self.new_folder_layout = BoxLayout(size_hint_x=None, spacing=5)
        self.new_folder_layout.bind(minimum_width=self.new_folder_layout.setter('width'))

        self.new_folder_input = TextInput(size_hint_x=None, width=0, opacity=0, multiline=False)
        self.new_folder_layout.add_widget(self.new_folder_input)

        self.create_folder_btn = Button(
            text=_('Create folder'),
            size_hint_x=None,
            width=130,
            on_release=self._create_folder_request,
        )
        self.new_folder_layout.add_widget(self.create_folder_btn)

        self.cancel_creation_btn = Button(
            text=_('Cancel'),
            size_hint_x=None,
            width=95,
            on_release=self._reset_btns_container,
        )
        self.submit_creation_btn = Button(
            text=_('Create'),
            size_hint_x=None,
            width=95,
            on_release=self._submit_folder_creation,
        )

        return self.new_folder_layout

    def _create_folder_request(self, *_):
        self.new_folder_layout.remove_widget(self.create_folder_btn)
        if self.cancel_creation_btn not in self.new_folder_layout.children:
            self.new_folder_layout.add_widget(self.cancel_creation_btn)
        if self.submit_creation_btn not in self.new_folder_layout.children:
            self.new_folder_layout.add_widget(self.submit_creation_btn)
        self._show_new_folder_input()

    def _show_new_folder_input(self, show=True):
        if show:
            self.new_folder_input.focus = True
            self.new_folder_input.opacity = 1
            self.header_container.bind(width=self._update_new_folder_input_size)
            self._update_new_folder_input_size()
        else:
            self.header_container.unbind(width=self._update_new_folder_input_size)
            self.new_folder_input.opacity = 0
            self.new_folder_input.width = 0

    def _update_new_folder_input_size(self, *_):
        self.new_folder_input.width = max(
            (
                self.header_container.width / 2
                - self.cancel_creation_btn.width
                - self.submit_creation_btn.width
                - self.header_container.spacing * 2
            ),
            110,
        )

    def _reset_btns_container(self, *_):
        self.new_folder_layout.remove_widget(self.cancel_creation_btn)
        self.new_folder_layout.remove_widget(self.submit_creation_btn)
        if self.create_folder_btn not in self.new_folder_layout.children:
            self.new_folder_layout.add_widget(self.create_folder_btn)
        self._show_new_folder_input(False)

    def _submit_folder_creation(self, *_):
        if folder_path := self._create_folder_safely():
            folder_path_str = str(folder_path)
            self.filechooser.path = folder_path_str
            self.filechooser.selection = [folder_path_str]
            self._reset_btns_container()

    def _update_path_label_text(self, *_):
        full_text = self.clicked_path
        label = self.path_label
        max_width = label.width
        core = CoreLabel(
            font_name=label.font_name,
            font_size=label.font_size,
            bold=label.bold,
            italic=label.italic,
        )

        core.text = full_text
        core.refresh()
        if core.texture.size[0] <= max_width:
            label.text = full_text
            return

        text = full_text
        while text:
            core.text = "…" + text
            core.refresh()
            if core.texture.size[0] <= max_width:
                break
            text = text[1:]
        label.text = "…" + text

    def _update_entry_height(self, _, entry, __):
        entry.height = self.entry_height

    def _on_path_change(self, _, path):
        self.clicked_path = path

    def _on_selection_change(self, _, selection):
        if selection:
            self.clicked_path = selection[0]

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

    def _create_folder_safely(self, *args) -> Optional[Path]:
        try:
            path = Path(self.clicked_path)
            if path.is_file():
                path = path.parent
            dir_name = self.new_folder_input.text.strip()
            if not dir_name:
                self._show_error_popup(_('Input folder name'))
                return None
            if not check_filepath_valid(dir_name):
                self._show_error_popup(_('Failed to create folder') + ': ' + _('invalid name'))
                return None
            dir_path = path / dir_name
            if dir_path.exists():
                self._show_error_popup(_('Failed to create folder') + ': ' + _('already exists'))
                return None
            dir_path.mkdir()
            return dir_path
        except Exception as exc:
            Logger.warning(f'FileChooserPopup: An error occurred while creating the folder.', exc_info=exc)
            self._show_error_popup(_('Failed to create folder'))
            return None

    @staticmethod
    def _show_error_popup(message: str):
        popup = ErrorPopup(
            text=message,
            size_hint=(0.3, 0.2),
            auto_dismiss=True,
        )
        popup.open()

    def open(self, *_args, **kwargs):
        self._reset_btns_container()
        self.new_folder_input.text = ''
        super().open(*_args, **kwargs)
