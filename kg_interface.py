from models import Entity, Relationship
from pydantic import BaseModel
import logging
import re
import copy
import pickle
import json
from typing import Dict, Tuple
from summary_update_interface import complete_entity_summary_update

logger = logging.getLogger("kg_interface")

alpha_check = re.compile('[^a-zA-Z]')

entity_id_count = 0

kg: Dict[str,Entity] = {}
edges: Dict[Tuple[str,str,str],Relationship]

current_user_input:str = None

def get_next_entity_id()->int:
    global entity_id_count
    result = copy.copy(entity_id_count)
    entity_id_count+=1
    return result

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

def standardize_entity_name(unsafe_name:str)->str:
    unsafe_name = unsafe_name.lower().strip()
    return alpha_check.sub('',unsafe_name)

def standardize_relationship_name(unsafe_name:str)->str:
    unsafe_name = unsafe_name.lower().strip()
    return alpha_check.sub('',unsafe_name)+'_relationship'

def get_relationship_key(start_name:str,end_name:str,relationship_name:str)->Tuple[str,str,str]:
    return (standardize_entity_name(start_name),standardize_entity_name(end_name),standardize_relationship_name(relationship_name))

def check_for_entity(entity_name:str)->bool:
    entity_name = standardize_entity_name(entity_name)
    logger.warning(f"checking for {entity_name}")
    return entity_name in kg

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
    entity_name = standardize_entity_name(entity_name)
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
    entity_name = standardize_entity_name(entity_name)
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

def set_current_user_input(text:str)->None:
    global current_user_input
    current_user_input = text

def update_kg_with_new_entity_summary(entity_name:str,new_summary:str)->None:
    kg[standardize_entity_name(entity_name)].summary = new_summary

def update_entity_summary(entity_name:str)->HTTPResponse:
    global current_user_input
    logger.warning(f"Updating summary for {entity_name}")
    new_summary = complete_entity_summary_update(entity_name,current_user_input,get_entity_summary(entity_name))
    logger.warning(f"New summary\n{new_summary}")
    update_kg_with_new_entity_summary(entity_name,new_summary)
    return HTTPResponse()

def update_entity_summary_tool(entity_name:str)->str:
    return update_entity_summary(entity_name).model_dump_json()

update_entity_summary_tool_def = {
    "type": "function",
    "function": {
        "name": "update_entity_summary",
        "description": "Update the summary of the input entity in the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "The name of the entity who's summary you want to update in the knowledge graph"
                }
            },
            "required": [
                "entity_name"
            ],
            "additionalProperties": False
        }
    }
}

def check_for_relationship(start_entity_name:str, end_entity_name:str, relationship_name:str)->HTTPResponse:
    if not check_for_entity(start_entity_name):
        return HTTPResponse(status=400,detail=f"Relationship cannot be checked because start entity {start_entity_name} is not in knowledge graph.")
    if not check_for_entity(end_entity_name):
        return HTTPResponse(status=400,detail=f"Relationship cannot be checked because end entity {end_entity_name} is not in knowledge graph.")
    relationship_key = get_relationship_key(start_entity_name,end_entity_name,relationship_name)
    logger.warning(f"checking for {relationship_key}")
    return HTTPResponse(status=200,detail=str(relationship_key in edges))

def check_for_relationship_tool(start_entity_name:str, end_entity_name:str, relationship_name:str)->str:
    return check_for_relationship(start_entity_name, end_entity_name, relationship_name).model_dump_json()

check_for_relationship_tool_def = {
    "type": "function",
    "function": {
        "name": "check_for_relationship",
        "description": "Check if the input relationship is in the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "start_entity_name": {
                    "type": "string",
                    "description": "The name of the entity in the knowledge graph the relationship you want to check the knowledge graph for starts from"
                },
                "end_entity_name": {
                    "type": "string",
                    "description": "The name of the entity in the knowledge graph the relationship you want to check the knowledge graph for ends on"
                },
                "relationship_name": {
                    "type": "string",
                    "description": "The name of the relationship you want to check the knowledge graph for"
                }
            },
            "required": [
                "start_entity_name",
                "end_entity_name",
                "relationship_name"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}