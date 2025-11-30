from dataclasses import dataclass

from cpu.flags import Flags, WORD_BITS, WORD_MASK, SIGN_BIT


def _to_signed(value: int) -> int:
    """
    Преобразовать 32-битное беззнаковое значение в знаковое (двойное доп. кодирование).
    """
    value &= WORD_MASK
    if value & SIGN_BIT:
        return value - (1 << WORD_BITS)
    return value


@dataclass
class ALU:
    """
    Арифметико-логическое устройство.

    Работает с 32-битными словами (см. WORD_BITS/WORD_MASK в flags.py)
    и обновляет флаги после каждой операции.
    """

    flags: Flags

    # ---------- Арифметические операции ---------- #

    def add(self, a: int, b: int) -> int:
        """
        Сложение двух 32-битных чисел: a + b.

        Возвращает результат (обрезанный до 32 бит) и обновляет флаги:
            Z, N, C, V.
        """
        a &= WORD_MASK
        b &= WORD_MASK

        full = a + b                    # "широкий" результат
        result = full & WORD_MASK       # обрежем до 32 бит

        # Carry: был ли перенос за предел 32 бит
        carry = (full >> WORD_BITS) != 0

        # Overflow: знаковое переполнение
        sa = _to_signed(a)
        sb = _to_signed(b)
        sr = _to_signed(result)

        overflow = (sa >= 0 and sb >= 0 and sr < 0) or \
                   (sa < 0 and sb < 0 and sr >= 0)

        self.flags.update_from_result(result, carry=carry, overflow=overflow)
        return result

    def sub(self, a: int, b: int) -> int:
        """
        Вычитание двух 32-битных чисел: a - b.

        Возвращает результат (обрезанный до 32 бит) и обновляет флаги:
            Z, N, C, V.

        Для беззнаковой арифметики:
            C = 1, если произошёл займ (a < b).
        """
        a &= WORD_MASK
        b &= WORD_MASK

        full = a - b
        result = full & WORD_MASK

        # Carry здесь трактуем как "заём": если a < b, то пришлось занимать
        carry = a < b

        sa = _to_signed(a)
        sb = _to_signed(b)
        sr = _to_signed(result)

        # Формула знакового переполнения для вычитания:
        # если знаки a и b разные, и знак результата отличается от знака a.
        overflow = (sa >= 0 and sb < 0 and sr < 0) or \
                   (sa < 0 and sb >= 0 and sr >= 0)

        self.flags.update_from_result(result, carry=carry, overflow=overflow)
        return result

    def mul(self, a: int, b: int) -> int:
        """
        Умножение двух 32-битных чисел: a * b.

        В этой учебной модели мы берём только младшие 32 бита результата.
        Флаг C считаем установленным, если старшие биты были отброшены.
        Флаг V можно приравнять к C (т.е. считаем переполнением).
        """
        a &= WORD_MASK
        b &= WORD_MASK

        full = a * b
        result = full & WORD_MASK

        # если что-то "вылезло" за 32 бита, считаем это переносом/переполнением
        carry = (full >> WORD_BITS) != 0
        overflow = carry

        self.flags.update_from_result(result, carry=carry, overflow=overflow)
        return result

    def neg(self, a: int) -> int:
        """
        Унарный минус: -a (в 32-битном диапазоне).
        """
        a &= WORD_MASK
        result = (-_to_signed(a)) & WORD_MASK

        # Можно рассматривать как 0 - a
        sa = 0
        sb = _to_signed(a)
        sr = _to_signed(result)

        carry = False  # в этой простой модели можно не вычислять явно
        overflow = (sa >= 0 and sb < 0 and sr < 0) or \
                   (sa < 0 and sb >= 0 and sr >= 0)

        self.flags.update_from_result(result, carry=carry, overflow=overflow)
        return result

    # ---------- Операция сравнения ---------- #

    def cmp(self, a: int, b: int) -> None:
        """
        Сравнение a и b.

        По сути выполняем a - b, но результат никуда не записываем,
        нас интересуют только флаги (Z, N, C, V).
        """
        _ = self.sub(a, b)  # sub уже обновит флаги

    # ---------- Логические операции (на будущее) ---------- #

    def bit_and(self, a: int, b: int) -> int:
        result = (a & b) & WORD_MASK
        # для логических операций C/V обычно сбрасывают
        self.flags.update_from_result(result, carry=False, overflow=False)
        return result

    def bit_or(self, a: int, b: int) -> int:
        result = (a | b) & WORD_MASK
        self.flags.update_from_result(result, carry=False, overflow=False)
        return result

    def bit_xor(self, a: int, b: int) -> int:
        result = (a ^ b) & WORD_MASK
        self.flags.update_from_result(result, carry=False, overflow=False)
        return result
