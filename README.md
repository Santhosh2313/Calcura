# Calcura — Premium Scientific Calculator

A dark-luxury themed scientific calculator with smooth glassmorphism UI, satisfying animations, and full keyboard support.

## Overview
This repository contains two identical, pixel-perfect versions of the same calculator:
1. **Desktop App**: `calculator.py` (built in Python/tkinter)
2. **Web App**: `index.html`, `style.css`, `app.js` (built in pure HTML/CSS/Vanilla JS)

## Features
- **Dark Luxury Theme**: Deep slate backgrounds, electric cyan accents, subtle glows.
- **Micro-Animations**: Color fading, press depth shifting, result fade-ins.
- **Robust Logic**: Chained operations, error handling, percent, toggle sign, squares, roots, reciprocals. 
- **Keyboard Support**: Fully navigable via keyboard (`0-9`, `+-*/`, `Enter`, `Backspace`, `s` for square root, `q` for square, `Esc` for clear).

## Running the Web Version
Simply open `index.html` in any web browser, or use a live server:
```bash
npx serve .
```

## Running the Desktop Version
You must have Python installed. No external libraries required.
```bash
python calculator.py
```

## Deployment (Vercel)
This repository is configured for immediate deployment to Vercel via the included `vercel.json`.

1. Push this repository to GitHub.
2. Log into [Vercel](https://vercel.com/) and click "Add New Project".
3. Import this repository.
4. Leave all settings as default and click "Deploy".
