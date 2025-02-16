from fastapi import APIRouter, Request
from openai import OpenAI
from kg_interface import check_for_entity_tool, check_for_entity_tool_def
import json
from typing import List
import logging
client = OpenAI()

logger = logging.getLogger('router')

MODEL_NAME = "gpt-4o"

CHECK_ENTITY_SYSTEM_PROMPT = ''.join([
    'You are a detial orient knowledge graph creator.',
    'In order to perform your mission you will use the provided API to interface with the knowledge graph.',
    'The goal of the knowledge graph is to hold all of the entities (people, organizations, places) and their relationships.',
    'For the first phase of your task check if the knowledge graph has an entry for each of the entities in the text the user provides.',
    'Therefore you should call the check_for_entity tool once per entity in the input text'
])

tool_names_to_def_dict = {'check_for_entity':check_for_entity_tool}

check_entity_tools = [check_for_entity_tool_def]


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

def has_tool_calls(completion)->bool:
    return not completion.choices[0].message.tool_calls is None and len(completion.choices[0].message.tool_calls) >0


def handle_tool_calls(completion)->List:
    logger.warning(f"handling tool calls for completion\n{completion}")
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
    logger.warning(f"Calling openai with messages\n{messages}")
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

