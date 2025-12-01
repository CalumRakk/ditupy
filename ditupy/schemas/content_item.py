from typing import Literal

from pydantic import BaseModel


class Metadata(BaseModel):
    contentId: int
    contentType: Literal["VOD"]
    contentSubtype: Literal["EPISODE"]
    title: str
    longDescription: str
    episodeTitle: str
    episodeNumber: int
    genres: list[str]
    season: int
    duration: int


class ContentItem(BaseModel):
    id: str
    layaout: Literal["CONTENT_ITEM"]
    metadata: Metadata
