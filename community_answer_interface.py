from typing import List
from openai import OpenAI
import logging
from utils import sort_list2_accordingto_list1, MAX_CONTEXT_WINDOW
client = OpenAI()



logger = logging.getLogger("community_summary")

async def is_community_relevant(community_summary:str,question:str)->int:
    system_prompt = ''.join([
        'You want to help the user determine if this news article is relevant to their question.',
        "Respond with only a number between 0 and 100 indicating how likely this article is to be relevant to their question.",
        f"Article:\n{community_summary}"
    ])
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
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
              "text": question
            }
          ]
        }
      ],
      response_format={
        "type": "text"
      },
      temperature=1,
      max_completion_tokens=4,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    text_response = completion.choices[0].message.content
    try:
        return int(text_response)
    except ValueError:
        return 0

async def complete_community_answer(community_summary:str,question:str)->str:
    system_prompt = ''.join([
        'You want to help the user determine how this news article relates to their question.',
        "Respond with relevant details from this news article to answer the user's question.",
        f"Article:\n{community_summary}"
    ])
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
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
              "text": question
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

def get_global_answer(community_answers:List[str],relevancy_scores:List[int],question:str)->str:
    relevancy_scores, community_answers = sort_list2_accordingto_list1(relevancy_scores,community_answers,reverse=True)
    context_window = 0
    community_entity_i=0
    global_answer_input:List[str] = []
    while context_window<MAX_CONTEXT_WINDOW and community_entity_i<len(community_answers):
        community_answer = community_answers[community_entity_i]
        community_entity_i+=1
        context_window+=len(community_answer)
        global_answer_input.append(community_answer)
    return complete_global_answer('\n'.join(global_answer_input),question)

def complete_global_answer(community_answer:str,question:str)->str:
    system_prompt = ''.join([
        "You want to use the provided information from recent news articles to answer the user's question.",
        "These articles contain recent events with new information so you should rely solely on them for answering the question.",
        "Not all the provided information will be helpful so keep your answer breif and to the point while focusing only on the most important facts.",
        f"\nRecent news:\n{community_answer}"
    ])
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
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
              "text": question
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