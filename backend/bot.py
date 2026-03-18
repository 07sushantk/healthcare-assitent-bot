# AI Healthcare Assistant Telegram Bot with RAG

import os
import io
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from PIL import Image
from langdetect import detect, DetectorFactory, LangDetectException
from pathlib import Path

# Import RAG pipeline
from rag import rag_pipeline
from embeddings import get_embedding

DetectorFactory.seed = 0

# --- Setup / env ---
load_dotenv(Path(__file__).resolve().parent / ".env")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY missing")
    raise SystemExit("GEMINI_API_KEY missing")

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error("Failed to configure Gemini API: %s", e)
    raise

SYSTEM_INSTRUCTION = (
    "You are a concise healthcare analysis assistant. Do NOT produce greetings. "
    "When asked to summarize symptoms, produce a single English sentence only. "
    "When asked for details, follow the requested markdown headings and be concise."
)

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite",
    system_instruction=SYSTEM_INSTRUCTION,
)

# --- Local yes-words dictionary (fast checks) ---
YES_WORDS = {
    "en": {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "please", "tell me more", "more", "continue"},
    "hi": {"हाँ", "हां", "ठीक", "ठीक है", "जी", "हाँ जी", "हूँ"},
    "mr": {"होय", "हो", "ठीक"},
    "th": {"ใช่", "ได้", "โอเค"},
    "ta": {"ஆம்", "ஆமாம்"},
    "kn": {"ಹೌದು", "ಹೌ"},
    "te": {"అవును"},
    "sw": {"ndio"},
}

LANG_NAME_TO_CODE = {
    "english": "en", "eng": "en",
    "hindi": "hi", "hin": "hi",
    "marathi": "mr",
    "thai": "th",
    "tamil": "ta",
    "telugu": "te",
    "kannada": "kn",
    "bengali": "bn",
    "gujarati": "gu",
    "swahili": "sw",
}

COMMON_ENGLISH_WORDS = {
    "i","am","i'm","you","are","today","feeling","have","has","had","cold","fever","cough","headache",
    "sore","throat","pain","chills","body","ache","nausea","vomiting","diarrhea","tired","weak","breath",
    "shortness","runny","nose","congestion","sneezing","temperature","hot","chilly","dizzy"
}

# --- Heuristics & detection ---
def _unicode_script_guess(text: str) -> str:
    if not text:
        return "en"
    for ch in text:
        c = ord(ch)
        if 0x0900 <= c <= 0x097F:
            return "hi"
        if 0x0E00 <= c <= 0x0E7F:
            return "th"
        if 0x0B80 <= c <= 0x0BFF:
            return "te"
        if 0x0C80 <= c <= 0x0CFF:
            return "kn"
        if 0x0980 <= c <= 0x09FF:
            return "bn"
        if 0x0A00 <= c <= 0x0A7F:
            return "gu"
    return "en"

def detect_language_fast(text: str) -> str:
    if not text:
        return "en"
    try:
        lang = detect(text)
        if isinstance(lang, str) and len(lang) >= 2:
            return lang[:2]
    except LangDetectException:
        return None
    except Exception as e:
        logger.warning("langdetect failed: %s", e)
        return None

def is_likely_english(text: str, threshold: float = 0.35) -> bool:
    if not text:
        return False
    tokens = [t.strip(".,!?()[]\"'").lower() for t in text.split()]
    if not tokens:
        return False
    matches = sum(1 for t in tokens if t in COMMON_ENGLISH_WORDS)
    ratio = matches / len(tokens)
    ascii_letters = sum(1 for t in tokens if all(ord(c) < 128 for c in t))
    if ratio >= threshold or (ascii_letters / len(tokens) > 0.7 and matches >= 1):
        return True
    return False

async def detect_language_with_model(text: str) -> str:
    if not text:
        return "en"
    prompt = (
        "Detect the language of the text below and return ONLY the 2-letter ISO 639-1 language code. "
        "If you cannot, return the language name in English (e.g., 'Hindi').\n\n"
        f"---TEXT---\n{text}\n---END---\nReturn only the code or name."
    )
    try:
        resp = await model.generate_content_async(prompt)
        out = (resp.text or "").strip().lower()
        if not out:
            raise ValueError("Empty model detect")
        token = out.split()[0].strip().strip(".,;:\"'")
        if len(token) == 2 and token.isalpha():
            return token
        if token in LANG_NAME_TO_CODE:
            return LANG_NAME_TO_CODE[token]
        for name, code in LANG_NAME_TO_CODE.items():
            if name in token:
                return code
    except Exception as e:
        logger.warning("Model language detect failed: %s", e)
    guess = _unicode_script_guess(text)
    return guess

