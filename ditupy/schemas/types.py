# from typing import List, Optional

# from pydantic import BaseModel
# from typing_extensions import Literal


# class Episode(BaseModel):
#     contentId: int
#     subtype: Literal["EPISODE"]
#     title: str
#     description: str
#     episode_title: str
#     episode_number: int
#     year: int
#     genres: List[str]
#     season: int
#     uri: str


# class Collection(BaseModel):
#     id: str
#     layout: Literal["HIGHLIGHT", "POSTER"]
#     title: str
#     items_count: Optional[int]
#     uri: str


# class RetrieveItems(BaseModel):
#     uri: str
#     type: Literal["REMOTE"]


# class ActionItem(BaseModel):
#     key: Literal["onClick"]
#     uri: str
#     targetType: Literal["PAGE"]


# class ParentItem(BaseModel):
#     parentId: int
#     parentType: Literal["GROUP_OF_BUNDLES"]
#     parentSubType: Literal["SERIE"]


# class CollectionItem(BaseModel):
#     layout: Literal["BUNDLE_ITEM", "CONTENT_ITEM"]
#     actions: List[ActionItem]
#     retrieveItems: Optional[RetrieveItems] = None
#     id: str
#     contentId: int
#     longDescription: str
#     title: str
#     duration: int
#     contentSubtype: Literal["SEASON", "SERIE", "MOVIE", "SOAP_OPERA"]
#     season: int
#     genres: List[str]

#     parents: Optional[List[ParentItem]] = None
