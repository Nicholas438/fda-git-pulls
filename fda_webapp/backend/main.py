import base64
import io
import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from PIL import Image
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="FDA Food Nutrition Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
CHAT_MODEL = "llama-3.3-70b-versatile"

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

After providing the label, let the user know they can ask any follow-up questions about the food, its ingredients, healthier alternatives, or dietary advice."""

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
Always base your advice on the food context from earlier in the conversation."""


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    food_context: str = ""


def encode_image_to_base64(image_bytes: bytes, content_type: str) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def compress_image(image_bytes: bytes, max_size_kb: int = 1000) -> tuple[bytes, str]:
    """Compress image if it's too large, return bytes and mime type."""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA to RGB if needed
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output = io.BytesIO()
    quality = 85
    img.save(output, format="JPEG", quality=quality, optimize=True)
    compressed = output.getvalue()

    # If still too large, reduce quality further
    while len(compressed) > max_size_kb * 1024 and quality > 20:
        quality -= 10
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        compressed = output.getvalue()

    return compressed, "image/jpeg"


@app.post("/api/analyze-food")
async def analyze_food(file: UploadFile = File(...)):
    """Analyze a food image and return a Nutrition Facts label."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()

    # Compress image for faster processing
    compressed_bytes, mime_type = compress_image(image_bytes)
    image_b64 = encode_image_to_base64(compressed_bytes, mime_type)

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": NUTRITION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
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

        nutrition_label = response.choices[0].message.content
        return {"nutrition_label": nutrition_label, "model": VISION_MODEL}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Continue the conversation about the food."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Build the messages array for the API
    system_content = CHAT_SYSTEM_PROMPT
    if request.food_context:
        system_content += f"\n\nContext — the user's food analysis:\n{request.food_context}"

    api_messages = [{"role": "system", "content": system_content}]

    for msg in request.messages:
        api_messages.append({"role": msg.role, "content": msg.content})

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=api_messages,
            max_tokens=800,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        return {"reply": reply, "model": CHAT_MODEL}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
