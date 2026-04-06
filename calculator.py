"""
Calcura — Premium Scientific Calculator
A dark-luxury themed scientific calculator built with tkinter.
No external libraries required: tkinter, math, re, locale only.
"""

import tkinter as tk
import tkinter.font as tkfont
import math
import re
import locale

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = {
    # window / display
    "bg":           "#0f0f0f",
    "border":       "#1e1e1e",
    "display_bg":   "#141414",
    "display_bdr":  "#252525",
    "text_primary": "#e8e8e8",
    "text_secondary": "#555555",

    # number buttons
    "num_bg":       "#1c1c1c",
    "num_fg":       "#e0e0e0",
    "num_hover":    "#2a2a2a",
    "num_press":    "#111111",

    # operator buttons
    "op_bg":        "#1a2a2a",
    "op_fg":        "#00d4aa",
    "op_hover":     "#1e3333",
    "op_press":     "#0f2020",

    # equals button
    "eq_bg":        "#00d4aa",
    "eq_fg":        "#0a0a0a",
    "eq_hover":     "#00f0c0",
    "eq_press":     "#009980",

    # clear buttons (AC, ⌫)
    "cl_bg":        "#2a1a1a",
    "cl_fg":        "#ff5f5f",
    "cl_hover":     "#331a1a",
    "cl_press":     "#1a0f0f",

    # function buttons (%, ±, √, x², 1/x)
    "fn_bg":        "#1a1a2a",
    "fn_fg":        "#7a9fff",
    "fn_hover":     "#1f1f33",
    "fn_press":     "#111122",
}


