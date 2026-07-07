import base64
import io
import logging
import os
import time
import traceback
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import Groq
from PIL import Image
from pydantic import BaseModel

from guardrails import (
    GUARDRAIL_SYSTEM_ADDENDUM,
    check_chat_request,
    check_message,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nutrichat")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="FDA Food Nutrition Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info("→ %s %s", request.method, request.url.path)

    try:
        response = await call_next(request)
    except Exception:
        # Unhandled exception — log full traceback then re-raise
        logger.error(
            "Unhandled exception on %s %s\n%s",
            request.method,
            request.url.path,
            traceback.format_exc(),
        )
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    level = logging.INFO if response.status_code < 400 else logging.WARNING
    logger.log(
        level,
        "← %s %s  status=%d  %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
CHAT_MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
NUTRITION_SYSTEM_PROMPT = """You are a professional nutritionist and dietitian AI assistant.
When a user shares a food image, analyze it carefully and provide a detailed FDA-style Nutrition Facts label.

Format your response EXACTLY like this (use this structure every time for a food image):

## 🥗 Food Identified: [Food Name]

---

### Nutrition Facts
**Serving Size:** [estimated serving size]
**Servings Per Container:** About [number]

| Nutrient | Amount Per Serving | % Daily Value* |
|---|---|---|
| **Calories** | [kcal] | |
| **Total Fat** | [g] | [%] |
| Saturated Fat | [g] | [%] |
| Trans Fat | [g] | |
| **Cholesterol** | [mg] | [%] |
| **Sodium** | [mg] | [%] |
| **Total Carbohydrate** | [g] | [%] |
| Dietary Fiber | [g] | [%] |
| Total Sugars | [g] | |
| Added Sugars | [g] | [%] |
| **Protein** | [g] | |
| Vitamin D | [mcg] | [%] |
| Calcium | [mg] | [%] |
| Iron | [mg] | [%] |
| Potassium | [mg] | [%] |

*Percent Daily Values are based on a 2,000 calorie diet.

---

### 💡 Quick Health Summary
[2-3 sentences summarizing the nutritional highlights, what's good, what to watch out for]

---

After providing the label, let the user know they can ask any follow-up questions about the food, its ingredients, healthier alternatives, or dietary advice.""" + GUARDRAIL_SYSTEM_ADDENDUM

CHAT_SYSTEM_PROMPT = """You are a knowledgeable, friendly nutritionist and dietitian AI.
The user has already received a Nutrition Facts label for their food.
Now have a warm, conversational back-and-forth with them about:
- The nutritional content and what it means for their health
- Whether it fits their dietary goals
- Healthier alternatives or modifications
- Portion control advice
- How it fits into a balanced diet
- Ingredient questions
- Allergen information
- Cooking or preparation tips

Keep responses concise, friendly, and practical. Use emojis sparingly to keep things warm.
Always base your advice on the food context from earlier in the conversation.""" + GUARDRAIL_SYSTEM_ADDENDUM


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    food_context: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def compress_image(image_bytes: bytes, max_size_kb: int = 1000) -> tuple[bytes, str]:
    """Compress image to stay under max_size_kb, returns (bytes, mime_type)."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output = io.BytesIO()
    quality = 85
    img.save(output, format="JPEG", quality=quality, optimize=True)
    compressed = output.getvalue()

    while len(compressed) > max_size_kb * 1024 and quality > 20:
        quality -= 10
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        compressed = output.getvalue()

    logger.debug(
        "Image compressed: original=%dKB  final=%dKB  quality=%d",
        len(image_bytes) // 1024,
        len(compressed) // 1024,
        quality,
    )
    return compressed, "image/jpeg"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/api/analyze-food")
async def analyze_food(file: UploadFile = File(...)):
    """Analyze a food image and return an FDA-style Nutrition Facts label."""
    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning("analyze-food: rejected non-image upload content_type=%s", file.content_type)
        raise HTTPException(status_code=400, detail="File must be an image")

    # Guardrail: scan filename for injection payloads
    if file.filename:
        gr = check_message(file.filename, field="filename")
        if not gr.allowed:
            logger.warning(
                "analyze-food: guardrail blocked filename  reason=%r  category=%s",
                gr.reason, gr.category,
            )
            raise HTTPException(status_code=400, detail="Invalid request")

    logger.info("analyze-food: received file filename=%s size_hint=%s", file.filename, file.size)

    image_bytes = await file.read()
    compressed_bytes, mime_type = compress_image(image_bytes)
    image_b64 = encode_image_to_base64(compressed_bytes)

    try:
        logger.info("analyze-food: calling Groq vision model=%s", VISION_MODEL)
        t0 = time.perf_counter()

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": NUTRITION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                        },
                        {
                            "type": "text",
                            "text": "Please analyze this food and provide a complete Nutrition Facts label as instructed.",
                        },
                    ],
                },
            ],
            max_tokens=1500,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        nutrition_label = response.choices[0].message.content
        tokens_used = getattr(response.usage, "total_tokens", "n/a")

        logger.info(
            "analyze-food: OK  model=%s  tokens=%s  %.1fms  label_chars=%d",
            VISION_MODEL,
            tokens_used,
            elapsed_ms,
            len(nutrition_label or ""),
        )
        return {"nutrition_label": nutrition_label, "model": VISION_MODEL}

    except Exception as e:
        logger.error("analyze-food: Groq call failed\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Continue the conversation about the food."""
    if not request.messages:
        logger.warning("chat: request arrived with no messages")
        raise HTTPException(status_code=400, detail="No messages provided")

    # Guardrail: pre-filter all user messages + food context
    gr = check_chat_request(request.messages, request.food_context)
    if not gr.allowed:
        logger.warning(
            "chat: guardrail blocked request  reason=%r  category=%s",
            gr.reason, gr.category,
        )
        # Return a polite refusal rather than a hard error so the UI can display it
        return {
            "reply": (
                "I'm here to help with food and nutrition topics only. "
                "I can't help with that request — is there something about "
                "what you're eating I can assist you with? 🥗"
            ),
            "model": CHAT_MODEL,
            "blocked": True,
            "block_category": gr.category,
        }

    n_messages = len(request.messages)
    has_context = bool(request.food_context)
    logger.info("chat: n_messages=%d  has_food_context=%s", n_messages, has_context)

    system_content = CHAT_SYSTEM_PROMPT
    if request.food_context:
        system_content += f"\n\nContext — the user's food analysis:\n{request.food_context}"

    api_messages = [{"role": "system", "content": system_content}]
    for msg in request.messages:
        api_messages.append({"role": msg.role, "content": msg.content})

    try:
        logger.info("chat: calling Groq model=%s", CHAT_MODEL)
        t0 = time.perf_counter()

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=api_messages,
            max_tokens=800,
            temperature=0.7,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        reply = response.choices[0].message.content
        tokens_used = getattr(response.usage, "total_tokens", "n/a")

        logger.info(
            "chat: OK  model=%s  tokens=%s  %.1fms  reply_chars=%d",
            CHAT_MODEL,
            tokens_used,
            elapsed_ms,
            len(reply or ""),
        )
        return {"reply": reply, "model": CHAT_MODEL}

    except Exception as e:
        logger.error("chat: Groq call failed\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@app.get("/api/health")
async def health():
    logger.debug("health check")
    return {"status": "ok"}
