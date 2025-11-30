from dataclasses import dataclass, field
from typing import List, Dict

# Размер машинного слова для данных (в битах)
WORD_BITS = 32
WORD_MASK = (1 << WORD_BITS) - 1   # 0xFFFFFFFF для 32 бит


@dataclass
class Registers:
    """
    Регистрный файл процессора.

    Специальные регистры:
        ACC  – аккумулятор (основной регистр для ALU)
        PC   – счётчик команд
        IR   – регистр команды (instruction register)
        MAR  – регистр адреса памяти (memory address register)
        MDR  – регистр данных памяти (memory data register)

    Регистры общего назначения:
        GPR[0..3] – R0..R3 (по 32 бита)
    """

    ACC: int = 0
    PC: int = 0
    IR: int = 0
    MAR: int = 0
    MDR: int = 0

    # 4 регистра общего назначения по умолчанию
    GPR: List[int] = field(default_factory=lambda: [0] * 4)

    def reset(self) -> None:
        """
        Сброс всех регистров в 0.
        """
        self.ACC = 0
        self.PC = 0
        self.IR = 0
        self.MAR = 0
        self.MDR = 0
        for i in range(len(self.GPR)):
            self.GPR[i] = 0

    # -------- Работа с регистрами общего назначения -------- #

    def read_gpr(self, index: int) -> int:
        """
        Прочитать значение регистра общего назначения R[index].
        Результат обрезается до WORD_BITS.
        """
        self._validate_gpr_index(index)
        return self.GPR[index] & WORD_MASK

    def write_gpr(self, index: int, value: int) -> None:
        """
        Записать значение в регистр общего назначения R[index].
        Значение обрезается до WORD_BITS.
        """
        self._validate_gpr_index(index)
        self.GPR[index] = value & WORD_MASK

    @staticmethod
    def _validate_gpr_index(index: int) -> None:
        if not 0 <= index < 4:
            raise IndexError(f"Регистра R{index} не существует (доступны R0..R3)")

    # Удобные псевдонимы-свойства для R0..R3

    @property
    def R0(self) -> int:
        return self.read_gpr(0)

    @R0.setter
    def R0(self, value: int) -> None:
        self.write_gpr(0, value)

    @property
    def R1(self) -> int:
        return self.read_gpr(1)

    @R1.setter
    def R1(self, value: int) -> None:
        self.write_gpr(1, value)

    @property
    def R2(self) -> int:
        return self.read_gpr(2)

    @R2.setter
    def R2(self, value: int) -> None:
        self.write_gpr(2, value)

    @property
    def R3(self) -> int:
        return self.read_gpr(3)

    @R3.setter
    def R3(self, value: int) -> None:
        self.write_gpr(3, value)

    # -------- Вспомогательные методы -------- #

    def snapshot(self) -> Dict[str, int]:
        """
        Вернуть словарь со значениями всех регистров.
        Удобно для логирования или отображения в GUI.
        """
        data = {
            "ACC": self.ACC & WORD_MASK,
            "PC": self.PC,
            "IR": self.IR,
            "MAR": self.MAR,
            "MDR": self.MDR,
        }
        for i, value in enumerate(self.GPR):
            data[f"R{i}"] = value & WORD_MASK
        return data

    def __repr__(self) -> str:
        regs = self.snapshot()
        parts = [f"{name}={value:#010x}" if name.startswith("R") or name == "ACC"
                 else f"{name}={value}"
                 for name, value in regs.items()]
        return "Registers(" + ", ".join(parts) + ")"
