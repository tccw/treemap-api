from typing import Any
from pydantic import BaseModel


class UserPhotoResponse(BaseModel):
    created_at_utc: str
    """The UTC datetime string for when image was successfully uploaded to the server"""
    public_id: str
    """The publid ID used to acces the image and request derived products with"""
    full_size_url: str
    """The direct url to the full sized image"""


class CreationResponse(BaseModel):
    data: Any
    """The data corresponding to the created item"""
    html_url: str
    """The URL to GET the new entity"""


class GetResponse(BaseModel):
    type: str
    data: Any
    """The data corresponding to the item"""
    next_token: str
    """The cursor token required for pagination"""
