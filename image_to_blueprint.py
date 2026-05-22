from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from blueprint_model import Blueprint, PixelBlock


def image_to_blueprint(input_path: str, output_path: str, width: int, height: int) -> Blueprint:
    # Load original image at full resolution and perform box-average sampling
    src = Image.open(input_path).convert("RGBA")
    src_w, src_h = src.size
    src_px = src.load()

    blocks: list[PixelBlock] = []

    # For each target pixel, compute the source rectangle that maps to it
    for ty in range(height):
        for tx in range(width):
            # source rect (left, top, right, bottom)
            left = int(tx * src_w / width)
            right = int((tx + 1) * src_w / width)
            top = int(ty * src_h / height)
            bottom = int((ty + 1) * src_h / height)
            if right <= left: right = left + 1
            if bottom <= top: bottom = top + 1

            r_sum = g_sum = b_sum = a_sum = 0
            count = 0
            for sy in range(top, bottom):
                for sx in range(left, right):
                    r, g, b, a = src_px[sx, sy]
                    r_sum += r
                    g_sum += g
                    b_sum += b
                    a_sum += a
                    count += 1

            if count == 0:
                continue

            # Average color across the sampled box
            r_avg = int(r_sum / count)
            g_avg = int(g_sum / count)
            b_avg = int(b_sum / count)
            a_avg = int(a_sum / count)

            # Skip nearly-transparent / empty pixels
            if a_avg < 2:
                continue

            # Standard coordinate storage: (0,0) is top-left in the grid
            # Navigation logic (blueprint.py) will handle 'bottom-left first' traversal
            blocks.append(PixelBlock(x=tx, y=ty, color=f"#{r_avg:02X}{g_avg:02X}{b_avg:02X}"))

    blueprint = Blueprint(resolution=(width, height), blocks=blocks)
    blueprint.save(output_path)
    return blueprint


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert an image into a blueprint JSON file.")
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output blueprint path")
    parser.add_argument("--width", type=int, default=32, help="Target width")
    parser.add_argument("--height", type=int, default=32, help="Target height")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    image_to_blueprint(args.input, args.output, args.width, args.height)
    print(f"Blueprint saved to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()