import os
import random
import asyncio
from datetime import datetime
from time import time as time_now
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo # ✅ FIX: WebAppInfo को इम्पोर्ट किया

from Script import script
from database.ia_filterdb import db_count_documents, get_file_details, delete_files
from database.users_chats_db import db

from info import (
    IS_PREMIUM, URL, BIN_CHANNEL, ADMINS, 
    LOG_CHANNEL, PICS, IS_STREAM, REACTIONS, PM_FILE_DELETE_TIME
)
from utils import (
    is_premium, get_settings, get_size, temp, 
    get_readable_time, get_wish
)

# ─────────────────────────
# HELPERS
# ─────────────────────────
async def auto_delete_messages(msg_ids, chat_id, client, delay):
    await asyncio.sleep(delay)
    try: await client.delete_messages(chat_id=chat_id, message_ids=msg_ids)
    except: pass

# ─────────────────────────
# /start COMMAND
# ─────────────────────────
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    
    # 1. GROUP HANDLING
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(message.chat.title, message.chat.id, f"@{message.chat.username or 'Private'}", total))
            await db.add_chat(message.chat.id, message.chat.title)
        return await message.reply(f"<b>Hey {message.from_user.mention}, <i>{get_wish()}</i>\nHow can I help you?</b>")

    # 2. PRIVATE HANDLING (Reactions, DB Add)
    if REACTIONS:
        try: await message.react(random.choice(REACTIONS), big=True)
        except: pass

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(message.from_user.mention, message.from_user.id))

    # ✅ Premium Check (Admins Bypass)
    if IS_PREMIUM and message.from_user.id not in ADMINS and not await is_premium(message.from_user.id, client):
        return await message.reply_photo(
            random.choice(PICS), caption="🔒 **Premium Required**\n\nBot is only for Premium users.\nUse /plan to buy.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="activate_plan")]])
        )

    # 3. FILE HANDLING (start=file_id)
    if len(message.command) > 1 and message.command[1] != "premium":
        try:
            parts = message.command[1].split("_")
            if len(parts) >= 3:
                try: await message.delete()
                except: pass
                
                grp_id, file_id = int(parts[1]), "_".join(parts[2:])
                file = await get_file_details(file_id)
                if not file: return await message.reply("❌ File Not Found!")
                
                settings = await get_settings(grp_id)
                # ✅ प्रोफेशनल तरीका: Script.py से FILE_CAPTION ले रहा है
                cap_template = settings.get('caption', script.FILE_CAPTION)
                caption = cap_template.format(file_name=str(file.get('file_name', 'File')), file_size=get_size(file.get('file_size', 0)))
                
                btn = [[InlineKeyboardButton('❌ Close', callback_data=f'close_{message.from_user.id}')]]
                if IS_STREAM: btn.insert(0, [InlineKeyboardButton("▶️ Watch / Download", callback_data=f"stream#{file_id}")])

                msg = await client.send_cached_media(message.chat.id, file.get('file_ref', file_id), caption=caption, reply_markup=InlineKeyboardMarkup(btn))

                if PM_FILE_DELETE_TIME > 0:
                    del_msg = await msg.reply(f"⚠️ This message will delete in {get_readable_time(PM_FILE_DELETE_TIME)}.")
                    asyncio.create_task(auto_delete_messages([msg.id, del_msg.id], message.chat.id, client, PM_FILE_DELETE_TIME))
                    if not hasattr(temp, 'PM_FILES'): temp.PM_FILES = {}
                    temp.PM_FILES[msg.id] = {'file_msg': msg.id, 'note_msg': del_msg.id}
                return
        except Exception as e: print(f"Start Error: {e}")

    # 4. DEFAULT START MESSAGE
    btn = [
        # 🌟 NAYA FEATURE: Telegram Mini App Button
        [InlineKeyboardButton("🍿 Open Mini App", web_app=WebAppInfo(url=f"{URL}miniapp"))],
        [InlineKeyboardButton("+ Add to Group +", url=f"https://t.me/{temp.U_NAME}?startgroup=start")],
        [InlineKeyboardButton("👨‍🚒 Help", callback_data="help"), InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    # ✅ FIX: एडमिन को Premium Status बटन नहीं दिखेगा
    if message.from_user.id not in ADMINS:
        btn.append([InlineKeyboardButton("💎 Premium Status", callback_data="myplan")])

    await message.reply_photo(
        random.choice(PICS), caption=script.START_TXT.format(message.from_user.mention, get_wish()),
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ─────────────────────────
# /stats COMMAND
# ─────────────────────────
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(_, message):
    msg = await message.reply("🔄 Fetching Stats...")
    files, users, chats, premium = await asyncio.gather(
        db_count_documents(), db.total_users_count(), db.total_chat_count(), db.premium.count_documents({"status.premium": True})
    )
    await msg.edit(script.STATUS_TXT.format(users, chats, premium, files['total'], files['primary'], files['cloud'], files['archive'], get_readable_time(time_now() - temp.START_TIME)))

# ─────────────────────────
# ADMIN COMMANDS (/delete, /delete_all)
# ─────────────────────────
@Client.on_message(filters.command("delete") & filters.user(ADMINS))
async def delete_file_cmd(client, message):
    if len(message.command) < 3: return await message.reply("Usage: `/delete primary Avengers.mkv`")
    storage = message.command[1].lower()
    if storage not in ["primary", "cloud", "archive"]: return await message.reply("❌ Invalid Storage! Use: primary, cloud, archive")
    
    msg = await message.reply("🗑 Deleting...")
    count = await delete_files(" ".join(message.command[2:]), storage)
    await msg.edit(f"✅ Deleted `{count}` files from `{storage}`." if count else "❌ No files found.")

@Client.on_message(filters.command("delete_all") & filters.user(ADMINS))
async def delete_all_cmd(client, message):
    if len(message.command) < 2: return await message.reply("Usage: `/delete_all primary` or `/delete_all all`")
    storage = message.command[1].lower()
    if storage not in ["primary", "cloud", "archive", "all"]: return await message.reply("❌ Invalid Storage!")
    
    await message.reply(
        f"⚠️ <b>WARNING!</b>\n\nDeleting ALL files from `{storage}`.\nConfirm?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ CONFIRM DELETE", callback_data=f"confirm_del#{storage}"), InlineKeyboardButton("❌ CANCEL", callback_data=f"close_{message.from_user.id}")]])
    )

