import math

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.graphics import Color, Line, Scale, Translate
from kivy.logger import Logger
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty
from kivy.uix.floatlayout import FloatLayout
from kivy_garden.mapview import MapView, MapLayer, MapMarker
from kivy_garden.mapview.source import MapSource
from kivy_garden.mapview.utils import clamp

from consts import (DEFAULT_LAT, DEFAULT_LON, ZOOM_IN_PNG, ZOOM_OUT_PNG, MIN_LONGITUDE, MAX_LONGITUDE, MAX_LATITUDE,
    MIN_LATITUDE, MIN_CENTER_LATITUDE, MAX_CENTER_LONGITUDE, MAX_CENTER_LATITUDE, MIN_CENTER_LONGITUDE)
from mbtiles import DEFAULT_TILES_SUBDOMAINS
from mbtiles.utils import latlon_to_tile_xy
from tools.binding_manager import BindingManager
from tools.geometry import pointRadialDistance
from tools.quadkey_url import QuadKeyUrl
from uix import ButtonImage, BoxLayoutAutoresized


class MapMarkerSized(MapMarker):
    marker_size = NumericProperty(30)

    def __init__(self, **kwargs):
        kwargs.setdefault('opacity', 1.0)
        kwargs.setdefault('size_hint', (None, None))
        super(MapMarkerSized, self).__init__(**kwargs)
        self.height = self.marker_size
        self.bind(height=self._update_size)

    def _update_size(self, *args):
        self.height = self.marker_size
        Logger.debug("Map: marker resized {}".format(self.size))


class DrawersMapLayer(MapLayer):
    """
    self drawing MapLayer with a collection of separate drawers.

    origin point used to keep relative coordinates closer to zero.
    (and therefore avoid some float precision issues when drawing lines)
    Since lat is not a linear transform we must compute manually
    """
    origin_lat = NumericProperty(None, allownone=True)
    origin_lon = NumericProperty(None, allownone=True)

    class LayerDrawer(EventDispatcher):
        def __init__(self, layer, **kwargs):
            super().__init__(**kwargs)
            assert isinstance(layer, DrawersMapLayer)
            self._layer = layer
            layer.add_drawer(self)
        def unload(self):
            self._layer = None
        def init_canvas(self, canvas):
            pass
        def invalidate(self, *args):
            self._layer.invalidate_draw()
        def recalc(self):
            pass
        def draw(self):
            pass
        def unload(self):
            pass

    def __init__(self, **kwargs):
        self._trigger_draw = Clock.create_trigger(self._draw)
        super().__init__(**kwargs)
        self._zoom = 0
        self.ms = 0
        self._draw_offset = None
        self.scale_1 = Scale()
        self.trans_1 = Translate()
        self.scale_2 = Scale()
        self.trans_2 = Translate()
        self.trans_3 = Translate()
        self.trans_4 = Translate()
        self._drawers = []

    def unload(self):
        for d in self._drawers:
            d.unload()
        self._drawers = []
        self._trigger_draw.cancel()

    def add_drawer(self, drawer:LayerDrawer):
        assert isinstance(drawer, DrawersMapLayer.LayerDrawer)
        self._drawers.append(drawer)

    def _init_canvas(self, *_):
        self.canvas.clear()
        with self.canvas:
            self.canvas.add(self.scale_1)
            self.canvas.add(self.trans_1)
            self.canvas.add(self.scale_2)
            self.canvas.add(self.trans_2)
            self.canvas.add(self.trans_3)
            self.canvas.add(self.trans_4)
            for d in self._drawers:
                d.init_canvas(self.canvas)

    def on_parent(self, *_):
        assert isinstance(self.parent, MapView) or self.parent is None
        if self.parent:
            self.parent.bind(
                delta_x=self._trigger_draw,
                delta_y=self._trigger_draw,
                )

    def reposition(self):
        """Function called when :class:`MapView` is moved. You must recalculate the position of your children."""
        mapview = self.parent
        if self._zoom != mapview.zoom:
            map_source = mapview.map_source
            self.ms = pow(2.0, mapview.zoom) * map_source.dp_tile_size
            self.invalidate_draw()
            self._init_canvas()

    def unload(self):
        """Called when the view want to completly unload the layer."""
        self._trigger_draw.cancel()
        self._zoom = 0
        for d in self._drawers:
            d.unload()
        self._drawers = []

    def invalidate_draw(self, *_):
        self._draw_offset = None
        self._trigger_draw()

    def recalculate_draw(self, *_):
        mapview = self.parent
        self._zoom = mapview.zoom
        self._draw_offset = (
            self._get_x(self.origin_lat or 0),
            self._get_y(self.origin_lon or 0)
            )
        for d in self._drawers:
            d.recalc()

    def get_xy(self, lat, lon):
        """Get the x,y position on widget canvas the coordinates (lat,lon)"""
        return self._get_x(lon) - self._draw_offset[0], self._get_y(lat) - self._draw_offset[1]

    def _get_x(self, lon):
        """Get the x position on the map using this map source's projection (0, 0) is located at the top left."""
        return clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE) * self.ms / 360.0

    def _get_y(self, lat):
        """Get the y position on the map using this map source's projection (0, 0) is located at the top left."""
        if lat >= MAX_LATITUDE or lat <= MIN_LATITUDE:
            return 0
        lat = math.radians(-lat)
        return (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) * self.ms / 2.0

    def _draw(self, *_):
        mapview = self.parent
        scatter = mapview._scatter
        vx, vy, vs = mapview.viewport_pos[0], mapview.viewport_pos[1], mapview.scale
        sx, sy, ss = scatter.x - mapview.x, scatter.y - mapview.y, scatter.scale
        if self._draw_offset is None: self.recalculate_draw()

        self.scale_1.xyz = 1 / ss, 1 / ss, 1
        self.trans_1.xy = -sx, -sy
        self.scale_2.xyz = vs, vs, 1
        self.trans_2.xy = -vx, -vy
        self.trans_3.xy = self.ms / 2, 0
        self.trans_4.xy = self._draw_offset

        for d in self._drawers:
            d.draw()


