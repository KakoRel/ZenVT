import os
import sys
import subprocess
import shutil

def build():
    print("=== Начало процесса сборки ZenVT ===")
    
    # Пакеты, которые нужно включить целиком
    collect_packages = [
        "sounddevice",
        "numpy",
        "PyQt6"
    ]
    
    # Базовая команда
    cmd = [
        "pyinstaller",
        "--noconsole",          # Без окна консоли
        "--onedir",             # В папку (как просил пользователь)
        "--name=ZenVT",         # Имя .exe файла
        "--clean",              # Очистка кэша
    ]
    
    # Добавление данных (папки и файлы)
    # Формат: "путь_источник;путь_назначение" (в Windows точка с запятой)
    cmd.extend(["--add-data", "assets;assets"])
    
    # Полный сбор проблемных библиотек
    for pkg in collect_packages:
        cmd.extend(["--collect-all", pkg])
    
    # Точка входа
    cmd.append("main.py")
    
    print(f"Выполняю команду: {' '.join(cmd)}")
    
    try:
        # Проверка наличия pyinstaller
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
        
        # Запуск сборки
        subprocess.run(cmd, check=True)
        
        print("\n=== Сборка завершена успешно! ===")
        print(f"Готовое приложение находится в папке: {os.path.join(os.getcwd(), 'dist', 'ZenVT')}")
        
    except FileNotFoundError:
        print("\n[!] Ошибка: PyInstaller не установлен.")
        print("Запустите: pip install pyinstaller")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Ошибка при сборке: {e}")

if __name__ == "__main__":
    build()
