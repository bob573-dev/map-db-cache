from enum import StrEnum

from localization import _


class _ValuesMixin:
    @classmethod
    def values(cls) -> list:
        return list(cls)


class MapContent(_ValuesMixin, StrEnum):
    MAP_WITH_ELEVATION = _('Map + elevation')
    ONLY_MAP = _('Only map')
    ONLY_ELEVATION = _('Only elevation')
