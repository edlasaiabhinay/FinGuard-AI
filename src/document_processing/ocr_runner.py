import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OCR_SCRIPT = ROOT / "src/document_processing/run_paddle_ocr.py"
OCR_CONFIG = ROOT / "config/ocr_environment.txt"


def load_ocr_environment():
    if not OCR_CONFIG.is_file():
        raise FileNotFoundError(f"OCR configuration not found: {OCR_CONFIG}")

    config = {}

    for line in OCR_CONFIG.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()

    python_path = Path(config.get("OCR_PYTHON", ""))

    if not python_path.is_file():
        raise FileNotFoundError(
            f"Isolated OCR Python executable not found: {python_path}"
        )

    if not OCR_SCRIPT.is_file():
        raise FileNotFoundError(f"OCR script not found: {OCR_SCRIPT}")

    return python_path


def run_ocr(image_path, timeout=600):
    image_path = Path(image_path).expanduser().resolve()

    if not image_path.is_file():
        raise FileNotFoundError(f"Invoice image not found: {image_path}")

    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")

    ocr_python = load_ocr_environment()

    with tempfile.TemporaryDirectory(prefix="finguard_ocr_") as temp_dir:
        output_path = Path(temp_dir) / "ocr_result.json"

        command = [
            str(ocr_python),
            str(OCR_SCRIPT),
            "--input", str(image_path),
            "--output", str(output_path)
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"OCR processing exceeded {timeout} seconds."
            ) from exc

        if completed.returncode != 0:
            raise RuntimeError(
                "PaddleOCR execution failed.\n"
                f"STDOUT:\n{completed.stdout[-3000:]}\n"
                f"STDERR:\n{completed.stderr[-5000:]}"
            )

        if not output_path.is_file():
            raise RuntimeError("OCR completed without producing its JSON output.")

        with output_path.open("r", encoding="utf-8") as file:
            ocr_data = json.load(file)

    if not ocr_data.get("lines"):
        raise RuntimeError("OCR returned no recognized text lines.")

    return ocr_data
