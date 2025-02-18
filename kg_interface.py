from models import Entity, Relationship
from pydantic import BaseModel
import logging
import re
import copy
import pickle
import json
from typing import Dict, Tuple, List
from summary_update_interface import complete_entity_summary_update
import networkx as nx
import matplotlib.pyplot as plt
import igraph as ig
import leidenalg as la
from community_summary_interface import generate_community_summary

logger = logging.getLogger("kg_interface")

alpha_check = re.compile('[^a-zA-Z]')

entity_id_count = 0

kg: Dict[str,Entity] = {}
edges: Dict[Tuple[str,str,str],Relationship] = {}
kg_communities: Dict[int,List[int]] ={}
kg_community_summaries: Dict[int,str] = {}
nx_graph:nx.Graph = None

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
    logger.warning(f"Printing entities\n{json.dumps(kg,default=json_encoder_for_pydantic)}")

def print_edges()->None:
    logger.warning(f"Printing edges\n{json.dumps(list(edges.values()),default=json_encoder_for_pydantic)}")

def convert_to_multidigraph()->None:
    global nx_graph
    nx_graph = nx.MultiDiGraph()
    for entity in kg.values():
        nx_graph.add_node(entity.id,name=entity.name,summary=entity.summary)
    for relationship_key, relationship in edges.items():
        nx_graph.add_edge(kg[relationship_key[0]].id,kg[relationship_key[1]].id,relationship_key,summary=relationship.summary)

def print_solo_entities()->None:
    if nx_graph is None:
        convert_to_multidigraph()
    for entity in nx_graph.nodes():
        if nx_graph.degree(entity)==0:
            logger.warning(nx_graph.nodes[entity]['name'])

def kg_networkx_degree_hist()->None:
    if nx_graph is None:
        convert_to_multidigraph()
    logger.warning(nx.degree_histogram(nx_graph))

def kg_networkx_plot()->None:
    if nx_graph is None:
        convert_to_multidigraph()
    options = {
        "font_size": 36,
        "node_size": 3000,
        "node_color": "white",
        "edgecolors": "black",
        "linewidths": 5,
        "width": 5,
    }
    nx.draw_networkx(nx_graph, **options)

    # Set margins for the axes so that nodes aren't clipped
    ax = plt.gca()
    ax.margins(0.20)
    plt.axis("off")
    plt.show()
    plt.draw()
    fig = plt.figure()
    fig.savefig("kg_networkx_plot.png")

def connect_nodes_by_summary()->None:
    for entity in nx_graph.nodes():
        if nx_graph.degree(entity)==0:
            unconnected_entity_name:str = nx_graph.nodes[entity]['name']
            unconnected_entity_summary:str = nx_graph.nodes[entity]['summary']
            other_entities_mentioned_in_unconnected_entity_summary = filter_word_list_for_entities(unconnected_entity_summary.split(' '))
            for other_entity in other_entities_mentioned_in_unconnected_entity_summary:
                add_relationship(unconnected_entity_name,other_entity,'unknown','unknown')
    convert_to_multidigraph()
    kg_networkx_degree_hist()

def filter_word_list_for_entities(words:List[str])->List[str]:
    return [word for word in words if check_for_entity(word)]

def make_ig_nx_map(graph:nx.Graph)->None:
    return {i:entity_id for i, entity_id in enumerate(graph)}

def find_communities()->None:
    if nx_graph is None:
        convert_to_multidigraph()
    ig_graph = ig.Graph.from_networkx(nx_graph)
    partition = la.find_partition(ig_graph, la.ModularityVertexPartition)
    ig_nx_map = make_ig_nx_map(nx_graph)
    new_communities: Dict[int,str]={}
    new_community_summaries: Dict[int,str]={}
    for i, community in enumerate(partition):
        community = [ig_nx_map[j] for j in community]
        logger.warning(f"Community {i}: {community}")
        community_attribute_dict = {entity_id: i for entity_id in community}
        nx.set_node_attributes(nx_graph,community_attribute_dict,"community")
        new_communities[i] = community
        summary = generate_community_summary(nx_graph,community)
        logger.warning(f"Generated community summary {summary}")
        new_community_summaries[i] = summary
    set_communities(new_communities)
    set_community_summaries(new_community_summaries)

def set_communities(incoming:Dict[int,str])->None:
    global kg_communities
    kg_communities = incoming

def set_community_summaries(incoming:Dict[int,str])->None:
    global kg_community_summaries
    kg_community_summaries = incoming

def get_community_summaries()->Dict[int,str]:
    return kg_community_summaries

