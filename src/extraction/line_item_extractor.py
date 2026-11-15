
import re
from statistics import median


NUMBER_PATTERN = re.compile(
    r"^\s*\d+(?:,\d{3})*(?:\.\d+)?\s*$"
)


def _center(box):
    return (
        (box[0] + box[2]) / 2,
        (box[1] + box[3]) / 2
    )


def _find_header(lines, keyword):
    for line in lines:
        text = re.sub(r"\s+", " ", line["text"].upper()).strip()
        if text == keyword:
            return _center(line["bbox"])
    return None


def _number(text):
    return float(text.replace(",", "").strip())


def extract_line_items_with_audit(
    ocr_data,
    row_tolerance=35,
    description_tolerance=50
):
    lines = ocr_data["lines"]

    headers = {
        "description": _find_header(lines, "ITEM DESCRIPTION"),
        "quantity": _find_header(lines, "QTY"),
        "unit_price": _find_header(lines, "PRICE"),
        "line_total": _find_header(lines, "TOTAL")
    }

    if any(value is None for value in headers.values()):
        missing = [
            field for field, value in headers.items()
            if value is None
        ]
        raise ValueError(
            f"Required invoice table headers were not found: {missing}"
        )

    header_y = median(value[1] for value in headers.values())

    summary_patterns = re.compile(
        r"^(TAXABLE AMOUNT|CGST|SGST|IGST|GRAND TOTAL|"
        r"AMOUNT PAYABLE|NET PAYABLE)\b",
        re.IGNORECASE
    )

    summary_positions = [
        _center(line["bbox"])[1]
        for line in lines
        if summary_patterns.search(line["text"].strip())
        and _center(line["bbox"])[1] > header_y
    ]

    table_bottom = (
        min(summary_positions)
        if summary_positions
        else header_y + 500
    )

    numeric_cells = []
    description_cells = []

    for line in lines:
        x, y = _center(line["bbox"])

        if not (header_y + 20 < y < table_bottom):
            continue

        text = line["text"].strip()

        if NUMBER_PATTERN.fullmatch(text):
            distances = {
                field: abs(x - headers[field][0])
                for field in ("quantity", "unit_price", "line_total")
            }

            field = min(distances, key=distances.get)

            if distances[field] <= 120:
                numeric_cells.append({
                    "field": field,
                    "value": _number(text),
                    "x": x,
                    "y": y
                })

        elif x < (
            headers["description"][0] + headers["quantity"][0]
        ) / 2:
            description_cells.append({
                "text": text,
                "x": x,
                "y": y
            })

    numeric_cells.sort(key=lambda item: item["y"])
    row_groups = []

    for cell in numeric_cells:
        matching_group = None

        for group in row_groups:
            group_y = median(item["y"] for item in group)

            if abs(cell["y"] - group_y) <= row_tolerance:
                matching_group = group
                break

        if matching_group is None:
            row_groups.append([cell])
        else:
            matching_group.append(cell)

    extracted_items = []
    incomplete_rows = []
    used_descriptions = set()

    for group in row_groups:
        row_y = median(item["y"] for item in group)

        fields = {}
        for cell in group:
            if cell["field"] not in fields:
                fields[cell["field"]] = cell["value"]

        nearby_descriptions = [
            (index, item)
            for index, item in enumerate(description_cells)
            if abs(item["y"] - row_y) <= description_tolerance
            and index not in used_descriptions
        ]

        # Preserve the visual reading order and merge wrapped description lines.
        nearby_descriptions.sort(
            key=lambda pair: (pair[1]["y"], pair[1]["x"])
        )

        description = None

        if nearby_descriptions:
            description = " ".join(
                item["text"].strip()
                for _, item in nearby_descriptions
            )

            for description_index, _ in nearby_descriptions:
                used_descriptions.add(description_index)

        missing_fields = [
            field for field in (
                "quantity", "unit_price", "line_total", "description"
            )
            if (
                field == "description" and description is None
            ) or (
                field != "description" and field not in fields
            )
        ]

        if missing_fields:
            reasons = {
                "quantity": "MISSING_QUANTITY",
                "unit_price": "MISSING_UNIT_PRICE",
                "line_total": "MISSING_LINE_TOTAL",
                "description": "MISSING_DESCRIPTION"
            }

            incomplete_rows.append({
                "row_y": row_y,
                "detected_fields": {
                    **fields,
                    "description": description
                },
                "missing_fields": missing_fields,
                "reasons": [reasons[field] for field in missing_fields]
            })
            continue

        extracted_items.append({
            "description": description,
            "quantity": fields["quantity"],
            "unit_price": fields["unit_price"],
            "line_total": fields["line_total"],
            "row_y": row_y
        })

    # Audit descriptions that were not associated with any numeric row.
    # This catches item descriptions when OCR misses the entire numeric row.
    unmatched = [
        (index, item)
        for index, item in enumerate(description_cells)
        if index not in used_descriptions
    ]

    unmatched.sort(key=lambda pair: pair[1]["y"])
    description_groups = []

    for index, item in unmatched:
        matching_group = None

        for group in description_groups:
            group_y = median(entry[1]["y"] for entry in group)

            if abs(item["y"] - group_y) <= row_tolerance:
                matching_group = group
                break

        if matching_group is None:
            description_groups.append([(index, item)])
        else:
            matching_group.append((index, item))

    for group in description_groups:
        row_y = median(item["y"] for _, item in group)
        description = " ".join(
            item["text"].strip() for _, item in group
        )

        incomplete_rows.append({
            "row_y": row_y,
            "detected_fields": {
                "description": description,
                "quantity": None,
                "unit_price": None,
                "line_total": None
            },
            "missing_fields": [
                "quantity", "unit_price", "line_total"
            ],
            "reasons": [
                "MISSING_QUANTITY",
                "MISSING_UNIT_PRICE",
                "MISSING_LINE_TOTAL"
            ]
        })

    return {
        "items": extracted_items,
        "incomplete_rows": incomplete_rows,
        "status": "REVIEW" if incomplete_rows else "PASS"
    }


