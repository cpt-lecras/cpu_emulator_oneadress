import tkinter as tk
from tkinter import ttk, messagebox

from cpu.memory import Memory
from cpu.cpu import CPU
from program_loader import ProgramLoader
from cpu.decoder import Decoder


DEFAULT_PROGRAM = """\
; Пример: сумма массива
; @100 = N
; @101..@100+N-1 = элементы массива
; @200 = результат

start:
    ; R1 = N
    LOAD @100
    STORE R1

    ; R0 = 101
    LOAD #101
    STORE R0

    ; R2 = 0 (сумма)
    LOAD #0
    STORE R2

loop:
    LOAD R1
    CMP #0
    JZ end

    LOAD [R0]
    ADD R2
    STORE R2

    LOAD R0
    ADD #1
    STORE R0

    LOAD R1
    SUB #1
    STORE R1

    JMP loop

end:
    LOAD R2
    STORE @200
    HALT
"""


class CPUGui(tk.Tk):
    """
    GUI для одноадресного процессора:
      - ввод программы на ассемблере,
      - Assemble & Load,
      - Step / Run / Reset,
      - отображение регистров, флагов, текущей и следующей команды,
      - отображение памяти с подсветкой PC и адресов из R0..R3.
    """

    def __init__(self, memory_size: int = 256):
        super().__init__()
        self.title("CPU Emulator GUI (Одноадресная архитектура фон Неймана)")
        self.geometry("1200x700")

        self.memory_size = memory_size

        self.memory: Memory | None = None
        self.cpu: CPU | None = None
        self.loader: ProgramLoader | None = None
        self.decoder = Decoder()
        self.last_source: str = DEFAULT_PROGRAM

        self._create_widgets()
        self._layout_widgets()

        self.asm_text.insert("1.0", DEFAULT_PROGRAM)

    # ---------- UI ---------- #

    def _create_widgets(self):
        # Левая панель – код
        self.asm_frame = ttk.LabelFrame(self, text="Ассемблерный код")
        self.asm_text = tk.Text(self.asm_frame, wrap="none", font=("Consolas", 10))
        self.asm_scroll_y = ttk.Scrollbar(
            self.asm_frame, orient="vertical", command=self.asm_text.yview
        )
        self.asm_text.configure(yscrollcommand=self.asm_scroll_y.set)

        # Правая панель – управление + состояние
        self.control_frame = ttk.LabelFrame(self, text="Управление и состояние CPU")

        # ---- Кнопки (теперь отдельный контейнер) ----
        self.btn_frame = ttk.Frame(self.control_frame)

        self.btn_assemble = ttk.Button(
            self.btn_frame, text="Assemble & Load", command=self.on_assemble_load
        )
        self.btn_step = ttk.Button(
            self.btn_frame, text="Step", command=self.on_step, state="disabled"
        )
        self.btn_run = ttk.Button(
            self.btn_frame, text="Run", command=self.on_run, state="disabled"
        )
        self.btn_reset = ttk.Button(
            self.btn_frame, text="Reset", command=self.on_reset, state="disabled"
        )

        # ---- Регистры ----
        self.reg_frame = ttk.LabelFrame(self.control_frame, text="Регистры")
        self.labels_regs = {}
        for name in ["ACC", "PC", "IR", "MAR", "MDR", "R0", "R1", "R2", "R3"]:
            lbl_name = ttk.Label(self.reg_frame, text=f"{name}:")
            lbl_val = ttk.Label(self.reg_frame, text="0")
            self.labels_regs[name] = (lbl_name, lbl_val)

        # ---- Флаги ----
        self.flags_frame = ttk.LabelFrame(self.control_frame, text="Флаги")
        self.lbl_flag_Z = ttk.Label(self.flags_frame, text="Z = 0")
        self.lbl_flag_N = ttk.Label(self.flags_frame, text="N = 0")
        self.lbl_flag_C = ttk.Label(self.flags_frame, text="C = 0")
        self.lbl_flag_V = ttk.Label(self.flags_frame, text="V = 0")

        # ---- Инструкции ----
        self.instr_frame = ttk.LabelFrame(self.control_frame, text="Инструкции")
        self.lbl_last_instr = ttk.Label(self.instr_frame, text="Последняя: -")
        self.lbl_next_instr = ttk.Label(self.instr_frame, text="Следующая: -")

        # ---- Статус ----
        self.status_label = ttk.Label(
            self.control_frame, text="Статус: нет загруженной программы"
        )

        # ---- Память ----
        self.mem_frame = ttk.LabelFrame(self, text="Память")
        self.mem_text = tk.Text(self.mem_frame, wrap="none", font=("Consolas", 9), height=15)
        self.mem_scroll_y = ttk.Scrollbar(
            self.mem_frame, orient="vertical", command=self.mem_text.yview
        )
        self.mem_text.configure(yscrollcommand=self.mem_scroll_y.set)
        self.mem_text.tag_configure("pc", background="#ffd9cc")
        self.mem_text.tag_configure("reg_addr", background="#ddffdd")

    def _layout_widgets(self):
        # Основная сетка
        self.asm_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.control_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.mem_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=2)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)

        # asm_frame
        self.asm_frame.grid_rowconfigure(0, weight=1)
        self.asm_frame.grid_columnconfigure(0, weight=1)
        self.asm_text.grid(row=0, column=0, sticky="nsew")
        self.asm_scroll_y.grid(row=0, column=1, sticky="ns")

        # control_frame – кнопки
        self.btn_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_assemble.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        self.btn_step.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        self.btn_run.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        self.btn_reset.grid(row=0, column=3, padx=2, pady=2, sticky="ew")

        # Регистры
        self.reg_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        for i, name in enumerate(["ACC", "PC", "IR", "MAR", "MDR", "R0", "R1", "R2", "R3"]):
            lbl_name, lbl_val = self.labels_regs[name]
            lbl_name.grid(row=i, column=0, sticky="w")
            lbl_val.grid(row=i, column=1, sticky="w")

        # Флаги
        self.flags_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        self.lbl_flag_Z.grid(row=0, column=0, padx=5)
        self.lbl_flag_N.grid(row=0, column=1, padx=5)
        self.lbl_flag_C.grid(row=0, column=2, padx=5)
        self.lbl_flag_V.grid(row=0, column=3, padx=5)

        # Инструкции
        self.instr_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        self.lbl_last_instr.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.lbl_next_instr.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        # Статус
        self.status_label.grid(row=4, column=0, sticky="ew", padx=5, pady=5)

        # Память
        self.mem_frame.grid_rowconfigure(0, weight=1)
        self.mem_frame.grid_columnconfigure(0, weight=1)
        self.mem_text.grid(row=0, column=0, sticky="nsew")
        self.mem_scroll_y.grid(row=0, column=1, sticky="ns")

    # ---------- callbacks ---------- #

    def on_assemble_load(self):
        source = self.asm_text.get("1.0", "end").strip()
        if not source:
            messagebox.showwarning("Пустой код", "Введите ассемблерную программу.")
            return

        try:
            self.memory = Memory(size=self.memory_size)
            self.loader = ProgramLoader(self.memory)
            loaded = self.loader.load_from_source(source, code_base=0, clear_memory=True)
            self.cpu = self.loader.create_cpu(loaded)
            self.last_source = source
        except Exception as e:
            messagebox.showerror("Ошибка сборки/загрузки", str(e))
            self.cpu = None
            self.memory = None
            return

        self.status_label.config(text="Статус: программа загружена, готово к выполнению")
        self.btn_step.config(state="normal")
        self.btn_run.config(state="normal")
        self.btn_reset.config(state="normal")

        self.update_state_display(last_instr=None)

    def on_step(self):
        if self.cpu is None:
            return
        if self.cpu.halted:
            self.status_label.config(text="Статус: процессор уже остановлен (HALT)")
            return

        word = self.cpu.fetch()
        instr = self.cpu.decode(word)
        self.cpu.execute(instr)

        if self.cpu.halted:
            self.status_label.config(text="Статус: HALT")
        else:
            self.status_label.config(text="Статус: выполнен один шаг")

        self.update_state_display(last_instr=instr)

    def on_run(self):
        if self.cpu is None:
            return

        max_steps = 10000
        steps = 0
        last_instr = None

        while not self.cpu.halted and steps < max_steps:
            word = self.cpu.fetch()
            instr = self.cpu.decode(word)
            self.cpu.execute(instr)
            last_instr = instr
            steps += 1

        if self.cpu.halted:
            self.status_label.config(text=f"Статус: HALT (шагов: {steps})")
        else:
            self.status_label.config(text=f"Статус: достигнут лимит шагов ({steps})")

        self.update_state_display(last_instr=last_instr)

    def on_reset(self):
        # просто пересобираем текущий текст
        self.on_assemble_load()

    # ---------- отображение состояния ---------- #

    def update_state_display(self, last_instr):
        if self.cpu is None or self.memory is None:
            return

        snap = self.cpu.registers.snapshot()
        for name in ["ACC", "PC", "IR", "MAR", "MDR", "R0", "R1", "R2", "R3"]:
            val = snap.get(name, 0)
            _, lbl_val = self.labels_regs[name]
            if name in ("ACC", "R0", "R1", "R2", "R3"):
                lbl_val.config(text=f"{val} (0x{val & 0xFFFFFFFF:08X})")
            else:
                lbl_val.config(text=str(val))

        fl = self.cpu.flags
        self.lbl_flag_Z.config(text=f"Z = {int(fl.Z)}")
        self.lbl_flag_N.config(text=f"N = {int(fl.N)}")
        self.lbl_flag_C.config(text=f"C = {int(fl.C)}")
        self.lbl_flag_V.config(text=f"V = {int(fl.V)}")

        if last_instr is None:
            self.lbl_last_instr.config(text="Последняя: -")
        else:
            self.lbl_last_instr.config(
                text=f"Последняя: {last_instr.mnemonic or '?'} "
                     f"mode={last_instr.mode.name} op={last_instr.operand}"
            )

        try:
            pc = self.cpu.registers.PC
            next_word = self.memory.read_word(pc)
            next_instr = self.decoder.decode(next_word)
            self.lbl_next_instr.config(
                text=f"Следующая (@{pc}): {next_instr.mnemonic or '?'} "
                     f"mode={next_instr.mode.name} op={next_instr.operand}"
            )
        except Exception:
            self.lbl_next_instr.config(text="Следующая: (не удалось декодировать)")

        self.update_memory_view()

    def update_memory_view(self):
        if self.memory is None or self.cpu is None:
            return

        self.mem_text.config(state="normal")
        self.mem_text.delete("1.0", "end")

        pc = self.cpu.registers.PC
        reg_addrs = {
            self.cpu.registers.R0,
            self.cpu.registers.R1,
            self.cpu.registers.R2,
            self.cpu.registers.R3,
        }

        for addr in range(self.memory_size):
            try:
                val = self.memory.read_word(addr)
            except Exception:
                val = 0

            line = f"@{addr:03d}: 0x{val & 0xFFFFFFFF:08X}\n"
            start_index = self.mem_text.index("end-1c")
            self.mem_text.insert("end", line)
            end_index = self.mem_text.index("end-1c")

            if addr == pc:
                self.mem_text.tag_add("pc", start_index, end_index)
            if addr in reg_addrs:
                self.mem_text.tag_add("reg_addr", start_index, end_index)

        self.mem_text.config(state="disabled")


if __name__ == "__main__":
    app = CPUGui(memory_size=256)
    app.mainloop()
