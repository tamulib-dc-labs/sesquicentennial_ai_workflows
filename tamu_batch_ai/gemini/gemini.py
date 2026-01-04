from google import genai
from google.genai import types
import PIL.Image
import os

client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

with open('prompts/gemini-htr.md', 'r') as f:
    prompt = f.read()

img = PIL.Image.open('/Users/mark.baggett/Desktop/gemini_sample2_1.jpg')

response = client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(
        system_instruction=prompt,
        temperature=0.0,
    ),
    contents=[
        "Please transcribe the following image according to the established guidelines:",
        img
    ]
)

print(response.text)