from fastapi import APIRouter, Request
from openai import OpenAI
import asyncio
import nx_arangodb  as nxadb
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
    check_for_relationship_tool_def,
    add_relationship_tool,
    add_relationship_tool_def,
    print_edges,
    convert_to_multidigraph,
    kg_networkx_plot,
    kg_networkx_degree_hist,
    print_solo_entities,
    connect_nodes_by_summary,
    find_communities,
    get_community_summaries,
    louvian, 
    get_all_entities_from_string,
    pagerank,
    get_nxadb_subgraph,
    add_substring_edges
)
from community_answer_interface import (
    is_community_relevant, 
    complete_community_answer,
    get_global_answer
)
from arango_query_interface import arango_connection_finder, entity_degree, get_arango_keys, get_arango_subgraph
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
    'Another expert will handle actually updating the summary. You just need to identifiy the entities which need an update by name.',
    "For each entity that should have its summary updated call update_entity_summary"
])

CHECK_RELATIONSHIP_SYSTEM_PROMPT = ''.join([
    'You are a detial oriented expert knowledge graph creator.',
    'In order to perform your mission you will use the provided API to interface with the knowledge graph.',
    'The goal of the knowledge graph is to hold all of the entities (persons, leaders, reporters, newspapers, groups, countries, organizations, cities, provinces, buildings, treaties, meetings, important dates, important claims) and their relationships.',
    'For the first phase of your task check if the knowledge graph has an entry for each of the entities in the text the user provides.',
    'Therefore you should call the check_for_entity tool once per entity in the input text.',
    'If the knowledge graph does not have an entity, you may want to double check if it has the same entity under a different or similar name.',
    'The second phase of your task is to find relationships between the entities in the knowledge graph.',
    'You are looking for relationships like negotiations, meetings, supporting, ignoring, alliances, fighting, condeming, participating, urging, encouraging, killing, looting, alleging, fleeing',
    'Relationships on the knowledge graph are directional connections between entities in the knowledge graph. They have a single starting entity, a single ending entity, a one word relationship name, and a short summary of the relationship.',
    'It is not important to find every possible relation between entities in the knowledge graph. Brevity and focus on the most important relationships is much appreciated.',
    'For each relationship you indentify in the text that is between entities in the knowledge graph call check_for_relationship',
    'The third phase of your task is to add missing relationships to the knowledge graph.',
    "In this phase you want to make the knowledge graph more complete by adding new relationships identified from the user's new text",
    "However you only want to add relationships between entities that you already confirmed are in the knowledge graph during the first phase. Other experts are in charge of adding entities."
    'Therefore, you should call add_relationship for each relationship that is not in the graph',
])

tool_names_to_def_dict = {
    'check_for_entity':check_for_entity_tool, 
    'add_entity':add_entity_tool, 
    'get_entity_summary':get_entity_summary_tool,
    'update_entity_summary':update_entity_summary_tool,
    'check_for_relationship':check_for_relationship_tool,
    'add_relationship': add_relationship_tool}

check_entity_tools = [check_for_entity_tool_def, add_entity_tool_def, get_entity_summary_tool_def,update_entity_summary_tool_def]
check_relationship_tools = [check_for_entity_tool_def,check_for_relationship_tool_def,add_relationship_tool_def]

router = APIRouter(
    prefix="/mock",
    tags=["mock"],
    responses={404: {"description": "Not found"}},
)

@router.get("/print_entity_summary/{name}")
async def print_entity_summary(request: Request, name:str):
    logger.warning(get_entity_summary_tool(name))
    return {200:""}

@router.get("/print_kg_edges")
async def print_kg_edges(request: Request):
    print_edges()
    return {200:""}

@router.get("/print_unconnected_entities")
async def print_unconnected_entities(request: Request):
    print_solo_entities()
    return {200:""}

@router.get("/auto-relationship-builder")
async def auto_relationship_builder(request: Request):
    connect_nodes_by_summary()
    return {200:""}

@router.get("/arango-relationship-builder")
async def arango_relationship_builder(request: Request):
    arango_connection_finder()
    return {200:""}

@router.get("/leiden-communities")
async def leiden_communities(request: Request):
    find_communities()
    logger.warning(f"Updated {len(get_community_summaries())} summaries")
    return {200:""}

@router.get("/cu-communities")
async def cu_communities(request: Request):
    louvian()
    return {200:""}

@router.get("/best-string-degree/{text}")
async def best_string_degree(request: Request,text:str):
    entity_degree(get_all_entities_from_string(text))
    return {200:""}

@router.get("/get-entities/{text}")
async def get_entities(request: Request,text:str):
    get_arango_keys(get_all_entities_from_string(text))
    return {200:""}

