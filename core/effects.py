"""
Модуль эффектов - управление анимациями и состояниями аватара.
Эффекты: дрожь при разговоре, левитация, моргание, переходы.
"""
import math
import time
from enum import Enum


class AvatarState(Enum):
    IDLE = "idle"
    TALKING = "talking"
    TALK_END = "talk_end"
    BLINK = "blink"


class EffectManager:
    """
    Управляет эффектами аватара на основе состояния.
    Расчитывает смещения, текущий спрайт, параметры анимации.
    """

    def __init__(self):
        # Состояние
        self._state = AvatarState.IDLE
        self._state_time = 0.0  # время в текущем состоянии

        # Левитация
        self._levitation_offset = 0.0

        # Дрожь
        self._shake_offset_x = 0.0
        self._shake_offset_y = 0.0

        # Моргание
        self._is_blinking = False
        self._blink_timer = 0.0
        self._blink_start = 0.0

        # Переход talk -> idle
        self._transition_progress = 0.0

        # Время последнего обновления
        self._last_update = time.time()

        # Громкость (для синхронизации рта)
        self._current_volume = 0.0

    def update(self, fps=30):
        """Обновление всех эффектов. Вызывать каждый кадр."""
        now = time.time()
        dt = now - self._last_update
        self._last_update = now
        self._state_time += dt

        from core.config import config

        # --- Левитация ---
        lev_enabled = config.get("levitation", "enabled")
        if lev_enabled:
            speed = config.get("levitation", "speed")
            amplitude = config.get("levitation", "amplitude")
            self._levitation_offset = math.sin(self._state_time * speed * 2 * math.pi) * amplitude
        else:
            self._levitation_offset = 0.0

        # --- Дрожь (только при разговоре) ---
        if self._state == AvatarState.TALKING:
            shake_enabled = config.get("talking_effect", "shake_enabled")
            if shake_enabled:
                intensity = config.get("talking_effect", "shake_intensity")
                frequency = config.get("talking_effect", "shake_frequency")
                self._shake_offset_x = (
                    math.sin(self._state_time * frequency * 2 * math.pi) * intensity * 0.5
                )
                self._shake_offset_y = (
                    math.cos(self._state_time * frequency * 1.3 * 2 * math.pi) * intensity * 0.3
                )
            else:
                self._shake_offset_x = 0.0
                self._shake_offset_y = 0.0
        else:
            self._shake_offset_x = 0.0
            self._shake_offset_y = 0.0

        # --- Моргание ---
        blink_enabled = config.get("idle_effect", "blink_enabled")
        if blink_enabled and self._state == AvatarState.IDLE:
            blink_interval = config.get("idle_effect", "blink_interval")
            blink_duration = config.get("idle_effect", "blink_duration")

            self._blink_timer += dt
            if self._blink_timer >= blink_interval and not self._is_blinking:
                self._is_blinking = True
                self._blink_start = now
                self._blink_timer = 0.0

            if self._is_blinking:
                if now - self._blink_start >= blink_duration:
                    self._is_blinking = False
        else:
            self._is_blinking = False

        # --- Переход talk_end ---
        if self._state == AvatarState.TALK_END:
            trans_enabled = config.get("idle_effect", "transition_enabled")
            if trans_enabled:
                duration = config.get("idle_effect", "transition_duration")
                self._transition_progress = min(self._state_time / duration, 1.0)
                if self._transition_progress >= 1.0:
                    self._set_state(AvatarState.IDLE)
            else:
                self._set_state(AvatarState.IDLE)

    def set_talking(self, talking: bool):
        """Установка состояния разговора."""
        if talking and self._state != AvatarState.TALKING:
            self._set_state(AvatarState.TALKING)
        elif not talking and self._state == AvatarState.TALKING:
            self._set_state(AvatarState.TALK_END)

    def _set_state(self, state: AvatarState):
        """Внутренний метод смены состояния."""
        self._state = state
        self._state_time = 0.0
        self._transition_progress = 0.0

    def set_volume(self, volume: float):
        """Обновление текущей громкости."""
        self._current_volume = volume

    # --- Геттеры для рендера ---

    def get_levitation_offset(self):
        return self._levitation_offset

    def get_shake_offset(self):
        return self._shake_offset_x, self._shake_offset_y

    def is_blinking(self):
        return self._is_blinking

    def get_state(self):
        return self._state

    def get_mouth_open_amount(self):
        """
        Возвращает степень открытия рта (0.0 - 1.0).
        Зависит от громкости и настроек синхронизации.
        """
        from core.config import config

        if self._state == AvatarState.TALKING:
            mouth_sync = config.get("talking_effect", "mouth_sync")
            if mouth_sync:
                mouth_sens = config.get("talking_effect", "mouth_sensitivity") / 100.0
                return min(self._current_volume / max(mouth_sens, 0.01), 1.0)
            return 1.0  # Рот полностью открыт при разговоре
        elif self._state == AvatarState.TALK_END:
            # Плавное закрытие
            return max(0.0, 1.0 - self._transition_progress)
        return 0.0

    def get_eyes_state(self):
        """
        Возвращает состояние глаз: 'open' или 'closed'.
        Закрыты при моргании.
        """
        if self._is_blinking:
            return "closed"
        return "open"
