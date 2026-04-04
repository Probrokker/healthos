"""
Долгосрочная память сессий.
Хранит историю разговора и активный контекст (кто последний упоминался,
что обсуждали) — чтобы бот не переспрашивал очевидное.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional

# Храним в памяти процесса (для Railway достаточно — один инстанс)
# При рестарте сервера история сбрасывается, но это нормально для медассистента
_sessions: dict = {}

MAX_HISTORY = 20          # максимум сообщений в истории
SESSION_TTL_HOURS = 4     # через сколько часов сессия "остывает"


class SessionMemory:
    """Память одного пользователя."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history: list = []          # [{role, content, ts}]
        self.active_person: Optional[str] = None   # последний упомянутый член семьи
        self.last_activity: datetime = datetime.now()
        self.pending_context: dict = {}  # временный контекст (ожидаем уточнения)

    def add_message(self, role: str, content: str):
        """Добавляет сообщение в историю."""
        self.history.append({
            "role": role,
            "content": content,
            "ts": datetime.now().isoformat()
        })
        # Обрезаем до MAX_HISTORY
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
        self.last_activity = datetime.now()

    def set_active_person(self, name: str):
        """Запоминает о ком идёт разговор."""
        self.active_person = name
        self.last_activity = datetime.now()

    def get_history_for_claude(self) -> list:
        """Возвращает историю в формате для Claude API."""
        result = []
        for msg in self.history:
            result.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return result

    def get_context_summary(self) -> str:
        """Краткий текстовый контекст для роутера."""
        parts = []
        if self.active_person:
            parts.append(f"Последний упомянутый член семьи: {self.active_person}")
        if self.history:
            last = self.history[-3:]  # последние 3 сообщения
            parts.append("Последние сообщения разговора:")
            for m in last:
                role_label = "Пользователь" if m["role"] == "user" else "Бот"
                parts.append(f"  {role_label}: {m['content'][:150]}")
        return "\n".join(parts) if parts else ""

    def is_stale(self) -> bool:
        """Сессия устарела если давно не было активности."""
        return datetime.now() - self.last_activity > timedelta(hours=SESSION_TTL_HOURS)

    def reset_if_stale(self):
        """Сбрасывает активного человека если сессия остыла."""
        if self.is_stale():
            self.active_person = None
            self.history = []


def get_session(user_id: int) -> SessionMemory:
    """Возвращает или создаёт сессию пользователя."""
    if user_id not in _sessions:
        _sessions[user_id] = SessionMemory(user_id)
    session = _sessions[user_id]
    session.reset_if_stale()
    return session


def clear_old_sessions():
    """Чистит старые сессии (вызывать периодически)."""
    to_delete = [uid for uid, s in _sessions.items() if s.is_stale()]
    for uid in to_delete:
        del _sessions[uid]
