import asyncio
import io  
import time
import logging
from PIL import Image  
from google import genai
from google.genai import types as genai_types
from hydrogram import Client, filters, enums
from info import GEMINI_API_KEY
from utils import is_rate_limited

logger = logging.getLogger(__name__)

# ==========================================
# 🧠 AI CONFIGURATION & PERSONA
# ==========================================
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

# बॉट को प्रोफेशनल लुक देने के लिए सिस्टम प्रॉम्प्ट
AI_SYSTEM_INSTRUCTION = (
    "You are the advanced built-in AI Assistant of Fast Finder Telegram Bot. "
    "Provide clear, concise, and helpful answers. Use neat Markdown formatting with bullet points if necessary. "
    "Keep answers under Telegram's formatting limits where possible."
)

# 🧠 इन-मेमोरी चैट कॉन्टेक्स्ट कैशे (Koyeb RAM Safe)
AI_CHAT_MEMORY = {}
MEMORY_TTL = 600  # हर यूजर का संदर्भ 10 मिनट तक याद रहेगा

def get_user_history(user_id):
    """यूजर की चैट हिस्ट्री प्राप्त करें और एक्सपायर्ड डेटा को साफ़ करें।"""
    now = time.time()
    # कैशे क्लीनअप
    if len(AI_CHAT_MEMORY) > 300:
        for k in [k for k, (v, ts) in AI_CHAT_MEMORY.items() if now - ts > MEMORY_TTL]:
            AI_CHAT_MEMORY.pop(k, None)

    if user_id in AI_CHAT_MEMORY and (now - AI_CHAT_MEMORY[user_id][1]) < MEMORY_TTL:
        return AI_CHAT_MEMORY[user_id][0]
    return []

# ==========================================
# 🗣️ ULTRA ADVANCED AI CHAT COMMAND
# ==========================================
@Client.on_message(filters.command(["ask", "ai"]))
async def ask_ai(client, message):
    if not ai_client:
        return await message.reply("❌ **AI Error:** API Key missing from configuration.")

    # 🛡️ एंटी-स्पैम सुरक्षा: प्रति यूजर 6 सेकंड का कूलडाउन (Koyeb Protection)
    if is_rate_limited(message.from_user.id, "cmd_ai", seconds=6):
        return await message.reply("⏳ **Too Fast!** Please wait a few seconds before asking again.")

    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply(
            "⚡ <b>Gemini 2.5 Flash Ultra</b>\n\n"
            "<b>Usage:</b>\n"
            "• <code>/ai Who are you?</code>\n"
            "• Reply to any text/photo with <code>/ai</code>\n\n"
            "💡 <i>This AI remembers your last 10 minutes of conversation context!</i>",
            parse_mode=enums.ParseMode.HTML
        )

    question = ""
    image_input = None
    user_id = message.from_user.id
    
    # 1. इनपुट टेक्स्ट प्रोसेसिंग
    if len(message.command) > 1:
        question = message.text.split(None, 1)[1]
    elif message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        question = message.reply_to_message.text or message.reply_to_message.caption

    # 2. इनपुट इमेज प्रोसेसिंग (Vision Feature)
    if message.reply_to_message and message.reply_to_message.photo:
        status_msg = await message.reply("⬇️ Downloading Image for Analysis...")
        try:
            photo_stream = await client.download_media(message.reply_to_message.photo, in_memory=True)
            image_input = Image.open(io.BytesIO(photo_stream.getbuffer()))
            await status_msg.delete()
        except Exception as e:
            await status_msg.delete()
            return await message.reply(f"❌ **Image Download Error:** `{e}`")

    if not question and not image_input:
        return await message.reply("❌ कृपया कोई प्रश्न पूछें या किसी फ़ाइल/फोटो पर रिप्लाई करें।")
    
    if image_input and not question:
        question = "Examine this image carefully and describe it in detail."

    # 3. चैट कॉन्टेक्स्ट मेकर (History Integration)
    history = get_user_history(user_id)
    contents_body = []
    
    # पुरानी हिस्ट्री को स्ट्रक्चर में जोड़ें (सिर्फ टेक्स्ट मॉडल्स के लिए संदर्भ रखने हेतु)
    if not image_input:
        for role, text in history:
            contents_body.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part.from_text(text=text)]
            ))
            
    # वर्तमान सवाल जोड़ें
    current_parts = [genai_types.Part.from_text(text=question)]
    if image_input:
        # विजन इनपुट के लिए पीआईएल इमेज को पार्ट्स में अपेंड करें
        contents_body = [question, image_input]
    else:
        contents_body.append(genai_types.Content(role="user", parts=current_parts))

    status = await message.reply("⚡ <i>Thinking (Flash Mode)...</i>", parse_mode=enums.ParseMode.HTML)
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    try:
        loop = asyncio.get_event_loop()
        
        # एडवांस कॉन्फ़िगरेशन सेटिंग्स (सिस्टम इंस्ट्रक्शन + क्रिएटिविटी कंट्रोल)
        ai_config = genai_types.GenerateContentConfig(
            system_instruction=AI_SYSTEM_INSTRUCTION,
            temperature=0.7,
            top_p=0.95
        )
        
        # नॉन-ब्लॉकिंग एपीआई एक्जीक्यूशन
        response = await loop.run_in_executor(
            None, 
            lambda: ai_client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=contents_body,
                config=ai_config
            )
        )
        
        if not response.text:
            return await status.edit("❌ **AI Error:** Empty response generated.")

        answer = response.text

        # 4. हिस्ट्री को कैशे में अपडेट करना (अगर विजन नहीं है तो संदर्भ सुरक्षित रखें)
        if not image_input:
            history.append(("user", question))
            history.append(("model", answer))
            # कैशे लिमिटेशन: केवल आख़िरी 6 संदेश याद रखें ताकि रैम ओवरलोड न हो
            if len(history) > 6:
                history = history[-6:]
            AI_CHAT_MEMORY[user_id] = (history, time.time())

        # 5. टेलीग्राम मैसेज स्प्लिटिंग फिक्स (Safe Long Response Sender)
        if len(answer) > 4000:
            await status.delete()
            # यूज़र को कतारबद्ध तरीके से रिस्पॉन्स भेजें
            chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
            for chunk in chunks:
                await message.reply(chunk, parse_mode=enums.ParseMode.MARKDOWN)
                await asyncio.sleep(0.5)
        else:
            await status.edit(answer, parse_mode=enums.ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        await status.edit(f"❌ **AI Connection Error:**\n<code>{str(e)}</code>", parse_mode=enums.ParseMode.HTML)