def extract_line_items(
    ocr_data,
    row_tolerance=35,
    description_tolerance=50
):
    result = extract_line_items_with_audit(
        ocr_data,
        row_tolerance=row_tolerance,
        description_tolerance=description_tolerance
    )

    if not result["items"]:
        raise ValueError("No complete invoice line items were detected.")

    return result["items"]



def extract_line_items_wordlevel(
    ocr_data,
    row_tolerance=35,
    description_tolerance=50
):
    """
    Extract invoice line items using PaddleOCR word-level bounding boxes.
    Returns complete items and an audit of incomplete rows.
    """

    lines = ocr_data["lines"]

    if not lines or not all("words" in line for line in lines):
        raise ValueError("Word-level OCR data is required.")

    headers = {
        "description": _find_header(lines, "ITEM DESCRIPTION"),
        "quantity": _find_header(lines, "QTY"),
        "unit_price": _find_header(lines, "PRICE"),
        "line_total": _find_header(lines, "TOTAL")
    }

    if any(value is None for value in headers.values()):
        missing = [
            field for field, value in headers.items()
            if value is None
        ]
        raise ValueError(f"Required table headers missing: {missing}")

    header_y = median(value[1] for value in headers.values())

    summary_pattern = re.compile(
        r"^(TAXABLE AMOUNT|CGST|SGST|IGST|GRAND TOTAL|"
        r"AMOUNT PAYABLE|NET PAYABLE)\b",
        re.IGNORECASE
    )

    summary_positions = [
        _center(line["bbox"])[1]
        for line in lines
        if summary_pattern.search(line["text"].strip())
        and _center(line["bbox"])[1] > header_y
    ]

    table_bottom = (
        min(summary_positions)
        if summary_positions
        else header_y + 500
    )

    description_boundary = (
        headers["description"][0] + headers["quantity"][0]
    ) / 2

    numeric_cells = []
    description_cells = []

    for line in lines:
        for word in line["words"]:
            text = word["text"].strip()

            if not text:
                continue

            x1, y1, x2, y2 = word["bbox"]
            x = (x1 + x2) / 2
            y = (y1 + y2) / 2

            if not (header_y + 20 < y < table_bottom):
                continue

            if NUMBER_PATTERN.fullmatch(text):
                distances = {
                    field: abs(x - headers[field][0])
                    for field in (
                        "quantity", "unit_price", "line_total"
                    )
                }

                field = min(distances, key=distances.get)

                if distances[field] <= 120:
                    numeric_cells.append({
                        "field": field,
                        "value": _number(text),
                        "x": x,
                        "y": y
                    })

            elif x < description_boundary:
                description_cells.append({
                    "text": text,
                    "x": x,
                    "y": y
                })

    numeric_cells.sort(key=lambda item: item["y"])
    row_groups = []

    for cell in numeric_cells:
        matching_group = None

        for group in row_groups:
            group_y = median(item["y"] for item in group)

            if abs(cell["y"] - group_y) <= row_tolerance:
                matching_group = group
                break

        if matching_group is None:
            row_groups.append([cell])
        else:
            matching_group.append(cell)

    extracted_items = []
    incomplete_rows = []
    used_descriptions = set()

    for group in row_groups:
        row_y = median(item["y"] for item in group)

        fields = {}
        for cell in group:
            if cell["field"] not in fields:
                fields[cell["field"]] = cell["value"]

        nearby = [
            (index, item)
            for index, item in enumerate(description_cells)
            if index not in used_descriptions
            and abs(item["y"] - row_y) <= description_tolerance
        ]

        nearby.sort(key=lambda pair: (pair[1]["y"], pair[1]["x"]))

        description = None

        if nearby:
            description = " ".join(
                item["text"] for _, item in nearby
            )

            for index, _ in nearby:
                used_descriptions.add(index)

        missing = [
            field for field in (
                "quantity", "unit_price", "line_total", "description"
            )
            if (
                field == "description" and description is None
            ) or (
                field != "description" and field not in fields
            )
        ]

        if missing:
            reasons = {
                "quantity": "MISSING_QUANTITY",
                "unit_price": "MISSING_UNIT_PRICE",
                "line_total": "MISSING_LINE_TOTAL",
                "description": "MISSING_DESCRIPTION"
            }

            incomplete_rows.append({
                "row_y": row_y,
                "detected_fields": {
                    **fields,
                    "description": description
                },
                "missing_fields": missing,
                "reasons": [reasons[field] for field in missing]
            })
            continue

        extracted_items.append({
            "description": description,
            "quantity": fields["quantity"],
            "unit_price": fields["unit_price"],
            "line_total": fields["line_total"],
            "row_y": row_y
        })

    # Detect descriptions that have no associated numeric row.
    unmatched = [
        (index, item)
        for index, item in enumerate(description_cells)
        if index not in used_descriptions
    ]

    unmatched.sort(key=lambda pair: pair[1]["y"])
    description_groups = []

    for index, item in unmatched:
        matching_group = None

        for group in description_groups:
            group_y = median(entry[1]["y"] for entry in group)

            if abs(item["y"] - group_y) <= row_tolerance:
                matching_group = group
                break

        if matching_group is None:
            description_groups.append([(index, item)])
        else:
            matching_group.append((index, item))

    for group in description_groups:
        row_y = median(item["y"] for _, item in group)
        description = " ".join(
            item["text"] for _, item in sorted(
                group, key=lambda pair: (pair[1]["y"], pair[1]["x"])
            )
        )

        incomplete_rows.append({
            "row_y": row_y,
            "detected_fields": {
                "description": description,
                "quantity": None,
                "unit_price": None,
                "line_total": None
            },
            "missing_fields": [
                "quantity", "unit_price", "line_total"
            ],
            "reasons": [
                "MISSING_QUANTITY",
                "MISSING_UNIT_PRICE",
                "MISSING_LINE_TOTAL"
            ]
        })

    return {
        "items": extracted_items,
        "incomplete_rows": incomplete_rows,
        "status": "REVIEW" if incomplete_rows else "PASS"
    }
