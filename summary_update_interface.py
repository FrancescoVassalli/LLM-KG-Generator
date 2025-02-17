from openai import OpenAI
client = OpenAI()


def complete_entity_summary_update(entity_name:str, new_text:str, old_summary:str)->str:
    system_prompt = ''.join([
        'You are a detial oriented knowledge graph creator.',
        'The goal of the knowledge graph is to represent information from recent news sources by holding all of the entities (persons, leaders, reporters, newspapers, groups, countries, organizations, cities, provinces, buildings, treaties, meetings, important dates, important claims) and their relationships.',
        f'Each entity has a summary explaining what it is. Unfortunately, the sumary for the entity called {entity_name} is out of date.'
        f'However, the user will provide new information and you should use that to update just the summary for {entity_name}.',
        f'Here is the existing summary:\n{old_summary}\n',
        f'Retain the information from the existing summary and keep the new summary concise while adding only the details relevant to {entity_name}',
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
              "text": new_text
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


