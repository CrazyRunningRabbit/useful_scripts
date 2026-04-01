import subprocess
from pathlib import Path

# 输入文件夹
input_folder = Path(r"C:\000coding\000usefultools\260401 mp3处理")

# 输出文件夹
output_folder = input_folder / "mp3_output"
output_folder.mkdir(exist_ok=True)

# 支持的视频格式
video_extensions = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".m4v",
    ".webm",
    ".flv"
]

for file in input_folder.rglob("*"):
    
    if file.suffix.lower() in video_extensions:

        output_file = output_folder / (file.stem + ".mp3")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(file),
            "-vn",                  # 不要视频
            "-acodec", "libmp3lame",
            "-q:a", "2",            # 高质量
            str(output_file)
        ]

        print("Processing:", file)
        subprocess.run(cmd)

print("全部转换完成")