"""
play_pngs.py
从指定文件夹读取所有 .png 图片，按文件名末尾数字排序，
以每秒 2 帧的速度循环播放动画。

用法:
    python play_pngs.py                    # 默认读取当前目录
    python play_pngs.py /path/to/pngs      # 指定目录
"""

import sys
import os
import re
import glob
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from PIL import Image
import cv2
import numpy as np

def extract_trailing_number(filename):
    """提取文件名（不含扩展名）末尾的数字，用于排序。"""
    stem = os.path.splitext(os.path.basename(filename))[0]
    match = re.search(r'(\d+)$', stem)
    return int(match.group(1)) if match else -1


def main():
    # # ---------- 注释掉的这一段，用于python脚本和所有png在同一个文件夹的时候----------
    # if len(sys.argv) > 1:
    #     folder = sys.argv[1]
    # else:
    #     folder = os.getcwd()

    # ---------- 1. 确定文件夹路径 ----------
    # 脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) > 1:
        # 命令行参数：可以是绝对路径，也可以是相对于脚本的子文件夹名
        arg = sys.argv[1]
        if os.path.isabs(arg):
            folder = arg
        else:
            folder = os.path.join(script_dir, arg)
    else:
        # 默认：脚本同级下名为 "pngs" 的文件夹（按需修改名称）
        folder = os.path.join(script_dir, 'bfs_0317')

    # ---------- 2. 收集并排序 PNG ----------
    png_files = glob.glob(os.path.join(folder, '*.png'))
    if not png_files:
        print(f"错误: 在 '{folder}' 中未找到任何 .png 文件。")
        sys.exit(1)

    png_files.sort(key=extract_trailing_number)
    print(f"共找到 {len(png_files)} 张 PNG，排序后顺序:")
    for f in png_files:
        print(f"  {os.path.basename(f)}")

    # ---------- 3. 预加载所有图片 ----------
    images = []
    for f in png_files:
        img = Image.open(f)
        images.append(img)

    # ---------- 4. 用 matplotlib 动画播放 ----------
    fps = 5                       # 每秒帧数
    interval_ms = 1000 // fps     # 帧间隔（毫秒）

    fig, ax = plt.subplots()
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    im_display = ax.imshow(images[0])
    title_text = ax.set_title(os.path.basename(png_files[0]), fontsize=10)

    def update(frame_idx):
        im_display.set_data(images[frame_idx])
        title_text.set_text(
            f"{os.path.basename(png_files[frame_idx])}  "
            f"[{frame_idx + 1}/{len(images)}]"
        )
        return [im_display, title_text]

    ani = animation.FuncAnimation(
        fig,
        update,
        frames=len(images),
        interval=interval_ms,
        blit=False,
        repeat=True          # 循环播放
    )


    # ---------- 5. 保存为 AVI 视频 ----------
    output_path = os.path.join(script_dir, 'output.avi')
    writer = animation.FFMpegWriter(fps=fps, codec='mjpeg')
    print(f"正在保存视频到: {output_path} ...")
    ani.save(output_path, writer=writer)
    print("视频保存完成！")

    plt.show()


if __name__ == '__main__':
    main()