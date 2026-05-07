import math
import asyncio
import logging
from collections import deque
from typing import AsyncGenerator, Optional
from hydrogram.types import Message
from utils import temp
from hydrogram import Client, utils, raw
from hydrogram.session import Session, Auth
from hydrogram.errors import AuthBytesInvalid, FloodWait
from hydrogram.file_id import FileId, FileType, ThumbnailSource

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
#  Constants — tune these for best results
# ──────────────────────────────────────────
PREFETCH_AHEAD   = 3          # Kitne chunks aage se fetch karein
MAX_RETRIES      = 5          # Har chunk ke liye max retry attempts
RETRY_BASE_DELAY = 0.3        # Seconds — exponential backoff base
MIN_CHUNK        = 4  * 1024  # 4 KB
MAX_CHUNK        = 1024 * 1024  # 1 MB (Telegram's hard limit)


# ──────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────

def chunk_size(length: int) -> int:
    """Optimal chunk size based on file length (power of 2, 4 KB – 512 KB)."""
    return 2 ** max(min(math.ceil(math.log2(length / 1024)), 10), 2) * 1024


def offset_fix(offset: int, chunksize: int) -> int:
    return offset - (offset % chunksize)


class TGCustomYield:
    """
    Ultra-smooth Telegram file streaming with:
      • Async prefetch queue  — hides network RTT behind yield
      • Exponential-backoff retry — tolerates flaky DC connections
      • FloodWait auto-sleep   — respects Telegram rate limits
      • Adaptive chunk slicing — correct first/last/single-part handling
    """

    def __init__(self):
        self.main_bot: Client = temp.BOT

    # ── File properties ───────────────────────────────────────────────────

    @staticmethod
    async def generate_file_properties(msg: Message) -> FileId:
        media = getattr(msg, msg.media.value, None)
        return FileId.decode(media.file_id)

    # ── Media session (DC auth) ───────────────────────────────────────────

    async def generate_media_session(self, client: Client, msg: Message) -> Session:
        data = await self.generate_file_properties(msg)
        media_session = client.media_sessions.get(data.dc_id)

        if media_session is not None:
            return media_session

        if data.dc_id != await client.storage.dc_id():
            media_session = Session(
                client, data.dc_id,
                await Auth(client, data.dc_id, await client.storage.test_mode()).create(),
                await client.storage.test_mode(),
                is_media=True
            )
            await media_session.start()

            for attempt in range(3):
                exported_auth = await client.invoke(
                    raw.functions.auth.ExportAuthorization(dc_id=data.dc_id)
                )
                try:
                    await media_session.send(
                        raw.functions.auth.ImportAuthorization(
                            id=exported_auth.id,
                            bytes=exported_auth.bytes
                        )
                    )
                    break
                except AuthBytesInvalid:
                    if attempt == 2:
                        await media_session.stop()
                        raise
        else:
            media_session = Session(
                client, data.dc_id,
                await client.storage.auth_key(),
                await client.storage.test_mode(),
                is_media=True
            )
            await media_session.start()

        client.media_sessions[data.dc_id] = media_session
        return media_session

    # ── Location builder ──────────────────────────────────────────────────

    @staticmethod
    async def get_location(file_id: FileId):
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id,
                    access_hash=file_id.chat_access_hash
                )
            elif file_id.chat_access_hash == 0:
                peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
            else:
                peer = raw.types.InputPeerChannel(
                    channel_id=utils.get_channel_id(file_id.chat_id),
                    access_hash=file_id.chat_access_hash
                )
            return raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG
            )

        if file_type == FileType.PHOTO:
            return raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size
            )

        return raw.types.InputDocumentFileLocation(
            id=file_id.media_id,
            access_hash=file_id.access_hash,
            file_reference=file_id.file_reference,
            thumb_size=file_id.thumbnail_size
        )

    # ── Core: single chunk fetch with retry + FloodWait ──────────────────

    async def _fetch_chunk(
        self,
        media_session: Session,
        location,
        offset: int,
        limit: int
    ) -> bytes:
        """
        Fetch one raw chunk. Retries up to MAX_RETRIES times with
        exponential backoff. Handles FloodWait automatically.
        Returns b"" when Telegram signals EOF.
        """
        delay = RETRY_BASE_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = await media_session.send(
                    raw.functions.upload.GetFile(
                        location=location,
                        offset=offset,
                        limit=limit
                    )
                )
                if isinstance(r, raw.types.upload.File):
                    return r.bytes
                return b""                          # Unexpected type → EOF

            except FloodWait as e:
                wait = e.value + 1
                logger.warning("FloodWait %ds on chunk offset=%d", wait, offset)
                await asyncio.sleep(wait)

            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt == MAX_RETRIES:
                    logger.error("Chunk offset=%d failed after %d retries: %s",
                                 offset, MAX_RETRIES, e)
                    raise
                logger.warning("Chunk offset=%d attempt %d failed (%s), retry in %.1fs",
                                offset, attempt, e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 5.0)        # cap at 5 s

        return b""

    # ── Core: prefetch queue producer ────────────────────────────────────

    async def _prefetch_producer(
        self,
        media_session: Session,
        location,
        start_offset: int,
        csize: int,
        total_parts: int,
        queue: asyncio.Queue
    ):
        """
        Runs in the background. Fetches chunks ahead of the consumer
        and puts raw bytes into the queue.
        Sends None as sentinel when all chunks are fetched.
        """
        offset = start_offset
        for _ in range(total_parts):
            try:
                data = await self._fetch_chunk(media_session, location, offset, csize)
            except Exception as exc:
                await queue.put(exc)              # Forward exception to consumer
                return
            await queue.put(data)
            if not data:
                break
            offset += csize
        await queue.put(None)                     # Sentinel — all done

    # ── Public: streaming generator ──────────────────────────────────────

    async def yield_file(
        self,
        media_msg: Message,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        csize: int,
    ) -> AsyncGenerator[bytes, None]:
        """
        Yield file chunks with PREFETCH_AHEAD look-ahead to eliminate
        buffering pauses. Properly handles single-part, first-part,
        middle, and last-part slicing.
        """
        client       = self.main_bot
        data         = await self.generate_file_properties(media_msg)
        media_session = await self.generate_media_session(client, media_msg)
        location     = await self.get_location(data)

        # ── Queue with bounded back-pressure ──────────────────────────
        queue: asyncio.Queue = asyncio.Queue(maxsize=PREFETCH_AHEAD + 2)

        producer_task = asyncio.create_task(
            self._prefetch_producer(
                media_session, location,
                offset, csize, part_count, queue
            )
        )

        current_part = 1
        try:
            while current_part <= part_count:
                chunk = await queue.get()

                # Propagate exceptions from producer
                if isinstance(chunk, Exception):
                    raise chunk

                # EOF before expected
                if chunk is None or not chunk:
                    logger.warning("Stream ended early at part %d / %d",
                                   current_part, part_count)
                    break

                # ── Slice logic ───────────────────────────────────────
                if part_count == 1:
                    # Single-part request: cut both ends
                    yield chunk[first_part_cut:last_part_cut]
                    break
                elif current_part == 1:
                    yield chunk[first_part_cut:]
                elif current_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

                current_part += 1

        finally:
            # Always cancel the background producer to avoid leaks
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except (asyncio.CancelledError, Exception):
                    pass

    # ── Public: download full file into memory ────────────────────────────

    async def download_as_bytesio(self, media_msg: Message) -> list[bytes]:
        """
        Download entire file in 1 MB chunks with retry support.
        Returns list of byte chunks.
        """
        client        = self.main_bot
        data          = await self.generate_file_properties(media_msg)
        media_session = await self.generate_media_session(client, media_msg)
        location      = await self.get_location(data)

        limit  = MAX_CHUNK
        offset = 0
        m_file: list[bytes] = []

        while True:
            chunk = await self._fetch_chunk(media_session, location, offset, limit)
            if not chunk:
                break
            m_file.append(chunk)
            offset += limit

        return m_file
