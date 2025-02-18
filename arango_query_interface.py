from langchain.chains import ArangoGraphQAChain
from langchain_openai import ChatOpenAI
from langchain_community.graphs import ArangoGraph
import nx_arangodb  as nxadb
from arango import ArangoClient
import os
from kg_interface import filter_word_list_for_entities, standardize_entity_name
import logging

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

def arango_connection_finder(nxadb_graph:nxadb.Graph)->None:
    arangago_QA_chain.max_aql_generation_attempts = 3
    arangago_QA_chain.return_aql_query = False
    arangago_QA_chain.return_aql_result = True
    smart_result = arangago_QA_chain.invoke(
        f"Get each node with a degree less than three." 
    )['aql_result']
    arangago_QA_chain.return_aql_query = True
    arangago_QA_chain.return_aql_result = False
    arangago_QA_chain.max_aql_generation_attempts = 1
    for node in smart_result:
        summary_entities = filter_word_list_for_entities(node['summary'].split(' '))
        for entity in summary_entities:
            try:
                logger.warning(arangago_QA_chain.invoke(
                    f"Add an edge between the node with name attribute {node['name']} and {entity}."))
            except ValueError:
                pass

def arango_communities()->None:
    logger.warning(
        arangago_QA_chain.invoke(
            f"Identify communities" 
        )
    )