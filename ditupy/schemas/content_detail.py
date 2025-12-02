from typing import List, Literal, Optional

from pydantic import BaseModel


class Metadata(BaseModel):
    label: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    model_config = {"extra": "allow"}


class RetrieveItems(BaseModel):
    uri: str
    type: Literal["REMOTE"]


class Asset(BaseModel):
    assetId: int
    assetType: str  # Ej: "MASTER"
    videoType: str  # Ej: "HD", "NA"
    assetName: str
    model_config = {"extra": "allow"}


class ContentDetail(BaseModel):
    layout: Literal["CONTENT_DETAIL", "CONTENT_ITEM", "BUNDLE_ITEM"]
    title: Optional[str] = None
    id: str
    metadata: Metadata
    retrieveItems: Optional[RetrieveItems] = None
    assets: List[Asset] = []

    model_config = {"extra": "allow"}
