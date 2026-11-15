
import argparse
import json
from pathlib import Path

from paddleocr import PaddleOCR


def convert_to_word_level(data, source_file):
    texts = data.get("rec_texts", [])
    scores = data.get("rec_scores", [])
    line_boxes = data.get("rec_boxes", [])
    word_groups = data.get("text_word", [])
    word_box_groups = data.get("text_word_boxes", [])

    lengths = [
        len(texts), len(scores), len(line_boxes),
        len(word_groups), len(word_box_groups)
    ]

    if len(set(lengths)) != 1:
        raise ValueError(f"Inconsistent OCR arrays: {lengths}")

    lines = []
    total_words = 0

    for line_index, text in enumerate(texts):
        words = []

        if len(word_groups[line_index]) != len(word_box_groups[line_index]):
            raise ValueError(f"Word-box mismatch at line {line_index}")

        for token_index, (word, bbox) in enumerate(
            zip(word_groups[line_index], word_box_groups[line_index])
        ):
            word = str(word).strip()

            if not word:
                continue

            if len(bbox) != 4:
                raise ValueError(f"Invalid bounding box: {bbox}")

            words.append({
                "word_index": len(words),
                "token_index": token_index,
                "text": word,
                "bbox": [int(v) for v in bbox],
                "line_confidence": float(scores[line_index])
            })

        x1, y1, x2, y2 = line_boxes[line_index]
        total_words += len(words)

        lines.append({
            "page": 0,
            "line_index": line_index,
            "text": str(text),
            "confidence": float(scores[line_index]),
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "words": words
        })

    return {
        "source_file": str(source_file),
        "ocr_engine": "PaddleOCR",
        "ocr_version": "3.7.0",
        "word_box_enabled": True,
        "coordinate_format": "xyxy",
        "confidence_note": (
            "Word confidence uses the parent line recognition score; "
            "it is not an independent word-level confidence."
        ),
        "total_lines": len(lines),
        "total_words": total_words,
        "lines": lines
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    image_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not image_path.is_file():
        raise FileNotFoundError(image_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    ocr = PaddleOCR(return_word_box=True)
    results = ocr.predict(str(image_path), return_word_box=True)

    if not results:
        raise RuntimeError("PaddleOCR returned no results.")

    raw = results[0].json
    data = raw.get("res", raw)

    normalized = convert_to_word_level(data, image_path)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=2, ensure_ascii=False)

    print(json.dumps({
        "status": "SUCCESS",
        "source": str(image_path),
        "output": str(output_path),
        "total_lines": normalized["total_lines"],
        "total_words": normalized["total_words"]
    }, indent=2))


if __name__ == "__main__":
    main()
