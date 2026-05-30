import asyncio
import io  
from PIL import Image  
from google import genai
from hydrogram import Client, filters, enums
from info import GEMINI_API_KEY

# ==========================================
# 🧠 AI CONFIGURATION (Gemini 2.5 Flash ⚡)
# ==========================================
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

# ==========================================
# 🗣️ AI CHAT COMMAND
# ==========================================
@Client.on_message(filters.command(["ask", "ai"]))
async def ask_ai(client, message):
    if not ai_client:
        return await message.reply("❌ **AI Error:** API Key missing.")

    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply(
            "⚡ **Gemini 2.5 Flash**\n\n"
            "Usage:\n"
            "• `/ask Who is Batman?`\n"
            "• Reply to text/photo with `/ask`"
        )

    # --- INPUT PROCESSING ---
    question = ""
    image_input = None
    
    # 1. टेक्स्ट चेक करना (कमांड के साथ या रिप्लाई में)
    if len(message.command) > 1:
        question = message.text.split(None, 1)[1]
    elif message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        question = message.reply_to_message.text or message.reply_to_message.caption

    # 2. फोटो चेक करना (नया फीचर)
    if message.reply_to_message and message.reply_to_message.photo:
        status_msg = await message.reply("⬇️ Downloading Image...")
        try:
            # ✅ FIX: सीधे मैसेज के बजाय 'message.reply_to_message.photo' को पास किया ताकि लोकेशन सही मिले
            photo_stream = await client.download_media(message.reply_to_message.photo, in_memory=True)
            image_input = Image.open(io.BytesIO(photo_stream.getbuffer()))
            await status_msg.delete()
        except Exception as e:
            await status_msg.delete()
            return await message.reply(f"❌ Image Error: {e}")

    # अगर न तो टेक्स्ट है और न ही फोटो
    if not question and not image_input:
        return await message.reply("❌ कृपया सवाल पूछें या फोटो पर रिप्लाई करें।")
    
    # अगर सिर्फ फोटो है और सवाल नहीं लिखा, तो डिफ़ॉल्ट सवाल सेट करें
    if image_input and not question:
        question = "Describe this image."

    # Gemini को भेजने के लिए कंटेंट तैयार करें
    contents_body = [question]
    if image_input:
        contents_body.append(image_input)

    status = await message.reply("⚡ Thinking (Flash Mode)...")
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    try:
        loop = asyncio.get_event_loop()
        
        # ✅ FIX: मॉडल का नाम 'gemini-2.5-flash' किया गया जो कि एकदम सही और सुपरफ़ास्ट है
        response = await loop.run_in_executor(
            None, 
            lambda: ai_client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=contents_body
            )
        )
        
        if not response.text:
            return await status.edit("❌ Empty Response.")

        answer = response.text

        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.reply(answer[i:i+4000], parse_mode=enums.ParseMode.MARKDOWN)
            await status.delete()
        else:
            await status.edit(answer, parse_mode=enums.ParseMode.MARKDOWN)

    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)}`")
