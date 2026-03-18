import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash") # Use flash instead of flash-lite for better instruction following

def clean_json(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

try:
    print("Generating 50 symptoms with the exact requested JSON structure...")
    schema = '''[
  {
    "symptoms": "Name of the symptom (e.g. Headache)",
    "primary_advice": "What might be happening based on these symptoms and immediate doctor advice.",
    "healthcare_diet_or_advice": "Specific diet, lifestyle changes, or home care advice.",
    "medicine_to_take": "Over the counter or general medicine recommendations.",
    "when_to_visit_doctor": "Warning signs that indicate a doctor visit is necessary immediately."
  }
]'''
    
    symptoms_prompt = f"Generate a JSON array of exactly 50 common medical symptoms. You MUST strictly follow this exact JSON schema structure for each object:\n{schema}\n\nMake it highly accurate. Return ONLY a valid JSON array and nothing else. Do not use markdown blocks."
    
    symptoms_resp = model.generate_content(symptoms_prompt)
    symptoms_data = json.loads(clean_json(symptoms_resp.text))
    
    with open('symptoms_new.json', 'w', encoding='utf-8') as f:
        json.dump(symptoms_data, f, indent=2)

    print(f"Done! Saved {len(symptoms_data)} meticulously structured symptoms to symptoms_new.json.")

except Exception as e:
    print(f"Error occurred: {e}")