# ─────────────────────────────────────────────────────────────────────────────
# CalculatorLogic — pure state machine, no UI
# ─────────────────────────────────────────────────────────────────────────────
class CalculatorLogic:
    """
    Manages all calculator state and arithmetic operations.
    No tkinter references; purely computational.
    """

    def __init__(self):
        self.reset()

    # ── public helpers ────────────────────────────────────────────────────────

    def reset(self):
        """Full reset to factory state."""
        self._current: str = "0"       # string currently on display
        self._stored: float = 0.0      # left-hand operand
        self._operator: str | None = None  # pending operator
        self._just_evaluated: bool = False # True immediately after pressing =
        self._last_operand: float = 0.0    # for repeating = presses
        self._last_operator: str | None = None
        self._error: bool = False
        self._expression: str = ""         # secondary-row text

    @property
    def display_value(self) -> str:
        """Formatted value for the primary display row."""
        return self._current

    @property
    def expression(self) -> str:
        """Text for the secondary (history) display row."""
        return self._expression

    # ── digit / decimal input ─────────────────────────────────────────────────

    def input_digit(self, digit: str):
        """Append a digit to the current number."""
        if self._error:
            self._clear_error()
        if self._just_evaluated:
            self._current = digit
            self._just_evaluated = False
            self._expression = ""
        elif self._current == "0" and digit != ".":
            self._current = digit
        else:
            if len(self._current.replace("-", "").replace(".", "")) >= 12:
                return  # hard cap
            self._current += digit

    def input_decimal(self):
        """Insert decimal point if not already present."""
        if self._error:
            self._clear_error()
        if self._just_evaluated:
            self._current = "0."
            self._just_evaluated = False
            self._expression = ""
            return
        if "." not in self._current:
            self._current += "."

    # ── operators ─────────────────────────────────────────────────────────────

    def input_operator(self, op: str):
        """
        Handle binary operator (+, -, ×, ÷).
        Chained: if a pending operator exists and the user hasn't just pressed =,
        evaluate it first, then store the new operator.
        """
        if self._error:
            return
        current_val = self._parse_current()
        if current_val is None:
            return

        if self._operator and not self._just_evaluated:
            # chain: evaluate pending first
            result = self._apply(self._stored, self._operator, current_val)
            if result is None:
                return
            self._stored = result
            self._current = self._format(result)
        else:
            self._stored = current_val

        self._operator = op
        self._just_evaluated = False
        self._expression = f"{self._format_expr(self._stored)} {op}"

    def evaluate(self):
        """
        Execute the pending operation (or repeat the last one).
        """
        if self._error:
            return
        current_val = self._parse_current()
        if current_val is None:
            return

        if self._just_evaluated:
            # repeat last operation
            if self._last_operator is None:
                return
            result = self._apply(current_val, self._last_operator, self._last_operand)
            expr_op = self._last_operator
            expr_rhs = self._last_operand
        elif self._operator:
            self._last_operand = current_val
            self._last_operator = self._operator
            result = self._apply(self._stored, self._operator, current_val)
            expr_op = self._operator
            expr_rhs = current_val
            self._expression = (
                f"{self._format_expr(self._stored)} {self._operator} "
                f"{self._format_expr(current_val)} ="
            )
        else:
            # no operator — just show expression of the number itself
            self._expression = f"{self._format_expr(current_val)} ="
            self._just_evaluated = True
            return

        if result is None:
            return
        self._stored = result
        self._current = self._format(result)
        self._operator = None
        self._just_evaluated = True

    # ── special functions ─────────────────────────────────────────────────────

    def toggle_sign(self):
        """Negate current value."""
        if self._error:
            return
        val = self._parse_current()
        if val is None:
            return
        result = -val
        self._current = self._format(result)

    def percent(self):
        """Divide current value by 100."""
        if self._error:
            return
        val = self._parse_current()
        if val is None:
            return
        result = val / 100
        self._expression = f"{self._format_expr(val)} % ="
        self._current = self._format(result)
        self._just_evaluated = True

    def square_root(self):
        """Square root — error if negative."""
        if self._error:
            return
        val = self._parse_current()
        if val is None:
            return
        if val < 0:
            self._set_error("Invalid")
            return
        result = math.sqrt(val)
        self._expression = f"√{self._format_expr(val)} ="
        self._current = self._format(result)
        self._just_evaluated = True

    def square(self):
        """x²."""
        if self._error:
            return
        val = self._parse_current()
        if val is None:
            return
        result = val ** 2
        self._expression = f"{self._format_expr(val)}² ="
        self._current = self._format(result)
        self._just_evaluated = True

    def reciprocal(self):
        """1/x — error on zero."""
        if self._error:
            return
        val = self._parse_current()
        if val is None:
            return
        if val == 0:
            self._set_error("Error")
            return
        result = 1 / val
        self._expression = f"1/{self._format_expr(val)} ="
        self._current = self._format(result)
        self._just_evaluated = True

    def backspace(self):
        """Delete last character."""
        if self._error:
            self._clear_error()
            return
        if self._just_evaluated:
            return
        if len(self._current) <= 1 or (
            len(self._current) == 2 and self._current.startswith("-")
        ):
            self._current = "0"
        else:
            self._current = self._current[:-1]
            if self._current == "-":
                self._current = "0"

    def clear_all(self):
        """AC — full reset."""
        self.reset()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _parse_current(self) -> float | None:
        """Convert current display string to float."""
        try:
            return float(self._current)
        except ValueError:
            return None

    def _apply(self, a: float, op: str, b: float) -> float | None:
        """
        Apply binary operation. Returns None and sets error state on failure.
        """
        try:
            if op == "+":
                result = a + b
            elif op == "−":
                result = a - b
            elif op == "×":
                result = a * b
            elif op == "÷":
                if b == 0:
                    self._set_error("Error")
                    return None
                result = a / b
            else:
                return None

            if math.isinf(result) or (abs(result) > 1e99):
                self._set_error("Overflow")
                return None
            return result
        except OverflowError:
            self._set_error("Overflow")
            return None

    @staticmethod
    def _format(value: float) -> str:
        """
        Format a float for display:
        - Trim trailing zeros after decimal.
        - Integers shown without decimal point.
        - Very large/small numbers in scientific notation.
        """
        if math.isnan(value):
            return "Error"
        if abs(value) >= 1e12 or (abs(value) < 1e-9 and value != 0):
            return f"{value:.6e}"
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        # trim trailing zeros
        s = f"{value:.10f}".rstrip("0").rstrip(".")
        return s

    @staticmethod
    def _format_expr(value: float) -> str:
        """Short representation for the expression row."""
        if value == int(value) and abs(value) < 1e12:
            return str(int(value))
        s = f"{value:.6f}".rstrip("0").rstrip(".")
        return s

    def _set_error(self, msg: str):
        self._error = True
        self._current = msg
        self._expression = ""
        self._operator = None
        self._just_evaluated = False

    def _clear_error(self):
        self._error = False
        self._current = "0"
        self._expression = ""


