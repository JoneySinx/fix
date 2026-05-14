import asyncio
import re
import math
import random
import aiohttp
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from info import ADMINS, DELETE_TIME, MAX_BTN, IS_PREMIUM, PICS, IS_STREAM, SPELL_CHECK
from utils import is_premium, get_size, is_check_admin, temp, get_settings, save_group_settings
from database.ia_filterdb import get_search_results
from Script import script  

BUTTONS = {}
SRC_TO_SHORT = {"primary": "pri", "cloud": "cld", "archive": "arc"}
SHORT_TO_SRC = {"pri": "primary", "cld": "cloud", "arc": "archive"}

# 🕒 Smart Auto-Delete Tracker
SMART_TASKS = {}

def check_cache_limit():
    if len(BUTTONS) > 500:
        for k in list(BUTTONS.keys())[:100]:
            BUTTONS.pop(k, None)
            temp.FILES.pop(k, None)

async def is_valid_search(message):
    if not message.text or message.text.startswith("/"): return False
    if message.forward_date or message.photo or message.video or message.document: return False
    if message.entities and any(e.type in [enums.MessageEntityType.URL, enums.MessageEntityType.TEXT_LINK] for e in message.entities): return False
    if not any(c.isalnum() for c in message.text): return False
    return True

# ─────────────────────────────────────────────
# 🧠 SPELL CHECKER (Google Suggest API)
# ─────────────────────────────────────────────
async def get_spell_suggestion(query):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={query} movie"
            async with session.get(url) as resp:
                data = await resp.json()
                if data and len(data) > 1 and data[1]:
                    suggestion = data[1][0].replace(" movie", "").replace(" series", "").strip()
                    if suggestion.lower() != query.lower():
                        return suggestion.title()
    except Exception:
        pass
    return None

# ─────────────────────────────────────────────
# 🎨 UI HELPER FUNCTION (Ultra Clean UI)
# ─────────────────────────────────────────────
def get_filter_ui(search, files, total, act_src, offset, chat_id, req_id, key, next_off, simple_mode=True):
    list_items = [
        f"📁 <a href='https://t.me/{temp.U_NAME}?start=file_{chat_id}_{f['_id']}'>[{get_size(f['file_size'])}] {f['file_name']}</a>"
        for f in files
    ]
    files_text = "\n\n".join(list_items)
    total_pages = math.ceil(total / MAX_BTN)
    curr_page = (int(offset) // MAX_BTN) + 1
    
    cap = (f"<b>👑 Search: {search}\n🎬 Total: {total}\n📚 Source: {act_src.upper()}\n"
           f"📄 Page: {curr_page}/{total_pages}</b>\n\n{files_text}")

    # 1. अगर रिज़ल्ट 1 पेज के ही हैं, तो कोई बटन नहीं
    if total <= MAX_BTN:
        return cap, None

    btn = []
    act_src_short = SRC_TO_SHORT.get(act_src, "pri")

    # 2. पेजिनेशन (Next/Prev) - NO PAGE NUMBER BUTTON
    nav = []
    prev_off = int(offset) - MAX_BTN
    if prev_off >= 0: 
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"nav_{req_id}_{key}_{prev_off}_{act_src_short}"))
        
    if next_off: 
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"nav_{req_id}_{key}_{next_off}_{act_src_short}"))
    
    if nav: btn.append(nav)

    # 3. फुल मोड है तो सिर्फ सोर्स (Primary/Cloud/Archive) बटन्स लगाओ (Send All / Close हटाया गया)
    if not simple_mode:
        col_btn = []
        for c in ["primary", "cloud", "archive"]:
            tick = "✅" if c == act_src else "📂"
            col_btn.append(InlineKeyboardButton(f"{tick} {c.title()}", callback_data=f"coll_{req_id}_{key}_{SRC_TO_SHORT[c]}"))
        btn.append(col_btn)
    
    return cap, InlineKeyboardMarkup(btn)

# ─────────────────────────────────────────────
# 🕒 SMART INACTIVITY TRACKER
# ─────────────────────────────────────────────
async def smart_delete_msg(bot_msg, user_msg=None, delay=300): # 300 sec = 5 mins
    try:
        await asyncio.sleep(delay)
        try: await bot_msg.delete()
        except: pass
        if user_msg:
            try: await user_msg.delete()
            except: pass
        SMART_TASKS.pop(bot_msg.id, None)
    except asyncio.CancelledError:
        pass # अगर यूज़र ने Next बटन दबाया, तो यह पुराना टाइमर कैंसिल हो जाएगा