class CenteredAreaDrawer(DrawersMapLayer.LayerDrawer):
    center_lat = NumericProperty(None, allownone=True)
    center_lon = NumericProperty(None, allownone=True)
    side_in_km = NumericProperty(None, allownone=True)
    bottom_left_lat = NumericProperty(None, allownone=True)
    bottom_left_lon = NumericProperty(None, allownone=True)
    top_right_lat = NumericProperty(None, allownone=True)
    top_right_lon = NumericProperty(None, allownone=True)
    line_width = NumericProperty(1.5)
    color = ListProperty((.9, 0, 0, .8))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._color = Color(*self.color)
        self._points = []
        self._lines = Line(width=self.line_width)
        self.bind(
            center_lat=self.invalidate,
            center_lon=self.invalidate,
            side_in_km=self.invalidate,
            )
        self.canvas = None

    def init_canvas(self, canvas):
        canvas.add(self._color)
        canvas.add(self._lines)

    def recalc(self):
        if self.center_lat is None or self.center_lon is None or self.side_in_km is None:
            self._points = []
            self.bottom_left_lat = None
            self.bottom_left_lon = None
            self.top_right_lat = None
            self.top_right_lon = None
            return
        self._points = self._calc_rectangle_points()

    def _calc_rectangle_points(self):
        side = self.side_in_km
        bottom_center_coords = pointRadialDistance(self.center_lat, self.center_lon, 180, side/2)

        bottom_right_coords = pointRadialDistance(*bottom_center_coords, 90, side/2)
        top_right_coords = pointRadialDistance(*bottom_right_coords, 0, side)
        top_left_coords = pointRadialDistance(*top_right_coords, 270, side)
        bottom_left_coords = pointRadialDistance(*top_left_coords, 180, side)

        self.bottom_left_lat = bottom_left_coords[0]
        self.bottom_left_lon = bottom_left_coords[1]
        self.top_right_lat = top_right_coords[0]
        self.top_right_lon = top_right_coords[1]

        layer = self._layer
        bottom_left = layer.get_xy(*bottom_left_coords)
        return (
            *bottom_left,
            *layer.get_xy(*top_left_coords),
            *layer.get_xy(*top_right_coords),
            *layer.get_xy(*bottom_right_coords),
            *layer.get_xy(*bottom_right_coords),
            *bottom_left,
        )

    def draw(self):
        self._lines.points = self._points


