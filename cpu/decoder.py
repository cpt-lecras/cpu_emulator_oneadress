from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict


INSTR_WORD_BITS = 16
INSTR_WORD_MASK = (1 << INSTR_WORD_BITS) - 1  # 0xFFFF


# Разбиение 16-битной команды по полям
OPCODE_BITS = 4
MODE_BITS = 2
OPERAND_BITS = 10

# Смещения (сколько бит сдвигать вправо)
OPERAND_SHIFT = 0
MODE_SHIFT = OPERAND_BITS
OPCODE_SHIFT = MODE_SHIFT + MODE_BITS

# Маски полей
OPCODE_MASK = (1 << OPCODE_BITS) - 1   # 0xF
MODE_MASK = (1 << MODE_BITS) - 1       # 0x3
OPERAND_MASK = (1 << OPERAND_BITS) - 1 # 0x3FF


class AddressingMode(IntEnum):
    """
    Режимы адресации операнда в одноадресной команде.
    """
    IMMEDIATE = 0   # #value
    DIRECT = 1      # @addr (прямая адресация памяти)
    REGISTER = 2    # Rn
    INDIRECT = 3    # [Rn]


@dataclass
class Instruction:
    """
    Внутреннее представление команды.

    raw      – 16-битное машинное слово
    opcode   – числовой код операции (0..15)
    mode     – режим адресации (AddressingMode)
    operand  – поле операнда (0..1023)
    mnemonic – текстовая метка операции ("LOAD", "ADD", ...)
    """
    raw: int
    opcode: int
    mode: AddressingMode
    operand: int
    mnemonic: str | None = None

    def __repr__(self) -> str:
        mnem = self.mnemonic or f"OP{self.opcode}"
        return (f"Instruction(raw=0x{self.raw:04X}, "
                f"mnemonic={mnem}, mode={self.mode.name}, operand={self.operand})")


class Decoder:
    """
    Декодер команд.

    Умеет:
        - декодировать 16-битное машинное слово в объект Instruction,
        - кодировать (mnemonic, mode, operand) обратно в машинное слово.
    """

    def __init__(self) -> None:
        # Таблица соответствия: opcode -> mnemonic
        self.opcode_to_mnemonic: Dict[int, str] = {
            0x0: "NOP",
            0x1: "LOAD",
            0x2: "STORE",
            0x3: "ADD",
            0x4: "SUB",
            0x5: "MUL",
            0x6: "INC",
            0x7: "DEC",
            0x8: "CMP",
            0x9: "JMP",
            0xA: "JZ",
            0xB: "JNZ",
            0xC: "JG",
            0xD: "JL",
            0xF: "HALT",
        }

        # Обратная таблица: mnemonic -> opcode
        self.mnemonic_to_opcode: Dict[str, int] = {
            name: code for code, name in self.opcode_to_mnemonic.items()
        }

    # -------- Декодирование -------- #

    def decode(self, word: int) -> Instruction:
        """
        Преобразовать 16-битное машинное слово в объект Instruction.
        """
        word &= INSTR_WORD_MASK

        opcode = (word >> OPCODE_SHIFT) & OPCODE_MASK
        mode_value = (word >> MODE_SHIFT) & MODE_MASK
        operand = (word >> OPERAND_SHIFT) & OPERAND_MASK

        try:
            mode = AddressingMode(mode_value)
        except ValueError:
            raise ValueError(f"Неизвестный режим адресации: {mode_value}")

        mnemonic = self.opcode_to_mnemonic.get(opcode)

        return Instruction(
            raw=word,
            opcode=opcode,
            mode=mode,
            operand=operand,
            mnemonic=mnemonic,
        )

    # -------- Кодирование -------- #

    def encode(self, mnemonic: str, mode: AddressingMode, operand: int) -> int:
        """
        Сформировать 16-битное машинное слово из (mnemonic, mode, operand).

        :param mnemonic: строковая команда ("LOAD", "ADD", "JZ", ...)
        :param mode: режим адресации (AddressingMode)
        :param operand: значение операнда (0..1023)
        """
        mnemonic = mnemonic.upper()
        if mnemonic not in self.mnemonic_to_opcode:
            raise ValueError(f"Неизвестная команда: {mnemonic}")

        opcode = self.mnemonic_to_opcode[mnemonic]
        operand &= OPERAND_MASK

        word = ((opcode & OPCODE_MASK) << OPCODE_SHIFT) | \
               ((int(mode) & MODE_MASK) << MODE_SHIFT) | \
               (operand << OPERAND_SHIFT)

        return word & INSTR_WORD_MASK

    # -------- Вспомогательные методы -------- #

    def is_halt(self, instr: Instruction) -> bool:
        """
        Проверить, является ли команда HALT.
        """
        return instr.mnemonic == "HALT"