# ─────────────────────────────────────────────
# 🔍 COMMAND HANDLERS
# ─────────────────────────────────────────────
@Client.on_message(filters.command("button_style"))
async def button_style_toggle(client, message):
    """एडमिन (ग्रुप में) या यूज़र (PM में) द्वारा सिंपल/फुल बटन मोड सेट करने के लिए"""
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await is_check_admin(client, message.chat.id, message.from_user.id): return
        
    settings = await get_settings(message.chat.id)
    current_mode = settings.get("simple_mode", True)
    
    new_mode_val = not current_mode
    await save_group_settings(message.chat.id, "simple_mode", new_mode_val)
    
    new_mode_str = "SIMPLE (Only Next/Prev)" if new_mode_val else "FULL (With Source Buttons)"
    await message.reply(f"✅ Button style changed to: **{new_mode_str}**")

@Client.on_message(filters.command("search") & filters.group)
async def search_toggle(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id): return
    if len(message.command) < 2: return await message.reply("Usage: `/search on` or `/search off`")
    state = True if message.command[1].lower() == "on" else False
    await save_group_settings(message.chat.id, "search_enabled", state)
    await message.reply(f"✅ Search is now **{'ENABLED' if state else 'DISABLED'}**")

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if not await is_valid_search(message): return
    if IS_PREMIUM and message.from_user.id not in ADMINS and not await is_premium(message.from_user.id, client):
        return await message.reply_photo(random.choice(PICS), caption="🔒 **Premium Required**\n\nOnly Premium users can use this bot in DM.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="activate_plan"), InlineKeyboardButton("📊 My Plan", callback_data="myplan")]]))
    
    settings = await get_settings(message.chat.id)
    await auto_filter(client, message, collection_type="all", settings=settings)

@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    if not await is_valid_search(message): return
    chat_id, user_id = message.chat.id, message.from_user.id

    settings = await get_settings(chat_id)
    if not settings.get("search_enabled", True): return
    if IS_PREMIUM and user_id not in ADMINS and not await is_premium(user_id, client): return

    text_lower = message.text.lower()
    if "@admin" in text_lower:
        if await is_check_admin(client, chat_id, user_id): return
        mentions = [f"<a href='tg://user?id={m.user.id}'>\u2063</a>" async for m in client.get_chat_administrators(chat_id) if not m.user.is_bot]
        return await message.reply(f"✅ Report sent to admins!{''.join(mentions)}")

    if "http" in text_lower or "t.me/" in text_lower:
        if re.search(r"(?:http|www\.|t\.me/)", text_lower):
            if not await is_check_admin(client, chat_id, user_id):
                try: await message.delete()
                except: pass
                msg = await message.reply("❌ Links not allowed!", quote=True)
                asyncio.create_task(smart_delete_msg(msg, delay=5))
                return

    await auto_filter(client, message, collection_type="all", settings=settings)

# ─────────────────────────────────────────────
# 🚀 AUTO FILTER CORE 
# ─────────────────────────────────────────────
async def auto_filter(client, msg, collection_type="all", settings=None):
    check_cache_limit() 
    search = msg.text.strip()
    files, next_offset, total, act_src = await get_search_results(search, MAX_BTN, 0, collection_type=collection_type)

    if not settings: settings = await get_settings(msg.chat.id)
    is_simple_mode = settings.get("simple_mode", True)

    if not files:
        if SPELL_CHECK:
            suggestion = await get_spell_suggestion(search)
            if suggestion:
                btn = [[InlineKeyboardButton(f"✅ Yes, search '{suggestion}'", callback_data=f"spellchk_{msg.from_user.id}_{suggestion}")]]
                cap = f"❌ **{search}** not found.\n\n🤔 **Did you mean:** __{suggestion}__?"
                try:
                    m = await msg.reply(cap, reply_markup=InlineKeyboardMarkup(btn), quote=True)
                    if settings.get("auto_delete"):
                        SMART_TASKS[m.id] = asyncio.create_task(smart_delete_msg(m, msg, delay=300))
                except: pass
                return

        try:
            m = await msg.reply(script.NOT_FILE_TXT.format(msg.from_user.mention, search), quote=True)
            asyncio.create_task(smart_delete_msg(m, delay=5))
        except: pass
        return

    key = f"{msg.chat.id}-{msg.id}"
    temp.FILES[key] = files
    BUTTONS[key] = search

    cap, markup = get_filter_ui(search, files, total, act_src, 0, msg.chat.id, msg.from_user.id, key, next_offset, is_simple_mode)

    try:
        m = await msg.reply(cap, reply_markup=markup, disable_web_page_preview=True, quote=True)
        if settings.get("auto_delete"):
            SMART_TASKS[m.id] = asyncio.create_task(smart_delete_msg(m, msg, delay=300))
    except Exception as e: print(f"Error: {e}")

# ─────────────────────────────────────────────
# 📤 CALLBACK HANDLERS
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^spellchk_"))
async def spell_check_handler(client, query):
    try:
        _, req_id, suggestion = query.data.split("_", 2)
        if int(req_id) != query.from_user.id:
            return await query.answer("❌ This suggestion is not for you!", show_alert=True)
            
        await query.answer(f"🔍 Searching for {suggestion}...", show_alert=False)
        files, next_offset, total, act_src = await get_search_results(suggestion, MAX_BTN, 0, collection_type="all")
        
        if not files:
            return await query.message.edit_text(f"❌ Still no results found for **{suggestion}**.")
            
        key = f"{query.message.chat.id}-{query.message.id}"
        temp.FILES[key] = files
        BUTTONS[key] = suggestion
        
        settings = await get_settings(query.message.chat.id)
        is_simple_mode = settings.get("simple_mode", True)
        
        cap, markup = get_filter_ui(suggestion, files, total, act_src, 0, query.message.chat.id, query.from_user.id, key, next_offset, is_simple_mode)
        await query.message.edit_text(cap, reply_markup=markup, disable_web_page_preview=True)
        
        # ⏱️ Reset Auto Delete Timer on spellcheck click
        if settings.get("auto_delete") and query.message.id in SMART_TASKS:
            SMART_TASKS[query.message.id].cancel()
            SMART_TASKS[query.message.id] = asyncio.create_task(smart_delete_msg(query.message, delay=300))
            
    except Exception as e:
        print(f"Spellcheck Callback Error: {e}")
        await query.answer("❌ Error during search!", show_alert=True)

@Client.on_callback_query(filters.regex(r"^(nav_|coll_)"))
async def pagination_handler(client, query):
    try:
        data = query.data.split("_")
        action, req, key = data[0], data[1], data[2]
        if int(req) != query.from_user.id: return await query.answer("❌ Not for you!", show_alert=True)
    except: return await query.answer("❌ Error!", show_alert=True)

    if IS_PREMIUM and query.from_user.id not in ADMINS and not await is_premium(query.from_user.id, client): 
        return await query.answer("❌ Premium Expired!", show_alert=True)

    search = BUTTONS.get(key)
    if not search: return await query.answer("❌ Search Expired!", show_alert=True)

    offset, coll_short = (int(data[3]), data[4]) if action == "nav" else (0, data[3])
    coll_type = SHORT_TO_SRC.get(coll_short, "primary")

    files, next_off, total, act_src = await get_search_results(search, MAX_BTN, offset, collection_type=coll_type)
    
    if not files:
        err = "❌ No more pages!" if action == "nav" else f"❌ No files in {coll_type.upper()}"
        return await query.answer(err, show_alert=True)

    temp.FILES[key] = files
    
    settings = await get_settings(query.message.chat.id)
    is_simple_mode = settings.get("simple_mode", True)
    
    cap, markup = get_filter_ui(search, files, total, act_src, offset, query.message.chat.id, req, key, next_off, is_simple_mode)

    try: await query.message.edit_text(cap, reply_markup=markup, disable_web_page_preview=True)
    except: pass
    await query.answer()

    # ⏱️ Reset Smart Inactivity Timer 
    if settings.get("auto_delete") and query.message.id in SMART_TASKS:
        SMART_TASKS[query.message.id].cancel()
        SMART_TASKS[query.message.id] = asyncio.create_task(smart_delete_msg(query.message, delay=300))

@Client.on_callback_query(filters.regex(r"^close_"))
async def close_cb(c, q):
    try:
        if int(q.data.split("_")[1]) != q.from_user.id: return await q.answer("❌ This is not your search!", show_alert=True)
        await q.message.delete()
    except Exception: pass
