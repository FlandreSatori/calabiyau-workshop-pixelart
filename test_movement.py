import time
import mss
from pydd import PyDD
from build_config import BuildConfig
from vision_core import VisionCore
from movement_controller import MovementController

def main():
    # 初始化组件
    config = BuildConfig(blueprint_path="")
    dd = PyDD(config.dd_dll_path)
    
    # 动态检测监视器数量，防止索引越界
    vision = VisionCore(roi_size=config.roi_size, exe_name='Calabiyau-Win64-Shipping.exe')
    movement = MovementController(dd, vision)

    print("🚀 5秒后开始纯移动测试（无染色）：上2 -> 右3 -> 下4 -> 左5")
    for i in range(5, 0, -1):
        print(f"倒计时 {i} 秒")
        time.sleep(1)

    # 1. 确保初始使用铁板以触发绿色准心跳变检测
    dd.key_press("1")
    time.sleep(0.5)

    def place_block():
        """放置方块并切回铁板用于后续追踪"""
        print("   🔨 放置方块: 切换到2槽位 -> 左键点击 -> 切换回1槽位")
        dd.key_press("2")
        time.sleep(0.3)
        dd.mouse_click("left")
        time.sleep(0.3)
        dd.key_press("1")
        time.sleep(0.5)

    def move_up(blocks: int):
        print(f"\n⬆️ 开始向上移动 {blocks} 格...")
        for i in range(blocks):
            # 纵向目前通过固定时长按键移动（跳跃/下降）
            movement.move_to_next_block(config.vertical_up_key, timeout=10.0)
            time.sleep(0.5)
            place_block()

    def move_right(blocks: int):
        print(f"\n➡️ 开始向右移动 {blocks} 格...")
        for i in range(blocks):
            movement.move_to_next_block(config.horizontal_right_key, timeout=10.0)
            time.sleep(0.5)
            place_block()

    def move_down(blocks: int):
        print(f"\n⬇️ 开始向下移动 {blocks} 格...")
        for i in range(blocks):
            movement.move_to_next_block(config.vertical_down_key, timeout=10.0)
            time.sleep(0.5)
            place_block()

    def move_left(blocks: int):
        print(f"\n⬅️ 开始向左移动 {blocks} 格...")
        for i in range(blocks):
            movement.move_to_next_block(config.horizontal_left_key, timeout=10.0)
            time.sleep(0.5)
            place_block()

    # 原位先放一个（根据需求：移动路上每一格放置，起点看是否需要，暂按题目要求处理为21移动后放置）
    # 执行移动指令
    move_up(2)
    move_right(3)
    move_down(4)
    move_left(5)

    print("\n✅ 所有移动与放置测试完成！")

if __name__ == "__main__":
    main()