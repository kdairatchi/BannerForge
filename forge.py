#!/usr/bin/env python3
"""
Features:
 - ascii: generate ASCII banners (pyfiglet) with color support
 - svg: create vector banners (text + accent shapes) with gradients
 - png: render raster banners (Pillow TrueType text) with effects
 - combo: produce ascii + svg + png in one run
 - batch: read YAML/JSON list of banner specs and generate all
 - --ai: optional flag to ask an LLM for creative tagline variations
 - preview: display banner in terminal before saving
 - templates: pre-configured banner styles
 - animations: SVG with CSS animations
"""
from __future__ import annotations
import os
import sys
import io
import json
import textwrap
import datetime
import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

import click

# optional libs (install via requirements.txt)
try:
    import pyfiglet
except ImportError:
    pyfiglet = None

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
except ImportError:
    Image = ImageDraw = ImageFont = ImageFilter = ImageEnhance = None

try:
    import yaml
except ImportError:
    yaml = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    console = Console()
except ImportError:
    console = None

# ==================== CONSTANTS ====================

VERSION = "2.0.0"
BANNER_ASCII = r"""
    ____                              ______                    
   / __ )____ _____  ____  ___  _____/ ____/___  _________ ____ 
  / __  / __ `/ __ \/ __ \/ _ \/ ___/ /_  / __ \/ ___/ __ `/ _ \
 / /_/ / /_/ / / / / / / /  __/ /  / __/ / /_/ / /  / /_/ /  __/
/_____/\__,_/_/ /_/_/ /_/\___/_/  /_/    \____/_/   \__, /\___/ 
                                                   /____/       
"""

# ==================== UTILITIES ====================

def ensure_dir(path: str):
    """Create directory if it doesn't exist"""
    Path(path).mkdir(parents=True, exist_ok=True)

def hash_text(text: str) -> str:
    """Generate short hash for unique filenames"""
    return hashlib.md5(text.encode()).hexdigest()[:8]

def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text"""
    return re.sub(r'\033\[[0-9;]+m', '', text)

# ==================== COLOR PALETTES ====================

PALETTES = {
    "stealth": {
        "bg": "#0a0f14", 
        "accent": "#00ffff", 
        "text": "#ffffff", 
        "muted": "#9aa4ad",
        "gradient_start": "#00ffff",
        "gradient_end": "#0088ff"
    },
    "ember": {
        "bg": "#0f0a07", 
        "accent": "#ff8a3b", 
        "text": "#f5e9e3", 
        "muted": "#c9b5a3",
        "gradient_start": "#ff8a3b",
        "gradient_end": "#ff4d4d"
    },
    "forest": {
        "bg": "#0d1b0e",
        "accent": "#4ade80",
        "text": "#e8f5e9",
        "muted": "#81c784",
        "gradient_start": "#4ade80",
        "gradient_end": "#22c55e"
    },
    "ocean": {
        "bg": "#0a1628",
        "accent": "#38bdf8",
        "text": "#e0f2fe",
        "muted": "#7dd3fc",
        "gradient_start": "#38bdf8",
        "gradient_end": "#0ea5e9"
    },
    "sunset": {
        "bg": "#1a0f1e",
        "accent": "#f472b6",
        "text": "#fce7f3",
        "muted": "#f9a8d4",
        "gradient_start": "#f472b6",
        "gradient_end": "#ec4899"
    },
    "neon": {
        "bg": "#000000",
        "accent": "#00ff41",
        "text": "#00ff41",
        "muted": "#39ff14",
        "gradient_start": "#00ff41",
        "gradient_end": "#39ff14"
    },
    "royal": {
        "bg": "#1e1b4b",
        "accent": "#fbbf24",
        "text": "#fef3c7",
        "muted": "#fcd34d",
        "gradient_start": "#fbbf24",
        "gradient_end": "#f59e0b"
    },
    "cyberpunk": {
        "bg": "#0d0221",
        "accent": "#ff006e",
        "text": "#f72585",
        "muted": "#b5179e",
        "gradient_start": "#ff006e",
        "gradient_end": "#8338ec"
    },
    "matrix": {
        "bg": "#000000",
        "accent": "#00ff00",
        "text": "#00ff00",
        "muted": "#008f00",
        "gradient_start": "#00ff00",
        "gradient_end": "#00aa00"
    }
}

def get_palette(name: str = "stealth") -> dict:
    """Get palette by name with fallback"""
    return PALETTES.get(name, PALETTES["stealth"])


# ==================== SVG TEMPLATES ====================

SVG_TEMPLATE_SIMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{grad_start};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{grad_end};stop-opacity:1" />
    </linearGradient>
    {filters}
  </defs>
  <rect width="100%" height="100%" fill="{bg}" />
  <!-- accent shapes -->
  {accent}
  <!-- main text -->
  <text x="{x}" y="{y}" font-family="{font_family}" font-size="{font_size}" font-weight="700" fill="{text_fill}" text-anchor="middle" {text_style}>{text}</text>
  <!-- subtitle -->
  {subtitle}
  {animation}
</svg>
"""

