import logging
import re
import base64
import asyncio
import aiohttp
import io
from struct import pack
import motor.motor_asyncio
from hydrogram.file_id import FileId
from info import DATABASE_URL, DATABASE_NAME, MAX_BTN, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# ⚙️ MOTOR CONNECTION — Koyeb Free Tier Optimized
# ─────────────────────────────────────────────────────────
client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL,
    maxPoolSize=5,
    minPoolSize=1,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    retryWrites=True,
    retryReads=True,
)
db = client[DATABASE_NAME]

primary = db["Primary"]
cloud   = db["Cloud"]
archive = db["Archive"]

COLLECTIONS = {
    "primary": primary,
    "cloud":   cloud,
    "archive": archive,
}

# ─────────────────────────────────────────────────────────
# ⚡ INDEXES
# ─────────────────────────────────────────────────────────
async def ensure_indexes():
    for name, col in COLLECTIONS.items():
        try:
            await col.create_index(
                [("file_name", "text"), ("caption", "text")],
                name=f"{name}_text"
            )
            logger.info(f"✅ Text Index OK: {name}")
        except Exception as e:
            if "already exists" in str(e) or "IndexKeySpecsConflict" in str(e) or "86" in str(e):
                pass
            else:
                logger.warning(f"Index warning [{name}]: {e}")

# ─────────────────────────────────────────────────────────
# 📊 DB STATS
# ─────────────────────────────────────────────────────────
async def db_count_documents():
    try:
        p, c, a = await asyncio.gather(
            primary.estimated_document_count(),
            cloud.estimated_document_count(),
            archive.estimated_document_count(),
        )
        return {"primary": p, "cloud": c, "archive": a, "total": p + c + a}
    except Exception as e:
        logger.error(f"Count error: {e}")
        return {"primary": 0, "cloud": 0, "archive": 0, "total": 0}

# ─────────────────────────────────────────────────────────
# 📸 TELEGRAPH UPLOADER
# ─────────────────────────────────────────────────────────
async def upload_to_telegraph(file_bytes: bytes):
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field(
                'file',
                io.BytesIO(file_bytes),
                filename='thumb.jpg',
                content_type='image/jpeg'
            )
            async with session.post("https://telegra.ph/upload", data=data) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if isinstance(res, list) and len(res) > 0 and "src" in res[0]:
                        return "https://telegra.ph" + res[0]["src"]
                    else:
                        logger.warning(f"Telegraph unexpected response: {res}")
    except Exception as e:
        logger.error(f"Telegraph Upload Error: {e}")
    return None

# ─────────────────────────────────────────────────────────
# 💾 SAVE FILE (WITH AUTO TELEGRAPH CACHING)
# ✅ FIX: bot parameter directly pass करो — temp.BOT पर निर्भरता हटाई
# ─────────────────────────────────────────────────────────
async def save_file(media, collection_type="primary", bot=None):
    try:
        file_id = unpack_new_file_id(media.file_id)
        if not file_id:
            logger.warning(f"Could not unpack file_id: {media.file_name}")
            return "err"

        f_name  = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(getattr(media, 'file_name', "") or "")).strip()
        caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(getattr(media, 'caption', "") or "")).strip()
        file_type = type(media).__name__.lower()

        # 🌟 THUMBNAIL: Telegraph पर upload करो
        thumb_url = "https://i.ibb.co/30B3RcS/default-movie.png"  # Default fallback

        if bot and hasattr(media, 'thumbs') and media.thumbs:
            try:
                thumb_id = media.thumbs[0].file_id
                # ✅ FIX: bot directly use हो रहा है, temp.BOT नहीं
                file_data = await bot.download_media(thumb_id, in_memory=True)
                if file_data:
                    uploaded_url = await upload_to_telegraph(file_data.getvalue())
                    if uploaded_url:
                        thumb_url = uploaded_url
                        logger.info(f"📸 Thumb uploaded to Telegraph: {uploaded_url}")
                    else:
                        logger.warning(f"Telegraph upload returned None for: {f_name}")
            except Exception as e:
                logger.error(f"Thumb cache error [{f_name}]: {e}")

        doc = {
            "_id":       file_id,
            "file_ref":  media.file_id,
            "file_name": f_name,
            "file_size": media.file_size,
            "caption":   caption,
            "file_type": file_type,
            "thumb_url": thumb_url,  # ✅ Telegraph link या default
        }

        col    = COLLECTIONS.get(collection_type, primary)
        result = await col.replace_one({"_id": file_id}, doc, upsert=True)

        if result.matched_count > 0:
            logger.warning(f"Already Saved - {f_name}")
            return "dup"
        else:
            logger.info(f"Saved - {f_name} | thumb: {thumb_url}")
            return "suc"

    except Exception as e:
        logger.error(f"save_file error: {e}")
        return "err"

