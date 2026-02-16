# ========== EMOJI ДЛЯ ДИЗАЙНА (БЕЗ ЦВЕТНЫХ КРУГОВ) ==========
class Emoji:
    # Основные
    TARGET = "🎯"
    BOMB = "💣"
    SKULL = "💀"
    CROWN = "👑"
    STAR = "⭐️"
    FIRE = "🔥"
    DIAMOND = "💎"
    MONEY = "💰"
    CHART = "📊"
    ROBOT = "🤖"
    GIFT = "🎁"
    LOCK = "🔒"
    UNLOCK = "🔓"
    
    # Флаги стран
    RU = "🇷🇺"
    UA = "🇺🇦"
    KZ = "🇰🇿"
    UZ = "🇺🇿"
    US = "🇺🇸"
    TJ = "🇹🇯"
    
    # Действия
    CHECK = "✅"
    CROSS = "❌"
    WARN = "⚠️"
    INFO = "ℹ️"
    BACK = "◀️"
    FORWARD = "▶️"
    UP = "⬆️"
    DOWN = "⬇️"
    
    # Статусы
    ACTIVE = "✅"
    PENDING = "⏳"
    COMPLETED = "✅"
    FAILED = "❌"
    ERROR = "🚫"

# ========== ПРОГРЕСС-БАР ==========
def loading_bar(percent: int, width: int = 10) -> str:
    """Создает прогресс-бар"""
    filled = "█" * (percent // 10)
    empty = "▒" * (width - (percent // 10))
    return f"[{filled}{empty}] {percent}%"