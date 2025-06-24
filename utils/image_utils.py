import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_image_from_prompt(prompt: str) -> str:
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        print("❌ DALL·E Error:", e)
        return ""
