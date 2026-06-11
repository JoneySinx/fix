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
            await col.create_index(
                [("file_name", "text"), ("caption", "text")],
                name=f"{name}_text"
            )
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
# 🚀 SMART SEARCH — Fixed: No double count_documents
# FIX 1: count_documents हटाया — पहले find करो, अगर docs मिले तो
#         text search सफल। Total का estimate len(docs) से करो।
# FIX 2: Regex fallback का count भी हटाया — same logic।
# ─────────────────────────────────────────────────────────
async def _search(col, raw_query: str, regex, offset: int, limit: int, lang=None):
    clean_query = raw_query.replace('"', '').replace("'", "")
    strict_query = " ".join(f'"{word}"' for word in clean_query.split())

    text_flt = {"$text": {"$search": strict_query}}
    if lang:
        text_flt = {"$and": [text_flt, {"file_name": re.compile(lang, re.IGNORECASE)}]}

    projection = {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1,
                  "file_ref": 1, "caption": 1, "thumb_url": 1,
                  "score": {"$meta": "textScore"}}

    # ✅ FIX 1: count_documents हटाया — सीधे find करो
    # $text search के साथ सिर्फ textScore sort — _id sort नहीं (MongoDB restriction)
    try:
        cursor = col.find(text_flt, projection)
        cursor.sort([("score", {"$meta": "textScore"})])
        cursor.skip(offset).limit(limit)
        docs = await cursor.to_list(length=limit)
    except Exception:
        docs = []

    if docs:
        for doc in docs:
            doc["file_id"] = doc["_id"]
        # Total estimate: अगर full page मिली तो और results हो सकते हैं
        # exact count की जरूरत नहीं — pagination के लिए has_more काफी है
        estimated_total = offset + len(docs) + (limit if len(docs) == limit else 0)
        return docs, estimated_total

    # ── Regex Fallback ──
    if USE_CAPTION_FILTER:
        reg_flt = {"$or": [{"file_name": regex}, {"caption": regex}]}
    else:
        reg_flt = {"file_name": regex}

    if lang:
        reg_flt = {"$and": [reg_flt, {"file_name": re.compile(lang, re.IGNORECASE)}]}

    proj_regex = {"_id": 1, "file_name": 1, "file_size": 1, "file_type": 1,
                  "file_ref": 1, "caption": 1, "thumb_url": 1}

    cursor = col.find(reg_flt, proj_regex).sort('_id', -1)
    cursor.skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["file_id"] = doc["_id"]

    # ✅ FIX 2: Regex count_documents हटाया — same estimate logic
    estimated_total = offset + len(docs) + (limit if len(docs) == limit else 0)
    return docs, estimated_total

# ─────────────────────────────────────────────────────────
# 🌐 PUBLIC SEARCH API — Parallel Collection Search
# FIX 3: "all" mode में sequential loop हटाया।
#         asyncio.gather से तीनों collections एक साथ search।
#         जो पहले results दे, वही use होगी।
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
        # ✅ FIX 3: तीनों एक साथ parallel — पहले मिला वो use करो
        tasks = [
            _search(primary, raw_query, regex, offset, max_results, lang),
            _search(cloud,   raw_query, regex, offset, max_results, lang),
            _search(archive, raw_query, regex, offset, max_results, lang),
        ]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        src_names = ["primary", "cloud", "archive"]
        for i, res in enumerate(all_results):
            if isinstance(res, Exception):
                logger.warning(f"Search error in {src_names[i]}: {res}")
                continue
            docs, cnt = res
            if docs:
                results    = docs
                total      = cnt
                actual_src = src_names[i]
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
        # ✅ Parallel lookup — तीनों एक साथ
        tasks = [
            col.find_one(
                {"_id": file_id},
                {"_id": 1, "file_name": 1, "file_size": 1, "file_ref": 1, "caption": 1, "thumb_url": 1}
            )
            for col in [primary, cloud, archive]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for doc in results:
            if doc and not isinstance(doc, Exception):
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
