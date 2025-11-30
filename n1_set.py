from __future__ import annotations

from typing import List, Tuple

from cpu.memory import Memory
from cpu.cpu import CPU
from program_loader import ProgramLoader


# ----- Константы адресов для варианта №1 -----

DATA_BASE = 100      # адрес длины массива и первого элемента
RESULT_ADDR = 200    # адрес, куда пишем сумму
CODE_BASE = 0        # с какого адреса кладём код в память


# ----- Ассемблерная программа: сумма элементов массива -----

SUM_ARRAY_PROGRAM = """
; Задание №1 (одноадресная архитектура, фон Неймана)
; Сумма элементов массива.
;
; Память:
;   @100 - длина массива N
;   @101..@100+N-1 - элементы массива A[i]
;   @200 - сюда запишем результат суммы

start:
    ; R1 = N (длина массива)
    LOAD @100      ; ACC = N
    STORE R1       ; R1 = N

    ; R0 = адрес первого элемента массива (DATA_BASE + 1 = 101)
    LOAD #101
    STORE R0       ; R0 = 101

    ; R2 = 0 (начальная сумма)
    LOAD #0
    STORE R2

; ---------- главный цикл по элементам ----------

loop:
    ; if R1 == 0 -> end
    LOAD R1        ; ACC = R1
    CMP #0         ; сравниваем с 0
    JZ end         ; если Z = 1 (R1 == 0), выходим

    ; ACC = A[i] = [R0]
    LOAD [R0]

    ; ACC = ACC + R2  (прибавляем текущую сумму)
    ADD R2

    ; R2 = новая сумма
    STORE R2

    ; R0 = R0 + 1 (переходим к следующему элементу)
    LOAD R0
    ADD #1
    STORE R0

    ; R1 = R1 - 1 (уменьшаем оставшееся количество)
    LOAD R1
    SUB #1
    STORE R1

    ; переход к началу цикла
    JMP loop

; ---------- завершение программы ----------

end:
    ; итоговая сумма в ACC
    LOAD R2

    ; записываем сумму в память по адресу RESULT_ADDR (200)
    STORE @200

    HALT
"""
# ============================
#      ЗАДАНИЕ №1 — часть 2
#      Свёртка двух массивов
# ============================

CONV_PROGRAM = """
; СВЁРТКА (СКАЛЯРНОЕ ПРОИЗВЕДЕНИЕ) ДВУХ МАССИВОВ
; A: @301..@310
; B: @311..@320
; Результат: @400

start:
    ; R3 = длина массива (10)
    LOAD @300
    STORE R3

    ; R0 = адрес первого элемента A
    LOAD #301
    STORE R0

    ; R1 = адрес первого элемента B
    LOAD #311
    STORE R1

    ; R2 = 0 (начальная сумма)
    LOAD #0
    STORE R2

loop:
    ; Если R3 == 0 -> конец
    LOAD R3
    CMP #0
    JZ end

    ; ACC = A[i]
    LOAD [R0]

    ; ACC = ACC * B[i]
    MUL [R1]

    ; ACC = ACC + R2
    ADD R2

    ; R2 = новая сумма
    STORE R2

    ; R0++ (следующий элемент A)
    LOAD R0
    ADD #1
    STORE R0

    ; R1++ (следующий элемент B)
    LOAD R1
    ADD #1
    STORE R1

    ; R3-- (уменьшаем оставшееся количество)
    LOAD R3
    SUB #1
    STORE R3

    JMP loop

end:
    LOAD R2
    STORE @400
    HALT
"""


# ----- Вспомогательные функции для задания №1 -----


def get_sum_array_program() -> str:
    """
    Вернуть текст ассемблерной программы для суммы массива.
    Удобно, если нужно просто получить исходник.
    """
    return SUM_ARRAY_PROGRAM


def _to_twos_complement_32(value: int) -> int:
    """
    Преобразовать Python int в 32-битное значение в доп. коде.
    (для записи отрицательных чисел в память).
    """
    return value & 0xFFFFFFFF


def _from_twos_complement_32(value: int) -> int:
    """
    Преобразовать 32-битное значение из доп. кода в обычный Python int.
    """
    value &= 0xFFFFFFFF
    if value & 0x80000000:
        return value - (1 << 32)
    return value