def persist_kg(filename:str='kg.pickle', human_readable:bool=False)->None:
    encoding = 0 if human_readable else 5
    with open(filename,'wb') as file:
        pickle.dump(kg,file,encoding)
    with open(f"edges_{filename}",'wb') as file:
        pickle.dump(edges,file,encoding)
    with open(f"community_{filename}",'wb') as file:
        pickle.dump(kg_communities,file,encoding)
    with open(f"summaries_{filename}",'wb') as file:
        pickle.dump(kg_community_summaries,file,encoding)

def load_kg(filename:str='kg.pickle')->None:
    global kg
    global edges
    global kg_communities
    global kg_community_summaries
    with open(filename,'rb') as file:
        kg = pickle.load(file)
    with open(f"edges_{filename}",'rb') as file:
        edges = pickle.load(file)
    with open(f"community_{filename}",'rb') as file:
        kg_communities = pickle.load(file)
    with open(f"summaries_{filename}",'rb') as file:
        kg_community_summaries = pickle.load(file)

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
                    "description": "A short summary of what the input text says about this entity. If there is not enough information about this entity to write a good summary this can be 'unknown'."
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

def get_entity_id(entity_name:str)->int:
    entity_name = standardize_entity_name(entity_name)
    return kg[entity_name].id

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
        "description": "Function to start the process for updating the summary of the input entity in the knowledge graph",
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
        },
        "strict": True
    }
}

def check_for_relationship(start_entity_name:str, end_entity_name:str, relationship_name:str)->HTTPResponse:
    if not check_for_entity(start_entity_name):
        return HTTPResponse(status=400,detail=f"Relationship cannot be checked because prerequisite start entity {start_entity_name} is not in knowledge graph.")
    if not check_for_entity(end_entity_name):
        return HTTPResponse(status=400,detail=f"Relationship cannot be checked because prerequisite end entity {end_entity_name} is not in knowledge graph.")
    relationship_key = get_relationship_key(start_entity_name,end_entity_name,relationship_name)
    logger.warning(f"checking for relationship {relationship_key}")
    if relationship_key in edges:
        return HTTPResponse(status=200,detail="True")
    else:
        return HTTPResponse(status=200,detail="False")

def check_for_relationship_tool(start_entity_name:str, end_entity_name:str, relationship_name:str)->str:
    result = check_for_relationship(start_entity_name, end_entity_name, relationship_name)
    logger.warning(f"Relationship check result: {result.model_dump_json()}")
    return result.detail
    if result.status == 200:
        if result.detail=="True":
            return f"The {relationship_name} relationship from {start_entity_name} to {end_entity_name} is in the knowledge graph."
        else:
            return f"The knowledge graph does not have a {relationship_name} relationship from {start_entity_name} to {end_entity_name}."
    else:
        return result.detail

check_for_relationship_tool_def = {
    "type": "function",
    "function": {
        "name": "check_for_relationship",
        "description": "Check if the input relationship is in the knowledge graph. Returns True if the input relationship is in the knowledge graph and False if it is not.",
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

def add_relationship(start_entity_name:str, end_entity_name:str, relationship_name:str, relationship_summary:str)->HTTPResponse:
    relationship_check_response  = check_for_relationship(start_entity_name,end_entity_name,relationship_name)
    if relationship_check_response.status == 200:
        if relationship_check_response.detail == "False":
            relationship_key = get_relationship_key(start_entity_name,end_entity_name,relationship_name)
            logger.warning(f"adding {relationship_key}")
            edges[relationship_key] = Relationship(
                id=get_next_entity_id(),
                name=relationship_name,
                start_entity_name=start_entity_name,
                start_entity_id=get_entity_id(start_entity_name),
                end_entity_name=end_entity_name,
                end_entity_id=get_entity_id(end_entity_name),
                summary=relationship_summary
            )
            return HTTPResponse()
        else:
            return HTTPResponse(status=400,detail=f"Cannot add relationship {relationship_name} between {start_entity_name} and {end_entity_name} because it is already in the knowledge graph.")
    return relationship_check_response


def add_relationship_tool(start_entity_name:str, end_entity_name:str, relationship_name:str, relationship_summary:str)->str:
    return add_relationship(start_entity_name, end_entity_name, relationship_name,relationship_summary).model_dump_json()

add_relationship_tool_def = {
    "type": "function",
    "function": {
        "name": "add_relationship",
        "description": "Add the input relationship to the knowledge graph",
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
                },
                "relationship_summary": {
                    "type": "string",
                    "description": "A short summary of what the input text said that led you to identify this relationship. If there is not enough information about this relationship to write a good summary this can be 'unknown'."
                }
            },
            "required": [
                "start_entity_name",
                "end_entity_name",
                "relationship_name",
                "relationship_summary"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}