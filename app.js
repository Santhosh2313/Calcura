/**
 * Calcura — Premium Scientific Calculator
 * app.js
 *
 * Class structure (mirrors the Python version):
 *   CalculatorLogic  — pure state machine, all math
 *   Display          — manages the two-row display panel
 *   CalculatorApp    — wires everything together, keyboard bindings
 *
 * No external dependencies.
 */

'use strict';

/* ============================================================
   CalculatorLogic — pure state machine
   ============================================================ */
class CalculatorLogic {
  constructor() {
    this.reset();
  }

  /** Full reset to factory state. */
  reset() {
    this._current        = '0';    // string on display
    this._stored         = 0;      // left-hand operand
    this._operator       = null;   // pending operator string
    this._justEvaluated  = false;  // true right after =
    this._awaitingOpd    = false;  // true right after operator
    this._lastOperand    = 0;      // for repeating =
    this._lastOperator   = null;
    this._error          = false;
    this._expression     = '';     // secondary-row text
  }

  // ── Getters ────────────────────────────────────────────────

  get displayValue()  { return this._current; }
  get expression()    { return this._expression; }
  get isError()       { return this._error; }

  // ── Digit / decimal input ───────────────────────────────────

  /** Append a digit character ('0'–'9') to the current number. */
  inputDigit(digit) {
    if (this._error) { this._clearError(); }

    if (this._justEvaluated || this._awaitingOpd) {
      this._current       = digit;
      if (this._justEvaluated) this._expression = '';
      this._justEvaluated = false;
      this._awaitingOpd   = false;
    } else if (this._current === '0' && digit !== '.') {
      this._current = digit;
    } else {
      // Hard cap: 12 significant characters
      const raw = this._current.replace('-', '').replace('.', '');
      if (raw.length >= 12) return;
      this._current += digit;
    }
  }

  /** Insert decimal point if not already present. */
  inputDecimal() {
    if (this._error) { this._clearError(); }

    if (this._justEvaluated || this._awaitingOpd) {
      this._current       = '0.';
      if (this._justEvaluated) this._expression = '';
      this._justEvaluated = false;
      this._awaitingOpd   = false;
      return;
    }
    if (!this._current.includes('.')) {
      this._current += '.';
    }
  }

  // ── Operators ────────────────────────────────────────────────

  /**
   * Handle a binary operator (+, −, ×, ÷).
   * Chained: if a pending operator exists and = hasn't just been pressed,
   * evaluate the pending operation first.
   */
  inputOperator(op) {
    if (this._error) return;

    if (this._awaitingOpd) {
      this._operator = op;
      this._expression = `${this._formatExpr(this._stored)} ${op}`;
      return;
    }

    const currentVal = this._parseCurrent();
    if (currentVal === null) return;

    if (this._operator && !this._justEvaluated) {
      const result = this._apply(this._stored, this._operator, currentVal);
      if (result === null) return;
      this._stored  = result;
      this._current = this._format(result);
    } else {
      this._stored = currentVal;
    }

    this._operator      = op;
    this._justEvaluated = false;
    this._awaitingOpd   = true;
    this._expression    = `${this._formatExpr(this._stored)} ${op}`;
  }

  /**
   * Execute the pending operation, or repeat the last one if = is pressed again.
   */
  evaluate() {
    if (this._error) return;
    const currentVal = this._parseCurrent();
    if (currentVal === null) return;

    if (this._justEvaluated) {
      // Repeat last operation
      if (!this._lastOperator) return;
      const result = this._apply(currentVal, this._lastOperator, this._lastOperand);
      if (result === null) return;
      this._expression = `${this._formatExpr(currentVal)} ${this._lastOperator} ${this._formatExpr(this._lastOperand)} =`;
      this._stored     = result;
      this._current    = this._format(result);
      return;
    }

    if (this._operator) {
      this._lastOperand  = currentVal;
      this._lastOperator = this._operator;
      const result = this._apply(this._stored, this._operator, currentVal);
      if (result === null) return;
      this._expression = `${this._formatExpr(this._stored)} ${this._operator} ${this._formatExpr(currentVal)} =`;
      this._stored     = result;
      this._current    = this._format(result);
      this._operator   = null;
    } else {
      // No pending operator — just mark the expression
      this._expression = `${this._formatExpr(currentVal)} =`;
    }

    this._justEvaluated = true;
  }

