from dataclasses import dataclass

from kivy_garden.mapview.source import MapSource

from mbtiles import DEFAULT_TILES_SUBDOMAINS, DEFAULT_TILE_FORMAT, DEFAULT_TIMEOUT
from tools.utils import current_year

DEFAULT_PROVIDER = 'Google Satellite'
KIVY_USER_AGENT = 'Kivy-garden.mapview'
BROWSER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0'
GOOGLE_TIMEOUT = 0.05
BING_TIMEOUT = 0.2
ESRI_TIMEOUT = 0.025

@dataclass
class ProviderData:
    min_zoom: int
    max_zoom: int
    url: str
    attribution: str = ''
    subdomains: tuple = tuple(DEFAULT_TILES_SUBDOMAINS)
    format: str = DEFAULT_TILE_FORMAT
    user_agent: str = BROWSER_USER_AGENT
    timeout: float = DEFAULT_TIMEOUT


PROVIDERS = {
    "Google Satellite": ProviderData(
        min_zoom=0,
        max_zoom=19,
        url='http://mt{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=uk',
        attribution=f'Map data ©{current_year()} Google',
        subdomains=('0', '1', '2', '3'),
        timeout=GOOGLE_TIMEOUT,
    ),
    'Bing Satellite': ProviderData(
        min_zoom = 1,
        max_zoom = 19,
        url = 'http://ak.dynamic.t{s}.tiles.virtualearth.net/comp/ch/{key}?mkt=uk-UA&it=A,G,L&shading=hill&og=8&n=z',
        subdomains=('1', '2', '3'),
        format='image/jpeg',
        timeout=BING_TIMEOUT,
    ),
    'Bing Satellite 2': ProviderData(
        min_zoom = 1,
        max_zoom = 19,
        url = 'http://ecn.t{s}.tiles.virtualearth.net/tiles/h{key}?g=761&mkt=en-us',
        subdomains=('1', '2', '3'),
        format='image/jpeg',
        timeout=BING_TIMEOUT,
    ),
    'Esri ArcGIS Satellite': ProviderData(
        min_zoom = 0,
        max_zoom = 19,
        url = 'https://server.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attribution="© Esri",
        format='image/jpeg',
        timeout=ESRI_TIMEOUT,
    ),
    "OpenTopoMap": ProviderData(
        min_zoom = 4,
        max_zoom = 17,
        url = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attribution = '© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)',
    ),
    'Thunderforest Landscape': ProviderData(
        min_zoom = MapSource.providers.get('thunderforest-landscape')[1],
        max_zoom = MapSource.providers.get('thunderforest-landscape')[2],
        url = MapSource.providers.get('thunderforest-landscape')[3],
        attribution = MapSource.providers.get('thunderforest-landscape')[4],
        user_agent = KIVY_USER_AGENT,
    ),
    'Thunderforest Outdoors': ProviderData(
        min_zoom = MapSource.providers.get('thunderforest-outdoors')[1],
        max_zoom = MapSource.providers.get('thunderforest-outdoors')[2],
        url = MapSource.providers.get('thunderforest-outdoors')[3],
        attribution = MapSource.providers.get('thunderforest-outdoors')[4],
        user_agent = KIVY_USER_AGENT,
    ),
    'Esri Topomap': ProviderData(
        min_zoom=0,
        max_zoom=19,
        url='https://server.arcgisonline.com/arcgis/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attribution="© Esri",
        format='image/jpeg',
        timeout=ESRI_TIMEOUT,
    ),
    'OSM': ProviderData(
        min_zoom = MapSource.providers.get('osm')[1],
        max_zoom = MapSource.providers.get('osm')[2],
        url = MapSource.providers.get('osm')[3],
        attribution = MapSource.providers.get('osm')[4],
        user_agent = KIVY_USER_AGENT,
    ),
    'OSM Hot': ProviderData(
        min_zoom = MapSource.providers.get('osm-hot')[1],
        max_zoom = MapSource.providers.get('osm-hot')[2],
        url = MapSource.providers.get('osm-hot')[3],
        attribution = MapSource.providers.get('osm-hot')[4],
        user_agent = KIVY_USER_AGENT,
    ),
    'Esri ArcGIS Streets': ProviderData(
        min_zoom=0,
        max_zoom=19,
        url='https://server.arcgisonline.com/arcgis/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attribution="© Esri",
        format='image/jpeg',
        timeout=ESRI_TIMEOUT,
    ),
    "Google Terrain": ProviderData(
        min_zoom=0,
        max_zoom=19,
        url='http://mt{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}&hl=uk',
        attribution=f'Map data ©{current_year()} Google',
        subdomains=('0', '1', '2', '3'),
        timeout=GOOGLE_TIMEOUT,
    ),
    "Google Roads": ProviderData(
        min_zoom=0,
        max_zoom=19,
        url='http://mt{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=uk',
        attribution=f'Map data ©{current_year()} Google',
        subdomains=('0', '1', '2', '3'),
        timeout=GOOGLE_TIMEOUT,
    ),
}
