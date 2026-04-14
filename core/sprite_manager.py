"""
Модуль загрузки и кэширования спрайтов.
"""
from PIL import Image
from pathlib import Path


class SpriteManager:
    """Управление загрузкой и хранением спрайтов аватара."""

    def __init__(self):
        self._sprites = {}
        self._cache = {}  # кэш resized изображений

    def load_sprite(self, key: str, path: str) -> bool:
        """
        Загрузка спрайта по ключу.
        key: 'eyes_open_mouth_closed', 'eyes_open_mouth_open', и т.д.
        path: путь к файлу изображения.
        """
        try:
            p = Path(path)
            if not p.exists():
                print(f"[SpriteManager] Файл не найден: {path}")
                return False

            img = Image.open(p).convert("RGBA")
            self._sprites[key] = img
            self._cache.clear()  # сброс кэша при изменении
            print(f"[SpriteManager] Загружен спрайт: {key}")
            return True
        except Exception as e:
            print(f"[SpriteManager] Ошибка загрузки {key}: {e}")
            return False

    def get_sprite(self, key: str, size: tuple = None):
        """
        Получить спрайт по ключу.
        size: (width, height) для ресайза, None = оригинальный размер.
        """
        if key not in self._sprites:
            return None

        img = self._sprites[key]

        if size:
            cache_key = (key, size)
            if cache_key in self._cache:
                return self._cache[cache_key]

            resized = img.resize(size, Image.Resampling.LANCZOS)
            self._cache[cache_key] = resized
            return resized

        return img

    def get_combined_sprite(self, eyes_state: str, mouth_open: float, size: tuple = None):
        """
        Получить комбинированный спрайт на основе состояния глаз и рта.
        mouth_open: 0.0 - 1.0 (степень открытия)
        """
        # Определяем ключ
        if mouth_open > 0.3:
            mouth_key = "mouth_open"
        else:
            mouth_key = "mouth_closed"

        sprite_key = f"eyes_{eyes_state}_{mouth_key}"

        return self.get_sprite(sprite_key, size)

    def has_sprite(self, key: str):
        return key in self._sprites

    def clear(self):
        self._sprites.clear()
        self._cache.clear()

    def get_loaded_sprites(self):
        """Список загруженных спрайтов."""
        return list(self._sprites.keys())
