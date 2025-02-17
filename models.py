from pydantic import BaseModel
from typing import List

class Entity(BaseModel):
    id:int
    name:str
    summary:str
    sources:List[str]

class Relationship(BaseModel):
    id:int
    name:str
    start_entity_name:str
    start_entity_id:int
    end_entity_name:str
    end_entity_id:int
    summary:str