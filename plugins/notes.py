import time
import html
from hydrogram import Client, filters, enums
from database.users_chats_db import db

# =========================
# 🚀 SMART CACHE SYSTEM
# =========================
NOTES_CACHE = {}
CACHE_TTL = 300  

async def get_notes(chat_id):
    now = time.time()
    if chat_id in NOTES_CACHE and (now - NOTES_CACHE[chat_id][1]) < CACHE_TTL:
        return NOTES_CACHE[chat_id][0]
    
    data = await db.get_all_notes(chat_id) or {}
    NOTES_CACHE[chat_id] = (data, now)
    return data

async def is_admin(c, m):
    if m.sender_chat and m.sender_chat.id == m.chat.id: return True 
    if not m.from_user: return False
    try:
        user = await c.get_chat_member(m.chat.id, m.from_user.id)
        return user.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except:
        return False

# =========================
# 📝 SAVE, DELETE & LIST
# =========================

@Client.on_message(filters.group & filters.command(["save", "addnote"]))
async def save_note(c, m):
    if not await is_admin(c, m): return
    if len(m.command) < 2 or not m.reply_to_message:
        return await m.reply("❗ Use: `/save <name>` (Reply to a message)")
    
    name = m.command[1].lower()
    reply = m.reply_to_message
    
    # 🎯 Smart Media Detection
    note_type, file_id = "text", None
    for t in ["photo", "video", "document", "sticker", "animation"]:
        media = getattr(reply, t, None)
        if media:
            note_type, file_id = t, media.file_id
            break
    
    # ✅ FIX: .markdown स्ट्रिंग क्रैश बग को पूरी तरह से साफ किया गया
    note_data = {
        "type": note_type,
        "file_id": file_id,
        "caption": reply.caption if reply.caption else "", 
        "text": reply.text if reply.text else ""
    }

    data = await get_notes(m.chat.id)
    data[name] = note_data
    NOTES_CACHE[m.chat.id] = (data, time.time())
    await db.save_note(m.chat.id, name, note_data)
    
    await m.reply(f"✅ Note **#{name}** saved!")

@Client.on_message(filters.group & filters.command(["clear", "rmnote"]))
async def delete_note(c, m):
    if not await is_admin(c, m): return
    if len(m.command) < 2: return await m.reply("❗ Use: `/clear <name>`")
    
    name = m.command[1].lower()
    data = await get_notes(m.chat.id)
    
    if name in data:
        del data[name]
        NOTES_CACHE[m.chat.id] = (data, time.time())
        await db.delete_note(m.chat.id, name)
        await m.reply(f"🗑️ Note **#{name}** deleted.")
    else:
        await m.reply(f"❌ Note **#{name}** not found.")

@Client.on_message(filters.group & filters.command("notes"))
async def list_notes(c, m):
    data = await get_notes(m.chat.id)
    if not data: return await m.reply("📭 No notes saved.")
    await m.reply("📝 **Saved Notes:**\n" + "\n".join(f"• `#{n}`" for n in data))

# =========================
# 🔎 NOTE FETCHER (Smart Filter)
# =========================

@Client.on_message(filters.group & filters.regex(r"^#[\w]+"), group=11)
async def get_note(c, m):
    msg_text = m.text or m.caption
    if not msg_text: return
    
    name = msg_text.split()[0][1:].lower()
    data = await get_notes(m.chat.id)
    if name not in data: return
    
    note = data[name]
    reply_id = m.reply_to_message.id if m.reply_to_message else m.id
    
    if note["type"] == "text":
        # पार्सिंग स्टाइलिंग को सेफ रखने के लिए डिफ़ॉल्ट रूप से HTML इनेबल्ड रखा है
        await c.send_message(m.chat.id, note["text"], reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
    else:
        # ✅ FIX: डायनामिक फंक्शन कॉल को म्यूट मैसेज 'm' से हटाकर क्लाइंट 'c' ऑब्जेक्ट पर सिंक किया गया
        send_method = getattr(c, f"send_{note['type']}") 
        
        # आर्गुमेंट्स डिक्शनरी को सेफली बिल्ड करें
        kwargs = {
            "chat_id": m.chat.id,
            "reply_to_message_id": reply_id
        }
        
        if note["type"] != "sticker": 
            kwargs["caption"] = note["caption"]
            kwargs["parse_mode"] = enums.ParseMode.HTML
            
        await send_method(file_id=note["file_id"], **kwargs)
