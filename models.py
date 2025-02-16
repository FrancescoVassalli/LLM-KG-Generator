from pydantic import BaseModel
from typing import List

class Entity(BaseModel):
    id:int
    name:str
    type:str
    sources:List[str]