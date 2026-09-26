"""Pydantic models for request/response schemas used by the API.
Add concrete models as the project evolves.
"""

# Example placeholder schema
from pydantic import BaseModel

class ExampleRequest(BaseModel):
    name: str
    value: float
