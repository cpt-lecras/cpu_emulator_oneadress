# cpu/exceptions.py

class CpuError(Exception):
    """Базовое исключение эмулятора."""


class MemoryOutOfRange(CpuError):
    """Обращение к несуществующей ячейке памяти."""


class InvalidOpcode(CpuError):
    """Неверный код операции."""


class DecodeError(CpuError):
    """Ошибка декодирования команды."""