class MapPanel(FloatLayout):
    url = StringProperty()
    subdomains = ListProperty(DEFAULT_TILES_SUBDOMAINS)
    attribution = StringProperty(None, allownone=True)
    zoom = NumericProperty(5)
    markers_size = NumericProperty(30)
    precision = NumericProperty(6)
    buttons_size = ListProperty([44, 44])
    center_lat = NumericProperty(None, allownone=True)
    center_lon = NumericProperty(None, allownone=True)
    side_in_km = NumericProperty(None, allownone=True)
    bottom_left_lat = NumericProperty(None, allownone=True)
    bottom_left_lon = NumericProperty(None, allownone=True)
    top_right_lat = NumericProperty(None, allownone=True)
    top_right_lon = NumericProperty(None, allownone=True)
    bbox = ListProperty(None, allownone=True)

    center_selection = BooleanProperty(False)
    __events__ = ['on_center_selected']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._center_marker = None
        self._drawers_layer = None
        self._center_drawer = None
        self.map_view = None
        self._bindings = BindingManager()
        self._trigger_center = Clock.create_trigger(self._center)
        self._trigger_update_map = Clock.create_trigger(self._update_map)
        self._trigger_on_center_changed = Clock.create_trigger(self._on_center_changed)
        self._trigger_update_bbox = Clock.create_trigger(self._update_bbox)
        self._init_map_view()
        self._init_buttons()
        self.bind(
            center_selection=self._on_center_selection,
            center_lat=self._trigger_on_center_changed,
            center_lon=self._trigger_on_center_changed,
            url=self._trigger_update_map,
            attribution=self._trigger_update_map,
            subdomains=self._trigger_update_map,
            bottom_left_lat=self._trigger_update_bbox,
            bottom_left_lon=self._trigger_update_bbox,
            top_right_lat=self._trigger_update_bbox,
            top_right_lon=self._trigger_update_bbox,
            bbox=self._on_bbox_changed,
        )

    def _update_map(self, *_):
        self._bindings.unbind_items()
        self._init_map_view()
        self._init_buttons()
        self._trigger_center()

    def _init_map_view(self):
        lat = DEFAULT_LAT
        lon = DEFAULT_LON
        if self.map_view:
            map_view = self.map_view
            if map_view.parent is self:
                self.remove_widget(map_view)
            lat = map_view.lat
            lon = map_view.lon

        url = QuadKeyUrl.from_url(self.url)
        self.map_source = MapSource(url=url, attribution=self.attribution, subdomains=self.subdomains)
        self.set_zoom(self.zoom)
        self.map_view = map_view = MapView(
            map_source=self.map_source,
            lat=lat, lon=lon,
            zoom=self.zoom,
        )
        self.add_widget(map_view)
        self._bindings.bind_item(map_view, 'zoom', self.setter('zoom'))
        self._bindings.bind_item(self, 'zoom', map_view.setter('zoom'))
        self._init_drawers(map_view)
        self._on_center_changed()

    def _init_drawers(self, mapview):
        self._drawers_layer = DrawersMapLayer()
        self._init_area_drawer(self._drawers_layer)
        mapview.add_layer(self._drawers_layer, "scatter")

    def _init_area_drawer(self, drawers_layer):
        self._center_drawer = drawer = CenteredAreaDrawer(
            layer=drawers_layer,
            center_lat=self.center_lat,
            center_lon=self.center_lon,
            side_in_km=self.side_in_km,
        )
        self._bindings.bind_item(self, 'center_lat', drawer.setter("center_lat"))
        self._bindings.bind_item(self, 'center_lon', drawer.setter("center_lon"))
        self._bindings.bind_item(self, 'side_in_km', drawer.setter("side_in_km"))
        self._bindings.bind_item(drawer, 'bottom_left_lat', self.setter("bottom_left_lat"))
        self._bindings.bind_item(drawer, 'bottom_left_lon', self.setter("bottom_left_lon"))
        self._bindings.bind_item(drawer, 'top_right_lat', self.setter("top_right_lat"))
        self._bindings.bind_item(drawer, 'top_right_lon', self.setter("top_right_lon"))

    def _init_buttons(self):
        buttons_container = BoxLayoutAutoresized(
            orientation='vertical',
            background=(0, 0, 0, 0),
            spacing=3,
            pos=(3, 3),
        )
        zoom_in_container = BoxLayoutAutoresized(
            padding=2,
            background=(.95, .95, .95, .75),
        )
        zoom_out_container = BoxLayoutAutoresized(
            padding=2,
            background=(.95, .95, .95, .75),
        )
        zoom_in_btn = ButtonImage(
            image=ZOOM_IN_PNG,
            size_hint=(None, None),
            size=self.buttons_size,
        )
        zoom_out_btn = ButtonImage(
            image=ZOOM_OUT_PNG,
            size_hint=(None, None),
            size=self.buttons_size,
        )
        self._bindings.bind_item(zoom_in_btn, 'on_release', self.zoom_in)
        self._bindings.bind_item(zoom_out_btn, 'on_release', self.zoom_out)

        zoom_in_container.add_widget(zoom_in_btn)
        zoom_out_container.add_widget(zoom_out_btn)

        buttons_container.add_widget(zoom_in_container)
        buttons_container.add_widget(zoom_out_container)
        self.add_widget(buttons_container)

    def _on_center_selection(self, _, center_selection):
        map_view = self.map_view
        if center_selection:
            self._bindings.bind_item(map_view, 'on_touch_down', self._select_center_on_touch)
            Logger.debug('Center selection on_touch_downd binded')
        else:
            self._bindings.unbind_item(map_view, 'on_touch_down', self._select_center_on_touch)
            Logger.debug('Center selection on_touch_downd unbinded')

    def _select_center_on_touch(self, _, touch):
        lat_lon = self.map_view.get_latlon_at(*touch.pos)
        self.center_lat = round(clamp(lat_lon[0], MIN_CENTER_LATITUDE, MAX_CENTER_LATITUDE), self.precision)
        self.center_lon = round(clamp(lat_lon[1], MIN_CENTER_LONGITUDE, MAX_CENTER_LONGITUDE), self.precision)
        self.dispatch('on_center_selected')

    def on_center_selected(self, *args):
        self.center_selection = False
        Logger.debug(f'Center selected: {self.center_lat}, {self.center_lon}')

    def _on_center_changed(self, *_):
        if self._center_marker:
            self.map_view.remove_marker(self._center_marker)
        if self.center_lat is None or self.center_lon is None:
            self._center_marker = None
        else:
            self._center_marker= MapMarkerSized(
                lat=self.center_lat,
                lon=self.center_lon,
                marker_size=self.markers_size,
            )
            self.map_view.add_marker(self._center_marker)

    def _update_bbox(self, *_):
        bbox = (self.bottom_left_lat, self.bottom_left_lon, self.top_right_lat, self.top_right_lon)
        if None in bbox:
            self.bbox = None
        else:
            self.bbox = bbox
        Logger.debug(f'bbox updated: {self.bbox}')

    def _on_bbox_changed(self, *_):
        if self.bbox:
            max_fit_zoom = self.get_max_zoom_for_bbox(self.bbox)
            self.set_zoom(max_fit_zoom -1)
            self._center()

    def get_max_zoom_for_bbox(self, bbox, max_zoom=19):
        min_lat, min_lon, max_lat, max_lon = bbox
        for zoom in reversed(range(max_zoom +1)):
            x1, y1 = latlon_to_tile_xy(min_lat, min_lon, zoom)
            x2, y2 = latlon_to_tile_xy(max_lat, max_lon, zoom)
            width_px = (x2 - x1) * self.map_source.dp_tile_size
            height_px = (y2 - y1) * self.map_source.dp_tile_size
            if width_px <= self.map_view.width and height_px <= self.map_view.height:
                return zoom
        return 0

    def set_zoom(self, zoom):
        self.zoom = clamp(zoom, self.map_source.get_min_zoom(), self.map_source.get_max_zoom())

    def zoom_in(self, *_):
        self.set_zoom(self.zoom + 1)

    def zoom_out(self, *_):
        self.set_zoom(self.zoom - 1)

    def _center(self, *_):
        if self.center_lat is not None and self.center_lon is not None:
            self.map_view.center_on(self.center_lat, self.center_lon)