# ─────────────────────────────────────────────────────────────────────────────
# Display — two-row display widget
# ─────────────────────────────────────────────────────────────────────────────
class Display(tk.Frame):
    """
    The calculator's two-row display panel.
    Top row: expression / history (small, grey).
    Bottom row: current number (large, white).
    """

    BASE_FONT_SIZE = 38
    MIN_FONT_SIZE  = 24
    MAX_CHARS      = 12

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=PALETTE["display_bg"],
            highlightbackground=PALETTE["display_bdr"],
            highlightthickness=1,
            **kwargs,
        )

        self._expr_var  = tk.StringVar(value="")
        self._main_var  = tk.StringVar(value="0")

        # secondary / expression row
        self._expr_label = tk.Label(
            self,
            textvariable=self._expr_var,
            bg=PALETTE["display_bg"],
            fg=PALETTE["text_secondary"],
            font=("Courier New", 13),
            anchor="e",
            padx=20,
        )
        self._expr_label.pack(fill="x", pady=(14, 0))

        # primary / value row
        self._main_label = tk.Label(
            self,
            textvariable=self._main_var,
            bg=PALETTE["display_bg"],
            fg=PALETTE["text_primary"],
            font=("Courier New", self.BASE_FONT_SIZE, "bold"),
            anchor="e",
            padx=20,
        )
        self._main_label.pack(fill="x", pady=(4, 14))

        # animation state
        self._anim_id: str | None = None

    # ── public ───────────────────────────────────────────────────────────────

    def update_values(self, main: str, expr: str, animate: bool = False):
        """Refresh both rows. Optionally fade-in the main value."""
        self._expr_var.set(expr)
        self._main_var.set(self._add_commas(main))
        self._adjust_font(main)
        if animate:
            self._start_fade()

    # ── private ──────────────────────────────────────────────────────────────

    def _adjust_font(self, text: str):
        """Scale font size down if text is long."""
        length = len(text)
        if length <= 9:
            size = self.BASE_FONT_SIZE
        elif length <= 11:
            size = 30
        else:
            size = self.MIN_FONT_SIZE
        self._main_label.config(font=("Courier New", size, "bold"))

    @staticmethod
    def _add_commas(text: str) -> str:
        """Insert thousand separators into integer portion of numeric strings."""
        # Don't format error/keyword strings
        special = {"Error", "Invalid", "Overflow"}
        if text in special:
            return text
        # Detect scientific notation — don't mangle it
        if "e" in text or "E" in text:
            return text
        # Split on decimal point
        parts = text.split(".")
        integer_part = parts[0]
        sign = ""
        if integer_part.startswith("-"):
            sign = "-"
            integer_part = integer_part[1:]
        try:
            integer_part = f"{int(integer_part):,}"
        except ValueError:
            pass
        result = sign + integer_part
        if len(parts) > 1:
            result += "." + parts[1]
        return result

    # ── fade-in animation ─────────────────────────────────────────────────────

    def _start_fade(self):
        """Fade the primary label from grey to white over ~200 ms."""
        if self._anim_id:
            self.after_cancel(self._anim_id)
        self._anim_step(0)

    def _anim_step(self, step: int):
        total = 10    # steps
        if step > total:
            self._main_label.config(fg=PALETTE["text_primary"])
            return
        ratio = step / total
        r = int(0x55 + (0xe8 - 0x55) * ratio)
        g = int(0x55 + (0xe8 - 0x55) * ratio)
        b = int(0x55 + (0xe8 - 0x55) * ratio)
        color = f"#{r:02x}{g:02x}{b:02x}"
        self._main_label.config(fg=color)
        self._anim_id = self.after(20, lambda: self._anim_step(step + 1))


