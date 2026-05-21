import asyncio
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(__file__))

# Импортируем и запускаем main
from main import main

if __name__ == "__main__":
    asyncio.run(main())