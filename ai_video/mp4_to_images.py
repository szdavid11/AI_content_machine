#!/usr/bin/env python3
"""
Extract frames from an MP4 video into images saved in a new folder.

Default behavior:
- Creates an output folder next to the input video named `<video_stem>_frames`.
- Uses `ffmpeg` if available; falls back to OpenCV if installed.

Examples:
  python ai_video/mp4_to_images.py path/to/video.mp4
  python ai_video/mp4_to_images.py video.mp4 -o out_frames --fps 2 --format jpg
"""

from __future__ import annotations

import argparse
import os
import sys
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert MP4 to sequence of images in a new folder",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to input .mp4 file",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory for frames. Default: sibling folder named "
            "'<video_stem>_frames' next to the input video."
        ),
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help=(
            "Frames per second to extract. Default: keep every frame. "
            "Example: --fps 2 extracts 2 frames per second."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["png", "jpg", "jpeg"],
        default="png",
        help="Image format for output frames (default: png)",
    )
    parser.add_argument(
        "--basename",
        default="frame",
        help="Base filename for frames (default: frame)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output folder if it exists",
    )
    parser.add_argument(
        "--force-backend",
        choices=["ffmpeg", "opencv"],
        default=None,
        help="Force a specific backend. Default: auto-detect ffmpeg, then OpenCV.",
    )
    return parser.parse_args()


def ensure_output_dir(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists():
        if not overwrite:
            # If exists and not overwriting, ensure it's empty to avoid mixup
            if any(output_dir.iterdir()):
                print(
                    f"Error: Output directory '{output_dir}' already exists and is not empty. "
                    "Use --overwrite to replace its contents.",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            # Remove and recreate to avoid stale files
            for child in output_dir.iterdir():
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    shutil.rmtree(child)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def run_ffmpeg_extract(
    input_path: Path,
    output_dir: Path,
    basename: str,
    ext: str,
    fps: float | None,
    overwrite: bool,
) -> int:
    pattern = output_dir / f"{basename}_%06d.{ext}"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
    ]
    cmd += ["-y" if overwrite else "-n"]
    cmd += ["-i", str(input_path)]
    if fps is not None:
        cmd += ["-vf", f"fps={fps}"]
    # For JPEG, set good quality unless user wants default
    if ext.lower() in {"jpg", "jpeg"}:
        cmd += ["-q:v", "2"]  # 2 is high quality, 31 is worst
    cmd += [str(pattern)]

    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd)
    return proc.returncode


def run_opencv_extract(
    input_path: Path,
    output_dir: Path,
    basename: str,
    ext: str,
    fps: float | None,
) -> int:
    try:
        import cv2  # type: ignore
    except Exception as e:  # pragma: no cover - best-effort import
        print(
            "OpenCV (cv2) not available, and ffmpeg was not usable.",
            f"Install OpenCV or ensure ffmpeg is on PATH. Details: {e}",
            file=sys.stderr,
        )
        return 1

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"Error: cannot open video: {input_path}", file=sys.stderr)
        return 1

    orig_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    if fps is None or fps <= 0 or orig_fps <= 0:
        step = 1
    else:
        # Calculate frame step to approximate desired sampling rate
        step = max(int(round(orig_fps / fps)), 1)

    idx = 0
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if step == 1 or (idx % step == 0):
            out_path = output_dir / f"{basename}_{saved+1:06d}.{ext}"
            ok = cv2.imwrite(str(out_path), frame)
            if not ok:
                print(f"Warning: failed to write {out_path}", file=sys.stderr)
            else:
                saved += 1
        idx += 1

    cap.release()
    if saved == 0:
        print("No frames were extracted.", file=sys.stderr)
        return 1
    print(f"Saved {saved} frames to '{output_dir}'.")
    return 0


def main() -> int:
    args = parse_args()
    input_path: Path = args.input

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1
    if input_path.suffix.lower() != ".mp4":
        print(
            f"Warning: input does not have .mp4 extension: {input_path.suffix}",
            file=sys.stderr,
        )

    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else input_path.with_name(f"{input_path.stem}_frames")
    )
    ext = "jpg" if args.format.lower() == "jpeg" else args.format.lower()

    ensure_output_dir(output_dir, args.overwrite)

    # Choose backend
    backend = args.force_backend
    if backend is None:
        backend = "ffmpeg" if have_ffmpeg() else "opencv"

    print(
        f"Input: {input_path}\nOutput dir: {output_dir}\nFormat: .{ext}\n"
        f"FPS: {'all frames' if args.fps is None else args.fps}\n"
        f"Backend: {backend}"
    )

    if backend == "ffmpeg":
        if not have_ffmpeg():
            print(
                "Error: ffmpeg not found on PATH. Install ffmpeg or use --force-backend opencv.",
                file=sys.stderr,
            )
            return 1
        rc = run_ffmpeg_extract(
            input_path=input_path,
            output_dir=output_dir,
            basename=args.basename,
            ext=ext,
            fps=args.fps,
            overwrite=True,  # already handled directory; allow ffmpeg to overwrite pattern
        )
        if rc == 0:
            # Best-effort frame count
            num = len(list(output_dir.glob(f"{args.basename}_*.{ext}")))
            print(f"Done. Saved ~{num} frames to '{output_dir}'.")
        return rc
    elif backend == "opencv":
        return run_opencv_extract(
            input_path=input_path,
            output_dir=output_dir,
            basename=args.basename,
            ext=ext,
            fps=args.fps,
        )
    else:
        print(f"Unknown backend: {backend}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)

