from langchain.chains import ArangoGraphQAChain
from langchain_openai import ChatOpenAI
from langchain_community.graphs import ArangoGraph
import nx_arangodb  as nxadb
from arango import ArangoClient
import os
from kg_interface import filter_word_list_for_entities, add_relationship, convert_to_multidigraph, kg_networkx_degree_hist
import logging
from typing import List

logger = logging.getLogger("Arango_query_interface")

DATABASE_HOST=os.getenv('DATABASE_HOST')
DATABASE_USERNAME =os.getenv('DATABASE_USERNAME')
DATABASE_PASSWORD=os.getenv('DATABASE_PASSWORD')
DATABASE_NAME=os.getenv('DATABASE_NAME')

db = ArangoClient(hosts=DATABASE_HOST).db(
    DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD, verify=True
)

arango_graph = ArangoGraph(db)

arangago_QA_chain = ArangoGraphQAChain.from_llm(
        ChatOpenAI(temperature=0), graph=arango_graph, verbose=True, allow_dangerous_requests=True
)
arangago_QA_chain.return_aql_query = False
arangago_QA_chain.return_aql_result = True

def arango_connection_finder()->None:
    arangago_QA_chain.max_aql_generation_attempts = 3
    arangago_QA_chain.return_aql_query = False
    arangago_QA_chain.return_aql_result = True
    smart_result = arangago_QA_chain.invoke(
        f"Get each node with less than three outbound edges." 
    )['aql_result']
    arangago_QA_chain.return_aql_query = True
    arangago_QA_chain.return_aql_result = False
    arangago_QA_chain.max_aql_generation_attempts = 1
    for node in smart_result:
        summary_entities = filter_word_list_for_entities(node['summary'].split(' '))
        for entity in summary_entities:
            try:
                # logger.warning(arangago_QA_chain.invoke(
                #     f"Add an edge between the node with name attribute {node['name']} and {entity}."))
                add_relationship(node['name'],entity,'unknown','unknown')
            except ValueError:
                pass
    convert_to_multidigraph()
    kg_networkx_degree_hist()

def entity_degree(names:List[str])->None:
    arangago_QA_chain.max_aql_generation_attempts = 5
    arangago_QA_chain.return_aql_query = False
    arangago_QA_chain.return_aql_result = True
    logger.warning(
        arangago_QA_chain.invoke(
            f"What is the degree for the node with name attribute: {names[0]}" 
        )
    )

def get_arango_keys(names:List[str])->List[int]:
    arangago_QA_chain.max_aql_generation_attempts = 5
    arangago_QA_chain.return_aql_query = False
    arangago_QA_chain.return_aql_result = True
    return arangago_QA_chain.invoke(
            f"Get all the keys for nodes with a name attribute matching one of the strings in this list: {names}" 
        )['aql_result']

def get_arango_subgraph(node_ids:List[int])->List[int]:
    arangago_QA_chain.max_aql_generation_attempts = 5
    arangago_QA_chain.return_aql_query = False
    arangago_QA_chain.return_aql_result = True
    return arangago_QA_chain.invoke(
            f"Get the subgraph of the sudan graph for these nodes: {node_ids}" 
        )['aql_result']
    