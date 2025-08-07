import inspect

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
            'if not self.collide_point(*touch.pos):',
            'if not self.collide_point(*touch.pos) or self.disabled:',
        )
    ]
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
