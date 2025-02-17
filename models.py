from pydantic import BaseModel
from typing import List

class Entity(BaseModel):
    id:int
    name:str
    summary:str
    sources:List[str]