  // ── Special functions ────────────────────────────────────────

  /** Toggle positive / negative. */
  toggleSign() {
    if (this._error) return;
    const val = this._parseCurrent();
    if (val === null) return;
    this._current = this._format(-val);
  }

  /** Convert to percentage (÷ 100). */
  percent() {
    if (this._error) return;
    const val = this._parseCurrent();
    if (val === null) return;
    const result      = val / 100;
    this._expression  = `${this._formatExpr(val)} % =`;
    this._current     = this._format(result);
    this._justEvaluated = true;
  }

  /** Square root — 'Invalid' for negatives. */
  squareRoot() {
    if (this._error) return;
    const val = this._parseCurrent();
    if (val === null) return;
    if (val < 0) { this._setError('Invalid'); return; }
    const result      = Math.sqrt(val);
    this._expression  = `√${this._formatExpr(val)} =`;
    this._current     = this._format(result);
    this._justEvaluated = true;
  }

  /** x² */
  square() {
    if (this._error) return;
    const val = this._parseCurrent();
    if (val === null) return;
    const result      = val * val;
    this._expression  = `${this._formatExpr(val)}² =`;
    this._current     = this._format(result);
    this._justEvaluated = true;
  }

  /** 1/x — 'Error' on zero. */
  reciprocal() {
    if (this._error) return;
    const val = this._parseCurrent();
    if (val === null) return;
    if (val === 0) { this._setError('Error'); return; }
    const result      = 1 / val;
    this._expression  = `1/${this._formatExpr(val)} =`;
    this._current     = this._format(result);
    this._justEvaluated = true;
  }

  /** Delete last character. */
  backspace() {
    if (this._error) { this._clearError(); return; }
    if (this._justEvaluated) return;
    if (this._current.length <= 1 ||
       (this._current.length === 2 && this._current.startsWith('-'))) {
      this._current = '0';
    } else {
      this._current = this._current.slice(0, -1);
      if (this._current === '-') this._current = '0';
    }
  }

  /** AC — full reset. */
  clearAll() {
    this.reset();
  }

  // ── Internal helpers ─────────────────────────────────────────

  _parseCurrent() {
    const v = parseFloat(this._current);
    return isNaN(v) ? null : v;
  }

  _apply(a, op, b) {
    let result;
    switch (op) {
      case '+': result = a + b; break;
      case '−': result = a - b; break;
      case '×': result = a * b; break;
      case '÷':
        if (b === 0) { this._setError('Error'); return null; }
        result = a / b;
        break;
      default: return null;
    }
    if (!isFinite(result) || Math.abs(result) > 1e99) {
      this._setError('Overflow');
      return null;
    }
    return result;
  }

  _format(value) {
    if (!isFinite(value)) return 'Error';
    if (Math.abs(value) >= 1e12 || (Math.abs(value) < 1e-9 && value !== 0)) {
      return value.toExponential(6);
    }
    if (value === Math.trunc(value) && Math.abs(value) < 1e15) {
      return String(Math.trunc(value));
    }
    // Trim trailing zeros
    return parseFloat(value.toFixed(10)).toString();
  }

  _formatExpr(value) {
    if (value === Math.trunc(value) && Math.abs(value) < 1e12) {
      return String(Math.trunc(value));
    }
    return parseFloat(value.toFixed(6)).toString();
  }

  _setError(msg) {
    this._error         = true;
    this._current       = msg;
    this._expression    = '';
    this._operator      = null;
    this._justEvaluated = false;
  }

  _clearError() {
    this._error      = false;
    this._current    = '0';
    this._expression = '';
  }
}


/* ============================================================
   Display — manages the two-row display panel
   ============================================================ */
class Display {
  constructor(exprEl, mainEl) {
    /** @type {HTMLElement} */
    this._exprEl = exprEl;
    /** @type {HTMLElement} */
    this._mainEl = mainEl;
    this._fadeId = null;
  }

  /**
   * Refresh both rows.
   * @param {string} main    – raw numeric string from logic
   * @param {string} expr    – expression / history string
   * @param {boolean} animate – fade-in the main value
   */
  update(main, expr, animate = false) {
    this._exprEl.textContent = expr;
    this._mainEl.textContent = Display._addCommas(main);
    this._adjustFont(main);
    if (animate) this._startFade();
  }

