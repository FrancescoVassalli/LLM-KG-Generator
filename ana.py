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
    get_entity_summary_tool_def
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
])

'Using the entity summary from the knowledge graph and the information from the text the user provided determine if the summary needs to be updated.',
'If the summary does need to be updated call update_summary'

tool_names_to_def_dict = {'check_for_entity':check_for_entity_tool, 'add_entity':add_entity_tool, 'get_entity_summary':get_entity_summary_tool}

check_entity_tools = [check_for_entity_tool_def, add_entity_tool_def, get_entity_summary_tool_def]

router = APIRouter(
    prefix="/mock",
    tags=["mock"],
    responses={404: {"description": "Not found"}},
)

@router.get("/check_text_for_entities/{text}")
async def check_text_for_entities(request: Request, text:str):
    messages = []
    completion = None
    while completion is None or has_tool_calls(completion):
        completion = prompt_model_with_tools_and_text(text,CHECK_ENTITY_SYSTEM_PROMPT,messages,check_entity_tools)
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