async def detect_language_of_text(text: str) -> str:
    if not text:
        return "en"
    fast = detect_language_fast(text)
    if fast == "en":
        return "en"
    if is_likely_english(text):
        return "en"
    if fast:
        if fast != "en" and is_likely_english(text, threshold=0.2):
            return "en"
        return fast
    model_lang = await detect_language_with_model(text)
    if model_lang != "en" and is_likely_english(text, threshold=0.2):
        return "en"
    return model_lang or _unicode_script_guess(text)

# --- Translation helpers ---
async def translate_to_english(text: str) -> str:
    if not text:
        return ""
    prompt = (
        "Translate the following text to English. Return only the translated text.\n\n"
        f"---TEXT---\n{text}\n---END---"
    )
    try:
        resp = await model.generate_content_async(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        logger.warning("translate_to_english failed: %s", e)
        return text

async def translate_to_target(text: str, target_lang: str) -> str:
    if not text:
        return ""
    if not target_lang or target_lang.startswith("en"):
        return text
    prompt = (
        f"Translate the following English text into the language with ISO code '{target_lang}'.\n"
        "Return ONLY the translated text and nothing else.\n\n"
        f"---TEXT---\n{text}\n---END---"
    )
    try:
        resp = await model.generate_content_async(prompt)
        translation = (resp.text or "").strip()
        if not translation:
            return text
        return translation
    except Exception as e:
        logger.warning("translate_to_target failed for %s: %s", target_lang, e)
        return text

# --- Affirmative detection ---
async def is_user_affirmative(raw_text: str, detected_lang: str) -> bool:
    if not raw_text:
        return False
    lowered = raw_text.strip().lower()
    local_set = YES_WORDS.get(detected_lang)
    if local_set:
        for w in local_set:
            if lowered == w or lowered.startswith(w):
                return True
    try:
        trans = await translate_to_english(raw_text)
        if not trans:
            return False
        lowered_en = trans.strip().lower()
        for w in YES_WORDS["en"]:
            if lowered_en == w or lowered_en.startswith(w):
                return True
    except Exception as e:
        logger.warning("affirmative fallback failed: %s", e)
    return False

# --- Messaging helpers ---
async def send_localized_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text_en: str, user_lang: str):
    if not user_lang or user_lang.startswith("en"):
        await update.message.reply_text(text_en)
        return
    translated = await translate_to_target(text_en, user_lang)
    await update.message.reply_text(translated)

# --- Image classification helper ---
async def classify_image_type(img: Image.Image) -> str:
    prompt = (
        "Look at the image and choose the single best tag from this set (medicine, prescription, label, xray, mri, other). "
        "Return ONLY the tag (one word)."
    )
    try:
        resp = await model.generate_content_async([prompt, img])
        tag = (resp.text or "").strip().lower().split()[0]
        if tag.startswith("x"): return "xray"
        if tag.startswith("mri"): return "mri"
        if "pres" in tag: return "prescription"
        if "pill" in tag or "tablet" in tag or "medicine" in tag: return "medicine"
        if "label" in tag: return "label"
        return tag if tag in {"medicine", "prescription", "label", "xray", "mri", "other"} else "other"
    except Exception as e:
        logger.warning("classify_image_type failed: %s", e)
        return "other"

