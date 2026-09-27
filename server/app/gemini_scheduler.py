"""Serialize Gemini API calls; interactive work runs before background imports."""

import asyncio
from enum import IntEnum
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class GeminiPriority(IntEnum):
    INTERACTIVE = 0
    BACKGROUND = 1


class GeminiScheduler:
    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[
            tuple[int, int, asyncio.Future, Callable[[], Awaitable[object]]]
        ] = asyncio.PriorityQueue()
        self._seq = 0
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def run(
        self,
        priority: GeminiPriority,
        fn: Callable[[], Awaitable[T]],
    ) -> T:
        self.start()
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._seq += 1
        await self._queue.put((int(priority), self._seq, fut, fn))
        return await fut

    async def _worker(self) -> None:
        while True:
            _priority, _seq, fut, fn = await self._queue.get()
            try:
                result = await fn()
            except Exception as exc:
                if not fut.done():
                    fut.set_exception(exc)
                continue
            if not fut.done():
                fut.set_result(result)


gemini_scheduler = GeminiScheduler()
