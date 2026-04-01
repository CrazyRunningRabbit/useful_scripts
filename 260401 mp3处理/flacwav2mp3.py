from pathlib import Path
import subprocess
import shutil
import sys


def convert_audio_to_mp3(folder: str, ffmpeg_path: str = "ffmpeg") -> None:
    """
    Convert all .flac and .wav files in a folder (including subfolders) to .mp3.

    Parameters
    ----------
    folder : str
        Root folder to search for audio files.
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

    # 同时查找 flac 和 wav
    audio_files = list(root.rglob("*.flac")) + list(root.rglob("*.wav"))

    if not audio_files:
        print("No .flac or .wav files found.")
        return

    print(f"Found {len(audio_files)} audio file(s).")

    for audio_file in audio_files:
        mp3_file = audio_file.with_suffix(".mp3")

        # 如果已经存在就跳过
        if mp3_file.exists():
            print(f"Skip (already exists): {mp3_file}")
            continue

        cmd = [
            ffmpeg_path,
            "-y",
            "-i", str(audio_file),
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(mp3_file)
        ]

        print(f"Converting: {audio_file}")

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            print(f"Done: {mp3_file}")
        else:
            print(f"Failed: {audio_file}")
            print(result.stderr)


if __name__ == "__main__":
    target_folder = r"C:\000coding\000usefultools\260401 mp3处理"
    convert_audio_to_mp3(target_folder)