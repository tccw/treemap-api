from typing import Any
from pydantic import BaseModel


class ResponseModel(BaseModel):
    type: str
    """The type of data returned in the data field"""
    data: Any
    """The data corresponding to the item"""
    # next_token: str
    # """The cursor token required for pagination"""