# ─────────────────────────────────────────────────────────────────────────────
# RoundedButton — custom canvas button with hover/press animations
# ─────────────────────────────────────────────────────────────────────────────
class RoundedButton(tk.Canvas):
    """
    A canvas-based button with:
    - Rounded rectangle background
    - Smooth hover colour transition (~150 ms)
    - Click flash (~80 ms) with 1-px content shift to simulate depth
    """

    RADIUS = 10

    def __init__(
        self,
        parent,
        text: str,
        command,
        bg: str,
        fg: str,
        hover_bg: str,
        press_bg: str,
        font_tuple: tuple,
        **kwargs,
    ):
        super().__init__(
            parent,
            bg=PALETTE["bg"],
            highlightthickness=0,
            cursor="hand2",
            **kwargs,
        )

        self._text       = text
        self._command    = command
        self._bg         = bg
        self._fg         = fg
        self._hover_bg   = hover_bg
        self._press_bg   = press_bg
        self._font_tuple = font_tuple

        self._current_bg = bg
        self._target_bg  = bg
        self._pressed    = False
        self._hover      = False
        self._fade_id    = None

        # Draw initial state
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>",     self._on_enter)
        self.bind("<Leave>",     self._on_leave)
        self.bind("<Button-1>",  self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

        self._rect_id = None
        self._text_id = None

    # ── drawing ───────────────────────────────────────────────────────────────

    def _draw(self, bg: str, offset_y: int = 0):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        r = self.RADIUS
        # Rounded rectangle via polygon
        self._rect_id = self._rounded_rect(0, 0, w, h, r, fill=bg, outline="")
        font_obj = tkfont.Font(
            family=self._font_tuple[0],
            size=self._font_tuple[1],
            weight=self._font_tuple[2] if len(self._font_tuple) > 2 else "normal",
        )
        self._text_id = self.create_text(
            w // 2,
            h // 2 + offset_y,
            text=self._text,
            fill=self._fg,
            font=font_obj,
        )

    def _rounded_rect(self, x1, y1, x2, y2, r, **kw):
        """Draw a rounded rectangle using polygon points."""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def _on_configure(self, _event):
        self._draw(self._current_bg)

    # ── interaction ───────────────────────────────────────────────────────────

    def _on_enter(self, _event):
        self._hover = True
        if not self._pressed:
            self._animate_to(self._hover_bg)

    def _on_leave(self, _event):
        self._hover = False
        if not self._pressed:
            self._animate_to(self._bg)

    def _on_press(self, _event):
        self._pressed = True
        if self._fade_id:
            self.after_cancel(self._fade_id)
            self._fade_id = None
        self._current_bg = self._press_bg
        self._draw(self._press_bg, offset_y=1)

    def _on_release(self, _event):
        self._pressed = False
        target = self._hover_bg if self._hover else self._bg
        self._draw(target)
        self._current_bg = target
        if self._command:
            self._command()

    # ── smooth colour fade ────────────────────────────────────────────────────

    def _animate_to(self, target: str, steps: int = 8, interval: int = 18):
        """Interpolate background colour from current to target."""
        if self._fade_id:
            self.after_cancel(self._fade_id)
        self._target_bg = target
        self._fade_step(self._current_bg, target, 0, steps, interval)

    def _fade_step(self, start: str, end: str, step: int, steps: int, interval: int):
        ratio = step / steps
        color = self._lerp_color(start, end, ratio)
        self._current_bg = color
        self._draw(color)
        if step < steps:
            self._fade_id = self.after(
                interval,
                lambda: self._fade_step(start, end, step + 1, steps, interval),
            )
        else:
            self._fade_id = None

    @staticmethod
    def _lerp_color(c1: str, c2: str, t: float) -> str:
        """Linear interpolation between two hex colours."""
        def parse(c):
            c = c.lstrip("#")
            return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

        r1, g1, b1 = parse(c1)
        r2, g2, b2 = parse(c2)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"


# ─────────────────────────────────────────────────────────────────────────────
# CalculatorApp — main window, layout, keyboard bindings
# ─────────────────────────────────────────────────────────────────────────────
class CalculatorApp:
    """
    Top-level application class.
    Composes Display, RoundedButton instances, and CalculatorLogic.
    """

    # button definitions: (label, category, colspan)
    # categories: num | op | eq | cl | fn
    BUTTONS = [
        # Row 1
        ("AC",  "cl", 1), ("±",   "fn", 1), ("%",   "fn", 1), ("√",   "fn", 1), ("⌫",  "cl", 1),
        # Row 2
        ("7",   "num", 1), ("8",  "num", 1), ("9",  "num", 1), ("÷",  "op", 1), ("x²", "fn", 1),
        # Row 3
        ("4",   "num", 1), ("5",  "num", 1), ("6",  "num", 1), ("×",  "op", 1), ("1/x","fn", 1),
        # Row 4
        ("1",   "num", 1), ("2",  "num", 1), ("3",  "num", 1), ("−",  "op", 1), ("",   "spacer", 1),
        # Row 5
        ("0",   "num", 2), (".",  "num", 1), ("+",  "op", 1),  ("=",  "eq", 1),
    ]

    # colour mapping from category
    CAT_COLORS = {
        "num": ("num_bg", "num_fg", "num_hover", "num_press"),
        "op":  ("op_bg",  "op_fg",  "op_hover",  "op_press"),
        "eq":  ("eq_bg",  "eq_fg",  "eq_hover",  "eq_press"),
        "cl":  ("cl_bg",  "cl_fg",  "cl_hover",  "cl_press"),
        "fn":  ("fn_bg",  "fn_fg",  "fn_hover",  "fn_press"),
    }

    def __init__(self, root: tk.Tk):
        self.root  = root
        self.logic = CalculatorLogic()

        self._configure_window()
        self._build_ui()
        self._bind_keyboard()

    # ── window setup ──────────────────────────────────────────────────────────

    def _configure_window(self):
        self.root.title("⊞  Calcura")
        self.root.geometry("420x700")
        self.root.resizable(False, False)
        self.root.configure(bg=PALETTE["bg"])
        # outer border via highlight
        self.root.config(
            highlightbackground=PALETTE["border"],
            highlightthickness=2,
        )
        # center on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 420) // 2
        y = (sh - 700) // 2
        self.root.geometry(f"420x700+{x}+{y}")

    # ── UI assembly ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── display ──────────────────────────────────────────────────────────
        self.display = Display(self.root, height=130)
        self.display.pack(fill="x", padx=2, pady=(2, 0))

        # ── button grid container ─────────────────────────────────────────────
        grid_frame = tk.Frame(self.root, bg=PALETTE["bg"])
        grid_frame.pack(fill="both", expand=True, padx=16, pady=16)

        PAD   = 10   # gap between buttons
        COLS  = 5
        BTN_H = 68

        # We use grid geometry manager
        for c in range(COLS):
            grid_frame.columnconfigure(c, weight=1, uniform="col")

        self._buttons: dict[str, RoundedButton] = {}
        row = 0
        col = 0

        for label, cat, colspan in self.BUTTONS:
            if cat == "spacer":
                # invisible placeholder so row 4 col 4 is empty
                spacer = tk.Frame(grid_frame, bg=PALETTE["bg"], height=BTN_H)
                spacer.grid(row=row, column=col, columnspan=colspan,
                            padx=(0, PAD if col < COLS - 1 else 0),
                            pady=(0, PAD), sticky="nsew")
            else:
                btn = self._make_button(grid_frame, label, cat)
                px_right = PAD if (col + colspan - 1) < COLS - 1 else 0
                btn.grid(
                    row=row, column=col, columnspan=colspan,
                    padx=(0, px_right), pady=(0, PAD),
                    sticky="nsew", ipady=0,
                )
                btn.configure(height=BTN_H)
                if label:
                    self._buttons[label] = btn

            col += colspan
            if col >= COLS:
                col = 0
                row += 1

        grid_frame.rowconfigure(list(range(row + 1)), weight=1)

    def _make_button(self, parent, label: str, cat: str) -> RoundedButton:
        """Instantiate a RoundedButton with correct colours and command."""
        bg_key, fg_key, hov_key, prs_key = self.CAT_COLORS[cat]
        is_num = cat == "num"
        font_size = 18 if is_num else 16
        font_tuple = ("Courier New", font_size, "bold")

        btn = RoundedButton(
            parent,
            text=label,
            command=lambda l=label: self._on_button(l),
            bg=PALETTE[bg_key],
            fg=PALETTE[fg_key],
            hover_bg=PALETTE[hov_key],
            press_bg=PALETTE[prs_key],
            font_tuple=font_tuple,
        )
        return btn

    # ── button → logic dispatch ───────────────────────────────────────────────

    def _on_button(self, label: str):
        """Route a button label to the appropriate logic method."""
        lg = self.logic
        animate = False

        if label.isdigit():
            lg.input_digit(label)
        elif label == ".":
            lg.input_decimal()
        elif label in ("+", "−", "×", "÷"):
            lg.input_operator(label)
        elif label == "=":
            lg.evaluate()
            animate = True
        elif label == "AC":
            lg.clear_all()
        elif label == "⌫":
            lg.backspace()
        elif label == "±":
            lg.toggle_sign()
        elif label == "%":
            lg.percent()
            animate = True
        elif label == "√":
            lg.square_root()
            animate = True
        elif label == "x²":
            lg.square()
            animate = True
        elif label == "1/x":
            lg.reciprocal()
            animate = True

        self._refresh_display(animate)

    def _refresh_display(self, animate: bool = False):
        self.display.update_values(
            self.logic.display_value,
            self.logic.expression,
            animate=animate,
        )

    # ── keyboard bindings ─────────────────────────────────────────────────────

    def _bind_keyboard(self):
        self.root.bind("<Key>", self._on_key)

    def _on_key(self, event: tk.Event):
        key = event.keysym
        char = event.char

        if char in "0123456789":
            self._on_button(char)
        elif char == ".":
            self._on_button(".")
        elif char == "+":
            self._on_button("+")
        elif char in ("-", "_"):
            self._on_button("−")
        elif char in ("*", "x", "X"):
            self._on_button("×")
        elif char == "/":
            self._on_button("÷")
        elif key in ("Return", "equal"):
            self._on_button("=")
        elif key == "BackSpace":
            self._on_button("⌫")
        elif key == "Escape":
            self._on_button("AC")
        elif char == "s":
            self._on_button("√")
        elif char == "q":
            self._on_button("x²")
        elif char == "%":
            self._on_button("%")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()
