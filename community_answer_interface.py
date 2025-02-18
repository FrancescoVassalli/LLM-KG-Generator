from typing import List
from openai import OpenAI
import logging
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

# def complete_community_answer(community_summary:str,question:str)->str:
    
#     completion = client.chat.completions.create(
#       model="gpt-4o",
#       messages=[
#         {
#           "role": "system",
#           "content": [
#             {
#               "type": "text",
#               "text": COMMUNITY_SUMMARY_SYSTEM_PROMPT
#             }
#           ]
#         },
#         {
#           "role": "user",
#           "content": [
#             {
#               "type": "text",
#               "text": community_summary_input
#             }
#           ]
#         }
#       ],
#       response_format={
#         "type": "text"
#       },
#       temperature=1,
#       max_completion_tokens=2048,
#       top_p=1,
#       frequency_penalty=0,
#       presence_penalty=0
#     )
#     return completion.choices[0].message.content