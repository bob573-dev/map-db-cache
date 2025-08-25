from pathlib import Path

from kivy.core.window import Window
from kivy.app import App
from kivy_garden.mapview import MapView
from kivy_garden.mapview.mbtsource import MBTilesMapSource

from consts import DEFAULT_MAPS_DIRECTORY, DEFAULT_MAP_BASENAME

DEFAULT_FILE = Path(DEFAULT_MAPS_DIRECTORY) / f'{DEFAULT_MAP_BASENAME}.mbtiles'
Window.show_cursor = True

class PreviewMapApp(App):
    def __init__(self, file: str, **kwargs):
        super().__init__(**kwargs)
        self.filepath = Path(file)
        self.title = f"Preview {self.filepath.absolute()}"

    def build(self):
        path = self.filepath
        if path.exists() and path.is_file() and path.suffix == '.mbtiles':
            print(f'Preview "{path.absolute()}" file')
            source = MBTilesMapSource(path)
            return MapView(map_source=source)
        print(f'Error: "{path}" does not exists or is not a valid file')
        sys.exit()


if __name__ == '__main__':
    import sys

    filename = DEFAULT_FILE
    if len(sys.argv) > 1:
        filename = sys.argv[1]

    PreviewMapApp(file=filename).run()
