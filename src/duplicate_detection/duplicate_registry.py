
import json
import os
import tempfile
from pathlib import Path

from src.duplicate_detection.duplicate_detector import compare_documents


SCHEMA_VERSION = 1

REQUIRED_FIELDS = {
    "file_hash",
    "normalized_invoice_number",
    "supplier_gstin",
    "invoice_date",
    "grand_total",
}


def get_default_registry_path():
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "datasets" / "processed" / "duplicate_registry.json"


def _validate_record(record):
    if not isinstance(record, dict):
        raise ValueError("Document record must be a dictionary.")

    missing = REQUIRED_FIELDS - set(record.keys())
    if missing:
        raise ValueError(
            f"Document record is missing required fields: {sorted(missing)}"
        )


def load_registry(registry_path=None):
    path = Path(registry_path) if registry_path else get_default_registry_path()

    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "documents": [],
        }

    try:
        with path.open("r", encoding="utf-8") as file:
            registry = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Duplicate registry is not valid JSON: {path}") from exc

    if not isinstance(registry, dict):
        raise ValueError("Duplicate registry must contain a JSON object.")

    if registry.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported duplicate registry schema version.")

    if not isinstance(registry.get("documents"), list):
        raise ValueError("Registry 'documents' must be a list.")

    for existing_record in registry["documents"]:
        _validate_record(existing_record)

    return registry


def save_registry(registry, registry_path=None):
    path = Path(registry_path) if registry_path else get_default_registry_path()

    if registry.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported duplicate registry schema version.")

    if not isinstance(registry.get("documents"), list):
        raise ValueError("Registry 'documents' must be a list.")

    for record in registry["documents"]:
        _validate_record(record)

    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            json.dump(registry, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, path)

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def check_and_register_document(document_record, registry_path=None):
    """
    Compare a document against registry history.

    A duplicate is returned but not registered again.
    A unique document is appended and saved.
    """
    _validate_record(document_record)

    registry = load_registry(registry_path)

    matches = []

    for existing_record in registry["documents"]:
        result = compare_documents(document_record, existing_record)

        if result["is_duplicate"]:
            matches.append({
                **result,
                "matching_document_id": existing_record.get("document_id"),
                "matching_file_path": existing_record.get("file_path"),
            })

    if matches:
        matches.sort(
            key=lambda item: (
                item["confidence"],
                item["duplicate_type"] == "EXACT_FILE_DUPLICATE",
            ),
            reverse=True,
        )

        return {
            "registry_status": "DUPLICATE_FOUND",
            "is_duplicate": True,
            "match": matches[0],
            "total_matches": len(matches),
            "registered": False,
        }

    registry["documents"].append(document_record)
    save_registry(registry, registry_path)

    return {
        "registry_status": "UNIQUE_REGISTERED",
        "is_duplicate": False,
        "match": None,
        "total_matches": 0,
        "registered": True,
    }
