# CARLA Tesla Keyboard Drive (Windows, Python)

Drive a **Tesla Model 3** (or any available vehicle) in the **CARLA Simulator** on **Windows** using only your keyboard (W, A, S, D keys — commonly used in video games for forward, left, reverse, and right) and arrow keys — no pygame required.  
Built with **Python** and the **Win32 API** for responsive, low-latency controls.

---

## Features

- **Windows-only** (uses `GetAsyncKeyState` from the Win32 API)
- **No pygame required**
- **WASD & Arrow key controls** for driving
- **Synchronous mode** at 60 FPS (`fixed_delta_seconds=1/60`)
- **Robust connection** — tries multiple ports until CARLA is ready
- **Fixed chase camera** for a stable driving view
- **Tesla-first spawn** (falls back to another drivable vehicle if unavailable)

---

## What does "WASD" mean?

It’s a common keyboard layout used in video games:  
- **W** → Forward / Throttle  
- **A** → Steer Left  
- **S** → Brake / Reverse  
- **D** → Steer Right  

This script also supports the **Arrow keys** as an alternative.

---

## Controls

| Key(s)                | Action          |
|-----------------------|-----------------|
| `W` / `↑` / `E`       | Throttle        |
| `S` / `↓` / `X`       | Brake           |
| `A` / `←`             | Steer Left      |
| `D` / `→`             | Steer Right     |
| `Space`               | Handbrake       |
| `R`                   | Toggle Reverse  |
| `Esc`                 | Quit            |

---

## Requirements

- **Windows 10/11**
- **CARLA simulator** running (server version must match your PythonAPI)
- **Python 3.8 – 3.11**
- Matching `carla` wheel/egg (install from `PythonAPI/carla/dist` if needed)

---
## Our Setup for CARLA on Windows
- Operating System: Windows 11  
- CPU: 12th Gen Intel Core i5-12500H (2.50 GHz)  
- RAM: 16 GB  
- GPU: NVIDIA GeForce RTX series  
- Implementation Platform: Visual Studio Code (VSCode)

---

## Installation

1. **Clone this repository**
   ```bash
   git clone https://github.com/mirzaakhi/carla-tesla-keyboard-python-windows.git
   cd carla-tesla-keyboard-python-windows

2. **Install dependencies**
   pip install carla
3. **Ensure CARLA is running**
   Launch CARLAUE4.exe before starting the script.
4. **Run the script**
   python test.py


---

