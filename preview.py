import io
import math
import sqlite3
from pathlib import Path

from PIL import Image, TiffTags
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import NumericProperty, ReferenceListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy_garden.mapview import MapView
from kivy_garden.mapview.mbtsource import MBTilesMapSource

from consts import DEFAULT_MAPS_DIRECTORY, DEFAULT_MAP_BASENAME

DEFAULT_FILE = Path(DEFAULT_MAPS_DIRECTORY) / f'{DEFAULT_MAP_BASENAME}.mbtiles'
Window.show_cursor = True


class MapViewElevation(MapView):
    elevation = NumericProperty(None, allownone=True)
    selected_lat = NumericProperty(None, allownone=True)
    selected_lon = NumericProperty(None, allownone=True)
    selected_coords = ReferenceListProperty(selected_lat, selected_lon)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left':
            if self.map_source and hasattr(self.map_source, 'filename'):
                self.selected_coords = lat, lon = self.get_latlon_at(*self.to_local(*touch.pos, relative=True))
                self.elevation = self.get_merged_elevation((lat, lon), filename=self.map_source.filename)
        return super().on_touch_up(touch)

    def get_merged_elevation(self, coords, filename):
        lat, lon = coords
        path = Path(filename)
        if path.is_file():
            try:
                with sqlite3.connect(filename) as db:
                    cursor = db.cursor()
                    data = list(
                        cursor.execute(
                            """SELECT *
                            FROM dem_tiles
                            WHERE min_lon <= :lon AND max_lon >= :lon
                              AND min_lat <= :lat AND max_lat >= :lat
                            LIMIT 1;""",
                            {"lon": lon, "lat": lat},
                        )
                    )
                tif_bytes = data[0][-1]
            except Exception:
                return None
            return self.elevation_from_tiff_bytes(tif_bytes, lat, lon)
        else:
            print(f'{filename} does not exists or is not a valid file')
        return None

    @staticmethod
    def elevation_from_tiff_bytes(tiff_bytes: bytes, lat: float, lon: float):
        try:
            img = Image.open(io.BytesIO(tiff_bytes))
            tags = {TiffTags.TAGS.get(k, k): v for k, v in img.tag.items()}

            scaleX, scaleY, _ = tags.get('ModelPixelScaleTag')
            tie = tags.get('ModelTiepointTag')

            i, j, k, x0, y0, z0 = tie

            # EXPLANATION:
            # x0, y0 — geocoordinates of the upper-left CORNER (not the center) 0,0 pixels
            # scaleX, scaleY — pixel size in coordinates
            # y is counted from the bottom → row is calculated as (y0 - lat)
            px = math.floor((lon - x0) / scaleX)
            py = math.floor((y0 - lat) / scaleY)
            if px < 0 or py < 0:
                return None

            try:
                return img.getpixel((px, py))
            except IndexError:
                return None
        except Exception as exc:
            print(f'elevation extraction failed: {exc}')
            return None

    @staticmethod
    def get_elevation_bounds(tiff_bytes: bytes):
        img = Image.open(io.BytesIO(tiff_bytes))
        tags = {TiffTags.TAGS.get(k, k): v for k, v in img.tag.items()}

        tie = tags["ModelTiepointTag"]
        i, j, k, x0, y0, z0 = tie

        scale = tags["ModelPixelScaleTag"]
        pixel_x, pixel_y = scale[0], scale[1]
        width, height = tags["ImageWidth"][0], tags["ImageLength"][0]

        min_lon = x0
        max_lon = x0 + width * pixel_x
        max_lat = y0
        min_lat = y0 - height * pixel_y
        return min_lat, min_lon, max_lat, max_lon


class PreviewMapApp(App):
    def __init__(self, file: str, **kwargs):
        super().__init__(**kwargs)
        self.filepath = Path(file)
        self.title = f'Preview {self.filepath.absolute()}'

    def build(self):
        root = BoxLayout(orientation='vertical')
        path = self.filepath
        if path.exists() and path.is_file() and path.suffix == '.mbtiles':
            print(f'Preview "{path.absolute()}" file')
            source = MBTilesMapSource(path)
            mapview = MapViewElevation(map_source=source, size_hint_y=0.9)

            labels_container = BoxLayout(size_hint_y=0.1)
            coords_label = Label(size_hint_x=0.5)
            elevation_label = Label(size_hint_x=0.5)

            def update_labels(*args):
                print(f'Coords: {mapview.selected_coords}\t' f'Altitude: {mapview.elevation}')
                coords_label.text = (
                    f'Coords: {tuple(map(lambda coord: round(coord, 6) if coord else coord, mapview.selected_coords))}'
                )
                elevation_label.text = f'Altitude: {mapview.elevation}'

            trigger_update_labels = Clock.create_trigger(update_labels)
            mapview.bind(
                selected_coords=trigger_update_labels,
                elevation=trigger_update_labels,
            )
            trigger_update_labels()

            labels_container.add_widget(coords_label)
            labels_container.add_widget(elevation_label)
            root.add_widget(mapview)
            root.add_widget(labels_container)
            return root
        print(f'Error: "{path}" does not exists or is not a valid file')
        sys.exit()


if __name__ == '__main__':
    import sys

    filename = DEFAULT_FILE
    if len(sys.argv) > 1:
        filename = sys.argv[1]

    PreviewMapApp(file=filename).run()
