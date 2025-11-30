from typing import Optional

from pydantic import BaseModel


class CatalogItem(BaseModel):
    contentId: int
    title: str
    description: Optional[str] = ""
    duration: Optional[int] = 0
    episodeId: Optional[int] = None
    episodeTitle: Optional[str] = None
    season: Optional[int] = None
    # Agregamos el ID de la colección para saber de dónde vino
    source_collection_id: str

    @property
    def is_episodic(self) -> bool:
        return self.episodeId is not None