# ─────────────────────────────────────────────────────────
# 🔍 REGEX BUILDER
# ─────────────────────────────────────────────────────────
def _build_regex(query: str):
    query = query.strip()
    if not query:
        raw = r'.'
    elif ' ' not in query:
        raw = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw = re.escape(query).replace(r'\ ', r'.*[\s\.\+\-_]')

    try:
        return re.compile(raw, flags=re.IGNORECASE)
    except Exception:
        return re.compile(re.escape(query), flags=re.IGNORECASE)

# ─────────────────────────────────────────────────────────
# 🚀 SMART SEARCH (HYBRID: TEXT INDEX + REGEX)
# ✅ FIX: cursor.skip().limit() अब reassign होता है
# ─────────────────────────────────────────────────────────
async def _search(col, raw_query: str, regex, offset: int, limit: int, lang=None):

    clean_query  = raw_query.replace('"', '').replace("'", "")
    strict_query = " ".join(f'"{word}"' for word in clean_query.split())

    text_flt = {"$text": {"$search": strict_query}}
    if lang:
        lang_regex = re.compile(lang, re.IGNORECASE)
        text_flt = {"$and": [text_flt, {"file_name": lang_regex}]}

    count = await col.count_documents(text_flt)

    if count > 0:
        async def _fetch_text():
            # ✅ FIX: cursor को reassign किया — पहले यह काम नहीं करता था
            cursor = col.find(text_flt, {"score": {"$meta": "textScore"}})
            cursor = cursor.sort([("score", {"$meta": "textScore"})])
            cursor = cursor.skip(offset).limit(limit)
            docs = await cursor.to_list(length=limit)
            for doc in docs:
                doc["file_id"] = doc["_id"]
            return docs
        return await _fetch_text(), count

    if USE_CAPTION_FILTER:
        reg_flt = {"$or": [{"file_name": regex}, {"caption": regex}]}
    else:
        reg_flt = {"file_name": regex}

    if lang:
        lang_regex = re.compile(lang, re.IGNORECASE)
        reg_flt = {"$and": [reg_flt, {"file_name": lang_regex}]}

    count = await col.count_documents(reg_flt)

    async def _fetch_reg():
        # ✅ FIX: यहाँ भी cursor reassign
        cursor = col.find(reg_flt).sort('_id', -1)
        cursor = cursor.skip(offset).limit(limit)
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc["file_id"] = doc["_id"]
        return docs

    docs = await _fetch_reg()
    return docs, count

