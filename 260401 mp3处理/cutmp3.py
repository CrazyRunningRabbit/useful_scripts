import os
import subprocess
from pathlib import Path

# 你的文件夹
folder = r"C:\000coding\000usefultools\260401 flac2mp3"

# 截取时间（1分44秒 = 104秒）
duration = 104

# 输出文件夹
output_folder = os.path.join(folder, "cut_mp3")

os.makedirs(output_folder, exist_ok=True)

for file in os.listdir(folder):
    if file.lower().endswith(".mp3"):
        
        input_path = os.path.join(folder, file)
        output_path = os.path.join(output_folder, file)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-t", str(duration),
            "-acodec", "copy",
            output_path
        ]

        print("Processing:", file)
        subprocess.run(cmd)

print("全部完成")