import logging
import re
import base64
import asyncio
from struct import pack
import motor.motor_asyncio
from hydrogram.file_id import FileId
from info import DATABASE_URL, DATABASE_NAME, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# ⚙️ MOTOR CONNECTION — Memory-Leak & RAM Guard Optimized
# ─────────────────────────────────────────────────────────
client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL,
    maxPoolSize=15,             # हैवी प्रीमियम ट्रैफिक के लिए पर्याप्त कनेक्शंस
    minPoolSize=0,              # आइडल टाइम पर 0 कनेक्शन (कोएब की रैम 100% सुरक्षित)
    maxIdleTimeMS=30000,        # 30 सेकंड तक शांत रहने पर सॉकेट्स बंद करें
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
# ⚡ INDEXES — Fixed Illegal Specs (Zero Warning Logs)
# ─────────────────────────────────────────────────────────
async def ensure_indexes():
    for name, col in COLLECTIONS.items():
        try:
            # ✅ कम्पाउंड टेक्स्ट इंडेक्स को सुरक्षित रखा गया
            await col.create_index(
                [("file_name", "text"), ("caption", "text")],
                name=f"{name}_text"
            )
            
            # ✅ NEW UPGRADE: रेगेक्स सर्च (COLLSCAN) से बचने के लिए सिंगल-फील्ड इंडेक्स जोड़ा गया
            await col.create_index(
                "file_name", 
                name=f"{name}_filename_idx"
            )
            
            logger.info(f"✅ Fast Search & Regex Indexes OK: {name}")
        except Exception as e:
            if "already exists" in str(e) or "IndexKeySpecsConflict" in str(e):
                pass
            else:
                logger.warning(f"Index warning [{name}]: {e}")

# ─────────────────────────────────────────────────────────
# 📊 DB STATS — With Live Thumbnail Breakdown Sync
# ─────────────────────────────────────────────────────────
async def db_count_documents():
    try:
        p_task = primary.estimated_document_count()
        c_task = cloud.estimated_document_count()
        a_task = archive.estimated_document_count()
        
        pt_task = primary.count_documents({"thumb_url": {"$regex": "^TG_ID:"}})
        ct_task = cloud.count_documents({"thumb_url": {"$regex": "^TG_ID:"}})
        at_task = archive.count_documents({"thumb_url": {"$regex": "^TG_ID:"}})

        p, c, a, pt, ct, at = await asyncio.gather(
            p_task, c_task, a_task, pt_task, ct_task, at_task
        )
        
        return {
            "primary": p, "cloud": c, "archive": a, "total": p + c + a,
            "primary_thumb": pt, "cloud_thumb": ct, "archive_thumb": at, "total_thumb": pt + ct + at
        }
    except Exception as e:
        logger.error(f"Count Breakdown error: {e}")
        return {
            "primary": 0, "cloud": 0, "archive": 0, "total": 0,
            "primary_thumb": 0, "cloud_thumb": 0, "archive_thumb": 0, "total_thumb": 0
        }