# ─────────────────────────────────────────────────────────
# 🌐 PUBLIC SEARCH API
# ─────────────────────────────────────────────────────────
async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None, collection_type="primary"):
    if not query:
        return [], "", 0, collection_type

    raw_query  = str(query).strip()
    regex      = _build_regex(raw_query)
    results    = []
    total      = 0
    actual_src = collection_type

    if collection_type == "all":
        cascade = [("primary", primary), ("cloud", cloud), ("archive", archive)]
        for src, col in cascade:
            docs, cnt = await _search(col, raw_query, regex, offset, max_results, lang)
            if docs:
                results    = docs
                total      = cnt
                actual_src = src
                break

    elif collection_type in COLLECTIONS:
        col       = COLLECTIONS[collection_type]
        docs, cnt = await _search(col, raw_query, regex, offset, max_results, lang)
        results   = docs
        total     = cnt

    else:
        docs, cnt = await _search(primary, raw_query, regex, offset, max_results, lang)
        results   = docs
        total     = cnt

    next_offset = offset + max_results
    next_offset = "" if next_offset >= total else next_offset

    return results, next_offset, total, actual_src

# ─────────────────────────────────────────────────────────
# 💻 WEB API SEARCH
# ─────────────────────────────────────────────────────────
async def get_web_search_results(query, offset=0, limit=20):
    if not query:
        return []

    raw_query    = str(query).strip()
    clean_query  = raw_query.replace('"', '').replace("'", "")
    strict_query = " ".join(f'"{word}"' for word in clean_query.split())

    regex    = _build_regex(raw_query)
    text_flt = {"$text": {"$search": strict_query}}
    reg_flt  = {"file_name": regex}

    results = []
    try:
        for col in [primary, cloud, archive]:
            count = await col.count_documents(text_flt)

            if count > 0:
                cursor = col.find(text_flt, {"score": {"$meta": "textScore"}})
                cursor = cursor.sort([("score", {"$meta": "textScore"})])
            else:
                cursor = col.find(reg_flt).sort('_id', -1)

            # ✅ FIX: यहाँ भी reassign
            cursor = cursor.skip(offset).limit(limit)
            docs = await cursor.to_list(length=limit)
            for doc in docs:
                doc["file_id"] = doc["_id"]
                results.append(doc)

            if len(results) >= limit:
                break

        return results[:limit]
    except Exception as e:
        logger.error(f"Web Search Error: {e}")
        return []

# ─────────────────────────────────────────────────────────
# 🗑 DELETE FILES
# ─────────────────────────────────────────────────────────
async def delete_files(query, collection_type="all"):
    deleted = 0
    try:
        if query == "*":
            cols    = [col for name, col in COLLECTIONS.items()
                       if collection_type == "all" or name == collection_type]
            results = await asyncio.gather(*[col.delete_many({}) for col in cols])
            return sum(r.deleted_count for r in results)

        regex = _build_regex(str(query))
        flt   = {"file_name": regex}
        cols  = [(name, col) for name, col in COLLECTIONS.items()
                 if collection_type == "all" or name == collection_type]

        results = await asyncio.gather(*[col.delete_many(flt) for _, col in cols])
        for (name, _), res in zip(cols, results):
            deleted += res.deleted_count
            if res.deleted_count:
                logger.info(f"🗑 Deleted {res.deleted_count} from {name}")

        return deleted

    except Exception as e:
        logger.error(f"delete_files error: {e}")
        return deleted

# ─────────────────────────────────────────────────────────
# 📂 GET FILE DETAILS
# ─────────────────────────────────────────────────────────
async def get_file_details(file_id):
    try:
        for col in [primary, cloud, archive]:
            doc = await col.find_one({"_id": file_id})
            if doc:
                doc["file_id"] = doc["_id"]
                return doc
        return None
    except Exception as e:
        logger.error(f"get_file_details error: {e}")
        return None

# ─────────────────────────────────────────────────────────
# 🔑 FILE ID ENCODING UTILS
# ─────────────────────────────────────────────────────────
def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n  = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id: str):
    try:
        decoded = FileId.decode(new_file_id)
        return encode_file_id(
            pack(
                "<iiqq",
                int(decoded.file_type),
                decoded.dc_id,
                decoded.media_id,
                decoded.access_hash,
            )
        )
    except Exception as e:
        logger.error(f"unpack_new_file_id error: {e}")
        return None
