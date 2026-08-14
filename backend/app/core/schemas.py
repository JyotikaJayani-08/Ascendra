"""
Ascendra — Core Schemas.

Generic response schemas shared across multiple modules.
"""

from pydantic import BaseModel

class MessageResponse(BaseModel):
    message: str
