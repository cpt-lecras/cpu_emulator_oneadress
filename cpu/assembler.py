from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

from cpu.decoder import Decoder, AddressingMode


@dataclass
class AssembledProgram:
    """
    Результат работы ассемблера.

    code_words  – список машинных слов (16 бит), готовых для загрузки в память.
    labels      – таблица меток: имя -> адрес (номер инструкции).
    """
    code_words: List[int]
    labels: Dict[str, int]


class Assembler:
    """
    Простой двухпроходный ассемблер для нашего одноадресного процессора.

    Поддерживаемый синтаксис строк:

        [LABEL:] MNEMONIC [OPERAND] [; comment]

    Операнды:

        #N        – непосредственное значение (IMMEDIATE)
        @N        – прямая адресация памяти (DIRECT)
        @LABEL    – прямая адресация по метке (DIRECT)
        R0..R3    – регистровая адресация (REGISTER)
        [R0]..[R3]– косвенно-регистровая ([REGISTER] -> INDIRECT)
        LABEL     – адрес метки как непосредственное значение (IMMEDIATE),
                    удобно для команд перехода: JZ loop

    Комментарии: всё после ; игнорируется.
    """

    def __init__(self) -> None:
        self.decoder = Decoder()

    # ---------- Публичный интерфейс ---------- #

    def assemble_from_string(self, source: str) -> AssembledProgram:
        """
        Ассемблировать исходный код, переданный одной строкой с переносами.
        """
        lines = source.splitlines()
        return self.assemble(lines)

    def assemble(self, lines: List[str]) -> AssembledProgram:
        """
        Ассемблировать список строк ассемблерного кода.
        """
        # 1. Первый проход: собираем таблицу меток
        labels = self._first_pass_collect_labels(lines)

        # 2. Второй проход: генерируем машинный код
        code_words: List[int] = []
        for line_no, line in enumerate(lines, start=1):
            stripped, _, _ = self._strip_comment(line)
            if not stripped:
                continue

            label, rest = self._split_label(stripped)
            if not rest:
                # строка содержала только метку (LABEL:) — инструкции нет
                continue

            mnemonic, operand_text = self._parse_instruction(rest, line_no)
            if mnemonic is None:
                # пустая после метки/комментария — пропускаем
                continue

            mode, operand_value = self._parse_operand(operand_text, labels, line_no)

            word = self.decoder.encode(mnemonic, mode, operand_value)
            code_words.append(word)

        return AssembledProgram(code_words=code_words, labels=labels)

    # ---------- Первый проход: метки ---------- #

    def _first_pass_collect_labels(self, lines: List[str]) -> Dict[str, int]:
        """
        Первый проход: определяем адрес каждой метки (LABEL:).
        Адрес = порядковый номер инструкции (0, 1, 2, ...).
        """
        labels: Dict[str, int] = {}
        current_address = 0

        for line_no, line in enumerate(lines, start=1):
            stripped, _, _ = self._strip_comment(line)
            if not stripped:
                continue

            label, rest = self._split_label(stripped)
            if label is not None:
                if label in labels:
                    raise ValueError(f"Повторное определение метки '{label}' в строке {line_no}")
                labels[label] = current_address

            if rest:
                # есть часть после метки — предполагаем, что это инструкция
                mnemonic, _ = self._parse_instruction(rest, line_no)
                if mnemonic is not None:
                    current_address += 1

        return labels

    # ---------- Вспомогательные парсеры ---------- #

    def _strip_comment(self, line: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Убрать комментарий, вернуть:
            (строка_без_комментария, разделитель, комментарий_или_None)
        """
        if ";" in line:
            code, comment = line.split(";", 1)
            return code.strip(), ";", comment
        return line.strip(), None, None

    def _split_label(self, line: str) -> Tuple[Optional[str], str]:
        """
        Разделить строку на метку и остаток.

        Примеры:
            "loop: LOAD #1" -> ("loop", "LOAD #1")
            "start:"        -> ("start", "")
            "LOAD #1"       -> (None, "LOAD #1")
        """
        if ":" in line:
            label_part, rest = line.split(":", 1)
            label = label_part.strip()
            return (label if label else None), rest.strip()
        return None, line.strip()

    def _parse_instruction(self, text: str, line_no: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Разобрать часть строки как инструкцию: MNEMONIC [OPERAND]

        Возвращает: (mnemonic_or_None, operand_text_or_None)
        """
        if not text:
            return None, None

        parts = text.split()
        if not parts:
            return None, None

        mnemonic = parts[0].upper()
        operand_text = None

        if len(parts) > 1:
            # всё, что после мнемоники, считаем операндом (без запятой)
            operand_text = " ".join(parts[1:]).replace(",", "").strip()

        # проверим, что такая команда существует
        if mnemonic not in self.decoder.mnemonic_to_opcode:
            raise ValueError(f"Неизвестная команда '{mnemonic}' в строке {line_no}")

        return mnemonic, operand_text

    def _parse_operand(
        self,
        text: Optional[str],
        labels: Dict[str, int],
        line_no: int
    ) -> Tuple[AddressingMode, int]:
        """
        Разобрать операнд и вернуть (режим_адресации, значение_операнда).

        Если у инструкции нет операнда (text is None), считаем:
            - режим IMMEDIATE, значение 0.
        """
        if text is None or text == "":
            # часть команд у нас вообще без операндов (NOP, HALT)
            return AddressingMode.IMMEDIATE, 0

        t = text.strip()

        # 1) Непосредственное значение: #N
        if t.startswith("#"):
            num_str = t[1:]
            try:
                value = int(num_str, 0)  # поддержим 10, 0x10, 0b1010 и т.п.
            except ValueError:
                raise ValueError(f"Некорректное непосредственное значение '{t}' в строке {line_no}")

            # Проверим диапазон 10-битного знакового числа (-512..511)
            if not -512 <= value <= 511:
                raise ValueError(
                    f"Непосредственное значение {value} вне диапазона -512..511 "
                    f"в строке {line_no}"
                )
            # В операнд кладём просто значение, декодер его не трогает,
            # а CPU при чтении сделает sign-extend.
            # Здесь можно оставить как есть: CPU потом обрежет до 10 бит.
            return AddressingMode.IMMEDIATE, value & 0x3FF

        # 2) Прямая адресация: @N или @LABEL
        if t.startswith("@"):
            target = t[1:].strip()
            # сначала попробуем как число
            try:
                addr = int(target, 0)
            except ValueError:
                # не число — считаем, что это метка
                if target not in labels:
                    raise ValueError(f"Неизвестная метка '{target}' в строке {line_no}")
                addr = labels[target]

            if not (0 <= addr <= 0x3FF):
                raise ValueError(
                    f"Адрес {addr} вне диапазона 0..1023 (10 бит) в строке {line_no}"
                )
            return AddressingMode.DIRECT, addr

        # 3) Регистровая адресация: R0..R3
        if t.upper() in {"R0", "R1", "R2", "R3"}:
            reg_index = int(t[1])
            return AddressingMode.REGISTER, reg_index  # поместим номер регистра в operand

        # 4) Косвенная регистровая: [R0]..[R3]
        if t.startswith("[") and t.endswith("]"):
            inner = t[1:-1].strip().upper()
            if inner in {"R0", "R1", "R2", "R3"}:
                reg_index = int(inner[1])
                return AddressingMode.INDIRECT, reg_index
            else:
                raise ValueError(
                    f"Некорректная косвенная адресация '{t}' в строке {line_no} "
                    f"(ожидалось [R0]..[R3])"
                )

        # 5) Просто LABEL: будем рассматривать как IMMEDIATE-операнд,
        #    содержащий адрес этой метки. Удобно для переходов: JZ loop
        if t in labels:
            addr = labels[t]
            if not (0 <= addr <= 0x3FF):
                raise ValueError(
                    f"Адрес метки {addr} вне диапазона 0..1023 в строке {line_no}"
                )
            return AddressingMode.IMMEDIATE, addr

        # Если сюда дошли — операнд не распознан
        raise ValueError(f"Не удалось распарсить операнд '{t}' в строке {line_no}")
