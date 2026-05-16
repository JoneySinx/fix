import re
import time
import asyncio
from hydrogram import Client, filters, enums
from hydrogram.errors import FloodWait
from info import ADMINS
# ✅ Updated Import
from database.ia_filterdb import save_file
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time

lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    data_parts = query.data.split("#")
    ident = data_parts[1]
    
    if ident == 'yes':
        # Show collection selection buttons (Direct Skip 0 comes here directly)
        chat = data_parts[2]
        lst_msg_id = data_parts[3]
        skip = data_parts[4]
        
        buttons = [
            [
                InlineKeyboardButton('✅ PRIMARY', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#primary'),
                InlineKeyboardButton('📂 CLOUD', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#cloud')
            ],
            [
                InlineKeyboardButton('📦 ARCHIVES', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#archive')
            ],
            [
                InlineKeyboardButton('❌ CANCEL', callback_data='close_data')
            ]
        ]
        await query.message.edit(
            f"🗂️ <b>Select Collection to Index:</b>\n"
            f"⏭️ Skip: <code>{skip}</code>\n\n"
            "• <b>PRIMARY</b> - Main database\n"
            "• <b>CLOUD</b> - Cloud storage\n"
            "• <b>ARCHIVES</b> - Archive storage",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    elif ident == 'ask_skip':
        # Manual Skip Selection
        chat = data_parts[2]
        lst_msg_id = data_parts[3]
        
        await query.message.edit("📝 <b>Send the number of messages to skip:</b>\n\nSend <code>0</code> to start from beginning.")
        
        try:
            msg = await bot.listen(chat_id=query.message.chat.id, user_id=query.from_user.id)
            skip = int(msg.text)
            await msg.delete() # delete user message
        except:
            return await query.message.edit("❌ Invalid number or Timeout. Try again.")
            
        # After getting skip, show collection buttons
        buttons = [
            [
                InlineKeyboardButton('✅ PRIMARY', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#primary'),
                InlineKeyboardButton('📂 CLOUD', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#cloud')
            ],
            [
                InlineKeyboardButton('📦 ARCHIVES', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#archive')
            ],
            [
                InlineKeyboardButton('❌ CANCEL', callback_data='close_data')
            ]
        ]
        await query.message.edit(
            f"🗂️ <b>Select Collection to Index:</b>\n"
            f"⏭️ Skip: <code>{skip}</code>\n\n"
            "• <b>PRIMARY</b> - Main database\n"
            "• <b>CLOUD</b> - Cloud storage\n"
            "• <b>ARCHIVES</b> - Archive storage",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif ident == 'start':
        # Start indexing with selected collection
        chat = data_parts[2]
        lst_msg_id = data_parts[3]
        skip = data_parts[4]
        collection = data_parts[5]
        
        msg = query.message
        await msg.edit(f"Starting Indexing to <b>{collection.upper()}</b> collection...")
        
        try:
            chat = int(chat)
        except:
            chat = chat
        
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip), collection)
    
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("Trying to cancel Indexing...")


# Auto-index when forwarded message or channel link is sent
@Client.on_message(filters.private & filters.user(ADMINS) & (filters.forwarded | filters.text))
async def auto_index(bot, message):
    # Skip if it's a command or regular chat
    if message.text and not message.text.startswith("https://t.me"):
        if not message.forward_from_chat:
            return
    
    if lock.locked():
        return await message.reply('⏳ Wait until previous indexing process completes.')
    
    # Handle forwarded messages
    if message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    
    # Handle channel links
    elif message.text and message.text.startswith("https://t.me"):
        try:
            msg_link = message.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except:
            return await message.reply('❌ Invalid message link!')
    else:
        return
    
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'❌ Error: {e}')

    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("⚠️ I can only index channels.")

    # Show Initial Options (Direct Skip 0 OR Custom Skip)
    buttons = [
        [
            InlineKeyboardButton('⚡ START INDEXING (Skip 0)', callback_data=f'index#yes#{chat_id}#{last_msg_id}#0')
        ],
        [
            InlineKeyboardButton('📝 CUSTOM SKIP', callback_data=f'index#ask_skip#{chat_id}#{last_msg_id}')
        ],
        [
            InlineKeyboardButton('❌ CANCEL', callback_data='close_data')
        ]
    ]
    await message.reply(
        f'🗂️ <b>Ready to Index:</b>\n\n'
        f'📢 Channel: <b>{chat.title}</b>\n'
        f'📨 Total Messages: <code>{last_msg_id}</code>\n\n'
        f'Choose an option:',
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def index_files_to_db(lst_msg_id, chat, msg, bot, skip, collection_type="primary"):
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    badfiles = 0
    current = skip
    
    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                time_taken = get_readable_time(time.time()-start_time)
                
                if temp.CANCEL:
                    temp.CANCEL = False
                    await msg.edit(
                        f"<b>✅ Successfully Cancelled!</b>\n"
                        f"📚 Collection: <code>{collection_type.upper()}</code>\n"
                        f"⏱ Completed in: <code>{time_taken}</code>\n\n"
                        f"📁 Saved Files: <code>{total_files}</code>\n"
                        f"🔄 Duplicates: <code>{duplicate}</code>\n"
                        f"🗑 Deleted: <code>{deleted}</code>\n"
                        f"❌ No Media: <code>{no_media + unsupported}</code>\n"
                        f"⚠️ Unsupported: <code>{unsupported}</code>\n"
                        f"❗ Errors: <code>{errors}</code>\n"
                        f"🚫 Bad Files: <code>{badfiles}</code>"
                    )
                    return
                
                current += 1
                
                # Update progress every 50 messages (Less spam)
                if current % 50 == 0:
                    btn = [[
                        InlineKeyboardButton('CANCEL', callback_data=f'index#cancel#{chat}#{lst_msg_id}#{skip}')
                    ]]
                    try:
                        await msg.edit_text(
                            text=f"<b>📊 Indexing Progress</b>\n"
                            f"📚 Collection: <code>{collection_type.upper()}</code>\n"
                            f"⏱ Time: <code>{time_taken}</code>\n\n"
                            f"📨 Total Received: <code>{current}</code>\n"
                            f"📁 Saved: <code>{total_files}</code>\n"
                            f"🔄 Duplicates: <code>{duplicate}</code>\n"
                            f"🗑 Deleted: <code>{deleted}</code>\n"
                            f"❌ No Media: <code>{no_media + unsupported}</code>\n"
                            f"⚠️ Unsupported: <code>{unsupported}</code>\n"
                            f"❗ Errors: <code>{errors}</code>\n"
                            f"🚫 Bad Files: <code>{badfiles}</code>", 
                            reply_markup=InlineKeyboardMarkup(btn)
                        )
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception:
                        pass
                
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                
                # Check file size - skip files under 2 MB
                file_size = getattr(media, 'file_size', 0)
                if file_size < 2097152:  # 2 MB in bytes
                    badfiles += 1
                    continue
                
                media.caption = message.caption
                # ✅ Safe Name Cleaning (No Error)
                try:
                    media.file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
                except:
                    pass
                
                # Save to selected collection
                sts = await save_file(media, collection_type=collection_type)
                
                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
                    
        except Exception as e:
            await msg.reply(f'❌ Index canceled due to Error - {e}')
        else:
            time_taken = get_readable_time(time.time()-start_time)
            await msg.edit(
                f'<b>✅ Successfully Indexed!</b>\n'
                f'📚 Collection: <code>{collection_type.upper()}</code>\n'
                f'⏱ Completed in: <code>{time_taken}</code>\n\n'
                f'📁 Saved Files: <code>{total_files}</code>\n'
                f'🔄 Duplicates: <code>{duplicate}</code>\n'
                f'🗑 Deleted: <code>{deleted}</code>\n'
                f'❌ No Media: <code>{no_media + unsupported}</code>\n'
                f'⚠️ Unsupported: <code>{unsupported}</code>\n'
                f'❗ Errors: <code>{errors}</code>\n'
                f'🚫 Bad Files: <code>{badfiles}</code>'
            )
