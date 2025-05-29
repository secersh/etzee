# etzee 101

**Modular • Ortholinear • Ergonomic**

The first keyboard from the **etzee** project, where code meets craft.

---

### 👋 About

**etzee 101** is a split, ortholinear ergonomic keyboard designed for developers, tinkerers, and digital creators.  
It combines a minimalist grid layout with a modular form factor, optimized for comfort, adaptability, and expressive input.

Its name, etzee 101, reflects both form and function: The keyboard features two opposing vertical displays and a central knob, visually evoking the structure of 1-0-1. But the deeper inspiration comes from the side connector, whose repeating pattern of dot–dash–dot–dash recalls the rhythm of Morse code, a symbolic thread woven into the design language.
More than a tool, it's a signal, a functional artifact shaped by story, precision, and developer intuition.

---

### 💶 Cost tracking

Transparent by design. Track the current bill of materials, component prices, and vendor sources here:

👉 [Cost tracking spreadsheet](https://docs.google.com/spreadsheets/d/1hsjmCfjx_bOpDNgU5xkm26Te8jMBZIxf6nlqbuKPTOA/edit?gid=0#gid=0)

---

### 🏭 Manufacturing 

Each component of etzee 101 is identified with a structured part number. This system keeps the design, manufacturing, and documentation process clear and consistent.

Part numbers encode relevant details such as the type of part, half side (if applicable), switch profile (if applicable), and number of key swith columns (also if applicable).
Some parts may omit certain fields when they're not relevant by using value `U`.

Part No. format:

```text
XXX-SX-PX-WX
^-^ ^^ ^^ ^^
|   |  |   |
|   |  |   +--- (W) Number of key switch column
|   |  +------- (P) Keyboard key switch profile
|   +---------- (S) Keyboard half side designator
+-------------- Unique part identifier code

(W) -> 5, 6, U
(P) -> [N]ormal, [L]ow, U
(S) -> [L]eft, [R]ight, U
```

###### 3D printing

| Part No. | Version | Material | Status     | Notes |
| -------- | ------- | -------- | ---------- | ----- |
| TP-L-6-N | v1.4    | PLA      | ✅ Printed |       |

### 🧠 Firmware

Open-source and fully customizable firmware based on **[QMK](https://qmk.fm/)** or **[ZMK](https://zmk.dev/)** (TBD).

- Support for split communication (I²C / serial)
- Rotary encoder support
- Display integration (e.g., OLED or e-paper modules)
- Layer-based layouts
- Hotkey macros and developer-friendly tweaks

*Firmware development is ongoing — contributions welcome!*

---

### 🖌️ Graphical design

- Visual identity inspired by **monospace typography** and **Morse code** rhythm  
- Brand assets (logos, iconography) are optimized for both digital and physical media  
- Aesthetic: clean, modular, developer-native  

> Fonts used: JetBrains Mono, IBM Plex Mono, Recursive  
> Logo sketching and refinement in progress — see `/design` folder for prototypes

---

### 🚧 Roadmap

- [ ] Publish full STL/STEP parts
- [ ] Complete first full assembly
- [ ] Finalize firmware base layer
- [ ] Launch landing page
- [ ] Get initial community feedback
- [ ] Open preorders

---

### 🤝 Contributing

Whether you're a firmware nerd, a 3D-printing wizard, or just someone with strong opinions about keyboards — you're welcome to help shape **etzee 101**.

Pull requests, issues, and ideas encouraged.

---

### 🛰️ License

Open-source hardware & software. Final license TBA. Likely CERN-OHL or MIT.

---

> Created with intent. Designed for flow.  
> **etzee 101** — the first signal in a new developer ecosystem.
