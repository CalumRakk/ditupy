import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests
from git import Union
from unidecode import unidecode

from ditupy.schemas.bundle_item import BundleItem
from ditupy.schemas.common import ChannelInfo
from ditupy.schemas.content_detail import ContentDetail
from ditupy.schemas.dashmanifest_response import ApiResponse
from ditupy.schemas.raw_schedule_response import RawTVScheduleResponse
from ditupy.schemas.simple_schedule import CurrentSchedule, SimpleSchedule
from ditupy.schemas.types import ContentSubType, ContentType, Manifest
from ditupy.utils import cookies_to_requests

logger = logging.getLogger(__name__)


class DituClient:
    """
    Cliente para interactuar con la API de Ditu/Caracol.
    Maneja la sesión HTTP, headers y la lógica de extracción de datos.
    """

    BASE_URL = "https://varnish-prod.avscaracoltv.com/AGL/1.6/A/ENG/ANDROID/ALL"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Restful": "yes",
                "Accept-Encoding": "gzip, deflate, br",
                "User-Agent": "okhttp/4.12.0",
            }
        )

    def _get_day_range_timestamps(self) -> Tuple[int, int]:
        """Calcula timestamps start/end para el día actual."""
        now = datetime.now()
        start_dt = datetime(now.year, now.month, now.day)
        end_dt = start_dt + timedelta(hours=27)  # Cubre hasta las 3AM del día siguiente
        return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

    def _fetch_epg_raw(self) -> RawTVScheduleResponse:
        """
        Obtiene el JSON crudo de la EPG.
        Esta es la fuente de verdad tanto para canales como para horarios.
        """
        start, end = self._get_day_range_timestamps()
        url = f"{self.BASE_URL}/TRAY/EPG"
        params = {
            "orderBy": "orderId",
            "sortOrder": "asc",
            "filter_startTime": str(start),
            "filter_endTime": str(end),
        }
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_channels(self) -> List[ChannelInfo]:
        """Extrae la lista de canales únicos desde la EPG."""
        raw_data = self._fetch_epg_raw()
        channels_map = {}  # Usamos dict para evitar duplicados por ID

        for container in raw_data.get("resultObj", {}).get("containers", []):
            items = container.get("containers", [])
            if not items:
                continue

            # El primer item suele tener la info del canal correcta
            first_item = items[0]
            if "channel" in first_item:
                ch = first_item["channel"]
                channels_map[ch["channelId"]] = ChannelInfo(
                    channelId=ch["channelId"], channelName=ch["channelName"]
                )

        return list(channels_map.values())

    def find_channel(self, query: str) -> ChannelInfo:
        """Busca un canal por nombre (insensible a mayúsculas/tildes)."""
        query_norm = unidecode(query.lower())
        for channel in self.get_channels():
            if query_norm in unidecode(channel["channelName"].lower()):
                return channel
        raise ValueError(f"Canal '{query}' no encontrado.")

    def get_schedule(self, channel_id: int) -> List[SimpleSchedule]:
        """Obtiene la parrilla para un ID de canal específico."""
        raw_data = self._fetch_epg_raw()
        schedules = []

        for channel_cont in raw_data["resultObj"]["containers"]:
            items = channel_cont.get("containers", [])
            if not items:
                continue

            first_ch_info = items[0].get("channel", {})
            if first_ch_info.get("channelId") != channel_id:
                continue

            for item in items:
                schedules.append(self._parse_program_item(item))  # type: ignore

        return schedules

    def get_current_live_program(self, channel_id: int) -> CurrentSchedule:
        """Obtiene qué están dando AHORA mismo (endpoint específico)."""
        url = f"{self.BASE_URL}/TRAY/SEARCH/PROGRAM"
        params = {
            "filter_channelIds": str(channel_id),
            "filter_airingTime": "now",
        }
        resp = self.session.get(url, params=params)
        resp.raise_for_status()

        data = resp.json()
        try:
            item = data["resultObj"]["containers"][0]
            meta = item["metadata"]
            return CurrentSchedule(
                contentId=meta["contentId"],
                title=meta["title"],
                longDescription=meta["longDescription"],
                duration=meta["duration"],
                airingStartTime=meta["airingStartTime"],
                airingEndTime=meta["airingEndTime"],
                episodeId=meta["episodeId"],
                episodeTitle=meta["episodeTitle"],
                season=meta["season"],
                channel_info=item["channel"],
            )
        except (IndexError, KeyError):
            raise ValueError(f"No hay información en vivo para el canal {channel_id}")

    def get_manifest_url(self, channel_id: int) -> str:
        """Obtiene la URL del MPD para ver en vivo."""
        url = f"{self.BASE_URL}/CONTENT/VIDEOURL/LIVE/{channel_id}/10"
        resp = self.session.get(url)
        resp.raise_for_status()

        response: ApiResponse = ApiResponse(**resp.json())
        return response.resultObj["src"]

    def _parse_program_item(self, item: dict) -> SimpleSchedule:
        """Convierte el item crudo al Schema SimpleSchedule."""
        meta = item["metadata"]
        return SimpleSchedule(
            contentId=meta["contentId"],
            title=meta["title"],
            shortDescription=meta["longDescription"],
            airingStartTime=meta["airingStartTime"],
            airingEndTime=meta["airingEndTime"],
            duration=meta["duration"],
            episodeId=meta["episodeId"],
            episodeTitle=meta["episodeTitle"] or "",
            episodeNumber=meta["episodeNumber"],
            season=meta["season"],
            channel_info=item["channel"],
        )

    def get_content_details(
        self, content_id: str, content_type: ContentType
    ) -> ContentDetail:
        """
        Obtiene el detalle de un contenido directamente por ID, sin navegar menús.
        Ruta: /CONTENT/DETAIL/{type}/{id}
        """
        url = f"{self.BASE_URL}/CONTENT/DETAIL/{content_type.value}/{content_id}"
        resp = self.session.get(url)
        resp.raise_for_status()

        response = ApiResponse(**resp.json())
        containers = response.resultObj.get("containers", [])
        if not containers:
            raise ValueError(f"Contenido {content_id} no encontrado.")

        return ContentDetail(**containers[0])

    def get_vod_stream(self, content_id: str, asset_id: str) -> Manifest:
        """
        Obtiene la URL del MPD para contenido VOD (Catchup, Episodios, Películas).
        Ruta: /CONTENT/VIDEOURL/VOD/{content_id}/{asset_id}
        """
        url = f"{self.BASE_URL}/CONTENT/VIDEOURL/VOD/{content_id}/{asset_id}"
        resp = self.session.get(url)
        resp.raise_for_status()

        response: ApiResponse = ApiResponse(**resp.json())
        return Manifest(**response.resultObj)

    def get_metadata(
        self, content_id: Union[int, str], content_type: ContentType
    ) -> ContentDetail:
        """
        Obtiene la ficha técnica completa de un contenido (Serie, Temporada o VOD).
        """
        # Endpoint directo: /CONTENT/DETAIL/{TIPO}/{ID}
        url = f"{self.BASE_URL}/CONTENT/DETAIL/{content_type.value}/{content_id}"
        resp = self.session.get(url)
        resp.raise_for_status()

        data = resp.json()
        containers = data.get("resultObj", {}).get("containers", [])

        if not containers:
            raise ValueError(f"Contenido {content_id} no encontrado.")

        return ContentDetail(**containers[0])

    def list_children(self, parent_id: str) -> List[BundleItem]:
        """
        Obtiene los hijos de un contenedor.
        - Si parent_id es una SERIE -> Devuelve Temporadas (Bundles).
        - Si parent_id es una TEMPORADA -> Devuelve Episodios (VODs).
        """
        # Usamos el endpoint de búsqueda filtrando por el padre
        # Nota: Usamos SEARCH/VOD genéricamente, suele funcionar para traer hijos mixtos
        url = f"{self.BASE_URL}/TRAY/SEARCH/VOD"

        params = {"filter_parentId": parent_id}

        resp = self.session.get(url, params=params)
        resp.raise_for_status()

        items = resp.json().get("resultObj", {}).get("containers", [])

        return [BundleItem(**item) for item in items]

    def get_stream_url(self, content_id: Union[str, int]) -> Manifest:
        """
        Obtiene la URL del MPD lista para reproducir un VOD.
        Hace la magia de buscar el Asset ID automáticamente.
        """
        logger.info(f"Iniciando búsqueda de flujo para ContentID: {content_id}")

        detail = self.get_metadata(content_id, ContentType.VOD)
        if not detail.assets:
            logger.error(f"El contenido {content_id} no retornó lista de assets.")
            raise ValueError(
                f"El contenido {content_id} no tiene assets de video disponibles."
            )

        asset_types = [a.assetType for a in detail.assets]
        logger.debug(f"Assets disponibles para {content_id}: {asset_types}")

        # Buscamos el asset tipo 'MASTER' (el principal)
        master_asset = next((a for a in detail.assets if a.assetType == "MASTER"), None)

        if not master_asset:
            logger.error(f"No se encontró asset MASTER. Disponibles: {asset_types}")
            raise ValueError(
                f"No se encontró un asset MASTER para el contenido {content_id}"
            )

        logger.info(
            f"Asset MASTER seleccionado: {master_asset.assetName} (ID: {master_asset.assetId}, VideoType: {master_asset.videoType})"
        )
        return self._fetch_vod_manifest(content_id, master_asset.assetId)

    def get_episodes(self, serie_id: str) -> List[BundleItem]:
        """Alias de list_children para Temporadas."""
        return self.list_children(serie_id)

    def _fetch_vod_manifest(
        self, content_id: Union[str, int], asset_id: Union[str, int]
    ) -> Manifest:
        """Obtiene la URL final del MPD."""
        url = f"{self.BASE_URL}/CONTENT/VIDEOURL/VOD/{content_id}/{asset_id}"
        resp = self.session.get(url)
        resp.raise_for_status()
        response = ApiResponse(**resp.json())
        raw_set_cookies = resp.headers.get("set-cookie", "")
        if not raw_set_cookies:
            raise ValueError("No se encontraron cookies en la respuesta.")

        response.resultObj["cookies"] = cookies_to_requests(raw_set_cookies)
        return Manifest(**response.resultObj)

    def get_movies(self) -> List[BundleItem]:
        return self.search_content(content_subtype=ContentSubType.MOVIE)

    def get_series(self) -> List[BundleItem]:
        return self.search_content(content_subtype=ContentSubType.SERIE)

    def get_soap_operas(self) -> List[BundleItem]:
        return self.search_content(content_subtype=ContentSubType.SOAP_OPERA)

    def search_content(
        self,
        parent_id: Optional[str] = None,
        content_type: Optional[ContentType] = None,
        content_subtype: Optional[ContentSubType] = None,
    ) -> List[BundleItem]:
        """
        Busca contenido usando un solo filtro activo por llamada.

        Prioridad de filtros:
            1. parent_id — si se especifica, ignora los demás.
            2. content_type — si se especifica, ignora los demás.
            3. content_subtype — si se especifica, ignora los demás.

        Si no se especifica ninguno, usa GROUP_OF_BUNDLES por defecto.
        """
        url = f"{self.BASE_URL}/TRAY/SEARCH/VOD"

        params = {}
        if parent_id:
            params["filter_parentId"] = parent_id
            params["filter_contentType"] = (
                "VOD"  # Hijos de un padre siempre son VODs (creo)
            )
        elif content_type:
            params["filter_contentType"] = content_type.value
        elif content_subtype:
            params["filter_contentSubtype"] = content_subtype.value
        else:
            params["filter_contentType"] = ContentType.GROUP_OF_BUNDLES.value

        resp = self.session.get(url, params=params)
        resp.raise_for_status()

        items = resp.json().get("resultObj", {}).get("containers", [])
        return [BundleItem(**item) for item in items]
