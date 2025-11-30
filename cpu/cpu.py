from __future__ import annotations

from dataclasses import dataclass

from cpu.flags import Flags
from cpu.registers import Registers, WORD_MASK
from cpu.memory import Memory
from cpu.alu import ALU
from cpu.decoder import Decoder, Instruction, AddressingMode


@dataclass
class CPU:
    """
    Центральное устройство: связывает память, регистры, АЛУ и декодер.

    Основной цикл:
        fetch  -> decode -> execute
    """

    memory: Memory
    registers: Registers = None
    flags: Flags = None
    alu: ALU = None
    decoder: Decoder = None

    halted: bool = False  # признак остановки (HALT)

    def __post_init__(self) -> None:
        # Инициализируем компоненты, если не переданы извне
        if self.registers is None:
            self.registers = Registers()
        if self.flags is None:
            self.flags = Flags()
        if self.alu is None:
            self.alu = ALU(self.flags)
        if self.decoder is None:
            self.decoder = Decoder()

    # ---------- Управление состоянием ---------- #

    def reset(self, clear_memory: bool = False) -> None:
        """
        Сброс процессора в начальное состояние.

        :param clear_memory: если True, обнуляет также память.
        """
        self.registers.reset()
        self.flags.reset()
        self.halted = False

        # Стартуем с адреса 0
        self.registers.PC = 0

        if clear_memory:
            self.memory.clear()

    # ---------- Цикл выборки/декодирования ---------- #

    def fetch(self) -> int:
        """
        Выборка (fetch) следующей команды из памяти.

        Читает слово по адресу PC, кладёт его в IR и увеличивает PC.
        """
        pc = self.registers.PC
        word = self.memory.read_word(pc)
        self.registers.IR = word & 0xFFFF  # регистр команды 16 бит
        self.registers.PC = (pc + 1) & 0xFFFF  # ограничим PC разумным диапазоном
        return self.registers.IR

    def decode(self, word: int) -> Instruction:
        """
        Декодировать слово в структуру Instruction.
        """
        return self.decoder.decode(word)

    # ---------- Работа с операндами ---------- #

    def _sign_extend_10bit(self, value: int) -> int:
        """
        Знаковое расширение 10-битного значения до 32 бит.
        Нужно для непосредственных операндов (IMMEDIATE).
        """
        value &= 0x3FF  # 10 бит
        sign_bit = 1 << 9
        if value & sign_bit:
            # отрицательное число
            return value - (1 << 10)
        return value

    def _read_operand(self, instr: Instruction) -> int:
        """
        Прочитать значение операнда в зависимости от режима адресации.
        """
        mode = instr.mode
        op = instr.operand

        if mode == AddressingMode.IMMEDIATE:
            # непосредственное значение (знаковое)
            return self._sign_extend_10bit(op) & WORD_MASK

        elif mode == AddressingMode.DIRECT:
            # прямой адрес памяти
            addr = op
            return self.memory.read_word(addr) & WORD_MASK

        elif mode == AddressingMode.REGISTER:
            # регистр Rn — берём младшие 2 бита операнда как номер регистра
            reg_index = op & 0b11
            return self.registers.read_gpr(reg_index)

        elif mode == AddressingMode.INDIRECT:
            # косвенная регистровая: [Rn]
            reg_index = op & 0b11
            addr = self.registers.read_gpr(reg_index)
            return self.memory.read_word(addr) & WORD_MASK

        else:
            raise ValueError(f"Неизвестный режим адресации: {mode}")

    def _write_operand(self, instr: Instruction, value: int) -> None:
        """
        Записать value в операнд (используется, например, в STORE).

        IMMEDIATE здесь не имеет смысла (нельзя записать "в константу").
        """
        mode = instr.mode
        op = instr.operand
        value &= WORD_MASK

        if mode == AddressingMode.IMMEDIATE:
            raise ValueError("Нельзя записывать в непосредственный операнд (IMMEDIATE)")

        elif mode == AddressingMode.DIRECT:
            addr = op
            self.memory.write_word(addr, value, is_instruction=False)

        elif mode == AddressingMode.REGISTER:
            reg_index = op & 0b11
            self.registers.write_gpr(reg_index, value)

        elif mode == AddressingMode.INDIRECT:
            reg_index = op & 0b11
            addr = self.registers.read_gpr(reg_index)
            self.memory.write_word(addr, value, is_instruction=False)

        else:
            raise ValueError(f"Неизвестный режим адресации: {mode}")

    # ---------- Исполнение команды ---------- #

    def execute(self, instr: Instruction) -> None:
        """
        Выполнить одну инструкцию.
        """
        mnem = instr.mnemonic

        # Если команда неизвестна (opcode не из таблицы)
        if mnem is None:
            raise ValueError(f"Неизвестный opcode: {instr.opcode}")

        # --- Команды без операндов --- #
        if mnem == "NOP":
            return

        if mnem == "HALT":
            self.halted = True
            return

        # --- Команды с операндами --- #
        # Для большинства команд сначала читаем значение
        if mnem in {"LOAD", "STORE", "ADD", "SUB", "MUL", "INC", "DEC", "CMP",
                    "JMP", "JZ", "JNZ", "JG", "JL"}:
            value = self._read_operand(instr)

        # Арифметика и пересылка
        if mnem == "LOAD":
            # ACC = operand
            self.registers.ACC = value & WORD_MASK
            # флаги можно обновлять или нет; разумно обновить:
            self.alu.flags.update_from_result(self.registers.ACC)

        elif mnem == "STORE":
            # operand = ACC
            self._write_operand(instr, self.registers.ACC)

        elif mnem == "ADD":
            self.registers.ACC = self.alu.add(self.registers.ACC, value)

        elif mnem == "SUB":
            self.registers.ACC = self.alu.sub(self.registers.ACC, value)

        elif mnem == "MUL":
            self.registers.ACC = self.alu.mul(self.registers.ACC, value)

        elif mnem == "INC":
            # игнорируем прочитанное value, инкрементируем ACC
            self.registers.ACC = self.alu.add(self.registers.ACC, 1)

        elif mnem == "DEC":
            self.registers.ACC = self.alu.sub(self.registers.ACC, 1)

        elif mnem == "CMP":
            # сравниваем ACC и операнд, ACC не меняем, только флаги
            self.alu.cmp(self.registers.ACC, value)

        # Переходы
        elif mnem in {"JMP", "JZ", "JNZ", "JG", "JL"}:
            do_jump = False

            if mnem == "JMP":
                do_jump = True
            elif mnem == "JZ":
                do_jump = self.flags.Z
            elif mnem == "JNZ":
                do_jump = not self.flags.Z
            elif mnem == "JG":
                # "больше нуля" для знаковых чисел: Z=0 и N=0
                do_jump = (not self.flags.Z) and (not self.flags.N)
            elif mnem == "JL":
                # "меньше нуля": N=1
                do_jump = self.flags.N

            if do_jump:
                # В простом варианте считаем, что value — уже целевой адрес
                # (т.е. JUMP #addr или JUMP @addr, где в памяти лежит адрес)
                # Для начала будем использовать только IMMEDIATE: JUMP #10
                target = value
                # Ограничим PC разумным диапазоном
                self.registers.PC = target & 0xFFFF

        else:
            # если команда не обработана выше
            raise ValueError(f"Команда пока не реализована: {mnem}")

    # ---------- Высокоуровневые методы ---------- #

    def step(self) -> None:
        """
        Выполнить один цикл: fetch -> decode -> execute.

        Если CPU уже остановлен (HALT), ничего не делает.
        """
        if self.halted:
            return

        word = self.fetch()
        instr = self.decode(word)
        self.execute(instr)

    def run(self, max_steps: int | None = None) -> None:
        """
        Выполнять программу, пока не встретится HALT или не будет достигнут
        лимит по количеству шагов (чтобы избежать бесконечного цикла).

        :param max_steps: максимальное число шагов (если None – без лимита).
        """
        steps = 0
        while not self.halted:
            self.step()
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break

    def snapshot(self) -> dict:
        """
        Вернуть "снимок" состояния CPU: регистры + флаги.
        Удобно для отладки/GUI.
        """
        snap = self.registers.snapshot()
        snap.update({
            "FLAGS": repr(self.flags),
            "HALTED": self.halted,
        })
        return snap
