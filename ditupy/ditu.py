import logging
from datetime import datetime, timedelta
from typing import List, Tuple

import requests
from unidecode import unidecode

from ditupy.schemas.common import ChannelInfo
from ditupy.schemas.dashmanifest_response import DashManifestResponse
from ditupy.schemas.raw_schedule_response import RawTVScheduleResponse
from ditupy.schemas.simple_schedule import CurrentSchedule, SimpleSchedule

logger = logging.getLogger(__name__)

class DituClient:
    """
    Cliente para interactuar con la API de Ditu/Caracol.
    Maneja la sesión HTTP, headers y la lógica de extracción de datos.
    """
    
    BASE_URL = "https://varnish-prod.avscaracoltv.com/AGL/1.6/A/ENG/ANDROID/ALL"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Restful": "yes",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "okhttp/4.12.0",
        })

    def _get_day_range_timestamps(self) -> Tuple[int, int]:
        """Calcula timestamps start/end para el día actual."""
        now = datetime.now()
        start_dt = datetime(now.year, now.month, now.day)
        end_dt = start_dt + timedelta(hours=27) # Cubre hasta las 3AM del día siguiente
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
        channels_map = {} # Usamos dict para evitar duplicados por ID

        for container in raw_data.get("resultObj", {}).get("containers", []):
            items = container.get("containers", [])
            if not items: 
                continue
                
            # El primer item suele tener la info del canal correcta
            first_item = items[0]
            if "channel" in first_item:
                ch = first_item["channel"]
                channels_map[ch["channelId"]] = ChannelInfo(
                    channelId=ch["channelId"],
                    channelName=ch["channelName"]
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
                schedules.append(self._parse_program_item(item)) # type: ignore
        
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
        
        data: DashManifestResponse = resp.json()
        return data["resultObj"]["src"]


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