import logging
import xml.etree.ElementTree as ET
from typing import Any, List, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


NAMESPACES = {
    "mpd": "urn:mpeg:dash:schema:mpd:2011"
}

class XmlNode:
    """Clase base para envolver elementos XML y facilitar la extracción segura."""
    def __init__(self, element: ET.Element, base_url: str = ""):
        self._el = element
        self._base_url = base_url

    def _attr(self, name: str, default: Any = None, cast_type: type = str) -> Any:
        """Extrae un atributo de forma segura y lo tipa."""
        val = self._el.get(name)
        if val is None:
            return default
        try:
            return cast_type(val)
        except (ValueError, TypeError):
            logger.warning(f"Error casteando atributo '{name}' con valor '{val}' a {cast_type}")
            return default

    def _find_children(self, tag_name: str) -> List[ET.Element]:
        """Busca hijos directos usando el namespace."""
        return self._el.findall(f"mpd:{tag_name}", NAMESPACES)

    def _find_child(self, tag_name: str) -> Optional[ET.Element]:
        return self._el.find(f"mpd:{tag_name}", NAMESPACES)

    @property
    def base_url(self) -> str:
        """Resuelve la BaseURL acumulativa (MPD -> Period -> ...)"""
        node = self._find_child("BaseURL")
        local_base = node.text.strip() if node is not None and node.text else ""
        
        # Si hay una URL base local, la unimos a la del padre, si no, devolvemos la del padre
        if local_base:
            return urljoin(self._base_url, local_base)
        return self._base_url

class SegmentTemplate(XmlNode):
    @property
    def initialization(self) -> str:
        return self._attr("initialization", "")

    @property
    def media(self) -> str:
        return self._attr("media", "")

    @property
    def start_number(self) -> int:
        return self._attr("startNumber", 1, int)

    @property
    def timescale(self) -> int:
        return self._attr("timescale", 1, int)

    def generate_segment_urls(self, representation_id: str) -> List[str]:
        """
        Genera la lista de URLs basada en los segmentos 'S' (Timeline).
        Esta lógica se mueve aquí para encapsular la complejidad del Timeline.
        """
        segments = []
        timeline = self._find_child("SegmentTimeline")
        if not timeline:
            return segments

        current_number = self.start_number
        
        # Patrón de reemplazo: $Number$ y $RepresentationID$
        media_pattern = self.media.replace("$RepresentationID$", str(representation_id))

        for s in timeline.findall("mpd:S", NAMESPACES):
            repeat = int(s.get("r", 0))
            # El segmento S representa (1 + r) segmentos reales
            for _ in range(repeat + 1):
                url_rel = media_pattern.replace("$Number$", str(current_number))
                segments.append(urljoin(self._base_url, url_rel))
                current_number += 1
        
        return segments

class Representation(XmlNode):
    @property
    def id(self) -> str:
        return self._attr("id") # String porque a veces son alfanuméricos

    @property
    def bandwidth(self) -> int:
        return self._attr("bandwidth", 0, int)
    
    @property
    def width(self) -> Optional[int]:
        return self._attr("width", None, int)

    @property
    def height(self) -> Optional[int]:
        return self._attr("height", None, int)
    
    @property
    def codecs(self) -> str:
        return self._attr("codecs", "")

    @property
    def frame_rate(self) -> str:
        return self._attr("frameRate", "")
    
    @property
    def audio_sampling_rate(self) -> str:
        return self._attr("audioSamplingRate", "")

    def get_segments(self) -> List[str]:
        """Obtiene los segmentos combinando información propia o heredada."""
        # DASH permite definir SegmentTemplate en el AdaptationSet padre o en la Representation.
        # Aquí buscamos primero en el hijo (self), si no está, asumimos que viene del contexto (que tendríamos que pasar)
        # Para simplificar, Ditu parece ponerlo dentro de Representation:
        tmpl_node = self._find_child("SegmentTemplate")
        if tmpl_node:
            template = SegmentTemplate(tmpl_node, self.base_url)
            return template.generate_segment_urls(self.id)
        return []
    
    @property
    def initialization_url(self) -> str:
        tmpl_node = self._find_child("SegmentTemplate")
        if tmpl_node:
            template = SegmentTemplate(tmpl_node, self.base_url)
            init_pattern = template.initialization.replace("$RepresentationID$", str(self.id))
            return urljoin(self.base_url, init_pattern)
        return ""

class AdaptationSet(XmlNode):
    @property
    def mime_type(self) -> str:
        return self._attr("mimeType", "")
    
    @property
    def is_video(self) -> bool:
        return "video" in self.mime_type

    @property
    def is_audio(self) -> bool:
        return "audio" in self.mime_type

    def get_representations(self) -> List[Representation]:
        return [Representation(el, self.base_url) for el in self._find_children("Representation")]

    def get_best_representation(self) -> Optional[Representation]:
        reps = self.get_representations()
        if not reps:
            return None
        
        if self.is_video:
            return sorted(reps, key=lambda r: r.bandwidth, reverse=True)[0]
        else:
            return sorted(reps, key=lambda r: r.bandwidth, reverse=True)[0]

class Period(XmlNode):
    @property
    def id(self) -> str:
        return self._attr("id")

    @property
    def start(self) -> str:
        return self._attr("start")

    def get_adaptation_sets(self, type_filter: Optional[str] = None) -> List[AdaptationSet]:
        """
        type_filter: 'video', 'audio', o None para todos.
        """
        sets = [AdaptationSet(el, self.base_url) for el in self._find_children("AdaptationSet")]
        if type_filter == 'video':
            return [a for a in sets if a.is_video]
        elif type_filter == 'audio':
            return [a for a in sets if a.is_audio]
        return sets

class DashManifest:
    def __init__(self, xml_content: str, source_url: str = ""):
        """
        source_url: La URL original del .mpd, necesaria para resolver rutas relativas si no hay BaseURL.
        """
        # Si el dash contiene BaseURL, se usará esa; si no, el valor de source_url para construir las URLs completas de los segmentos.
        self._root = ET.fromstring(xml_content)
        self._source_url = source_url
    
    @property
    def base_url(self) -> str:
        node = self._root.find("mpd:BaseURL", NAMESPACES)
        if node is not None and node.text:
            val = node.text.strip()
            if self._source_url:
                return urljoin(self._source_url, val)
            return val
        return self._source_url

    def get_periods(self) -> List[Period]:
        return [Period(el, self.base_url) for el in self._root.findall("mpd:Period", NAMESPACES)]

    def get_content_period(self) -> Period:
        """Logica 'magica' para encontrar el contenido real."""
        periods = self.get_periods()
        return periods[0]