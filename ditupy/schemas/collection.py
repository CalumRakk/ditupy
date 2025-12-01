from typing import List, Literal

from pydantic import BaseModel


class ActionItem(BaseModel):
    uri: str
    model_config = {"extra": "allow"}


class RetrieveItems(BaseModel):
    uri: str
    type: Literal["REMOTE"]


class Metadata(BaseModel):
    label: str
    model_config = {"extra": "allow"}


class Collection(BaseModel):
    layout: Literal["HIGHLIGHT", "POSTER"]
    id: str
    title: str
    metadata: Metadata
    retrieveItems: RetrieveItems
    actions: List[ActionItem]
