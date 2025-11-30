from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from cpu.memory import Memory
from cpu.cpu import CPU
from cpu.assembler import Assembler, AssembledProgram


@dataclass
class LoadedProgram:
    """
    Результат загрузки программы в память.

    assembled   – результат ассемблирования (машинный код + метки)
    entry_point – адрес, с которого будет стартовать CPU (PC)
    code_base   – базовый адрес размещения кода в памяти
    """
    assembled: AssembledProgram
    entry_point: int
    code_base: int


class ProgramLoader:
    """
    Загрузчик программ в память процессора.

    Базовый сценарий:
        1) assembler.assemble(...)
        2) memory.load_words(base_addr, code_words, as_instructions=True)
        3) cpu.reset()
        4) cpu.registers.PC = entry_point
    """

    def __init__(self, memory: Memory) -> None:
        self.memory = memory
        self.assembler = Assembler()

    # ---------- Публичный интерфейс ---------- #

    def load_from_source(
        self,
        source: str,
        code_base: int = 0,
        clear_memory: bool = True,
    ) -> LoadedProgram:
        """
        Ассемблировать исходный текст и загрузить программу в память.

        :param source: текст программы на ассемблере (строка с переводами строк)
        :param code_base: базовый адрес кода в памяти
        :param clear_memory: обнулять ли память перед загрузкой
        """
        if clear_memory:
            self.memory.clear()

        assembled = self.assembler.assemble_from_string(source)

        # Загрузим машинные слова в память, начиная с code_base
        self.memory.load_words(code_base, assembled.code_words, as_instructions=True)

        # Точка входа:
        # если есть метка "start" или "START", используем её,
        # иначе – стартуем с code_base.
        labels = assembled.labels
        entry_point = code_base
        for candidate in ("start", "START", "main", "MAIN"):
            if candidate in labels:
                entry_point = code_base + labels[candidate]
                break

        return LoadedProgram(
            assembled=assembled,
            entry_point=entry_point,
            code_base=code_base,
        )

    def create_cpu(self, loaded_program: LoadedProgram) -> CPU:
        """
        Создать CPU, сбросить его и установить PC на entry_point.
        """
        cpu = CPU(self.memory)
        cpu.reset(clear_memory=False)  # память уже загружена
        cpu.registers.PC = loaded_program.entry_point
        return cpu
