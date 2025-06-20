import json, os
from openai import OpenAI

def save_transcript(user: str, transcript: list):
    os.makedirs("memory", exist_ok=True)
    with open(f"memory/{user}.json", "w") as f:
        json.dump(transcript, f)

def get_followups(user: str) -> str:
    try:
        with open(f"memory/{user}.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        return "No history found."

    prompt = f"Here is a user's conversation: {data}. What are creative follow-up ideas?"
    response = OpenAI().ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]
