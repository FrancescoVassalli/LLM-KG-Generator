import networkx as nx
from typing import List
from openai import OpenAI
import logging
from utils import sort_list2_accordingto_list1, MAX_CONTEXT_WINDOW
client = OpenAI()

logger = logging.getLogger("community_summary")

def generate_community_summary(nx_graph:nx.Graph,community:List[int])->str:
    if len(community)==1:
        return nx_graph.nodes[community[0]]['summary']
    if len(community)==2:
        return '\n'.join([nx_graph.nodes[community[0]]['summary'],nx_graph.nodes[community[1]]['summary']])
    community_degrees = [degree_info[1] for degree_info in nx_graph.degree(community)]
    community_degrees, community = sort_list2_accordingto_list1(community_degrees,community,reverse=True)
    context_window = 0
    community_entity_i=0
    community_summary_input:List[str] = []
    while context_window<MAX_CONTEXT_WINDOW and community_entity_i<len(community):
        entity_id = community[community_entity_i]
        community_entity_i+=1
        community_entity_summary = nx_graph.nodes[entity_id]['summary']
        context_window+=len(community_entity_summary)
        community_summary_input.append(community_entity_summary)
    return complete_community_summary('\n'.join(community_summary_input))

COMMUNITY_SUMMARY_SYSTEM_PROMPT = ''.join([
        'You are a detial oriented news summarizer.',
        'The user will provided are several details of items in recent news',
        "Respond with a summary about the user's input."
    ])

def complete_community_summary(community_summary_input:str)->str:
    
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {
          "role": "system",
          "content": [
            {
              "type": "text",
              "text": COMMUNITY_SUMMARY_SYSTEM_PROMPT
            }
          ]
        },
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": community_summary_input
            }
          ]
        }
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
    return completion.choices[0].message.content