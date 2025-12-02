from typing import List, Literal, Optional

from pydantic import BaseModel
from unidecode import unidecode


class Action(BaseModel):
    key: Literal["onClick"]
    uri: str
    targetType: Literal["PAGE"]


class RetrieveItems(BaseModel):
    uri: str
    type: Literal["REMOTE"]


class Metadata(BaseModel):
    contentId: int
    contentType: Literal["BUNDLE", "VOD", "GROUP_OF_BUNDLES"]
    longDescription: str
    title: str
    season: Optional[int] = None
    contentSubtype: Literal["SOAP_OPERA", "SEASON", "MOVIE", "SERIE", "EPISODE"]
    genres: list[str]

    model_config = {"extra": "allow"}
    duration: int
    year: Optional[str] = None
    episodeTitle: Optional[str] = None
    episodeNumber: Optional[int] = None


class BundleItem(BaseModel):
    id: str
    layout: Literal["BUNDLE_ITEM", "CONTENT_ITEM"]
    retrieveItems: Optional[RetrieveItems] = None
    actions: List[Action]
    metadata: Metadata

    @property
    def title_slug(self) -> str:
        return unidecode(self.metadata.title).lower().replace(" ", "_")