# ─────────────────────────
# /link COMMAND
# ─────────────────────────
@Client.on_message(filters.command("link"))
async def link_generator(client, message):
    if IS_PREMIUM and message.from_user.id not in ADMINS and not await is_premium(message.from_user.id, client):
        return await message.reply("🔒 **Premium Feature**\n\nOnly Admins and Premium Users can generate direct links.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", callback_data="activate_plan")]]), quote=True)

    media = getattr(message.reply_to_message, 'document', None) or getattr(message.reply_to_message, 'video', None) or getattr(message.reply_to_message, 'audio', None)
    if not media: return await message.reply("❌ **No media found in the replied message.**", quote=True)

    msg = await message.reply("⏳ **Generating Link...**", quote=True)
    try:
        copied = await message.reply_to_message.copy(BIN_CHANNEL)
        btn = [[InlineKeyboardButton("↗️ WATCH ONLINE", url=f"{URL}watch/{copied.id}"), InlineKeyboardButton("↗️ FAST DOWNLOAD", url=f"{URL}download/{copied.id}")], [InlineKeyboardButton("❌ CLOSE ❌", callback_data=f"close_{message.from_user.id}")]]
        await msg.edit_text("<i><b>Here is your link</b></i>", reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e: await msg.edit_text(f"❌ **Error generating link:** `{e}`")

# ─────────────────────────
# 🎨 SMART UI CALLBACKS
# ─────────────────────────
@Client.on_callback_query(filters.regex(r"^(help|user_cmds|admin_cmds|stats|back_start)$"))
async def ui_cb(client, query):
    data = query.data
    
    if data == "back_start":
        text = script.START_TXT.format(query.from_user.mention, get_wish())
        btn = [
            # 🌟 NAYA FEATURE: Back बटन दबाने पर भी Mini App का बटन दिखेगा
            [InlineKeyboardButton("🍿 Open Mini App", web_app=WebAppInfo(url=f"{URL}miniapp"))],
            [InlineKeyboardButton("+ Add to Group +", url=f"https://t.me/{temp.U_NAME}?startgroup=start")],
            [InlineKeyboardButton("👨‍🚒 Help", callback_data="help"), InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ]
        # ✅ FIX: एडमिन को Premium Status नहीं दिखेगा
        if query.from_user.id not in ADMINS:
            btn.append([InlineKeyboardButton("💎 Premium Status", callback_data="myplan")])

    elif data == "help":
        text = script.HELP_TXT.format(query.from_user.mention)
        btn = [[InlineKeyboardButton("👨‍💻 User Commands", callback_data="user_cmds")]]
        if query.from_user.id in ADMINS: btn[0].append(InlineKeyboardButton("👮‍♂️ Admin Commands", callback_data="admin_cmds"))
        btn.append([InlineKeyboardButton("⬅️ Back", callback_data="back_start")])
        
    elif data == "user_cmds":
        text = script.USER_COMMAND_TXT
        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="help")]]
        
    elif data == "admin_cmds":
        # 🔒 Security Check
        if query.from_user.id not in ADMINS: return await query.answer("❌ You are not an Admin!", show_alert=True)
        text = script.ADMIN_COMMAND_TXT
        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="help")]]
        
    elif data == "stats":
        files = await db_count_documents()
        uptime = get_readable_time(time_now() - temp.START_TIME)

        # 🔒 Security Check: Admin को पूरा Stats दिखेगा, Premium User को सिर्फ Files और Uptime
        if query.from_user.id in ADMINS:
            users, chats, premium = await asyncio.gather(
                db.total_users_count(), 
                db.total_chat_count(), 
                db.premium.count_documents({"status.premium": True})
            )
            text = script.STATUS_TXT.format(
                users, chats, premium, 
                files['total'], files['primary'], files['cloud'], files['archive'], 
                uptime
            )
        else:
            # ✅ प्रीमियम यूजर के लिए Script.py वाला USER_STATUS_TXT इस्तेमाल होगा
            text = script.USER_STATUS_TXT.format(
                files['total'], files['primary'], files['cloud'], files['archive'], 
                uptime
            )
        
        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="back_start")]]

    await query.message.edit_caption(
        caption=text, 
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ─────────────────────────
# OTHER CALLBACKS
# ─────────────────────────
@Client.on_callback_query(filters.regex(r"^confirm_del#"))
async def confirm_del(client, query):
    # 🔒 Security Check
    if query.from_user.id not in ADMINS: return await query.answer("❌ You are not an Admin!", show_alert=True)
    
    storage = query.data.split("#")[1]
    await query.message.edit("🗑 Processing... This may take time.")
    count = await delete_files("*", storage)
    await query.message.edit(f"✅ Deleted `{count}` files from `{storage}`.")

@Client.on_callback_query(filters.regex(r"^stream#"))
async def stream_cb(client, query):
    file_id = query.data.split("#")[1]
    await query.answer("🔗 Generating Links...")
    try:
        msg = await client.send_cached_media(BIN_CHANNEL, file_id)
        btn = [[InlineKeyboardButton("▶️ Watch", url=f"{URL}watch/{msg.id}"), InlineKeyboardButton("⬇️ Download", url=f"{URL}download/{msg.id}")], [InlineKeyboardButton("❌ Close", callback_data=f"close_{query.from_user.id}")]]
        await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))
    except Exception as e: await query.answer(f"Error: {e}", show_alert=True)

@Client.on_callback_query(filters.regex(r"^close_"))
async def close_cb(c, q):
    try:
        parts = q.data.split("_")
        # 🔒 Security Check: सिर्फ वही यूज़र क्लोज कर सकता है जिसने रिक्वेस्ट की थी
        if len(parts) > 1 and parts[1].isdigit() and int(parts[1]) != q.from_user.id:
            return await q.answer("❌ You cannot close this!", show_alert=True)
        
        await q.message.delete()
        if hasattr(temp, 'PM_FILES') and q.message.id in temp.PM_FILES:
            try:
                await c.delete_messages(q.message.chat.id, temp.PM_FILES[q.message.id]['note_msg'])
                del temp.PM_FILES[q.message.id]
            except: pass
    except: pass
