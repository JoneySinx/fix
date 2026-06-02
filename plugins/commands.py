import os
import random
import asyncio
import logging
from datetime import datetime
from time import time as time_now
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

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

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ✅ MINI APP URL - HTTPS Auto-Fix
# ─────────────────────────────────────────────
def _build_mini_app_url(base_url: str) -> str:
    url = base_url.strip() if base_url else ""
    if not url:
        return ""
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.startswith("https://"):
        url = f"https://{url}"
    return f"{url.rstrip('/')}/miniapp"

MINI_APP_URL = _build_mini_app_url(URL)


# ─────────────────────────
# /start COMMAND
# ─────────────────────────
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):

    # 1. GROUP HANDLING
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(
                message.chat.title, message.chat.id,
                f"@{message.chat.username or 'Private'}", total
            ))
            await db.add_chat(message.chat.id, message.chat.title)
        return await message.reply(
            f"<b>Hey {message.from_user.mention}, <i>{get_wish()}</i>\nHow can I help you?</b>"
        )

    # 2. PRIVATE HANDLING
    if REACTIONS:
        try: await message.react(random.choice(REACTIONS), big=True)
        except: pass

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(
            message.from_user.mention, message.from_user.id
        ))

    # Premium Check (Admins Bypass)
    if IS_PREMIUM and message.from_user.id not in ADMINS and not await is_premium(message.from_user.id, client):
        return await message.reply_photo(
            random.choice(PICS),
            caption="🔒 **Premium Required**\n\nBot is only for Premium users.\nUse /plan to buy.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 Buy Premium", callback_data="activate_plan")
            ]])
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
                if not file:
                    return await message.reply("❌ File Not Found!")

                settings = await get_settings(grp_id)
                cap_template = settings.get('caption', script.FILE_CAPTION)
                caption = cap_template.format(
                    file_name=str(file.get('file_name', 'File')),
                    file_size=get_size(file.get('file_size', 0))
                )

                btn = [[InlineKeyboardButton('❌ Close', callback_data=f'close_{message.from_user.id}')]]
                if IS_STREAM:
                    btn.insert(0, [InlineKeyboardButton("▶️ Watch / Download", callback_data=f"stream#{file_id}")])

                target_media = file.get('file_ref') if file.get('file_ref') else file_id

                msg = await client.send_cached_media(
                    message.chat.id,
                    target_media,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(btn)
                )

                if PM_FILE_DELETE_TIME > 0:
                    del_msg = await msg.reply(
                        f"⚠️ This message will delete in {get_readable_time(PM_FILE_DELETE_TIME)}."
                    )
                    
                    # डेटाबेस आधारित रीस्टार्ट-प्रूफ ऑटो-डिलीट इंजन कतार
                    await db.add_to_delete_queue(message.chat.id, msg.id, PM_FILE_DELETE_TIME)
                    await db.add_to_delete_queue(message.chat.id, del_msg.id, PM_FILE_DELETE_TIME)
                    
                    if not hasattr(temp, 'PM_FILES'):
                        temp.PM_FILES = {}
                    temp.PM_FILES[msg.id] = {'file_msg': msg.id, 'note_msg': del_msg.id}
                
                # ✅ UI DUP FIX: रिटर्न को यहाँ इफ-ब्लॉक के कोर रूट पर रखा गया है
                # ताकि फ़ाइल भेजने के बाद स्क्रिप्ट यहीं पर स्टॉप हो जाए।
                return
                
        except Exception as e:
            logger.error(f"Start File Extraction Error: {e}")
            return

        # यदि ऊपर का ट्राई-पार्ट सफलतापूर्वक चलता है, तो डिफ़ॉल्ट संदेश को ब्लॉक करने के लिए सेफ एग्जिट
        return

    # 4. DEFAULT START MESSAGE
    btn = [
        [InlineKeyboardButton("🍿 Open Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("+ Add to Group +", url=f"https://t.me/{temp.U_NAME}?startgroup=start")],
        [InlineKeyboardButton("👨‍🚒 Help", callback_data="help"), InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    if message.from_user.id not in ADMINS:
        btn.append([InlineKeyboardButton("💎 Premium Status", callback_data="myplan")])

    await message.reply_photo(
        random.choice(PICS),
        caption=script.START_TXT.format(message.from_user.mention, get_wish()),
        reply_markup=InlineKeyboardMarkup(btn)
    )


# ─────────────────────────
# /stats COMMAND
# ─────────────────────────
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(_, message):
    msg = await message.reply("🔄 Fetching Stats...")
    files, users, chats, premium = await asyncio.gather(
        db_count_documents(),
        db.total_users_count(),
        db.total_chat_count(),
        db.premium.count_documents({"status.premium": True})
    )
    await msg.edit(script.STATUS_TXT.format(
        users, chats, premium,
        files['total'], files['primary'], files['cloud'], files['archive'],
        get_readable_time(time_now() - temp.START_TIME)
    ))


# ─────────────────────────
# ADMIN COMMANDS
# ─────────────────────────
@Client.on_message(filters.command("delete") & filters.user(ADMINS))
async def delete_file_cmd(client, message):
    if len(message.command) < 3:
        return await message.reply("Usage: `/delete primary Avengers.mkv`")
    storage = message.command[1].lower()
    if storage not in ["primary", "cloud", "archive"]:
        return await message.reply("❌ Invalid Storage! Use: primary, cloud, archive")

    msg = await message.reply("🗑 Deleting...")
    count = await delete_files(" ".join(message.command[2:]), storage)
    await msg.edit(
        f"✅ Deleted `{count}` files from `{storage}`." if count else "❌ No files found."
    )


@Client.on_message(filters.command("delete_all") & filters.user(ADMINS))
async def delete_all_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/delete_all primary` or `/delete_all all`")
    storage = message.command[1].lower()
    if storage not in ["primary", "cloud", "archive", "all"]:
        return await message.reply("❌ Invalid Storage!")

    await message.reply(
        f"⚠️ <b>WARNING!</b>\n\nDeleting ALL files from `{storage}`.\nConfirm?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ CONFIRM DELETE", callback_data=f"confirm_del#{storage}"),
            InlineKeyboardButton("❌ CANCEL", callback_data=f"close_{message.from_user.id}")
        ]])
    )


# ─────────────────────────
# /link COMMAND
# ─────────────────────────
@Client.on_message(filters.command("link"))
async def link_generator(client, message):
    if IS_PREMIUM and message.from_user.id not in ADMINS and not await is_premium(message.from_user.id, client):
        return await message.reply(
            "🔒 **Premium Feature**\n\nOnly Admins and Premium Users can generate direct links.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 Buy Premium", callback_data="activate_plan")
            ]]),
            quote=True
        )

    media = (
        getattr(message.reply_to_message, 'document', None) or
        getattr(message.reply_to_message, 'video', None) or
        getattr(message.reply_to_message, 'audio', None)
    )
    if not media:
        return await message.reply("❌ **No media found in the replied message.**", quote=True)

    msg = await message.reply("⏳ **Generating Link...**", quote=True)
    try:
        copied = await message.reply_to_message.copy(BIN_CHANNEL)
        btn = [
            [
                InlineKeyboardButton("↗️ WATCH ONLINE", url=f"{URL}watch/{copied.id}"),
                InlineKeyboardButton("↗️ FAST DOWNLOAD", url=f"{URL}download/{copied.id}")
            ],
            [InlineKeyboardButton("❌ CLOSE ❌", callback_data=f"close_{message.from_user.id}")]
        ]
        await msg.edit_text("<i><b>Here is your link</b></i>", reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await msg.edit_text(f"❌ **Error generating link:** `{e}`")


# ─────────────────────────
# UI CALLBACKS
# ─────────────────────────
@Client.on_callback_query(filters.regex(r"^(help|user_cmds|admin_cmds|stats|back_start)$"))
async def ui_cb(client, query):
    data = query.data

    if data == "back_start":
        text = script.START_TXT.format(query.from_user.mention, get_wish())
        btn = [
            [InlineKeyboardButton("🍿 Open Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("+ Add to Group +", url=f"https://t.me/{temp.U_NAME}?startgroup=start")],
            [InlineKeyboardButton("👨‍🚒 Help", callback_data="help"), InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ]
        if query.from_user.id not in ADMINS:
            btn.append([InlineKeyboardButton("💎 Premium Status", callback_data="myplan")])

    elif data == "help":
        text = script.HELP_TXT.format(query.from_user.mention)
        btn = [[InlineKeyboardButton("👨‍💻 User Commands", callback_data="user_cmds")]]
        if query.from_user.id in ADMINS:
            btn[0].append(InlineKeyboardButton("👮‍♂️ Admin Commands", callback_data="admin_cmds"))
        btn.append([InlineKeyboardButton("⬅️ Back", callback_data="back_start")])

    elif data == "user_cmds":
        text = script.USER_COMMAND_TXT
        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="help")]]

    elif data == "admin_cmds":
        if query.from_user.id not in ADMINS:
            return await query.answer("❌ You are not an Admin!", show_alert=True)
        text = script.ADMIN_COMMAND_TXT
        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="help")]]

    elif data == "stats":
        files = await db_count_documents()
        uptime = get_readable_time(time_now() - temp.START_TIME)

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
            text = script.USER_STATUS_TXT.format(
                files['total'], files['primary'], files['cloud'], files['archive'],
                uptime
            )

        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="back_start")]]

    try:
        await query.message.edit_caption(
            caption=text,
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except Exception:
        try: await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(btn))
        except: pass


# ─────────────────────────
# OTHER CALLBACKS
# ─────────────────────────
@Client.on_callback_query(filters.regex(r"^confirm_del#"))
async def confirm_del(client, query):
    if query.from_user.id not in ADMINS:
        return await query.answer("❌ You are not an Admin!", show_alert=True)

    storage = query.data.split("#")[1]
    await query.message.edit("🗑 Processing... This may take time.")
    count = await delete_files("*", storage)
    await query.message.edit(f"✅ Deleted `{count}` files from `{storage}`.")


@Client.on_callback_query(filters.regex(r"^stream#"))
async def stream_cb(client, query):
    file_id = query.data.split("#")[1]
    await query.answer("🔗 Generating Links...", show_alert=False)
    try:
        file = await get_file_details(file_id)
        if not file:
            return await query.answer("❌ File expired or removed from Database!", show_alert=True)
            
        target_media = file.get('file_ref') if file.get('file_ref') else file_id

        msg = await client.send_cached_media(BIN_CHANNEL, target_media)
        btn = [
            [
                InlineKeyboardButton("▶️ Watch", url=f"{URL}watch/{msg.id}"),
                InlineKeyboardButton("⬇️ Download", url=f"{URL}download/{msg.id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data=f"close_{query.from_user.id}")]
        ]
        await query.message.edit_reply_markup(InlineKeyboardMarkup(btn))
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^close_"))
async def close_cb(c, q):
    try:
        parts = q.data.split("_")
        if len(parts) > 1 and parts[1].isdigit() and int(parts[1]) != q.from_user.id:
            return await q.answer("❌ You cannot close this!", show_alert=True)

        chat_id = q.message.chat.id
        current_msg_id = q.message.id

        # मुख्य रिज़ल्ट मैसेज आईडी और उसके इर्द-गिर्द की कतार नोटिस आईडी को एक साथ ढूंढकर मिटाना
        msg_ids_to_clean = [current_msg_id, current_msg_id - 1, current_msg_id + 1]

        # इन-मेमोरी रेंडरर बकेट क्लीनअप पैच
        if hasattr(temp, 'PM_FILES'):
            target_key = None
            for k, v in temp.PM_FILES.items():
                if v.get('file_msg') == current_msg_id or k == current_msg_id:
                    msg_ids_to_clean.append(v.get('note_msg'))
                    target_key = k
                    break
            if target_key:
                del temp.PM_FILES[target_key]

        # डेटाबेस आधारित टाइमर कतार (Queue) रिकॉर्ड साफ़ करें ताकि डुप्लीकेट एक्जीक्यूशन न हो
        for mid in msg_ids_to_clean:
            if mid: await db.remove_from_delete_queue(chat_id, mid)

        # चैट स्क्रीन से हमेशा के लिए संदेश मिटाएं
        await c.delete_messages(chat_id, [m for m in msg_ids_to_clean if m])

    except Exception as e:
        try: await q.message.delete()
        except: pass