# ─────────────────────────────────────────────────────────
# 💾 SAVE FILE (Auto-PreFetch Thumbnail & Write IOPS Protection)
# ─────────────────────────────────────────────────────────
async def save_file(media, collection_type="primary"):
    try:
        file_id = unpack_new_file_id(media.file_id)
        if not file_id:
            return "err"

        f_name  = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name or "")).strip()
        caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption  or "")).strip()
        file_type = type(media).__name__.lower()

        col = COLLECTIONS.get(collection_type, primary)
        
        existing_doc = await col.find_one({"_id": file_id}, {"file_ref": 1, "thumb_url": 1})
        
        if existing_doc:
            if existing_doc.get("file_ref") == media.file_id:
                return "dup"
            
            old_thumb = existing_doc.get("thumb_url")
            thumb_url = old_thumb if old_thumb and "TG_ID:" in old_thumb else None
        else:
            thumb_url = None

        doc = {
            "_id":       file_id,     
            "file_id":   file_id,     
            "file_ref":  media.file_id,
            "file_name": f_name,
            "file_size": media.file_size,
            "caption":   caption,
            "file_type": file_type,   
            "thumb_url": thumb_url 
        }

        await col.replace_one({"_id": file_id}, doc, upsert=True)
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
# 🚀 SMART SEARCH (Instant Response Projection Engine)
# ─────────────────────────────────────────────────────────
async def _search(col, raw_query: str, regex, offset: int, limit: int, lang=None):
    clean_query = raw_query.replace('"', '').replace("'", "")
    strict_query = " ".join(f'"{word}"' for word in clean_query.split())

    text_flt = {"$text": {"$search": strict_query}}
    if lang:
        text_flt = {"$and": [text_flt, {"file_name": re.compile(lang, re.IGNORECASE)}]}

    count = await col.count_documents(text_flt)
    
    if count > 0:
        # ✅ प्रोजेक्शन इंजन में "thumb_url" को सिंक किया गया ताकि फ़्रंटएंड इमेज कैशे बस्टर तेज़ी से लोड हो
        cursor = col.find(text_flt, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "caption": 1, "thumb_url": 1, "score": {"$meta": "textScore"}})
        cursor.sort([("score", {"$meta": "textScore"})])
        cursor.skip(offset).limit(limit)
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc["file_id"] = doc["_id"]
        return docs, count

    if USE_CAPTION_FILTER:
        reg_flt = {"$or": [{"file_name": regex}, {"caption": regex}]}
    else:
        reg_flt = {"file_name": regex}

    if lang:
        reg_flt = {"$and": [reg_flt, {"file_name": re.compile(lang, re.IGNORECASE)}]}

    # ✅ यहाँ भी प्रोजेक्शन में "thumb_url" और "file_type" को प्रोजेक्ट किया गया है ताकि सर्च रिज़ल्ट्स रॉकेट स्पीड से काम करें
    cursor = col.find(reg_flt, {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1, "file_ref": 1, "caption": 1, "thumb_url": 1}).sort('_id', -1)
    cursor.skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["file_id"] = doc["_id"]

    return docs, await col.count_documents(reg_flt)

# ─────────────────────────────────────────────────────────
# 🌐 PUBLIC SEARCH API — Adaptive Result Sync (Bot 12 vs Web 21)
# ─────────────────────────────────────────────────────────
async def get_search_results(query, max_results, offset=0, lang=None, collection_type="primary"):
    if not query:
        return [], "", 0, collection_type

    raw_query  = str(query).strip()
    regex      = _build_regex(raw_query)
    results    = []
    total      = 0
    actual_src = collection_type

    if collection_type == "all":
        for src, col in [("primary", primary), ("cloud", cloud), ("archive", archive)]:
            docs, cnt = await _search(col, raw_query, regex, offset, max_results, lang)
            if docs:
                results    = docs
                total      = cnt
                actual_src = src
                break  
    else:
        col = COLLECTIONS.get(collection_type, primary)
        results, total = await _search(col, raw_query, regex, offset, max_results, lang)

    next_offset = offset + max_results
    next_offset = "" if next_offset >= total else next_offset

    return results, next_offset, total, actual_src

# ─────────────────────────────────────────────────────────
# 🗑 DELETE FILES (Sequential Lock Guard)
# ─────────────────────────────────────────────────────────
async def delete_files(query, collection_type="all"):
    deleted = 0
    try:
        if query == "*":
            cols = [col for name, col in COLLECTIONS.items() if collection_type == "all" or name == collection_type]
            for col in cols:
                res = await col.delete_many({})
                deleted += res.deleted_count
            return deleted

        flt   = {"file_name": _build_regex(str(query))}
        cols  = [col for name, col in COLLECTIONS.items() if collection_type == "all" or name == collection_type]

        for col in cols:
            res = await col.delete_many(flt)
            deleted += res.deleted_count

        return deleted
    except Exception as e:
        logger.error(f"delete_files error: {e}")
        return deleted

# ─────────────────────────────────────────────
# 📂 GET FILE DETAILS (Strict Token Security Lookup)
# ─────────────────────────────────────────────
async def get_file_details(file_id):
    try:
        for col in [primary, cloud, archive]:
            doc = await col.find_one(
                {"_id": file_id},
                {"_id": 1, "file_name": 1, "file_size": 1, "file_ref": 1, "caption": 1, "thumb_url": 1}
            )
            if doc:
                doc["file_id"] = doc["_id"]  
                return doc
        return None
    except Exception as e:
        logger.error(f"get_file_details error: {e}")
        return None

# ─────────────────────────────────────────────────────────
# 🗑 UNPACK/ENCODE UTILS
# ─────────────────────────────────────────────────────────
def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0: n += 1
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
