import logging
import re
import gc
from hydrogram import Client, filters
from info import PRIMARY_CHANNEL, CLOUD_CHANNEL, ARCHIVE_CHANNEL, LOG_CHANNEL
# नो-रिपिटिशन रूल: सीधे ia_filterdb का कोर save_file फंक्शन उपयोग करेंगे
from database.ia_filterdb import COLLECTIONS, unpack_new_file_id, save_file, primary

logger = logging.getLogger(__name__)

CHANNELS = {}
for cid in PRIMARY_CHANNEL: CHANNELS[cid] = "primary"
for cid in CLOUD_CHANNEL: CHANNELS[cid] = "cloud"
for cid in ARCHIVE_CHANNEL: CHANNELS[cid] = "archive"

# चैनल आईडी की सूची तैयार करें
INDEX_CHATS = list(CHANNELS.keys())

def get_file_info(message):
    media = message.document or message.video or message.audio
    if not media: return None
    
    file_id = media.file_id
    file_size = media.file_size
    
    caption_text = message.caption if message.caption else None
    file_name = caption_text or getattr(media, 'file_name', None) or "Unknown_File"
    
    # नाम को साफ और कस्टमाइज्ड फॉर्मेट में क्लीन करना
    try: 
        file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(file_name)).strip()
    except: 
        pass
        
    return media, file_id, file_size, file_name

if INDEX_CHATS:
    
    # ─────────────────────────────────────────────────────────
    # 📥 NEW LIVE AUTO-INDEX FILE DETECTOR ROUTE
    # ─────────────────────────────────────────────────────────
    @Client.on_message(filters.chat(INDEX_CHATS) & (filters.document | filters.video | filters.audio))
    async def auto_index_files(client, message):
        parsed_data = get_file_info(message)
        if not parsed_data: return
            
        media, file_id, file_size, file_name = parsed_data
        target_col_name = CHANNELS[message.chat.id]
        
        # मीडिया ऑब्जेक्ट में कैप्शन वेरिएबल सिंक करें ताकि save_file इसे प्रोसेस कर सके
        media.caption = file_name
        
        # ✅ NO REPETITION: अलग से पूरा रिप्लेसमेंट कोड लिखने के बजाय सीधे कोर save_file को कॉल किया
        sts = await save_file(media, collection_type=target_col_name)
        
        try:
            if sts == "dup":
                await message.react("♻️")
                logger.info(f"➡️ Duplicate skipped in {target_col_name.upper()}: {file_name}")
                return
            elif sts == "suc":
                await message.react("✅")
                logger.info(f"✅ Auto-Indexed into {target_col_name.upper()}: {file_name}")
                
                # 📢 ✅ FIX: ऑटो-इंडेक्स होते ही LOG_CHANNEL में लाइव लॉग अलर्ट रिपोर्ट भेजें
                if LOG_CHANNEL:
                    size_str = f"{file_size / (1024*1024):.2f} MB"
                    log_text = (
                        f"📢 <b>#Auto_Index_Alert 🌐</b>\n\n"
                        f"🔹 <b>File Name:</b> <code>{file_name}</code>\n"
                        f"🔹 <b>Size:</b> <code>{size_str}</code>\n"
                        f"🔹 <b>Source Channel:</b> <code>{message.chat.title}</code>\n"
                        f"📚 <b>Collection Lock:</b> <code>{target_col_name.upper()}</code>\n\n"
                        f"✅ <i>Saved into Database successfully!</i>"
                    )
                    await client.send_message(LOG_CHANNEL, log_text)
            else:
                await message.react("❌")
        except Exception as log_err:
            logger.debug(f"Auto-Index Reaction/Log Error: {log_err}")
        finally:
            # कोएब रैम को आइडल टाइम पर 100% खाली रखने के लिए गारबेज कलेक्शन
            gc.collect()

    # ─────────────────────────────────────────────────────────
    # 🔄 LIVE EDITED CAPTION AUTO-UPDATE ROUTE
    # ─────────────────────────────────────────────────────────
    @Client.on_edited_message(filters.chat(INDEX_CHATS) & (filters.document | filters.video | filters.audio))
    async def update_indexed_files(client, message):
        parsed_data = get_file_info(message)
        if not parsed_data: return
            
        _, file_id, _, file_name = parsed_data
        db_id = unpack_new_file_id(file_id)
        if not db_id: return

        target_col_name = CHANNELS[message.chat.id]
        collection = COLLECTIONS.get(target_col_name, primary)
            
        # डेटाबेस में नाम और कैप्शन को लाइव रिफ्रेश करें
        result = await collection.update_one(
            {"_id": db_id}, 
            {"$set": {"file_name": file_name, "caption": file_name}}
        )
        
        try:
            if result.modified_count > 0:
                await message.react("🔄")
                logger.info(f"🔄 Updated caption in {target_col_name.upper()}: {file_name}")
                
                # 📢 ✅ FIX: फाइल एडिट होते ही LOG_CHANNEL में भी अपडेट का लाइव अलर्ट भेजें
                if LOG_CHANNEL:
                    update_log = (
                        f"🔄 <b>#Auto_Index_Update ⚙️</b>\n\n"
                        f"🔹 <b>New Name/Caption:</b> <code>{file_name}</code>\n"
                        f"🔹 <b>Channel:</b> <code>{message.chat.title}</code>\n"
                        f"📚 <b>Collection:</b> <code>{target_col_name.upper()}</code>\n\n"
                        f"⚡ <i>Database record updated on-the-fly!</i>"
                    )
                    await client.send_message(LOG_CHANNEL, update_log)
        except Exception as edit_err:
            logger.debug(f"Auto-Index Edit Log Error: {edit_err}")
        finally:
            gc.collect()
