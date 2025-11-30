from cpu.memory import Memory
from program_loader import ProgramLoader


# Простейшая тестовая программа на ассемблере:
#
# Задача:
#   ACC = 5 + 10
# Остановиться.
#
# Ожидаемый результат: ACC = 15 (0x0000000F)
TEST_PROGRAM = """
; Пример простой программы
start:
    LOAD #5      ; ACC = 5
    ADD  #10     ; ACC = ACC + 10
    HALT
"""


def run_test_program() -> None:
    # 1. Создаём память
    memory = Memory(size=1024)

    # 2. Создаём загрузчик и грузим программу
    loader = ProgramLoader(memory)
    loaded = loader.load_from_source(TEST_PROGRAM, code_base=0, clear_memory=True)

    # 3. Создаём CPU и устанавливаем PC на точку входа
    cpu = loader.create_cpu(loaded)

    print("=== Стартовое состояние CPU ===")
    print(cpu.snapshot())
    print()

    # 4. Выполняем программу
    cpu.run(max_steps=100)

    print("=== Состояние CPU после выполнения ===")
    print(cpu.snapshot())
    print()

    # 5. Для отладки можно вывести часть памяти
    print("=== Память [0..10) ===")
    print(memory.dump(0, 10))


def run_n1() -> None:
    from n1_set import run_sum_array_verbose
    from n2_set import run_convolution_verbose

    print("==================================== Задание 1 ====================================")
    data = [1, -2, 3, 4, -1]  # сумма = 5
    result = run_sum_array_verbose(data)
    print("\nИТОГ:", result)

    print("==================================== Задание 2 ====================================")
    A = [1, 2, 3, 4, 5, -1, -2, 3, 0, 7]
    B = [2, 0, 1, -1, 3, 4, 2, -2, 1, 1]

    result = run_convolution_verbose(A, B, watch_steps=(0, 1, 2, 5))
    print("\nРезультат свёртки:", result)

if __name__ == "__main__":
    run_test_program()
    run_n1()
