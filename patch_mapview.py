import inspect

from kivy_garden.mapview.downloader import Downloader
from kivy_garden.mapview.mbtsource import MBTilesMapSource
from kivy_garden.mapview import MapView


PATCHES = {
    inspect.getfile(MBTilesMapSource): [
        (
            'self.bounds = bounds = map(float, metadata["bounds"].split(","))',
            'self.bounds = bounds = list(map(float, metadata["bounds"].split(",")))',
        ),
        (
            'cx, cy, cz = map(float, metadata["center"].split(","))',
            'cx, cy, cz = list(map(float, metadata["center"].split(",")))',
        ),
    ],
    inspect.getfile(MapView): [
        (
            'from kivy.uix.image import Image',
            ('from kivy.uix.image import Image\n'
             'from kivy.core.image import Image as CoreImage'),
        ),
        (
            'def set_source(self, cache_fn):',
            ('def set_source(self, cache_fn, retry=3, delay=0.05):\n'
             '        try:\n'
             '            CoreImage(cache_fn)'),
        ),
        (
            'self.source = cache_fn',
            '    self.source = cache_fn',
        ),
        (
            'self.state = "need-animation"',
            ('    self.state = "need-animation"\n'
             '        except:\n'
             '            if retry > 0:\n'
             '                Clock.schedule_once(lambda dt: self.set_source(cache_fn, retry-1), delay)\n'
             '            else:\n'
             '                raise'),
        ),
        (
            'if not self.collide_point(*touch.pos):',
            'if not self.collide_point(*touch.pos) or self.disabled:',
        ),
        (
            '                # animate to the closest zoom\n',
            '',
        ),
        (
            '                zoom, scale = self._touch_zoom\n',
            '',
        ),
        (
            '                cur_zoom = self.zoom\n',
            '',
        ),
        (
            '                cur_scale = self._scale\n',
            '',
        ),
        (
            '                if cur_zoom < zoom or cur_scale < scale:\n',
            '',
        ),
        (
            '                    self.animated_diff_scale_at(1.0 - cur_scale, *touch.pos)\n',
            '',
        ),
        (
            '                elif cur_zoom > zoom or cur_scale > scale:\n',
            '',
        ),
        (
            '                    self.animated_diff_scale_at(2.0 - cur_scale, *touch.pos)\n',
            '                # Buggy behaviour was removed\n',
        ),
    ],
    inspect.getfile(Downloader): [
        (
            'from os import environ, makedirs',
            'from os import environ, makedirs, replace',
        ),
        (
            'traceback.print_exc()',
            'Logger.debug("Downloader: exception occurred while retrieving future result")',
        ),
        (
            'with open(cache_fn, "wb") as fd:',
            'tmp_fn = cache_fn + ".part"\n            with open(tmp_fn, "wb") as fd:',
        ),
        (
            'fd.write(data)',
            'fd.write(data)\n            replace(tmp_fn, cache_fn)',
        ),
    ],
}


def replace(filename, patches_list: list[tuple[str, str]]):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(filename, "w", encoding="utf-8") as f:
        for line in lines:
            new_line = line
            for _old, _new in patches_list:
                new_line = new_line.replace(_old, _new)
            f.write(new_line)


if __name__ == '__main__':
    for file, patches in PATCHES.items():
        replace(file, patches)
