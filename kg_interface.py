from models import Entity
from pydantic import BaseModel
import logging
import re
import copy
import pickle
import json
from typing import Dict

logger = logging.getLogger("kg_interface")

alpha_check = re.compile('[^a-zA-Z]')

entity_id_count = 0

def get_next_entity_id()->int:
    global entity_id_count
    result = copy.copy(entity_id_count)
    entity_id_count+=1
    return result

kg: Dict[str,Entity] = {}

class HTTPResponse(BaseModel):
    status:int = 200
    detail:str = ""

def json_encoder_for_pydantic(obj):
    if isinstance(obj,BaseModel):
        return obj.model_dump_json()
    else:
        return obj

def print_kg()->None:
    logger.warning(f"Printing knowledge graph\n{json.dumps(kg,default=json_encoder_for_pydantic)}")

def persist_kg(filename:str='kg.pickle', human_readable:bool=False)->None:
    global kg
    with open(filename,'wb') as file:
        encoding = 0 if human_readable else 5
        pickle.dump(kg,file,encoding)

def load_kg(filename:str='kg.picke')->None:
    global kg
    with open(filename,'rb') as file:
        kg = pickle.load(file)

def standardize_name(unsafe_name:str)->str:
    unsafe_name = unsafe_name.lower().strip()
    return alpha_check.sub('',unsafe_name)

def check_for_entity(entity_name:str)->bool:
    entity_name = standardize_name(entity_name)
    logger.warning(f"checking for {entity_name}")
    if entity_name in kg:
        return True
    return False

def check_for_entity_tool(entity_name:str)->str:
    return str(check_for_entity(entity_name))

check_for_entity_tool_def = {
    "type": "function",
    "function": {
        "name": "check_for_entity",
        "description": "Check if the input entity is in the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "The name of the entity you want to check for in the knowledge graph"
                }
            },
            "required": [
                "entity_name"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}

def add_entity(entity_name:str,entity_summary:str)->HTTPResponse:
    if check_for_entity(entity_name):
        return HTTPResponse(status=400,detail=f"Entity {entity_name} cannot be added because it is already in the knowledge graph")
    entity_name = standardize_name(entity_name)
    kg[entity_name] = Entity(id=get_next_entity_id(), name=entity_name,summary=entity_summary,sources=[])
    return HTTPResponse()

def add_entity_tool(entity_name:str,entity_summary:str)->str:
    return add_entity(entity_name,entity_summary).model_dump_json()

add_entity_tool_def = {
    "type": "function",
    "function": {
        "name": "add_entity",
        "description": "Add the input entity to the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "The name of the entity you want to add to the knowledge graph"
                },
                "entity_summary": {
                    "type": "string",
                    "description": "A short summary of what you know about the entity. If there is not enough information about this entity to write a good summary this can be 'unknown'."
                }
            },
            "required": [
                "entity_name",
                "entity_summary"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}

def get_entity_summary(entity_name:str)->str:
    logger.warning(f"Providing summary for entity: {entity_name}\n{kg[entity_name].summary}")
    return kg[entity_name].summary

def get_entity_summary_tool(entity_name:str)->str:
    return get_entity_summary(entity_name)

get_entity_summary_tool_def = {
    "type": "function",
    "function": {
        "name": "get_entity_summary",
        "description": "Get the summary of the input entity from the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "The name of the entity who's summary you want to retrieve from the knowledge graph"
                }
            },
            "required": [
                "entity_name"
            ],
            "additionalProperties": False
        }
    }
}