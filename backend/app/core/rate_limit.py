import asyncio
import math
import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.security import get_current_user
from app.db.models import User


class SlidingWindowRateLimiter:
    """
    In-memory Sliding Window Rate Limiter.
    Menghitung jumlah permintaan dalam rentang waktu bergerak (window)
    secara thread/asynchronous-safe dengan asyncio.Lock().
    """

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Mengecek apakah kueri diizinkan.
        Mengembalikan: (is_allowed: bool, remaining: int, retry_after: int)
        """
        if not settings.rate_limit_enabled:
            return True, max_requests, 0

        now = time.time()
        cutoff = now - window_seconds

        async with self._lock:
            timestamps = self._history[key]
            # Hapus timestamp di luar window
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                oldest = valid_timestamps[0]
                retry_after = max(1, math.ceil(oldest + window_seconds - now))
                self._history[key] = valid_timestamps
                return False, 0, retry_after

            # Tambahkan waktu kueri baru
            valid_timestamps.append(now)
            self._history[key] = valid_timestamps
            remaining = max(0, max_requests - len(valid_timestamps))
            return True, remaining, 0

    async def reset(self) -> None:
        """Reset seluruh history rate limiter (berguna untuk isolasi unit test)."""
        async with self._lock:
            self._history.clear()


# Global rate limiter instance
limiter = SlidingWindowRateLimiter()


def rate_limit(
    action: str,
    get_max_requests: int | None = None,
    get_window_seconds: int | None = None,
):
    """
    Factory FastAPI Dependency untuk membatasi laju pemanggilan endpoint
    berdasarkan identitas pengguna terautentikasi (user_id) atau IP client.
    """

    async def dependency(
        request: Request,
        response: Response,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> None:
        if not settings.rate_limit_enabled:
            return

        # Ambil konfigurasi dinamis atau default
        if action == "upload":
            max_requests = (
                get_max_requests
                if get_max_requests is not None
                else settings.rate_limit_upload_max
            )
            window_seconds = (
                get_window_seconds
                if get_window_seconds is not None
                else settings.rate_limit_upload_window_seconds
            )
        elif action == "chat":
            max_requests = (
                get_max_requests
                if get_max_requests is not None
                else settings.rate_limit_chat_max
            )
            window_seconds = (
                get_window_seconds
                if get_window_seconds is not None
                else settings.rate_limit_chat_window_seconds
            )
        else:
            max_requests = get_max_requests or 60
            window_seconds = get_window_seconds or 60

        identifier = str(current_user.id) if current_user else (request.client.host if request.client else "unknown")
        rate_key = f"{action}:{identifier}"

        allowed, remaining, retry_after = await limiter.check(
            key=rate_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        # Set standard rate-limit headers
        rate_headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(remaining),
        }
        for k, v in rate_headers.items():
            response.headers[k] = v
        request.state.rate_limit_headers = rate_headers

        if not allowed:
            response.headers["Retry-After"] = str(retry_after)
            action_desc = "mengunggah paper" if action == "upload" else "mengirim pertanyaan chat"
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Terlalu banyak permintaan {action_desc}. Batas: {max_requests} per {window_seconds} detik. Silakan coba lagi dalam {retry_after} detik.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

    return dependency


rate_limit_upload = rate_limit("upload")
rate_limit_chat = rate_limit("chat")