# --- Handlers ---

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_name = update.effective_user.first_name or ""
    welcome_message = f"Hello {user_name}! 👋 I'm your AI healthcare assistant powered by RAG. Tell me about your symptoms or show me a picture of a medicine."
    await update.message.reply_text(welcome_message)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text or ""
    detected_lang = await detect_language_of_text(raw)
    user_lang = context.user_data.get("preferred_lang") or detected_lang

    if context.user_data.get("pending_action"):
        if await is_user_affirmative(raw, detected_lang):
            await handle_follow_up(update, context)
            return
        context.user_data.clear()
        await update.message.reply_text("Okay — if you need anything else, tell me.")
        return

    context.user_data.clear()
    context.user_data["query_type"] = "text"
    context.user_data["last_query_original"] = raw
    context.user_data["last_query_lang"] = detected_lang

    text_en = await translate_to_english(raw)
    context.user_data["last_query_en"] = text_en

    await update.message.chat.send_action(action="typing")
    
    # NEW FLOW: Call RAG Pipeline
    response_en = await rag_pipeline(text_en)
    
    # Append follow-up question
    response_en += " Would you like to know more?"
    
    context.user_data["last_single_en"] = response_en
    context.user_data["preferred_reply_lang"] = user_lang
    context.user_data["pending_action"] = True
    
    await send_localized_reply(update, context, response_en, user_lang)

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or ""
    detected_lang = await detect_language_of_text(caption) if caption else (update.effective_user.language_code or "en").split("-")[0]
    user_lang = context.user_data.get("preferred_lang") or detected_lang

    try:
        await update.message.chat.send_action(action="typing")
        photo = update.message.photo[-1]
        file_bytes = io.BytesIO()
        file_obj = await context.bot.get_file(photo.file_id)
        await file_obj.download_to_memory(out=file_bytes)
        file_bytes.seek(0)
        img = Image.open(file_bytes).convert("RGB")

        context.user_data["query_type"] = "image"
        context.user_data["last_query_image_bytes"] = file_bytes.getvalue()
        context.user_data["last_query_lang"] = detected_lang

        image_type = await classify_image_type(img)
        context.user_data["image_type"] = image_type

        # NEW FLOW: Call RAG Pipeline with image context
        query = caption if caption else f"Analyze this {image_type} image."
        query_en = await translate_to_english(query)
        
        response_en = await rag_pipeline(query_en, img=img)
        response_en += " Would you like to know more?"
        
        context.user_data["last_single_en"] = response_en
        context.user_data["preferred_reply_lang"] = user_lang
        context.user_data["pending_action"] = True
        
        await send_localized_reply(update, context, response_en, user_lang)

    except Exception as e:
        logger.error("image_handler error: %s", e)
        await update.message.reply_text("I'm sorry, I couldn't analyze that image.")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tel_lang = (update.effective_user.language_code or "en").split("-")[0]
    user_lang = context.user_data.get("preferred_lang") or tel_lang
    try:
        await update.message.chat.send_action(action="typing")
        voice = update.message.voice
        file_bytes = io.BytesIO()
        file_obj = await context.bot.get_file(voice.file_id)
        await file_obj.download_to_memory(out=file_bytes)
        file_bytes.seek(0)

        uploaded_file = genai.upload_file(file_bytes, mime_type=voice.mime_type)
        trans_prompt = "Transcribe the audio and return ONLY the transcription text in English."
        resp = await model.generate_content_async([trans_prompt, uploaded_file])
        transcribed_text = (resp.text or "").strip()

        context.user_data["last_query_en"] = transcribed_text
        context.user_data["query_type"] = "text"
        context.user_data["last_query_lang"] = user_lang

        # NEW FLOW: Call RAG Pipeline
        response_en = await rag_pipeline(transcribed_text)
        response_en += " Would you like to know more?"
        
        context.user_data["last_single_en"] = response_en
        context.user_data["preferred_reply_lang"] = user_lang
        context.user_data["pending_action"] = True
        
        await send_localized_reply(update, context, response_en, user_lang)
    except Exception as e:
        logger.error("voice_handler error: %s", e)
        await update.message.reply_text("I'm sorry, I couldn't process that voice note.")

async def handle_follow_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Keep existing follow-up logic for detailed analysis
    query_type = context.user_data.get("query_type")
    user_lang = context.user_data.get("preferred_reply_lang") or context.user_data.get("preferred_lang") or (update.effective_user.language_code or "en").split("-")[0]
    last_en = context.user_data.get("last_query_en") or (await translate_to_english(context.user_data.get("last_query_original") or ""))
    image_type = context.user_data.get("image_type")

    await update.message.chat.send_action(action="typing")
    try:
        # Use RAG for follow-up as well to maintain context consistency
        detailed_prompt = (
            f"Provide a detailed medical analysis for: {last_en}. "
            "Use the provided context if available. "
            "Format with these markdown headings:\n"
            "*Possible Condition*\n---\n*What You Can Do at Home*\n---\n*When to See a Doctor*\n---\n"
            "End with a medical disclaimer."
        )
        
        # For follow-up, we can reuse the rag_pipeline logic but with a more detailed prompt
        # (Simplified here for brevity, but could be expanded)
        resp = await model.generate_content_async(detailed_prompt)
        detailed_en = (resp.text or "").strip()

        detailed_local = await translate_to_target(detailed_en, user_lang)
        await update.message.reply_text(detailed_local)
    except Exception as e:
        logger.error("handle_follow_up error: %s", e)
        await update.message.reply_text("Sorry, I ran into an issue getting the details for you.")
    finally:
        context.user_data.clear()

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found")
        return
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, image_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    logger.info("RAG Healthcare Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
