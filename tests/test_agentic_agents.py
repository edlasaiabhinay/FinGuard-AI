
import importlib


def test_extraction_agent_rejects_missing_ocr():
    module = importlib.import_module("src.agents.extraction_agent")

    result = module.extraction_agent({
        "document_id": "TEST-001",
        "ocr_data": None,
        "errors": [],
        "warnings": [],
        "completed_agents": [],
        "agent_status": {}
    })

    assert result["agent_status"]["extraction_agent"] == "FAILED"
    assert result["overall_status"] == "REVIEW"
    assert len(result["errors"]) == 1


def test_financial_agent_passes_valid_report(monkeypatch):
    module = importlib.import_module("src.agents.financial_agent")

    monkeypatch.setattr(
        module,
        "verify_invoice",
        lambda invoice, ocr_text: {
            "document_id": "TEST-002",
            "summary": {
                "total_checks": 6,
                "passed": 6,
                "failed": 0,
                "overall_status": "PASS"
            },
            "checks": []
        }
    )

    invoice = {
        "items": [{"quantity": 1}],
        "financial_details": {},
        "parties": {
            "supplier_gstin": {"value": "33ABCDE1234F1Z5"},
            "customer_gstin": {"value": "33XYZDE5678F1Z2"}
        }
    }

    result = module.financial_verification_agent({
        "invoice": invoice,
        "ocr_text": "Test invoice",
        "completed_agents": [],
        "agent_status": {},
        "overall_status": "PENDING_VERIFICATION",
        "human_review_required": False,
        "human_review_reason": []
    })

    assert result["agent_status"]["financial_agent"] == "COMPLETED"
    assert result["financial_verification"]["summary"]["overall_status"] == "PASS"
    assert result["human_review_required"] is False


def test_financial_agent_skips_incomplete_invoice():
    module = importlib.import_module("src.agents.financial_agent")

    result = module.financial_verification_agent({
        "invoice": {
            "items": [],
            "financial_details": {},
            "parties": {}
        },
        "warnings": [],
        "human_review_reason": [],
        "agent_status": {}
    })

    assert result["agent_status"]["financial_agent"] == "SKIPPED"
    assert result["financial_verification"] is None
    assert result["human_review_required"] is True


def test_po_agent_requires_review_without_purchase_order():
    module = importlib.import_module("src.agents.po_matching_agent")

    result = module.po_matching_agent({
        "invoice": {"items": []},
        "purchase_order": None,
        "warnings": [],
        "human_review_reason": [],
        "agent_status": {},
        "overall_status": "PENDING_VERIFICATION"
    })

    assert result["agent_status"]["po_matching_agent"] == "SKIPPED"
    assert result["overall_status"] == "REVIEW"
    assert result["human_review_required"] is True


def test_po_agent_handles_matcher_review(monkeypatch):
    module = importlib.import_module("src.agents.po_matching_agent")

    monkeypatch.setattr(
        module,
        "verify_invoice_against_po",
        lambda invoice, purchase_order: {
            "summary": {
                "total_checks": 14,
                "passed": 13,
                "failed": 0,
                "not_verifiable": 1,
                "overall_status": "REVIEW"
            },
            "checks": []
        }
    )

    result = module.po_matching_agent({
        "invoice": {"items": []},
        "purchase_order": {"po_number": "PO-TEST"},
        "completed_agents": [],
        "agent_status": {},
        "human_review_reason": [],
        "human_review_required": False,
        "overall_status": "PENDING_VERIFICATION"
    })

    assert result["agent_status"]["po_matching_agent"] == "REVIEW"
    assert result["overall_status"] == "REVIEW"
    assert result["human_review_required"] is True


def test_duplicate_agent_skips_missing_source_path():
    module = importlib.import_module("src.agents.duplicate_agent")

    result = module.duplicate_detection_agent({
        "invoice": {},
        "file_path": None,
        "agent_status": {},
        "human_review_reason": [],
        "overall_status": "PENDING_VERIFICATION"
    })

    assert result["agent_status"]["duplicate_agent"] == "SKIPPED"
    assert result["duplicate_detection"]["status"] == "SKIPPED_REVIEW"
    assert result["human_review_required"] is True