  // ── Private ───────────────────────────────────────────────

  _adjustFont(text) {
    this._mainEl.classList.remove('size-md', 'size-sm');
    const len = text.length;
    if      (len > 11) this._mainEl.classList.add('size-sm');
    else if (len > 8)  this._mainEl.classList.add('size-md');
  }

  static _addCommas(text) {
    const specials = new Set(['Error', 'Invalid', 'Overflow']);
    if (specials.has(text)) return text;
    if (text.includes('e') || text.includes('E')) return text;

    const [intPart, decPart] = text.split('.');
    const sign    = intPart.startsWith('-') ? '-' : '';
    const digits  = intPart.replace('-', '');
    let formatted;
    try   { formatted = parseInt(digits, 10).toLocaleString('en-US'); }
    catch { formatted = digits; }

    return sign + formatted + (decPart !== undefined ? '.' + decPart : '');
  }

  /** Fade primary display from grey (#888) to white (#e8e8e8) over ~220ms. */
  _startFade() {
    if (this._fadeId) cancelAnimationFrame(this._fadeId);
    const start     = performance.now();
    const duration  = 220; // ms
    const fromR = 0x55, fromG = 0x55, fromB = 0x55;
    const toR   = 0xe8, toG   = 0xe8, toB   = 0xe8;

    const step = (now) => {
      const t      = Math.min((now - start) / duration, 1);
      const eased  = 1 - Math.pow(1 - t, 2); // ease-out quad
      const r = Math.round(fromR + (toR - fromR) * eased);
      const g = Math.round(fromG + (toG - fromG) * eased);
      const b = Math.round(fromB + (toB - fromB) * eased);
      this._mainEl.style.color = `rgb(${r},${g},${b})`;
      if (t < 1) {
        this._fadeId = requestAnimationFrame(step);
      } else {
        this._mainEl.style.color = '';  // revert to CSS variable
        this._fadeId = null;
      }
    };

    this._fadeId = requestAnimationFrame(step);
  }
}


/* ============================================================
   CalculatorApp — layout, event wiring, keyboard bindings
   ============================================================ */
class CalculatorApp {
  /**
   * Button definitions: [label, category, colSpan]
   * Categories: 'num' | 'op' | 'eq' | 'cl' | 'fn' | 'spacer'
   */
  static BUTTONS = [
    // Row 1
    ['AC',  'cl',  1], ['±',   'fn', 1], ['%',   'fn', 1], ['√',   'fn', 1], ['⌫',  'cl', 1],
    // Row 2
    ['7',   'num', 1], ['8',  'num', 1], ['9',  'num', 1], ['÷',  'op', 1], ['x²', 'fn', 1],
    // Row 3
    ['4',   'num', 1], ['5',  'num', 1], ['6',  'num', 1], ['×',  'op', 1], ['1/x','fn', 1],
    // Row 4
    ['1',   'num', 1], ['2',  'num', 1], ['3',  'num', 1], ['−',  'op', 1], ['',  'spacer', 1],
    // Row 5
    ['0',   'num', 2], ['.',  'num', 1], ['+',  'op', 1],  ['=',  'eq', 1],
  ];

  constructor() {
    this.logic   = new CalculatorLogic();
    this.display = new Display(
      document.getElementById('display-expr'),
      document.getElementById('display-main'),
    );
    this._activeOpBtn = null;  // tracks which operator button is highlighted

    this._buildButtons();
    this._bindKeyboard();
    this._refresh();
  }

  // ── Build button grid ──────────────────────────────────────

  _buildButtons() {
    const grid = document.getElementById('btn-grid');

    for (const [label, cat, span] of CalculatorApp.BUTTONS) {
      if (cat === 'spacer') {
        const sp = document.createElement('div');
        sp.className = 'btn-spacer';
        grid.appendChild(sp);
        continue;
      }

      const btn = document.createElement('button');
      btn.type      = 'button';
      btn.className = `btn btn-${cat}${span > 1 ? ' btn-span' + span : ''}`;
      btn.textContent = label;
      btn.dataset.label = label;
      if (label) btn.id = `btn-${label.replace(/[^a-zA-Z0-9]/g, '_')}`;
      btn.setAttribute('aria-label', this._ariaLabel(label));

      btn.addEventListener('click', () => this._onButton(label));
      // Prevent double-fire on mobile
      btn.addEventListener('touchend', (e) => { e.preventDefault(); this._onButton(label); });

      grid.appendChild(btn);
    }
  }

