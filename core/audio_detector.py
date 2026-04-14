"""
Модуль обнаружения речи - анализ аудио с микрофона.
Использует sounddevice. Все callback-и вызываются через queue для безопасности потоков.
"""
import sounddevice as sd
import numpy as np
import time
import queue
from core.config import config


class AudioDetector:
    """
    Обнаружение речи через анализ громкости и pitch.
    Callback-и вызываются безопасно через очередь.
    """

    def __init__(self):
        self._stream = None
        self._running = False

        # Callback-и
        self.on_talk_start = None
        self.on_talk_end = None
        self.on_volume_change = None  # volume: 0.0 - 1.0

        # Очередь событий для безопасного вызова из GUI потока
        self._event_queue = queue.Queue()

        # Состояние
        self._is_talking = False
        self._silence_timer = 0.0
        self._last_silence_check = 0.0

        # Параметры
        self._sensitivity = config.get("audio", "sensitivity") / 100.0
        self._silence_delay = config.get("audio", "silence_delay")
        self._pitch_detection = config.get("audio", "pitch_detection")

        # RMS smoothing
        self._smoothed_volume = 0.0
        self._smoothing_factor = 0.3

        # Для дебага
        self._debug_counter = 0
        self._last_debug_print = 0

    def _calculate_rms(self, data):
        rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))
        return min(rms, 1.0)

    def _detect_pitch(self, data):
        if not self._pitch_detection:
            return 0.0

        audio_data = data.flatten()
        if len(audio_data) < 256:
            return 0.0

        audio_data -= np.mean(audio_data)
        std = np.std(audio_data)
        if std < 1e-6:
            return 0.0
        audio_data /= std

        n = len(audio_data)
        max_lag = min(n // 2, 2000)

        correlations = np.correlate(audio_data, audio_data, mode='full')
        correlations = correlations[n - 1:n - 1 + max_lag]

        if correlations[0] > 1e-6:
            correlations /= correlations[0]

        threshold = 0.3
        for i in range(20, len(correlations)):
            if correlations[i] > threshold:
                return correlations[i]

        return 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback из аудио-потока. Только расчёты, никаких внешних вызовов."""
        if status:
            print(f"[AudioDetector] Status: {status}")

        rms = self._calculate_rms(indata)

        # Сглаживание
        self._smoothed_volume = (
            self._smoothing_factor * rms +
            (1 - self._smoothing_factor) * self._smoothed_volume
        )

        volume = self._smoothed_volume

        # Pitch
        pitch_strength = self._detect_pitch(indata)

        # Порог
        talking_threshold = self._sensitivity
        if self._pitch_detection and pitch_strength > 0.3:
            talking_threshold *= 0.6

        is_currently_talking = volume > talking_threshold

        # Логика тишины
        now = time.time()
        if is_currently_talking:
            self._silence_timer = now

        # Дебаг — вывод раз в 2 секунды
        self._debug_counter += 1
        if now - self._last_debug_print > 2.0:
            self._last_debug_print = now
            print(f"[Audio] RMS={rms:.4f} Vol={volume:.4f} Talking={is_currently_talking} "
                  f"Pitch={pitch_strength:.3f} Thresh={talking_threshold:.4f}")

        # Помещаем события в очередь
        if is_currently_talking and not self._is_talking:
            self._is_talking = True
            self._event_queue.put("talk_start")

        if not is_currently_talking and self._is_talking:
            if now - self._silence_timer > self._silence_delay:
                self._is_talking = False
                self._event_queue.put("talk_end")

        self._event_queue.put(("volume", volume))

    def _process_events(self):
        """Обработка очереди событий. Вызывать из GUI потока через QTimer."""
        try:
            while True:
                event = self._event_queue.get_nowait()
                if event == "talk_start":
                    if self.on_talk_start:
                        self.on_talk_start()
                elif event == "talk_end":
                    if self.on_talk_end:
                        self.on_talk_end()
                elif isinstance(event, tuple) and event[0] == "volume":
                    if self.on_volume_change:
                        self.on_volume_change(event[1])
        except queue.Empty:
            pass

    def update_config(self):
        """Динамическое обновление настроек без перезапуска (если возможно)."""
        self._sensitivity = config.get("audio", "sensitivity") / 100.0
        self._silence_delay = config.get("audio", "silence_delay")
        self._pitch_detection = config.get("audio", "pitch_detection")

    def start(self):
        """Запуск обнаружения речи."""
        if self._running:
            return

        self.update_config()

        print(f"[AudioDetector] Чувствительность: {self._sensitivity:.2f}, "
              f"Задержка: {self._silence_delay}")

        try:
            device_idx = None
            config_idx = config.get("audio", "device_index")
            if config_idx is not None and config_idx != -1:
                device_idx = config_idx

            # Покажем список устройств для дебага
            print(f"[AudioDetector] Доступные устройства:")
            for dev in self.get_available_devices():
                default = sd.query_devices(kind='input')
                is_default = dev['index'] == default.get('index', -1)
                print(f"  [{dev['index']}] {dev['name']} {'(default)' if is_default else ''}")

            # Инициализация потока. Если samplerate не указан,
            # sounddevice использует дефолтный для устройства, это избегает ошибок "Invalid sample rate".
            self._stream = sd.InputStream(
                device=device_idx,
                channels=1,
                blocksize=1024,
                callback=self._audio_callback,
                dtype='float32',
            )
            self._stream.start()
            self._running = True

            # Запускаем обработку событий
            from PyQt6.QtCore import QTimer
            self._event_timer = QTimer()
            self._event_timer.timeout.connect(self._process_events)
            self._event_timer.start(50)  # каждые 50ms

            print(f"[AudioDetector] Запущен (устройство: {device_idx if device_idx is not None else 'default'})")
        except Exception as e:
            import traceback
            print(f"[AudioDetector] Ошибка запуска: {e}")
            print(traceback.format_exc())

    def stop(self):
        """Остановка."""
        if not self._running:
            return

        self._running = False

        if hasattr(self, '_event_timer'):
            self._event_timer.stop()

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        print("[AudioDetector] Остановлен")

    def is_talking(self):
        return self._is_talking

    def get_volume(self):
        return self._smoothed_volume

    def get_available_devices(self):
        devices = []
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    devices.append({
                        "index": i,
                        "name": dev['name'],
                        "channels": dev['max_input_channels'],
                        "default_rate": dev['default_samplerate'],
                    })
        except Exception as e:
            print(f"[AudioDetector] Ошибка получения устройств: {e}")
        return devices

    def cleanup(self):
        self.stop()
