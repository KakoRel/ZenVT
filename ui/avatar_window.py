"""
Прозрачное окно с аватаром — ТОЛЬКО для OBS захвата.
Рисует спрайт через paintEvent — никаких margin, никаких искажений.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PIL.ImageQt import ImageQt

from core.config import config
from core.effects import EffectManager, AvatarState
from core.sprite_manager import SpriteManager


class AvatarWindow(QWidget):
    """Отдельное прозрачное окно для OBS захвата."""

    def __init__(self):
        super().__init__()
        self._running = False
        self._setup_window()

        self.sprite_manager = SpriteManager()
        self.effect_manager = EffectManager()

        self.fps = config.get("avatar", "fps")
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_frame)
        self.update_timer.setInterval(int(1000 / self.fps))

        self._running = False
        self._current_sprite = None
        self._show_placeholder = True

    def _setup_window(self):
        w = config.get("avatar", "width")
        h = config.get("avatar", "height")
        self.resize(w, h)

        x = config.get("avatar", "position_x")
        y = config.get("avatar", "position_y")
        self.move(x, y)

        self.setWindowTitle(config.get("obs", "window_title"))
        self.update_flags()

    def update_flags(self):
        flags = Qt.WindowType.FramelessWindowHint
        if config.get("avatar", "always_on_top"):
            flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        if self._running:
            self.show()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def load_sprites_from_config(self):
        import os
        sprites = config.get("sprites")
        if sprites:
            for key, path in sprites.items():
                if path and os.path.exists(path):
                    self.sprite_manager.load_sprite(key, path)

    def set_talking(self, talking: bool):
        self.effect_manager.set_talking(talking)

    def set_volume(self, volume: float):
        self.effect_manager.set_volume(volume)

    def _update_frame(self):
        """Обновление кадра — только рассчитываем эффекты, перерисовка в paintEvent."""
        self.effect_manager.update(fps=self.fps)

        eyes = self.effect_manager.get_eyes_state()
        mouth = self.effect_manager.get_mouth_open_amount()

        sprite = self.sprite_manager.get_combined_sprite(
            eyes, mouth, size=(self.width(), self.height())
        )

        if sprite:
            qimage = ImageQt(sprite)
            self._current_sprite = QPixmap.fromImage(qimage)
            self._show_placeholder = False
        else:
            self._current_sprite = None
            self._show_placeholder = True

        # Перерисовка
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self._show_placeholder or self._current_sprite is None:
            painter.fillRect(self.rect(), QColor(40, 40, 40, 180))
            painter.setPen(QColor(200, 200, 200))
            font = QFont("Arial", 14)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Загрузите спрайты\nв настройках"
            )
            return

        # Если прозрачный фон отключен (для хромакея в OBS)
        if not config.get("obs", "background_transparency"):
            painter.fillRect(self.rect(), QColor(0, 255, 0, 255))

        # Применяем эффекты через translate
        lev_y = self.effect_manager.get_levitation_offset()
        shake_x, shake_y = self.effect_manager.get_shake_offset()

        painter.translate(shake_x, lev_y + shake_y)

        # Рисуем спрайт в центре окна
        pixmap = self._current_sprite
        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2
        painter.drawPixmap(x, y, pixmap)

    def start(self):
        self.update_timer.start(int(1000 / self.fps))
        self._running = True
        self.show()

    def stop(self):
        self.update_timer.stop()
        self._running = False
        self.hide()

    def is_running(self):
        return self._running

    def update_size(self):
        w = config.get("avatar", "width")
        h = config.get("avatar", "height")
        self.resize(w, h)
        self.fps = config.get("avatar", "fps")
        self.update_timer.setInterval(int(1000 / self.fps))

    def update_position(self):
        x = config.get("avatar", "position_x")
        y = config.get("avatar", "position_y")
        self.move(x, y)