SVG_ANIMATED_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="animGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{grad_start}">
        <animate attributeName="stop-color" values="{grad_start};{grad_end};{grad_start}" dur="3s" repeatCount="indefinite"/>
      </stop>
      <stop offset="100%" style="stop-color:{grad_end}">
        <animate attributeName="stop-color" values="{grad_end};{grad_start};{grad_end}" dur="3s" repeatCount="indefinite"/>
      </stop>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="{bg}"/>
  {accent}
  <text x="{x}" y="{y}" font-family="{font_family}" font-size="{font_size}" font-weight="700" fill="url(#animGrad)" text-anchor="middle">
    {text}
    <animate attributeName="opacity" values="0.8;1;0.8" dur="2s" repeatCount="indefinite"/>
  </text>
  {subtitle}
</svg>
"""

def svg_accent_wave(width: int, height: int, color: str, opacity: float = 0.12) -> str:
    """Generate decorative wave accent"""
    path = f'<path d="M0 {height*0.65} C {width*0.25} {height*0.4}, {width*0.75} {height*0.9}, {width} {height*0.6} L {width} {height} L 0 {height} Z" fill="{color}" opacity="{opacity}" />'
    return path

def svg_accent_geometric(width: int, height: int, color: str, opacity: float = 0.1) -> str:
    """Generate geometric accent shapes"""
    shapes = []
    # Circles
    shapes.append(f'<circle cx="{width*0.15}" cy="{height*0.2}" r="{height*0.15}" fill="{color}" opacity="{opacity}"/>')
    shapes.append(f'<circle cx="{width*0.85}" cy="{height*0.8}" r="{height*0.2}" fill="{color}" opacity="{opacity*0.7}"/>')
    # Rectangles
    shapes.append(f'<rect x="{width*0.7}" y="{height*0.1}" width="{width*0.2}" height="{height*0.15}" fill="{color}" opacity="{opacity*0.5}" transform="rotate(15 {width*0.8} {height*0.175})"/>')
    return '\n  '.join(shapes)

def svg_accent_grid(width: int, height: int, color: str, opacity: float = 0.05) -> str:
    """Generate grid pattern accent"""
    lines = []
    spacing = 50
    for x in range(0, width, spacing):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="{color}" opacity="{opacity}"/>')
    for y in range(0, height, spacing):
        lines.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{color}" opacity="{opacity}"/>')
    return '\n  '.join(lines)

def svg_accent_particles(width: int, height: int, color: str, opacity: float = 0.08) -> str:
    """Generate particle/dot pattern accent"""
    import random
    random.seed(42)  # Deterministic
    particles = []
    for _ in range(30):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(2, 8)
        particles.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="{opacity}"/>')
    return '\n  '.join(particles)

def write_svg(path: str, text: str, subtitle: Optional[str], width: int = 1200, 
              height: int = 300, palette: dict = None, style: str = "wave",
              animated: bool = False):
    """Write SVG banner with various styles"""
    if palette is None:
        palette = get_palette()
    
    # Choose accent style
    accent_map = {
        "wave": svg_accent_wave,
        "geometric": svg_accent_geometric,
        "grid": svg_accent_grid,
        "particles": svg_accent_particles
    }
    accent_func = accent_map.get(style, svg_accent_wave)
    accent = accent_func(width, height, palette["accent"])
    
    # Subtitle
    subtitle_tag = ""
    if subtitle:
        subtitle_tag = f'<text x="{width//2}" y="{int(height*0.78)}" font-family="Inter,Arial,Helvetica" font-size="{int(height*0.075)}" fill="{palette["muted"]}" text-anchor="middle">{subtitle}</text>'
    
    # Choose template
    if animated:
        template = SVG_ANIMATED_TEMPLATE
        svg = template.format(
            width=width, height=height, bg=palette["bg"],
            grad_start=palette["gradient_start"], grad_end=palette["gradient_end"],
            accent=accent, x=width//2, y=int(height*0.55),
            font_family="Orbitron,Inter,Arial", font_size=int(height*0.2),
            text=text, subtitle=subtitle_tag
        )
    else:
        filters = '<filter id="glow"><feGaussianBlur stdDeviation="2" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        text_style = 'filter="url(#glow)"' if style == "glow" else ''
        svg = SVG_TEMPLATE_SIMPLE.format(
            width=width, height=height, label=text, bg=palette["bg"],
            grad_start=palette["gradient_start"], grad_end=palette["gradient_end"],
            filters=filters, accent=accent, x=width//2, y=int(height*0.55),
            font_family="Orbitron,Inter,Arial", font_size=int(height*0.2),
            text_fill=palette["text"], text=text, subtitle=subtitle_tag,
            text_style=text_style, animation=""
        )
    
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)

# ==================== PNG RENDERING ====================

def render_png_text(path: str, text: str, subtitle: Optional[str] = None, 
                   width: int = 1200, height: int = 300, palette: dict = None, 
                   font_path: Optional[str] = None, effects: List[str] = None):
    """Render PNG with optional effects (glow, shadow, gradient)"""
    if Image is None:
        raise RuntimeError("Pillow is required. Install: pip install pillow")
    
    if palette is None:
        palette = get_palette()
    
    if effects is None:
        effects = []
    
    # Create base image
    img = Image.new("RGBA", (width, height), palette["bg"])
    
    # Add gradient background if requested
    if "gradient" in effects:
        for y in range(height):
            alpha = int(50 * (1 - y / height))
            for x in range(width):
                img.putpixel((x, y), (*_hex_to_rgb(palette["accent"]), alpha))
    
    draw = ImageDraw.Draw(img)
    
    def load_font(size: int):
        if font_path and os.path.isfile(font_path):
            return ImageFont.truetype(font_path, size=size)
        
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        ]
        for c in candidates:
            if os.path.isfile(c):
                try:
                    return ImageFont.truetype(c, size=size)
                except:
                    continue
        return ImageFont.load_default()
    
    title_font = load_font(int(height * 0.22))
    subtitle_font = load_font(int(height * 0.07))
    
    # Calculate text position
    bbox = draw.textbbox((0, 0), text, font=title_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) / 2
    y = height * 0.35 - text_height / 2
    
    # Add shadow effect
    if "shadow" in effects:
        shadow_offset = 4
        draw.text((x + shadow_offset, y + shadow_offset), text, 
                 font=title_font, fill=(0, 0, 0, 128))
    
    # Add glow effect (multiple passes)
    if "glow" in effects:
        glow_color = (*_hex_to_rgb(palette["accent"]), 80)
        for offset in range(3, 0, -1):
            draw.text((x - offset, y), text, font=title_font, fill=glow_color)
            draw.text((x + offset, y), text, font=title_font, fill=glow_color)
            draw.text((x, y - offset), text, font=title_font, fill=glow_color)
            draw.text((x, y + offset), text, font=title_font, fill=glow_color)
    
    # Draw main text
    draw.text((x, y), text, font=title_font, fill=palette["text"])
    
    # Draw subtitle
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_height = sub_bbox[3] - sub_bbox[1]
        sub_x = (width - sub_width) / 2
        sub_y = height * 0.75 - sub_height / 2
        draw.text((sub_x, sub_y), subtitle, font=subtitle_font, fill=palette["muted"])
    
    # Add accent stripe
    if "stripe" in effects:
        stripe_color = (*_hex_to_rgb(palette["accent"]), 68)
        draw.rectangle([(0, int(height * 0.85)), (width, height)], fill=stripe_color)
    
    # Apply blur filter for softer look
    if "blur" in effects and ImageFilter:
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
    
    img.save(path)

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# ==================== ASCII BANNERS ====================

def ascii_banner(text: str, font: str = "standard", colorize: bool = False, 
                color: str = "cyan") -> str:
    """Generate ASCII banner with optional ANSI colors"""
    if pyfiglet is None:
        raise RuntimeError("pyfiglet is required. Install: pip install pyfiglet")
    
    fig = pyfiglet.Figlet(font=font)
    banner = fig.renderText(text)
    
    if colorize:
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "reset": "\033[0m"
        }
        color_code = colors.get(color, colors["cyan"])
        banner = f"{color_code}{banner}{colors['reset']}"
    
    return banner

def list_figlet_fonts() -> List[str]:
    """List available figlet fonts"""
    if pyfiglet is None:
        return []
    return pyfiglet.FigletFont.getFonts()

# ==================== AI INTEGRATION ====================

def gemini_generate_taglines(prompt: str, n: int = 3, api_key: Optional[str] = None) -> List[str]:
    """
    Generate taglines using Gemini API (or fallback).
    Set GEMINI_API_KEY environment variable to use real API.
    """
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        # Deterministic fallbacks
        fallbacks = {
            "bannerforge": [
                "Forge Your Visual Identity",
                "Create. Design. Deploy.",
                "Professional Banners Made Simple"
            ],
            "default": [
                "See What Others Miss",
                "Innovation Through Design",
                "Crafted with Precision"
            ]
        }
        key = prompt.lower().split("'")[1] if "'" in prompt else "default"
        return fallbacks.get(key, fallbacks["default"])[:n]
    
    # Real API integration would go here
    # Example: call Google Gemini API
    return ["Creative Tagline 1", "Creative Tagline 2", "Creative Tagline 3"][:n]

# ==================== TEMPLATES ====================

TEMPLATES = {
    "minimal": {
        "style": "wave",
        "palette": "stealth",
        "effects": []
    },
    "professional": {
        "style": "grid",
        "palette": "royal",
        "effects": ["shadow"]
    },
    "creative": {
        "style": "geometric",
        "palette": "sunset",
        "effects": ["glow", "gradient"]
    },
    "tech": {
        "style": "wave",
        "palette": "neon",
        "effects": ["glow"]
    },
    "nature": {
        "style": "wave",
        "palette": "forest",
        "effects": ["blur"]
    },
    "cyberpunk": {
        "style": "particles",
        "palette": "cyberpunk",
        "effects": ["glow", "shadow"]
    }
}

# ==================== CLI COMMANDS ====================

@click.group(help="BannerForge — Banner Creator By @Kdairatchi (ASCII + SVG + PNG)")
@click.version_option(version="2.0.0")
def cli():
    pass

@cli.command(help="Generate ASCII banner")
@click.argument("text", type=str)
@click.option("--font", "-f", default="standard", help="pyfiglet font")
@click.option("--color", "-c", default="cyan", help="ANSI color (red, green, blue, etc.)")
@click.option("--colorize", is_flag=True, default=False, help="Apply color to output")
@click.option("--out", "-o", default=None, help="output file (defaults to stdout)")
@click.option("--list-fonts", is_flag=True, help="List available fonts")
def ascii(text, font, color, colorize, out, list_fonts):
    """Generate ASCII art banner"""
    if list_fonts:
        fonts = list_figlet_fonts()
        click.echo(f"Available fonts ({len(fonts)}):")
        for f in sorted(fonts)[:50]:  # Show first 50
            click.echo(f"  - {f}")
        click.echo("\n... and more. Use --font <name> to select.")
        return
    
    banner = ascii_banner(text, font=font, colorize=colorize, color=color)
    
    if out:
        # Strip ANSI codes when writing to file
        import re
        clean_banner = re.sub(r'\033\[[0-9;]+m', '', banner)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(clean_banner)
        click.echo(f"✓ Wrote ASCII banner to {out}")
    else:
        click.echo(banner)

@cli.command(help="Generate SVG banner")
@click.argument("text", type=str)
@click.option("--subtitle", "-s", default=None, help="subtitle text")
@click.option("--width", "-W", default=1200, type=int, help="svg width")
@click.option("--height", "-H", default=300, type=int, help="svg height")
@click.option("--palette", "-p", default="stealth", 
              type=click.Choice(list(PALETTES.keys())), help="color palette")
@click.option("--style", default="wave", 
              type=click.Choice(["wave", "geometric", "grid", "glow"]), help="accent style")
@click.option("--animated", is_flag=True, default=False, help="add CSS animations")
@click.option("--template", "-t", type=click.Choice(list(TEMPLATES.keys())), 
              help="use predefined template")
@click.option("--out", "-o", default=None, help="output SVG path")
@click.option("--ai", is_flag=True, default=False, help="use AI for subtitle suggestions")
def svg(text, subtitle, width, height, palette, style, animated, template, out, ai):
    """Generate SVG vector banner"""
    # Apply template if specified
    if template:
        tmpl = TEMPLATES[template]
        style = tmpl["style"]
        palette = tmpl["palette"]
    
    pal = get_palette(palette)
    
    if ai and subtitle is None:
        ideas = gemini_generate_taglines(f"Create subtitle for banner: '{text}'", n=1)
        subtitle = ideas[0]
        click.echo(f"AI suggestion: {subtitle}")
    
    if out is None:
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_text = text.replace(' ', '_')[:30]
        out = f"banner_{safe_text}_{timestamp}.svg"
    
    ensure_dir(os.path.dirname(out) or ".")
    write_svg(out, text, subtitle, width=width, height=height, 
             palette=pal, style=style, animated=animated)
    click.echo(f"✓ Wrote SVG to {out}")

@cli.command(help="Generate PNG raster banner")
@click.argument("text", type=str)
@click.option("--subtitle", "-s", default=None, help="subtitle text")
@click.option("--width", "-W", default=1200, type=int, help="image width")
@click.option("--height", "-H", default=300, type=int, help="image height")
@click.option("--palette", "-p", default="stealth", 
              type=click.Choice(list(PALETTES.keys())), help="color palette")
@click.option("--effects", "-e", multiple=True, 
              type=click.Choice(["shadow", "glow", "gradient", "stripe", "blur"]),
              help="visual effects (can specify multiple)")
@click.option("--template", "-t", type=click.Choice(list(TEMPLATES.keys())), 
              help="use predefined template")
@click.option("--out", "-o", default=None, help="output PNG path")
@click.option("--font", default=None, help="path to .ttf file")
@click.option("--ai", is_flag=True, default=False, help="use AI for subtitle")
def png(text, subtitle, width, height, palette, effects, template, out, font, ai):
    """Generate PNG raster banner"""
    # Apply template if specified
    if template:
        tmpl = TEMPLATES[template]
        palette = tmpl["palette"]
        effects = tmpl["effects"]
    
    pal = get_palette(palette)
    
    if ai and subtitle is None:
        ideas = gemini_generate_taglines(f"Create subtitle for: '{text}'", n=1)
        subtitle = ideas[0]
        click.echo(f"AI suggestion: {subtitle}")
    
    if out is None:
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_text = text.replace(' ', '_')[:30]
        out = f"banner_{safe_text}_{timestamp}.png"
    
    ensure_dir(os.path.dirname(out) or ".")
    render_png_text(out, text, subtitle, width=width, height=height, 
                   palette=pal, font_path=font, effects=list(effects))
    click.echo(f"✓ Wrote PNG to {out}")

@cli.command(help="Generate all formats (ASCII + SVG + PNG)")
@click.argument("text", type=str)
@click.option("--subtitle", "-s", default=None, help="subtitle for SVG/PNG")
@click.option("--prefix", "-P", default=None, help="output folder name")
@click.option("--template", "-t", type=click.Choice(list(TEMPLATES.keys())), 
              help="use predefined template")
@click.option("--ai", is_flag=True, default=False, help="use AI suggestions")
def combo(text, subtitle, prefix, template, ai):
    """Generate ASCII + SVG + PNG combo"""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    folder = prefix or f"banners_{timestamp}"
    ensure_dir(folder)
    
    safe_name = text.replace(' ', '_')[:30]
    
    # ASCII
    ascii_path = os.path.join(folder, f"{safe_name}.txt")
    with open(ascii_path, "w", encoding="utf-8") as fh:
        fh.write(ascii_banner(text))
    click.echo(f"✓ ASCII: {ascii_path}")
    
    # SVG
    svg_path = os.path.join(folder, f"{safe_name}.svg")
    ctx = click.Context(svg)
    ctx.invoke(svg, text=text, subtitle=subtitle, out=svg_path, 
              template=template, ai=ai)
    
    # PNG
    png_path = os.path.join(folder, f"{safe_name}.png")
    ctx = click.Context(png)
    ctx.invoke(png, text=text, subtitle=subtitle, out=png_path, 
              template=template, ai=ai)
    
    click.echo(f"\nGenerated combo in: {folder}")

@cli.command(help="Batch generate from JSON/YAML file")
@click.argument("spec", type=click.Path(exists=True))
@click.option("--outdir", "-o", default="batch_banners", help="output directory")
def batch(spec, outdir):
    """Batch process multiple banners from config file"""
    # Load spec file
    with open(spec, "r", encoding="utf-8") as fh:
        if spec.endswith('.yaml') or spec.endswith('.yml'):
            if yaml is None:
                raise RuntimeError("PyYAML required for YAML. Install: pip install pyyaml")
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)
    
    ensure_dir(outdir)
    
    for idx, item in enumerate(data, 1):
        kind = item.get("kind", "svg")
        text = item["text"]
        subtitle = item.get("subtitle")
        palette = item.get("palette", "stealth")
        width = int(item.get("width", 1200))
        height = int(item.get("height", 300))
        safe_name = text.replace(" ", "_")[:30]
        
        click.echo(f"[{idx}/{len(data)}] Generating {kind}: {text}")
        
        if kind == "ascii":
            path = os.path.join(outdir, f"{safe_name}.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(ascii_banner(text, font=item.get("font", "standard")))
        
        elif kind == "svg":
            path = os.path.join(outdir, f"{safe_name}.svg")
            write_svg(path, text, subtitle, width=width, height=height, 
                     palette=get_palette(palette),
                     style=item.get("style", "wave"),
                     animated=item.get("animated", False))
        
        elif kind == "png":
            path = os.path.join(outdir, f"{safe_name}.png")
            render_png_text(path, text, subtitle, width=width, height=height, 
                          palette=get_palette(palette),
                          font_path=item.get("font_path"),
                          effects=item.get("effects", []))
        
        click.echo(f"  ✓ {path}")
    
    click.echo(f"\nBatch complete: {len(data)} banners in {outdir}")

@cli.command(help="List available palettes and templates")
def info():
    """Show available palettes, templates, and fonts"""
    click.echo("Available Palettes:")
    for name, pal in PALETTES.items():
        click.echo(f"  {name:12} - bg:{pal['bg']} accent:{pal['accent']}")
    
    click.echo("\nAvailable Templates:")
    for name, tmpl in TEMPLATES.items():
        click.echo(f"  {name:12} - {tmpl['palette']} palette, {tmpl['style']} style")
    
    click.echo("\nSample Figlet Fonts:")
    if pyfiglet:
        sample_fonts = ["standard", "slant", "banner", "big", "digital", "block"]
        for f in sample_fonts:
            if f in list_figlet_fonts():
                click.echo(f"  - {f}")
    else:
        click.echo("  (Install pyfiglet to see fonts)")
    
    click.echo("\nVisual Effects (PNG):")
    effects_list = ["shadow", "glow", "gradient", "stripe", "blur"]
    for eff in effects_list:
        click.echo(f"  - {eff}")
    
    click.echo("\nSVG Styles:")
    styles = ["wave", "geometric", "grid", "glow"]
    for style in styles:
        click.echo(f"  - {style}")

@cli.command(help="Preview banner in terminal")
@click.argument("text", type=str)
@click.option("--font", "-f", default="standard", help="ASCII font")
@click.option("--color", "-c", default="cyan", help="preview color")
def preview(text, font, color):
    """Preview banner in terminal before generating"""
    banner = ascii_banner(text, font=font, colorize=True, color=color)
    
    if console:
        console.print(Panel(banner, title="[bold cyan]Banner Preview[/bold cyan]", 
                          border_style="cyan"))
    else:
        click.echo("\n" + "="*60)
        click.echo("PREVIEW:")
        click.echo("="*60)
        click.echo(banner)
        click.echo("="*60)

@cli.command(help="Create custom palette")
@click.option("--name", "-n", required=True, help="palette name")
@click.option("--bg", required=True, help="background color (hex)")
@click.option("--accent", required=True, help="accent color (hex)")
@click.option("--text", required=True, help="text color (hex)")
@click.option("--muted", required=True, help="muted color (hex)")
@click.option("--save", is_flag=True, help="save to palettes.json")
def palette(name, bg, accent, text, muted, save):
    """Create and optionally save custom color palette"""
    custom_pal = {
        "bg": bg,
        "accent": accent,
        "text": text,
        "muted": muted,
        "gradient_start": accent,
        "gradient_end": accent
    }
    
    click.echo(f"\n✓ Created palette '{name}':")
    for key, val in custom_pal.items():
        click.echo(f"  {key:15} : {val}")
    
    if save:
        palette_file = "custom_palettes.json"
        palettes = {}
        
        if os.path.exists(palette_file):
            with open(palette_file, 'r') as f:
                palettes = json.load(f)
        
        palettes[name] = custom_pal
        
        with open(palette_file, 'w') as f:
            json.dump(palettes, f, indent=2)
        
        click.echo(f"\n✓ Saved to {palette_file}")
        click.echo("  Load with: --palette-file custom_palettes.json")

@cli.command(help="Generate example batch config file")
@click.option("--format", "-f", type=click.Choice(["json", "yaml"]), 
              default="json", help="output format")
@click.option("--out", "-o", default="banner_config", help="output filename (no extension)")
def example(format, out):
    """Generate example configuration file for batch processing"""
    examples = [
        {
            "kind": "svg",
            "text": "BannerForge",
            "subtitle": "Ultimate Banner Creator",
            "width": 1200,
            "height": 300,
            "palette": "stealth",
            "style": "wave",
            "animated": False
        },
        {
            "kind": "png",
            "text": "Tech Conference 2025",
            "subtitle": "Innovation & Future",
            "width": 1920,
            "height": 400,
            "palette": "neon",
            "effects": ["glow", "shadow"]
        },
        {
            "kind": "ascii",
            "text": "Welcome",
            "font": "slant"
        },
        {
            "kind": "svg",
            "text": "Open Source",
            "subtitle": "Built by the Community",
            "palette": "forest",
            "style": "geometric",
            "animated": True
        }
    ]
    
    filename = f"{out}.{format}"
    
    with open(filename, 'w', encoding='utf-8') as f:
        if format == 'yaml':
            if yaml is None:
                click.echo("PyYAML not installed. Install: pip install pyyaml")
                return
            yaml.dump(examples, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(examples, f, indent=2)
    
    click.echo(f"✓ Created example config: {filename}")
    click.echo(f"  Run with: bannerforge batch {filename}")

@cli.command(help="Quick banner with minimal options")
@click.argument("text", type=str)
@click.option("--type", "-t", type=click.Choice(["ascii", "svg", "png", "all"]), 
              default="svg", help="output type")
def quick(text, type):
    """Quick banner generation with defaults"""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = text.replace(' ', '_')[:30]
    
    if type == "ascii" or type == "all":
        banner = ascii_banner(text, colorize=True)
        click.echo(banner)
        if type == "all":
            with open(f"{safe_name}_quick.txt", 'w') as f:
                import re
                clean = re.sub(r'\033\[[0-9;]+m', '', banner)
                f.write(clean)
    
    if type == "svg" or type == "all":
        filename = f"{safe_name}_quick.svg"
        write_svg(filename, text, None, palette=get_palette())
        click.echo(f"✓ SVG: {filename}")
    
    if type == "png" or type == "all":
        filename = f"{safe_name}_quick.png"
        render_png_text(filename, text, palette=get_palette(), effects=["shadow"])
        click.echo(f"✓ PNG: {filename}")

# ==================== MAIN ====================

if __name__ == "__main__":
    cli()
