import csv
import ctypes
import functools
import logging
import re
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from os import PathLike, linesep
from pathlib import Path
from typing import Union

from PySide6 import QtGui

logger = logging.getLogger(__name__)


@functools.cache
def get_short_path(long_path: str) -> str:
    """Convert long Windows path to short 8.3 path.

    This is necessary for paths which contain special utf-8 chars, which can't be
    handled as arguments by the tesseract binary on Windows.
    """
    if sys.platform != "win32":
        raise NotImplementedError(
            "_get_short_path_as_str() is only supported on Windows."
        )

    # bind the Win32 API
    _GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW  # type:ignore  # noqa: N806
    _GetShortPathName.argtypes = [
        wintypes.LPCWSTR,  # lpLongPath
        wintypes.LPWSTR,  # lpShortPath
        wintypes.DWORD,  # cchBuffer
    ]
    _GetShortPathName.restype = wintypes.DWORD

    # first call to get required buffer size
    needed = _GetShortPathName(long_path, None, 0)
    if needed == 0:
        raise ctypes.WinError()  # type:ignore  # not available on non-Windows systems

    # allocate buffer and fetch the short path
    buf = ctypes.create_unicode_buffer(needed)
    result = _GetShortPathName(long_path, buf, needed)
    if result == 0:
        raise ctypes.WinError()  # type:ignore  # not available on non-Windows systems

    return buf.value


def _raise_on_error(proc: subprocess.CompletedProcess) -> None:
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=proc.returncode, cmd=proc.args, stderr=proc.stderr
        )


def _run_command(cmd_args: list[str]) -> str:
    logger.debug("Executing '%s'", " ".join(cmd_args))
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", None)
        kwargs = {"creationflags": creationflags} if creationflags else {}
        proc = subprocess.run(  # noqa: S603
            cmd_args,
            capture_output=True,
            text=True,
            check=False,
            **kwargs,
        )
        _raise_on_error(proc)
        out_str = proc.stdout
        logger.debug(
            "Tesseract command output: %s", out_str.replace(linesep, " ¬ ").strip()
        )
    except FileNotFoundError as e:
        raise FileNotFoundError("Could not find Tesseract binary") from e
    return out_str


def get_languages(
    tesseract_cmd: Union[PathLike, str], tessdata_path: Union[PathLike, str, None]
) -> list[str]:
    cmd_args = [str(tesseract_cmd), "--list-langs"]
    if tessdata_path:
        if sys.platform == "win32":
            tessdata_path = get_short_path(str(tessdata_path))
        cmd_args.extend(["--tessdata-dir", str(tessdata_path)])

    output = _run_command(cmd_args=cmd_args)

    if languages := re.findall(r"^([a-zA-Z_]+)\r{0,1}$", output, flags=re.M):
        return languages

    raise ValueError(
        "Could not load any languages for tesseract. "
        "On Windows, make sure that TESSDATA_PREFIX environment variable is set. "
        "On Linux/macOS see if 'tesseract --list-langs' work is the command line."
    )


def _move_to_normcap_temp_dir(input_file: Path, postfix: str) -> None:
    """Move file to NormCap's debug image tempdir."""
    if not input_file.exists():
        logger.debug(
            "Skip moving file to temp dir, it does not exist: %s", input_file.resolve()
        )
        return

    normcap_temp_dir = Path(tempfile.gettempdir()) / "normcap"
    normcap_temp_dir.mkdir(exist_ok=True)
    now_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
    target_file = normcap_temp_dir / f"{now_str}{postfix}{input_file.suffix}"
    target_file.unlink(missing_ok=True)

    input_file.rename(target_file)


def _run_tesseract(
    tesseract_bin_path: Union[PathLike, str], image: QtGui.QImage, args: list[str]
) -> list[list[str]]:
    input_image_filename = "normcap_tesseract_input.png"

    if logger.getEffectiveLevel() == logging.DEBUG:
        args.extend(
            ["-c", "tessedit_write_images=1", "-c", "tessedit_dump_pageseg_images=1"]
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        input_image_path = str((Path(temp_dir) / input_image_filename).resolve())
        image.save(input_image_path)

        if sys.platform == "win32":
            input_image_path = get_short_path(input_image_path)

        cmd_args = [
            str(tesseract_bin_path),
            input_image_path,
            input_image_path,  # will be suffixed with .tsv
            "-c",
            "tessedit_create_tsv=1",
            *args,
        ]

        _ = _run_command(cmd_args=cmd_args)

        if logger.getEffectiveLevel() == logging.DEBUG:
            _move_to_normcap_temp_dir(
                input_file=Path(f"{input_image_path}.processed.tif"),
                postfix="_processed_by_tesseract",
            )
            _move_to_normcap_temp_dir(
                input_file=Path(f"{input_image_path}.png_debug.pdf"),
                postfix="_processed_by_tesseract",
            )

        with Path(f"{input_image_path}.tsv").open(encoding="utf-8") as fh:
            tsv_file = csv.reader(fh, delimiter="\t", quotechar=None)
            lines = list(tsv_file)

    return lines


def _tsv_to_list_of_dict(tsv_lines: list[list[str]]) -> list[dict]:
    fields = tsv_lines.pop(0)
    words: list[dict] = [{} for _ in range(len(tsv_lines))]
    for idx, line in enumerate(tsv_lines):
        for field, value in zip(fields, line):
            if field == "text":
                words[idx][field] = value
            elif field == "conf":
                words[idx][field] = float(value)
            else:
                words[idx][field] = int(value)

    # Filter empty words
    words = [w for w in words if "text" in w]
    return [w for w in words if w["text"].strip()]


def perform_ocr(
    tesseract_bin_path: Union[PathLike, str], image: QtGui.QImage, args: list[str]
) -> list[dict]:
    lines = _run_tesseract(
        tesseract_bin_path=tesseract_bin_path, image=image, args=args
    )
    return _tsv_to_list_of_dict(lines)
