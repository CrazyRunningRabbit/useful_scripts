from pathlib import Path
import subprocess
import sys
import tempfile


def merge_mp3(folder, output_name="merged.mp3", ffmpeg_path="ffmpeg"):
    folder = Path(folder)

    mp3_files = sorted(folder.glob("*.mp3"))

    if len(mp3_files) < 2:
        print("Need at least 2 mp3 files")
        return

    print("Files to merge:")
    for f in mp3_files:
        print(f.name)

    # 创建临时文件列表
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        list_file = Path(f.name)

        for mp3 in mp3_files:
            f.write(f"file '{mp3.as_posix()}'\n")

    output_file = folder / output_name

    cmd = [
        ffmpeg_path,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_file)
    ]

    subprocess.run(cmd)

    print("Merged to:", output_file)


if __name__ == "__main__":
    folder = r"C:\000coding\000usefultools\260401 mp3处理"
    merge_mp3(folder)