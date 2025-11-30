from dataclasses import dataclass

# Размер "машинного слова" нашего процессора (в битах)
WORD_BITS = 32
WORD_MASK = (1 << WORD_BITS) - 1           # 0xFFFFFFFF для 32 бит
SIGN_BIT = 1 << (WORD_BITS - 1)            # 0x80000000 для 32 бит


@dataclass
class Flags:
    """
    Регистр флагов для процессора.

    Z (Zero)      – результат равен 0
    N (Negative)  – результат отрицательный (старший бит результата = 1)
    C (Carry)     – флаг переноса/заёма (беззнаковая арифметика)
    V (Overflow)  – флаг переполнения (знаковая арифметика)
    """

    Z: bool = False
    N: bool = False
    C: bool = False
    V: bool = False

    def reset(self) -> None:
        """
        Сброс всех флагов.
        """
        self.Z = False
        self.N = False
        self.C = False
        self.V = False

    def update_from_result(self, result: int, carry: bool = False, overflow: bool = False) -> None:
        """
        Обновить флаги по результату операции.

        :param result: результат операции (должен быть уже обрезан до WORD_BITS)
        :param carry:  флаг переноса (C), вычисляется в АЛУ
        :param overflow: флаг переполнения (V), вычисляется в АЛУ
        """
        # гарантируем, что результат в границах машинного слова
        result &= WORD_MASK

        # Zero: результат равен 0
        self.Z = (result == 0)

        # Negative: установлен старший (знаковый) бит
        self.N = bool(result & SIGN_BIT)

        # Остальные флаги приходят "извне" (из АЛУ)
        self.C = carry
        self.V = overflow

    def as_int(self) -> int:
        """
        Закодировать флаги в одно целое число (например, для сохранения состояния).
        Биты:
            bit0 – Z
            bit1 – N
            bit2 – C
            bit3 – V
        """
        value = 0
        value |= int(self.Z) << 0
        value |= int(self.N) << 1
        value |= int(self.C) << 2
        value |= int(self.V) << 3
        return value

    @classmethod
    def from_int(cls, value: int) -> "Flags":
        """
        Восстановить объект Flags из целого числа, созданного as_int().
        """
        return cls(
            Z=bool(value & (1 << 0)),
            N=bool(value & (1 << 1)),
            C=bool(value & (1 << 2)),
            V=bool(value & (1 << 3)),
        )

    def __repr__(self) -> str:
        """
        Удобное текстовое представление флагов, например: Flags(Z=1, N=0, C=0, V=1)
        """
        return f"Flags(Z={int(self.Z)}, N={int(self.N)}, C={int(self.C)}, V={int(self.V)})"
