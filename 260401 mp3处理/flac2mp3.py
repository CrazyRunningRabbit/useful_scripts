from pathlib import Path
import subprocess
import shutil
import sys

def convert_flac_to_mp3(folder: str, ffmpeg_path: str = "ffmpeg") -> None:
    """
    Convert all .flac files in a folder (including subfolders) to .mp3.
    Output files are saved next to the original FLAC files.

    Parameters
    ----------
    folder : str
        Root folder to search for FLAC files.
    ffmpeg_path : str
        Path to ffmpeg executable. Default assumes ffmpeg is in PATH.
    """
    root = Path(folder)

    if not root.exists():
        print(f"Folder does not exist: {root}")
        sys.exit(1)

    if shutil.which(ffmpeg_path) is None and not Path(ffmpeg_path).exists():
        print("ffmpeg was not found. Please install ffmpeg or provide its full path.")
        sys.exit(1)

    flac_files = list(root.rglob("*.flac"))

    if not flac_files:
        print("No .flac files found.")
        return

    print(f"Found {len(flac_files)} FLAC file(s).")

    for flac_file in flac_files:
        mp3_file = flac_file.with_suffix(".mp3")

        cmd = [
            ffmpeg_path,
            "-y",
            "-i", str(flac_file),
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(mp3_file)
        ]

        print(f"Converting: {flac_file}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print(f"Done: {mp3_file}")
        else:
            print(f"Failed: {flac_file}")
            print(result.stderr)

if __name__ == "__main__":
    # 把这里改成想要转换的文件夹路径
    target_folder = r"C:\000coding\000usefultools\260401 flac2mp3"
    convert_flac_to_mp3(target_folder)