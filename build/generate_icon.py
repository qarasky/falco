"""Render the original Falco mark into desktop icon formats (requires Pillow).

The SVG in editor/assets is the editable source. This small renderer uses its
same geometric shapes, without requiring an SVG rendering library at build time.
Run: python build/generate_icon.py
"""
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw


def render(size: int) -> Image.Image:
    source = Path(__file__).resolve().parent.parent / "editor" / "assets" / "falco.svg"
    scale = size * 4 / 1024
    image = Image.new("RGBA", (size * 4, size * 4))
    draw = ImageDraw.Draw(image)
    for shape in ET.parse(source).getroot():
        tag = shape.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            x, y, width, height, radius = (float(shape.attrib[k]) * scale for k in ("x", "y", "width", "height", "rx"))
            draw.rounded_rectangle((x, y, x + width, y + height), radius, fill=shape.attrib["fill"])
        elif tag == "path":
            # The source deliberately contains only M/L/Z polygon paths.
            coords = shape.attrib["d"].replace("M", "").replace("L", "").replace("Z", "").split()
            values = [float(value) * scale for value in coords]
            draw.polygon(list(zip(values[::2], values[1::2])), fill=shape.attrib["fill"])
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    assets = Path(__file__).resolve().parent.parent / "editor" / "assets"
    image = render(1024)
    image.save(assets / "falco.png")
    render(64).save(assets / "falco-64.png")
    image.save(assets / "falco.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    image.save(assets / "falco.icns")


if __name__ == "__main__":
    main()
