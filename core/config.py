"""
Модуль конфигурации - сохранение и загрузка настроек приложения.
"""
import json
import sys
from pathlib import Path

def get_base_path():
    """Возвращает путь к папке приложения (учитывает PyInstaller)."""
    if getattr(sys, 'frozen', False):
        # Если запущено как .exe (PyInstaller)
        return Path(sys.executable).parent
    # Если запущен скрипт .py
    return Path(__file__).resolve().parent.parent

CONFIG_DIR = get_base_path()
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    # --- Аватар ---
    "avatar": {
        "width": 400,
        "height": 400,
        "position_x": 100,
        "position_y": 100,
        "fps": 30,
        "always_on_top": True,
    },
    # --- Левитация ---
    "levitation": {
        "enabled": True,
        "speed": 1.5,          # циклов в секунду
        "amplitude": 8,        # пикселей
    },
    # --- Спрайты ---
    "sprites": {
        "eyes_open_mouth_closed": "",
        "eyes_open_mouth_open": "",
        "eyes_closed_mouth_closed": "",
        "eyes_closed_mouth_open": "",
        # Дополнительные спрайты для эффектов
        "idle": "",            # статичный idle-спрайт (если задан, переопределяет комбинацию)
        "talk_end": "",        # спрайт для эффекта окончания разговора
    },
    # --- Аудио ---
    "audio": {
        "device_index": -1,    # -1 = устройство по умолчанию
        "sensitivity": 30,     # порог громкости (0-100)
        "silence_delay": 0.5,  # секунд тишины перед переключением в idle
        "pitch_detection": True,  # определять продолжительные звуки "аааа"
        "pitch_threshold": 50, # порог для pitch (0-100)
    },
    # --- Эффект "Говорит" ---
    "talking_effect": {
        "shake_enabled": True,
        "shake_intensity": 3,  # пикселей
        "shake_frequency": 8,  # Hz
        "mouth_sync": True,    # синхронизация рта с громкостью
        "mouth_sensitivity": 5, # доп. чувствительность для рта
    },
    # --- Эффект "Не говорит" ---
    "idle_effect": {
        "transition_enabled": True,
        "transition_duration": 0.3,  # секунд
        "blink_enabled": True,       # моргание в idle
        "blink_interval": 3.0,       # секунд между морганиями
        "blink_duration": 0.15,      # длительность моргания
    },
    # --- OBS ---
    "obs": {
        "window_title": "ZenVT Avatar",
        "background_transparency": True,
    },
}


class Config:
    """Управление конфигурацией приложения."""

    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self._load()

    def _deep_copy(self, d):
        return json.loads(json.dumps(d))

    def _load(self):
        """Загрузка конфигурации из файла."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Рекурсивное слияние с дефолтными
                self._merge(self._config, saved)
            except (json.JSONDecodeError, Exception) as e:
                print(f"[Config] Ошибка загрузки конфига: {e}")

    def _merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(base[key], value)
            else:
                base[key] = value

    def save(self):
        """Сохранение конфигурации в файл."""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def get(self, *keys):
        """Получение значения по пути ключей: get('audio', 'sensitivity')."""
        val = self._config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        return val

    def set(self, *args, value=None):
        """
        Установка значения. Два варианта вызова:
        - set('audio', 'sensitivity', 50)
        - set('audio', 'sensitivity', value=50)
        """
        if len(args) < 2:
            raise ValueError("Требуется минимум 2 аргумента (секция, ключ, [значение])")

        keys = list(args)
        if value is not None:
            keys.append(value)

        if len(keys) == 2:
            # set('section', value) - замена всей секции
            self._config[keys[0]] = keys[1]
        else:
            # set('section', 'key1', 'key2', value)
            target = self._config
            for k in keys[:-2]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-2]] = keys[-1]

    def get_all(self):
        """Возвращает полную копию конфига."""
        return self._deep_copy(self._config)

    def reset(self):
        """Сброс к дефолтным настройкам."""
        self._config = self._deep_copy(DEFAULT_CONFIG)
        self.save()


# Глобальный экземпляр
config = Config()
