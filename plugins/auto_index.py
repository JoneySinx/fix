import logging
from hydrogram import Client, filters
from info import PRIMARY_CHANNEL, CLOUD_CHANNEL, ARCHIVE_CHANNEL
from database.ia_filterdb import COLLECTIONS

logger = logging.getLogger(__name__)

# 🌟 मल्टीपल चैनल मैपिंग लॉजिक (Fix for unhashable type: 'list')
# हम तीनों सूचियों (Lists) को एक फ्लैट डिक्शनरी में बदल रहे हैं
CHANNELS = {}
for cid in PRIMARY_CHANNEL: CHANNELS[cid] = "primary"
for cid in CLOUD_CHANNEL: CHANNELS[cid] = "cloud"
for cid in ARCHIVE_CHANNEL: CHANNELS[cid] = "archive"

# उन सभी चैनल्स की एक मास्टर लिस्ट जहाँ बॉट को नजर रखनी है
INDEX_CHATS = list(CHANNELS.keys())

# ─────────────────────────────────────────────
# 🛠 HELPER: फाइल की जानकारी निकालना
# ─────────────────────────────────────────────
def get_file_info(message):
    media = message.document or message.video or message.audio
    if not media:
        return None
    
    file_id = media.file_id
    file_unique_id = media.file_unique_id
    file_size = media.file_size
    
    # प्राथमिकता: पहले Caption चेक करेगा, अगर नहीं है तो File का असली नाम लेगा
    caption_text = message.caption.html if message.caption else None
    file_name = caption_text or getattr(media, 'file_name', None) or "Unknown_File"
    file_type = media.__class__.__name__.lower()
    
    return file_id, file_unique_id, file_size, file_name, file_type

# ─────────────────────────────────────────────
# 📥 NEW FILE INDEXER & UPDATER
# ─────────────────────────────────────────────
# सुरक्षा जांच: यह तभी रजिस्टर होगा जब कम से कम 1 चैनल ID मौजूद हो
if INDEX_CHATS:
    
    @Client.on_message(filters.chat(INDEX_CHATS) & (filters.document | filters.video | filters.audio))
    async def auto_index_files(client, message):
        file_info = get_file_info(message)
        if not file_info: return
            
        file_id, file_unique_id, file_size, file_name, file_type = file_info
        target_col_name = CHANNELS[message.chat.id]
        collection = COLLECTIONS.get(target_col_name)
        
        if not collection: return
            
        doc = {
            "file_id": file_id, "file_ref": file_id, "file_name": file_name,
            "file_size": file_size, "file_type": file_type,
            "file_unique_id": file_unique_id, "message_id": message.id,
            "chat_id": message.chat.id
        }
        
        # डेटाबेस में अपडेट या इंसर्ट (upsert) करें
        result = await collection.update_one(
            {"file_unique_id": file_unique_id}, {"$set": doc}, upsert=True
        )
        
        try:
            if result.upserted_id:
                await message.react("✅")
                logger.info(f"✅ Indexed new file into {target_col_name.upper()}: {file_name}")
            else:
                await message.react("♻️")
                logger.info(f"♻️ File already exists in {target_col_name.upper()}: {file_name}")
        except: pass

    @Client.on_edited_message(filters.chat(INDEX_CHATS) & (filters.document | filters.video | filters.audio))
    async def update_indexed_files(client, message):
        file_info = get_file_info(message)
        if not file_info: return
            
        _, file_unique_id, _, file_name, _ = file_info
        target_col_name = CHANNELS[message.chat.id]
        collection = COLLECTIONS.get(target_col_name)
        
        if not collection: return
            
        # सिर्फ फाइल का नाम (Caption) अपडेट करें
        result = await collection.update_one(
            {"file_unique_id": file_unique_id}, {"$set": {"file_name": file_name}}
        )
        
        try:
            if result.modified_count > 0:
                await message.react("🔄")
                logger.info(f"🔄 Updated caption in {target_col_name.upper()}: {file_name}")
        except: pass
