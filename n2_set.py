from __future__ import annotations

from typing import List, Tuple

from cpu.memory import Memory
from cpu.cpu import CPU
from program_loader import ProgramLoader


# ============================
#   Константы для задания 2
# ============================

CONV_LENGTH_ADDR = 300   # сюда кладём длину массивов (10)
CONV_A_BASE = 301        # массив A: @301..@310
CONV_B_BASE = 311        # массив B: @311..@320
CONV_RESULT_ADDR = 400   # результат свёртки: @400
CONV_CODE_BASE = 0       # базовый адрес кода


# ============================
#   Ассемблерная программа
#   Свёртка двух массивов
# ============================

CONV_PROGRAM = """
; Задание №1 — часть 2
; Свёртка (скалярное произведение) двух массивов длиной 10.
;
; Память:
;   @300 - длина массивов (10)
;   @301..@310 - массив A[i]
;   @311..@320 - массив B[i]
;   @400 - сюда пишем результат свёртки

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
    ; результат свёртки в ACC = R2
    LOAD R2
    STORE @400
    HALT
"""


# ============================
#   Вспомогательные функции
# ============================

def _to_twos_complement_32(value: int) -> int:
    """
    Преобразовать Python int в 32-битное значение в доп. коде
    (для записи в память).
    """
    return value & 0xFFFFFFFF


def _from_twos_complement_32(value: int) -> int:
    """
    Преобразовать 32-битное значение из доп. кода
    в обычный Python int.
    """
    value &= 0xFFFFFFFF
    if value & 0x80000000:
        return value - (1 << 32)
    return value


def setup_convolution_memory(
    memory: Memory,
    A: List[int],
    B: List[int],
    length_addr: int = CONV_LENGTH_ADDR,
    base_A: int = CONV_A_BASE,
    base_B: int = CONV_B_BASE,
    result_addr: int = CONV_RESULT_ADDR,
):
    """
    Инициализировать память для задачи свёртки.

    Требование: A и B длиной ровно 10.
    Пишем:
        @length_addr  = 10
        @base_A..     = элементы A
        @base_B..     = элементы B
        @result_addr  = 0 (очистка результата)
    """
    if len(A) != 10 or len(B) != 10:
        raise ValueError("Для задания 2 требуются массивы длиной РОВНО 10 элементов.")

    # длина массивов
    memory.write_word(length_addr, 10, is_instruction=False)

    # массив A
    for i, v in enumerate(A):
        memory.write_word(base_A + i, _to_twos_complement_32(v), is_instruction=False)

    # массив B
    for i, v in enumerate(B):
        memory.write_word(base_B + i, _to_twos_complement_32(v), is_instruction=False)

    # очистка результата
    memory.write_word(result_addr, 0, is_instruction=False)

    return result_addr


def create_convolution_cpu(
    memory: Memory,
    code_base: int = CONV_CODE_BASE,
) -> CPU:
    """
    Загрузить программу свёртки в память и создать CPU,
    готовый к исполнению.
    """
    loader = ProgramLoader(memory)
    loaded = loader.load_from_source(
        CONV_PROGRAM,
        code_base=code_base,
        clear_memory=False,  # данные массивов уже лежат в памяти
    )
    cpu = loader.create_cpu(loaded)
    return cpu


# ============================
#   Подробный запуск (verbose)
# ============================

def run_convolution_verbose(
    A: List[int],
    B: List[int],
    memory_size: int = 1024,
    max_steps: int = 1000,
    watch_steps: Tuple[int, ...] = (0, 1, 5),
) -> int:
    """
    Выполнить свёртку двух массивов A и B (по 10 элементов)
    с подробным выводом шагов процессора.

    Возвращает результат свёртки как Python int.
    """

    print("\n========== ИНИЦИАЛИЗАЦИЯ ДАННЫХ ==========\n")

    memory = Memory(size=memory_size)
    setup_convolution_memory(memory, A, B)

    print("Массив A:", A)
    print("Массив B:", B)
    print("\nСодержимое памяти (длина, A, B):")
    for addr in range(CONV_LENGTH_ADDR, CONV_B_BASE + 10 + 1):
        print(f"  @{addr}: {memory.read_word(addr)}")
    print()

    cpu = create_convolution_cpu(memory)

    print("Начальное состояние CPU:")
    print(cpu.snapshot())
    print()

    print("========== ВЫПОЛНЕНИЕ ПРОГРАММЫ ==========\n")

    step = 0
    while not cpu.halted and step < max_steps:

        if step in watch_steps:
            print(f"----- ШАГ {step} -----")
            print("PC =", cpu.registers.PC)
            print("ACC =", cpu.registers.ACC)
            print("R0–R3 =", cpu.registers.GPR)
            print("FLAGS =", cpu.flags)

        word = cpu.fetch()
        instr = cpu.decode(word)

        if step in watch_steps:
            print("FETCH:", hex(word))
            print("DECODE:", instr)

        cpu.execute(instr)

        if step in watch_steps:
            print("EXECUTE:")
            print("  ACC  =", cpu.registers.ACC)
            print("  R0–R3 =", cpu.registers.GPR)
            print("  FLAGS =", cpu.flags)
            print()

        step += 1

    print("\n========== ПРОГРАММА ЗАВЕРШЕНА ==========\n")

    raw_result = memory.read_word(CONV_RESULT_ADDR)
    result = _from_twos_complement_32(raw_result)

    print("Итоговое состояние CPU:")
    print(cpu.snapshot())
    print()
    print(f"Результат свёртки @${CONV_RESULT_ADDR} = {raw_result} → {result}")

    print("\nФрагмент памяти вокруг результата:")
    for addr in range(CONV_RESULT_ADDR - 2, CONV_RESULT_ADDR + 3):
        print(f"  @{addr}: {memory.read_word(addr)}")

    return result


if __name__ == "__main__":
    # Небольшой само-тест модуля
    A_test = [1, 2, 3, 4, 5, -1, -2, 3, 0, 7]
    B_test = [2, 0, 1, -1, 3, 4, 2, -2, 1, 1]

    print("Тестовая свёртка A·B")
    res = run_convolution_verbose(A_test, B_test)
    print("\nИТОГ:", res)
