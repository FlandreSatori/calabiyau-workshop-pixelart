from __future__ import annotations

import argparse
import time

from blueprint_model import Blueprint
from build_config import BuildConfig
from fsm_engine import BuildContext, BuildFSM
from pydd import PyDD
from vision_core import VisionCore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the pixel art auto builder.")
    parser.add_argument("--blueprint", required=True, help="Blueprint JSON path")
    parser.add_argument("--dll", default="./dd.54900.dll", help="DD DLL path")
    parser.add_argument("--monitor", type=int, default=2, help="Capture monitor index")
    parser.add_argument("--roi-size", type=int, default=315, help="Vision ROI size")
    parser.add_argument("--color-input-x", type=int, default=2157, help="HEX input X coordinate")
    parser.add_argument("--color-input-y", type=int, default=930, help="HEX input Y coordinate")
    parser.add_argument("--confirm-button-x", type=int, default=2222, help="Confirm button X coordinate")
    parser.add_argument("--confirm-button-y", type=int, default=1052, help="Confirm button Y coordinate")
    parser.add_argument("--checkpoint", default=".temp_checkpoint.json", help="Checkpoint file path")
    parser.add_argument("--dry-run", action="store_true", help="Run without actual mouse/keyboard actions")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    blueprint = Blueprint.load(args.blueprint)
    config = BuildConfig(
        blueprint_path=args.blueprint,
        dd_dll_path=args.dll,
        monitor_index=args.monitor,
        roi_size=args.roi_size,
        color_input_x=args.color_input_x,
        color_input_y=args.color_input_y,
        confirm_button_x=args.confirm_button_x,
        confirm_button_y=args.confirm_button_y,
        checkpoint_path=args.checkpoint,
        dry_run=args.dry_run,
    )
    dd = None if config.dry_run else PyDD(config.dd_dll_path)
    vision = VisionCore(roi_size=config.roi_size, exe_name='Calabiyau-Win64-Shipping.exe')
    context = BuildContext(
        blueprint=blueprint,
        color_input_x=config.color_input_x,
        color_input_y=config.color_input_y,
        confirm_button_x=config.confirm_button_x,
        confirm_button_y=config.confirm_button_y,
    )
    if dd is None:
        class _DryRunDD:
            def mouse_click(self, *args, **kwargs):
                print(f"[DRY-RUN] mouse_click args={args} kwargs={kwargs}")

            def mouse_move_relative(self, *args, **kwargs):
                print(f"[DRY-RUN] mouse_move_relative args={args} kwargs={kwargs}")

            def key_press(self, *args, **kwargs):
                print(f"[DRY-RUN] key_press args={args} kwargs={kwargs}")

            def key_down(self, *args, **kwargs):
                print(f"[DRY-RUN] key_down args={args} kwargs={kwargs}")

            def key_up(self, *args, **kwargs):
                print(f"[DRY-RUN] key_up args={args} kwargs={kwargs}")

            def key_combination(self, *args, **kwargs):
                print(f"[DRY-RUN] key_combination args={args} kwargs={kwargs}")

        dd = _DryRunDD()

    print("🚀 即将开始自动搭建！请在 5 秒内切换回游戏...")
    for i in range(5, 0, -1):
        print(f"倒计时 {i} 秒")
        time.sleep(1)

    fsm = BuildFSM(dd, vision, context, config)
    fsm.run()


if __name__ == "__main__":
    main()