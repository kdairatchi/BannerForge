# BannerForge  
### Banner Creator CLI for Developers, Frameworks & Labs  
*by kdairatchi*

---

### Overview
BannerForge is a cross-platform CLI tool for generating high-quality banners in **ASCII**, **SVG**, and **PNG** formats.  
It’s designed for developers who want their frameworks, CLIs, or documentation to have a **distinct visual identity** — fast, reproducible, and scriptable.

Use it to brand tools, build CI-generated assets, or design dark-themed cyber banners for professional repos.

---

### Key Features
- **Multi-format output:** ASCII, SVG, PNG, or all at once.  
- **Professional palettes:** pre-defined “stealth”, “ember”, and “neon” themes.  
- **AI-ready:** optional Gemini / LLM stub to generate creative taglines offline-safe.  
- **Batch processing:** feed JSON/YAML spec files for bulk generation.  
- **No fluff:** zero dependencies beyond `click`, `pyfiglet`, and `Pillow`.  
- **Portable:** runs anywhere Python 3.11+ is available.

---

### Installation
```bash
git clone https://github.com/kdairatchi/bannerforge.git
cd bannerforge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
````

---

### Quick Usage

**Generate an ASCII banner**

```bash
python forge.py ascii "IntelThief" -f slant
```

**Generate an SVG banner**

```bash
python forge.py svg "IntelThief" \
  --subtitle "Information Reconnaissance & Intelligence Framework" \
  --out banners/intelthief.svg
```

**Generate a PNG banner**

```bash
python forge.py png "IntelThief" \
  --subtitle "See What Others Miss" \
  --out banners/intelthief.png
```

**Generate all formats at once**

```bash
python forge.py combo "IntelThief" --prefix release_assets
```

**Batch from JSON**

```bash
python forge.py batch examples/batch_specs.json --outdir assets/
```

---

### Folder Structure

```
bannerforge/
│
├── bannerforge.py          # main CLI
├── requirements.txt
├── templates/              # SVG / ASCII style templates
│   ├── ribbon.svg
│   ├── radar.svg
│   ├── grid.svg
│   └── raven.svg
├── palettes/               # JSON color schemes
│   ├── stealth.json
│   ├── ember.json
│   └── neon.json
├── examples/               # Example banners & batch specs
│   ├── intelthief.svg
│   ├── filefang.svg
│   └── batch_specs.json
└── README.md
```

---

### Template Design Ideas

| Template       | Description                                                   | File                    |
| -------------- | ------------------------------------------------------------- | ----------------------- |
| **ribbon.svg** | Wavy background stripe with gradient accent.                  | `/templates/ribbon.svg` |
| **radar.svg**  | Circular radar lines & center icon — perfect for cyber tools. | `/templates/radar.svg`  |
| **grid.svg**   | Subtle matrix-grid background for developer tools.            | `/templates/grid.svg`   |
| **raven.svg**  | Polygonal bird head for “intel” or reconnaissance themes.     | `/templates/raven.svg`  |

Each SVG uses placeholders like:

```xml
{{TEXT}}
{{SUBTITLE}}
{{ACCENT_COLOR}}
```

These get dynamically replaced by `bannerforge.py`.

---

### Example Palette JSON

`/palettes/stealth.json`

```json
{
  "bg": "#0a0f14",
  "accent": "#00ffff",
  "text": "#ffffff",
  "muted": "#9aa4ad"
}
```

---

### Logo Design Guide

**Name:** `BannerForge`
**Icon Concept:**

* **Forge anvil + spark** — symbolizes crafting digital banners.
* **Monogram “BF”** in geometric sans font (Orbitron or Exo 2).
* Optional subtle **hex pattern or circuit lines** in background.

**Color Systems:**

| Theme   | Primary   | Secondary | Accent    |
| ------- | --------- | --------- | --------- |
| Stealth | `#0a0f14` | `#1b1f23` | `#00ffff` |
| Ember   | `#0f0a07` | `#2f1b14` | `#ff8a3b` |
| Neon    | `#000015` | `#101040` | `#7c3fff` |

**Typography:**

* Display font: *Orbitron Bold or Exo 2 SemiBold*
* Body font: *Inter Regular*
* All uppercase, tight spacing.

**Layout:**

> Centered “BannerForge” text with a glowing underline (accent color).
> Below it: tagline — *“Create, Customize, Deploy — in One Line”*

You can generate an initial SVG logo with this command:

```bash
python bannerforge.py svg "BannerForge" \
  --subtitle "Create, Customize, Deploy — in One Line" \
  --palette ember --out logo/bannerforge.svg
```

---

### Integration Ideas

* **Docs automation:** run BannerForge in your CI to update project logos automatically.
* **CLI branding:** import banners into your own framework startup screens.
* **Dark-mode dashboards:** use SVG banners as hero headers in docs sites.
* **Labs:** generate unique banners for each internal lab environment.

---

### Roadmap

* [ ] Add animated ASCII pulse banner.
* [ ] Add JSON-driven multi-font template loader.
* [ ] Implement Gemini API adapter for creative subtitles.
* [ ] Publish `pip install bannerforge`.
* [ ] Build a web-UI wrapper with Flask + Tailwind.

---

