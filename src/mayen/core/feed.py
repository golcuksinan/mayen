"""Kaydedilen olayların ve sözlerin canlı yayını (§5.5: panel olaylara abone olur).

Ayrı bir olay altyapısı değildir: kayda giren her şey, yazıldıktan sonra aboneye de verilir.
Yavaş bir abone kaydı bekletmez; kuyruğu dolunca abonelik düşer ve bunu kendisi görür.
Sessizce atlanan bir olay, panelde hiç yaşanmamış gibi görünürdü.
"""

import asyncio

from mayen.ports.events import Event
from mayen.ports.transcript import Utterance

type Item = Event | Utterance


class Subscription:
    def __init__(self, feed: "Feed", limit: int) -> None:
        self._feed = feed
        self._queue: asyncio.Queue[Item] = asyncio.Queue(limit)
        self.overflowed = False

    def offer(self, item: Item) -> None:
        if self.overflowed:
            return
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            self.overflowed = True
            self._feed.unsubscribe(self)

    async def next(self) -> Item:
        """Sıradaki kayıt; abonelik düştüyse ve kuyruk boşsa `OverflowError`."""
        if self.overflowed and self._queue.empty():
            raise OverflowError("subscriber fell behind the feed")
        return await self._queue.get()

    def pending(self) -> list[Item]:
        items: list[Item] = []
        while not self._queue.empty():
            items.append(self._queue.get_nowait())
        return items

    def close(self) -> None:
        self._feed.unsubscribe(self)


class Feed:
    def __init__(self, limit: int = 1000) -> None:
        self._limit = limit
        self._subscribers: list[Subscription] = []

    def subscribe(self) -> Subscription:
        subscription = Subscription(self, self._limit)
        self._subscribers.append(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        if subscription in self._subscribers:
            self._subscribers.remove(subscription)

    def publish(self, item: Item) -> None:
        for subscription in list(self._subscribers):
            subscription.offer(item)