@router.get("/get-subgraph/{text}")
async def get_entities(request: Request,text:str):
    smart_keys = get_arango_keys(get_all_entities_from_string(text))
    logger.warning(get_nxadb_subgraph(([int(key) for key in smart_keys])))
    return {200:""}

@router.get("/get-subgraph-rank/{text}")
async def get_answer_entity_top_rank(request: Request,text:str):
    smart_keys = get_arango_keys(get_all_entities_from_string(text))
    sub_graph = get_nxadb_subgraph(([int(key) for key in smart_keys]))
    if len(sub_graph.edges)>2:
        return {200:get_most_influencial_pagerank(sub_graph)}
    return {200:False}

def get_most_influencial_pagerank(sub_graph:nxadb.MultiDiGraph)->str:
    ranking = pagerank(sub_graph)
    max_rank = 0
    best_rank_name = None
    for key, data in sub_graph.nodes(data=True):
        if ranking[key]>max_rank:
            max_rank = ranking[key]
            best_rank_name = data['name']
    return f"The Arango DB cuGraph pagerank predicts that {best_rank_name} is the most influencial entity amoung those mentioned here."

@router.get("/substring-edge-creator")
async def substring_edge_creator(request: Request):
    add_substring_edges()
    return {200:""}

@router.get("/print-community-summaries")
async def print_community_summaries(request: Request):
    for summary in get_community_summaries().values():
        logger.warning(f"Summary\n{summary}")
    return {200:""}  

@router.get("/check-relevant-communities/{text}")
async def check_relevant_communities(request: Request,text:str):
    tasks = [is_community_relevant(community_summary,text) for community_summary in get_community_summaries().values()]
    results = await asyncio.gather(*tasks)
    logger.warning(results)
    return {200:""}

@router.get("/get-community-answers/{text}")
async def get_community_answers(request: Request,text:str):
    tasks = [is_community_relevant(community_summary,text) for community_summary in get_community_summaries().values()]
    relevancy_results = await asyncio.gather(*tasks)
    relevant_community_summaries  = [community_summary for community_summary, relevancy_score in zip(get_community_summaries().values(),relevancy_results) if relevancy_score>20]
    tasks = [complete_community_answer(relevant_summary,text) for relevant_summary in relevant_community_summaries]
    community_answers = await asyncio.gather(*tasks)
    logger.warning(community_answers)
    return {200:""}

@router.get("/get-global-answer/{text}")
async def global_answer(request: Request,text:str):
    tasks = [is_community_relevant(community_summary,text) for community_summary in get_community_summaries().values()]
    relevancy_results = await asyncio.gather(*tasks)
    relevant_community_summaries  = [community_summary for community_summary, relevancy_score in zip(get_community_summaries().values(),relevancy_results) if relevancy_score>20]
    relevant_scores  = [relevancy_score for relevancy_score in relevancy_results if relevancy_score>20]
    tasks = [complete_community_answer(relevant_summary,text) for relevant_summary in relevant_community_summaries]
    community_answers = await asyncio.gather(*tasks)
    global_answer = get_global_answer(community_answers,relevant_scores,text)
    return {200:global_answer}

@router.get("/hybrid-answer/{text}")
async def get_hybrid_answer(request: Request,text:str):
    text_answer = (await global_answer(request,text))[200]
    influence_sentence  = await get_answer_entity_top_rank(request,text_answer)
    if influence_sentence[200]==False:
        return text_answer
    else:
        return f"{text_answer}\n{influence_sentence[200]}"

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

@router.get("/convert-kg-to-networkx-multidigraph")
async def convert_kg_to_networkx_multidigraph(request: Request):
    convert_to_multidigraph()
    return {200:""}

@router.get("/networkx-plot")
async def networkx_plot(request: Request):
    kg_networkx_plot()
    return {200:""}

@router.get("/networkx-degree-hist")
async def networkx_degree_hist(request: Request):
    kg_networkx_degree_hist()
    return {200:""}

@router.get("/expand-kg-with-text/{text}")
async def expand_kg_with_text(request: Request,text:str):
    await check_text_for_entities(request,text)
    await check_text_for_relationships(request,text)
    return {200:""}

def has_tool_calls(completion)->bool:
    return not completion.choices[0].message.tool_calls is None and len(completion.choices[0].message.tool_calls) >0

def handle_tool_calls(completion)->List:
    tool_response_messages = [completion.choices[0].message]
    if has_tool_calls(completion):
        for tool_call in completion.choices[0].message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = tool_names_to_def_dict[name](**args)
            except:
                logger.exception(f"Failed to call tool with tool_call {tool_call}")
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