def setup_sum_array_memory(
    memory: Memory,
    data: List[int],
    data_base: int = DATA_BASE,
    result_addr: int = RESULT_ADDR,
) -> Tuple[int, int]:
    """
    Инициализировать память для задачи "сумма элементов массива".

    Пишет:
        @data_base      = N (длина массива)
        @data_base+1..  = элементы массива
        @result_addr    = 0 (очищаем ячейку результата)

    :param memory: объект Memory
    :param data: список целых чисел (массив A[i])
    :param data_base: базовый адрес массива (по умолчанию 100)
    :param result_addr: адрес результата (по умолчанию 200)
    :return: (data_base, result_addr) — на всякий случай.
    """
    n = len(data)

    # длина массива
    memory.write_word(data_base, n, is_instruction=False)

    # элементы массива (в 32-битном доп. коде)
    for i, value in enumerate(data):
        addr = data_base + 1 + i
        memory.write_word(addr, _to_twos_complement_32(value), is_instruction=False)

    # очистим ячейку результата
    memory.write_word(result_addr, 0, is_instruction=False)

    return data_base, result_addr


def create_sum_array_cpu(
    memory: Memory,
    code_base: int = CODE_BASE,
) -> CPU:
    """
    Загрузить программу суммы массива в память и создать CPU,
    готовый к выполнению.

    Память перед этим НЕ очищаем, чтобы не стереть данные массива.
    """
    loader = ProgramLoader(memory)
    loaded = loader.load_from_source(
        SUM_ARRAY_PROGRAM,
        code_base=code_base,
        clear_memory=False,  # данные массива уже лежат в памяти
    )
    cpu = loader.create_cpu(loaded)
    return cpu


def run_sum_array_example(
    data: List[int],
    memory_size: int = 1024,
    max_steps: int = 1000,
) -> int:
    """
    Удобная обёртка: создать память, записать массив, загрузить программу,
    выполнить её и вернуть результат из ячейки RESULT_ADDR.

    Это можно использовать как "юнит-тест" задания.
    """
    # Создаём память
    memory = Memory(size=memory_size)

    # Инициализируем массив и адрес результата
    setup_sum_array_memory(memory, data, data_base=DATA_BASE, result_addr=RESULT_ADDR)

    # Создаём CPU с загруженной программой
    cpu = create_sum_array_cpu(memory, code_base=CODE_BASE)

    # Выполняем программу
    cpu.run(max_steps=max_steps)

    # Читаем результат из памяти и преобразуем к знаковому int
    raw = memory.read_word(RESULT_ADDR)
    result = _from_twos_complement_32(raw)

    return result
def run_sum_array_verbose(
    data: List[int],
    memory_size: int = 1024,
    max_steps: int = 200,
    watch_steps: Tuple[int, ...] = (0, 1, 5),   # какие шаги показать подробно
):
    """
    Версия с подробным выводом каждого важного этапа.
    Показывает:
        - память до выполнения
        - регистры до старта
        - отдельные шаги выполнения (fetch, decode, execute)
        - память после завершения

    watch_steps — номера шагов, которые надо вывести подробно
    (например, 0, 1 и 5 шаг).
    """

    print("\n========== ИНИЦИАЛИЗАЦИЯ ==========\n")

    memory = Memory(size=memory_size)
    setup_sum_array_memory(memory, data)

    print("Исходный массив:", data)
    print("Данные в памяти:")
    for i in range(DATA_BASE, DATA_BASE + len(data) + 1):
        print(f"  @{i}: {memory.read_word(i)}")
    print()

    cpu = create_sum_array_cpu(memory)

    print("Начальное состояние CPU:")
    print(cpu.snapshot())
    print()

    print("========== ВЫПОЛНЕНИЕ ПРОГРАММЫ ==========\n")

    step_count = 0
    while not cpu.halted and step_count < max_steps:
        if step_count in watch_steps:
            print(f"----- ШАГ {step_count} -----")
            print("PC:", cpu.registers.PC)
            print("ACC:", cpu.registers.ACC)
            print("R0–R3:", cpu.registers.GPR)
            print("FLAGS:", cpu.flags)

        # F–D–E цикл
        word = cpu.fetch()
        instr = cpu.decode(word)

        if step_count in watch_steps:
            print("FETCH: IR =", hex(word))
            print("DECODE:", instr)

        cpu.execute(instr)

        if step_count in watch_steps:
            print("EXECUTE:")
            print("  ACC =", cpu.registers.ACC)
            print("  R0–R3 =", cpu.registers.GPR)
            print("  FLAGS =", cpu.flags)
            print()

        step_count += 1

    print("\n========== ПРОГРАММА ЗАВЕРШЕНА ==========\n")
    print("Итоговое состояние CPU:")
    print(cpu.snapshot())
    print()

    sum_raw = memory.read_word(RESULT_ADDR)
    sum_val = _from_twos_complement_32(sum_raw)

    print(f"Результат в памяти @200 = {sum_raw} → {sum_val}")

    print("\nФрагмент памяти, где хранится результат:")
    for i in range(198, 203):
        print(f"  @{i}: {memory.read_word(i)}")

    return sum_val