def test_anomaly_agent_handles_normal_prediction(monkeypatch):
    module = importlib.import_module("src.agents.anomaly_agent")

    monkeypatch.setattr(
        module,
        "analyze_invoice_anomaly",
        lambda field_extraction, items: {
            "status": "COMPLETED",
            "model_version": "2.0",
            "prediction": "NORMAL",
            "is_anomaly": False,
            "review_required": False
        }
    )

    result = module.anomaly_detection_agent({
        "field_extraction": {"invoice_details": {}},
        "invoice": {"items": [{"quantity": 1}]},
        "completed_agents": [],
        "agent_status": {},
        "human_review_reason": [],
        "human_review_required": False,
        "overall_status": "PENDING_VERIFICATION"
    })

    assert result["agent_status"]["anomaly_agent"] == "COMPLETED"
    assert result["anomaly_detection"]["prediction"] == "NORMAL"
    assert result["human_review_required"] is False


def test_anomaly_agent_requires_review_on_model_failure(monkeypatch):
    module = importlib.import_module("src.agents.anomaly_agent")

    monkeypatch.setattr(
        module,
        "analyze_invoice_anomaly",
        lambda field_extraction, items: {
            "status": "ERROR",
            "prediction": "NOT_RUN"
        }
    )

    result = module.anomaly_detection_agent({
        "field_extraction": {},
        "invoice": {"items": [{"quantity": 1}]},
        "completed_agents": [],
        "agent_status": {},
        "human_review_reason": [],
        "human_review_required": False,
        "overall_status": "PENDING_VERIFICATION"
    })

    assert result["agent_status"]["anomaly_agent"] == "REVIEW"
    assert result["overall_status"] == "REVIEW"
    assert result["human_review_required"] is True


def test_supervisor_returns_pass_when_all_agents_pass():
    module = importlib.import_module("src.orchestration.graph")

    result = module.supervisor_agent({
        "agent_status": {
            "extraction_agent": "COMPLETED",
            "financial_agent": "COMPLETED",
            "po_matching_agent": "COMPLETED",
            "duplicate_agent": "COMPLETED",
            "anomaly_agent": "COMPLETED"
        },
        "completed_agents": [],
        "human_review_required": False,
        "human_review_reason": [],
        "errors": [],
        "overall_status": "PENDING_VERIFICATION"
    })

    assert result["final_decision"] == "PASS"
    assert result["workflow_status"] == "COMPLETED"
    assert result["human_review_required"] is False


def test_supervisor_returns_review_for_po_review():
    module = importlib.import_module("src.orchestration.graph")

    result = module.supervisor_agent({
        "agent_status": {
            "extraction_agent": "COMPLETED",
            "financial_agent": "COMPLETED",
            "po_matching_agent": "REVIEW",
            "duplicate_agent": "COMPLETED",
            "anomaly_agent": "COMPLETED"
        },
        "completed_agents": [],
        "human_review_required": True,
        "human_review_reason": ["PO reference is unavailable."],
        "errors": [],
        "overall_status": "REVIEW"
    })

    assert result["final_decision"] == "REVIEW"
    assert result["human_review_required"] is True


def test_supervisor_preserves_duplicate_exception():
    module = importlib.import_module("src.orchestration.graph")

    result = module.supervisor_agent({
        "agent_status": {
            "extraction_agent": "COMPLETED",
            "financial_agent": "COMPLETED",
            "po_matching_agent": "COMPLETED",
            "duplicate_agent": "DUPLICATE",
            "anomaly_agent": "COMPLETED"
        },
        "completed_agents": [],
        "human_review_required": True,
        "human_review_reason": ["Exact duplicate detected."],
        "errors": [],
        "overall_status": "EXCEPTION"
    })

    assert result["final_decision"] == "EXCEPTION"
    assert result["overall_status"] == "EXCEPTION"
    assert result["human_review_required"] is True
