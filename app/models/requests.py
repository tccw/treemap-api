import datetime
from pydantic_geojson import FeatureModel
from pydantic import BaseConfig, BaseModel
from typing import Optional
from starlite import UploadFile


class UserPhotoProperties(BaseModel):
    created_at_utc: Optional[datetime.datetime]
    """The UTC datetime string for when image was successfully uploaded to the server"""
    public_id: Optional[str]
    """The publid ID used to acces the image and request derived products with"""
    full_size_url: Optional[str]
    """The direct url to the full sized image"""


"""
    Tuples break OpenAPI doc generation unless line 148 of the below file:
    venv/lib/python3.11/site-packages/pydantic_openapi_schema/v3_1_0/schema.py

    is changed to items: Optional[Union[Reference, "Schema", List["Schema"]]] = None
    FROM items: Optional[Union[Reference, "Schema"]] = None

    This is due to PointModel, the geometry used in this feature being a NamedTuple

    class Coordinates(NamedTuple):
        lon: LonField
        lat: LatField

    see https://github.com/pydantic/pydantic/issues/3210

    This is unlikely to be fixed.
"""


class UserPhotoPointFeature(FeatureModel):
    properties: UserPhotoProperties


class UserPhotoPostRequest(BaseModel):
    """

    """
    feature: UserPhotoPointFeature
    image: UploadFile  # how can this be bytes or something more specific

    class Config(BaseConfig):
        arbitrary_types_allowed = True
