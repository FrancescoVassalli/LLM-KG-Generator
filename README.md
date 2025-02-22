# LLM-KG-Generator
A method for creating knowledge graphs with an LLM in a format amenable to using the KG to do RAG. Inspired by [Microsoft blog post](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/) and [pre-print](https://arxiv.org/pdf/2404.16130). The inital graph that is created may be too sparse for good query anssering. However this implementation leverages an ArangoDB backend with Arango's langchain community package to query sparse areas of the graph and find where node contents overlap for automated edge building. This creates a much dense graph. The community building step of the Microsoft mdoel is implemented with cuGraph's louvian algorithm.

## Setup
1. Setup your `.env` see steps below
1. Have docker engine running on your system 
1. In this directory `docker compose up -d`
1. Go to `localhost:8000` to access the API

### Env
Make a file in this directory called .env then write this in it with the env variables you get from Open AI / Arango respectively.
````
OPENAI_API_KEY=<key>
DATABASE_HOST=<host_address>  should look this this not real one https://1111111.arangodb.cloud:11111
DATABASE_USERNAME =<username> it is root unless you made a new one
DATABASE_PASSWORD=<password>  
DATABASE_NAME=<database_name>
````


## Important API Endpoints 
The API has many functions. Most of these are just for testing different parts of the system in isolation. Here are the important ones
* `expand-kg-with-text`: this is where you enter source text to expand the knowledge graph
* `save-kg`: If you do not have arango cloud DB you can save and read stuff locally 
* `convert-kg-to-networkx-multidigraph`: once you expanded the graph this adds it to the cloud 
* `arango-relationship-builder`: makes the graph more dense using AI
* `cu-communities`: find the commuities and generate summaries (this takes a long time because a lot of text is made with LLM)
* `hybrid-answer`: does the graph rag 