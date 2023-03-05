from pydantic_geojson import FeatureModel
from pydantic import BaseConfig, BaseModel
from typing import Tuple, Any
from starlite import UploadFile

from models.responses import UserPhotoResponse


class UserPhotoPointFeature(FeatureModel):
    properties: UserPhotoResponse


# Tuples break OpenAPI doc generation unless line 148 of the below file:
# venv/lib/python3.11/site-packages/pydantic_openapi_schema/v3_1_0/schema.py
#
# is changed to items: Optional[Union[Reference, "Schema", List["Schema"]]] = None
# FROM items: Optional[Union[Reference, "Schema"]] = None
#
#
# see https://github.com/pydantic/pydantic/issues/3210
class SimpleTupleModel(BaseModel):
    tupz: Tuple[float, float]


class UserPhotoPostRequest(BaseModel):
    feature: UserPhotoPointFeature
    image: UploadFile  # how can this be bytes or something more specific

    class Config(BaseConfig):
        arbitrary_types_allowed = True
