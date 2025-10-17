import os
import sys
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

# Initialize Gemini client with API key
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
if len(sys.argv) <= 1:
  print("You didn't enter a txt file for me to gemini yup")
input_file = sys.argv[1]
output_file = "fixed.txt"
with open(input_file, "r") as f:
    user_text = f.read()
# Generate content
prompt = f"Fix the grammar and clarity of this text. Output the corrected version only:\n\n{user_text}"

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[{"role": "user", "parts": [{"text": prompt}]}],
)


with open(output_file, "w") as f:
    f.write(response.text.strip())
print(f"Old file: {user_text}")
print(f"This is the response: \n{response.text}")
print(f"Saved to {output_file} yup")
