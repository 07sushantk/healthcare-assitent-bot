import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash-lite")

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
    print("Generating 50 symptoms...")
    symptoms_prompt = "Generate a JSON array of exactly 50 common medical symptoms. Each object must have 'name', 'description', and 'advice' keys. Make it highly accurate. Return ONLY a valid JSON array and nothing else."
    symptoms_resp = model.generate_content(symptoms_prompt)
    symptoms_data = json.loads(clean_json(symptoms_resp.text))
    
    # Merge with existing
    try:
        with open(BASE_DIR / 'symptoms.json', 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except:
        existing = []
    
    # Avoid exact duplicates by name
    existing_names = set(x.get('name', '').lower() for x in existing)
    for s in symptoms_data:
        if s.get('name', '').lower() not in existing_names:
            existing.append(s)

    with open(BASE_DIR / 'symptoms.json', 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2)

    print("Generating 50 medicines...")
    medicines_prompt = "Generate a JSON array of exactly 50 common medicines/drugs. Each object must have 'name', 'usage', 'side_effects', and 'dosage' keys. Return ONLY a valid JSON array and nothing else."
    medicines_resp = model.generate_content(medicines_prompt)
    medicines_data = json.loads(clean_json(medicines_resp.text))
    
    try:
        with open(BASE_DIR / 'medicines.json', 'r', encoding='utf-8') as f:
            existing_meds = json.load(f)
    except:
        existing_meds = []
        
    existing_med_names = set(x.get('name', '').lower() for x in existing_meds)
    for m in medicines_data:
        if m.get('name', '').lower() not in existing_med_names:
            existing_meds.append(m)

    with open(BASE_DIR / 'medicines.json', 'w', encoding='utf-8') as f:
        json.dump(existing_meds, f, indent=2)

    print(f"Done! Saved {len(existing)} symptoms and {len(existing_meds)} medicines.")
except Exception as e:
    print(f"Error occurred: {e}")