  _ariaLabel(label) {
    const map = {
      'AC': 'All Clear', '±': 'Toggle sign', '%': 'Percent',
      '√': 'Square root', '⌫': 'Backspace', '÷': 'Divide',
      '×': 'Multiply', '−': 'Subtract', '+': 'Add', '=': 'Equals',
      'x²': 'Square', '1/x': 'Reciprocal', '.': 'Decimal point',
    };
    return map[label] || label;
  }

  // ── Button → logic dispatch ────────────────────────────────

  _onButton(label) {
    const lg = this.logic;
    let animate = false;

    // Clear active operator highlight on any non-operator press
    const isOp = ['+', '−', '×', '÷'].includes(label);

    if (!isOp) this._clearActiveOp();

    if (/^\d$/.test(label))      { lg.inputDigit(label); }
    else if (label === '.')      { lg.inputDecimal(); }
    else if (isOp)               { lg.inputOperator(label); this._highlightOp(label); }
    else if (label === '=')      { lg.evaluate();    this._clearActiveOp(); animate = true; }
    else if (label === 'AC')     { lg.clearAll(); }
    else if (label === '⌫')     { lg.backspace(); }
    else if (label === '±')      { lg.toggleSign(); }
    else if (label === '%')      { lg.percent();    animate = true; }
    else if (label === '√')      { lg.squareRoot(); animate = true; }
    else if (label === 'x²')     { lg.square();     animate = true; }
    else if (label === '1/x')    { lg.reciprocal(); animate = true; }

    this._refresh(animate);
  }

  _refresh(animate = false) {
    this.display.update(
      this.logic.displayValue,
      this.logic.expression,
      animate,
    );
  }

  // ── Active operator highlighting ────────────────────────────

  _highlightOp(op) {
    this._clearActiveOp();
    const opLabelMap = { '+': 'btn-_-1', '−': 'btn-__1', '×': 'btn-_1', '÷': 'btn-_0' };
    // Find by data-label attribute instead
    const btn = document.querySelector(`.btn-op[data-label="${op}"]`);
    if (btn) {
      btn.classList.add('active-op');
      this._activeOpBtn = btn;
    }
  }

  _clearActiveOp() {
    if (this._activeOpBtn) {
      this._activeOpBtn.classList.remove('active-op');
      this._activeOpBtn = null;
    }
  }

  // ── Keyboard bindings ───────────────────────────────────────

  _bindKeyboard() {
    document.addEventListener('keydown', (e) => {
      // Prevent default for calculator keys to avoid page scroll etc.
      const calc = ['0','1','2','3','4','5','6','7','8','9',
                    '+','-','*','/','.',
                    'Enter','Backspace','Escape','=','%'];
      if (calc.includes(e.key) || ['s','q'].includes(e.key)) {
        e.preventDefault();
      }

      if (/^[0-9]$/.test(e.key)) {
        this._onButton(e.key);
        this._flashKey(e.key);
      } else {
        switch (e.key) {
          case '.':        this._onButton('.'); this._flashKey('.'); break;
          case '+':        this._onButton('+'); this._flashKey('+'); break;
          case '-':        this._onButton('−'); this._flashKey('−'); break;
          case '*':        this._onButton('×'); this._flashKey('×'); break;
          case '/':        this._onButton('÷'); this._flashKey('÷'); break;
          case 'Enter':
          case '=':        this._onButton('='); this._flashKey('='); break;
          case 'Backspace':this._onButton('⌫'); this._flashKey('⌫'); break;
          case 'Escape':   this._onButton('AC'); this._flashKey('AC'); break;
          case 's':        this._onButton('√'); this._flashKey('√'); break;
          case 'q':        this._onButton('x²'); this._flashKey('x²'); break;
          case '%':        this._onButton('%'); this._flashKey('%'); break;
        }
      }
    });
  }

  /** Briefly apply :active styling to the corresponding DOM button. */
  _flashKey(label) {
    const btn = document.querySelector(`[data-label="${label}"]`);
    if (!btn) return;
    btn.classList.add('key-flash');
    setTimeout(() => btn.classList.remove('key-flash'), 120);
  }
}


/* ============================================================
   Boot
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  new CalculatorApp();
});
