from fastapi import APIRouter, Request
from openai import OpenAI
from kg_interface import (
    check_for_entity_tool, 
    check_for_entity_tool_def, 
    add_entity_tool, 
    add_entity_tool_def,
    persist_kg,
    load_kg,
    print_kg,
    get_entity_summary_tool,
    get_entity_summary_tool_def,
    set_current_user_input,
    update_entity_summary_tool,
    update_entity_summary_tool_def,
    check_for_relationship_tool,
    check_for_relationship_tool_def
)
import json
from typing import List
import logging
client = OpenAI()

logger = logging.getLogger('router')

MODEL_NAME = "gpt-4o"

CHECK_ENTITY_SYSTEM_PROMPT = ''.join([
    'You are a detial oriented knowledge graph creator.',
    'In order to perform your mission you will use the provided API to interface with the knowledge graph.',
    'The goal of the knowledge graph is to hold all of the entities (persons, leaders, reporters, newspapers, groups, countries, organizations, cities, provinces, buildings, treaties, meetings, important dates, important claims) and their relationships.',
    'For the first phase of your task check if the knowledge graph has an entry for each of the entities in the text the user provides.',
    'Therefore you should call the check_for_entity tool once per entity in the input text.',
    'The second phase of your task is to add missing entities to the knowledge graph.'
    'If an entity is not in the knowledge graph then you should call add_entity once per entity to add them to the knowledge graph.',
    'If you think there are no more entities to add check again. Sometimes the user will give you a lot of text and your attention is only so long.',
    'The third phase of your task is to reference the summaries for the entities in the knowledge graph.',
    'Call get_entity_summary once per entity in the knowledge graph to read the summary for each entity.',
    'Now that you have summaries from the knowledge graph for your entities you should use this information to make informed decisions in the subsequent phases',
    'The fourth phase of your task is to determine which entities should have their summmary updated.',
    "An entity's summary should be updated when the text provided by the user adds significant new information about the entity",
    "For each entity that should have its summary updated call update_entity_summary"
])

CHECK_RELATIONSHIP_SYSTEM_PROMPT = ''.join([
    'You are a detial oriented knowledge graph creator.',
    'In order to perform your mission you will use the provided API to interface with the knowledge graph.',
    'The goal of the knowledge graph is to hold all of the entities (persons, leaders, reporters, newspapers, groups, countries, organizations, cities, provinces, buildings, treaties, meetings, important dates, important claims) and their relationships.',
    'For the first phase of your task check if the knowledge graph has an entry for each of the entities in the text the user provides.',
    'Therefore you should call the check_for_entity tool once per entity in the input text.',
    'The second phase of your task is to find relationships between the entities in the knowledge graph.',
    'You are looking for relationships like negotiations, meetings, supporting, ignoring, alliances, fighting, condeming, participating, urging, encouraging, killing, looting, alleging, fleeing',
    'Relationships on the knowledge graph are directional connections between entities in the knowledge graph. They have a single starting entity, a single ending entity, a one word relationship name, and a short summary of the relationship.',
    'It is not important to find every possible relation between entities in the knowledge graph. Brevity and focus on the most important relationships is much appreciated.',
    'For each relationship you indentify from the text that is between entities in the knowledge graph call check_for_relationship',
])

tool_names_to_def_dict = {
    'check_for_entity':check_for_entity_tool, 
    'add_entity':add_entity_tool, 
    'get_entity_summary':get_entity_summary_tool,
    'update_entity_summary':update_entity_summary_tool,
    'check_for_relationship':check_for_relationship_tool}

check_entity_tools = [check_for_entity_tool_def, add_entity_tool_def, get_entity_summary_tool_def,update_entity_summary_tool_def]
check_relationship_tools = [check_for_entity_tool_def,check_for_relationship_tool_def]

router = APIRouter(
    prefix="/mock",
    tags=["mock"],
    responses={404: {"description": "Not found"}},
)

@router.get("/check_text_for_entities/{text}")
async def check_text_for_entities(request: Request, text:str):
    set_current_user_input(text)
    messages = []
    completion = None
    while completion is None or has_tool_calls(completion):
        completion = prompt_model_with_tools_and_text(text,CHECK_ENTITY_SYSTEM_PROMPT,messages,check_entity_tools)
        messages.extend(handle_tool_calls(completion))
    return completion

@router.get("/check_text_for_relationships/{text}")
async def check_text_for_relationships(request: Request, text:str):
    set_current_user_input(text)
    messages = []
    completion = None
    while completion is None or has_tool_calls(completion):
        completion = prompt_model_with_tools_and_text(text,CHECK_RELATIONSHIP_SYSTEM_PROMPT,messages,check_relationship_tools)
        messages.extend(handle_tool_calls(completion))
    return completion

@router.get("/save-kg/{filename}/{human_readable}")
async def save_kg(request: Request, filename:str=None, human_readable:bool=False):
    if filename == "":
        filename = None
    persist_kg(filename)
    return {200:""}

@router.get("/print-knowledge-graph")
async def print_knowledge_graph(request: Request):
    print_kg()
    return {200:""}

@router.get("/read-kg-from-file/{filename}")
async def read_kg_from_file(request: Request, filename:str):
    if filename == "":
        filename = None
    load_kg(filename)
    return {200:""}

def has_tool_calls(completion)->bool:
    return not completion.choices[0].message.tool_calls is None and len(completion.choices[0].message.tool_calls) >0

def handle_tool_calls(completion)->List:
    tool_response_messages = [completion.choices[0].message]
    if has_tool_calls(completion):
        for tool_call in completion.choices[0].message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            result = tool_names_to_def_dict[name](**args)
            tool_response_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
    return tool_response_messages

def prompt_model_with_tools_and_text(text:str,system_prompt:str,messages:List,tools):
    if len(messages)==0:
        messages.extend([
                {
                  "role": "system",
                  "content": [
                    {
                      "type": "text",
                      "text": system_prompt
                    }
                  ]
                },
                {
                  "role": "user",
                  "content": [
                    {
                      "type": "text",
                      "text": text
                    }
                  ]
                },
            ]
        )
    return client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools
    )


@router.get("/welcome")
async def welcome(request: Request):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": "Hello"
                }
              ]
            },
        ],
        response_format={
          "type": "text"
        },
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response

