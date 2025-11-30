from dataclasses import dataclass, field
from typing import List, Iterable

# Разрядность машинного слова для ДАННЫХ
DATA_WORD_BITS = 32
DATA_WORD_MASK = (1 << DATA_WORD_BITS) - 1  # 0xFFFFFFFF для 32 бит

# Разрядность машинного слова для ИНСТРУКЦИЙ
INSTR_WORD_BITS = 16
INSTR_WORD_MASK = (1 << INSTR_WORD_BITS) - 1  # 0xFFFF для 16 бит


@dataclass
class Memory:
    """
    Модель оперативной памяти процессора (архитектура фон Неймана).

    Память представлена как массив "слов".
    В этой учебной модели мы используем ОДНУ общую память для:
        - инструкций (16 бит)
        - данных (32 бита)

    Адресация — по словам (0..size-1).
    """

    size: int = 1024  # по умолчанию 1024 слова памяти
    _cells: List[int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._cells = [0] * self.size

    # -------- Вспомогательные методы -------- #

    def _check_address(self, address: int) -> None:
        if not 0 <= address < self.size:
            raise IndexError(f"Адрес {address} вне диапазона памяти (0..{self.size - 1})")

    # -------- Операции чтения/записи -------- #

    def read_word(self, address: int) -> int:
        """
        Прочитать слово из памяти по адресу.

        Для данных будем считать, что вызывающая сторона сама решает,
        интерпретировать ли это как 16- или 32-битное значение.
        """
        self._check_address(address)
        return self._cells[address]

    def write_word(self, address: int, value: int, is_instruction: bool = False) -> None:
        """
        Записать слово в память по адресу.

        :param address: адрес слова
        :param value: записываемое значение
        :param is_instruction: если True — значение обрежется до 16 бит,
                               иначе до 32 бит (для данных).
        """
        self._check_address(address)

        if is_instruction:
            value &= INSTR_WORD_MASK
        else:
            value &= DATA_WORD_MASK

        self._cells[address] = value

    # -------- Сервисные методы -------- #

    def clear(self) -> None:
        """
        Обнулить всю память.
        """
        for i in range(self.size):
            self._cells[i] = 0

    def load_words(self, start_address: int, words: Iterable[int], as_instructions: bool = False) -> None:
        """
        Загрузить последовательность слов в память, начиная с указанного адреса.

        :param start_address: начальный адрес
        :param words: итерируемая последовательность целых чисел
        :param as_instructions: трактовать ли слова как инструкции (16 бит)
        """
        addr = start_address
        for word in words:
            self.write_word(addr, word, is_instruction=as_instructions)
            addr += 1

    def dump(self, start: int = 0, end: int | None = None) -> List[int]:
        """
        Вернуть срез памяти в виде списка значений [start, end).

        Удобно для отладки или отображения в GUI/логах.
        """
        if end is None:
            end = self.size
        if start < 0 or end > self.size or start > end:
            raise ValueError(f"Некорректный диапазон dump: start={start}, end={end}")
        return self._cells[start:end]
