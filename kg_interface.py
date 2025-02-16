from models import Entity
import logging
import re

logger = logging.getLogger("kg_interface")

alpha_check = re.compile('[^a-zA-Z]')

kg = {}

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