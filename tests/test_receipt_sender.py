from datetime import date, datetime, timezone
from decimal import Decimal

from monthly_statement.models import PaymentEvent, RiskLevel, StatementRequest
from monthly_statement.receipt_sender import send_monthly_statement


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def account_usage(self) -> dict[str, object]:
        self.calls.append("usage")
        return {"units": 83, "period": "2026-08"}

    def generate_pdf(self, markdown: str, request_id: str) -> dict[str, object]:
        self.calls.append("pdf")
        assert "Payment event total: USD 18.40" in markdown
        assert request_id == "statement:creator-studio-42:2026-08-01:2026-08-31"
        return {"url": "https://downloads.example/statement.pdf"}

    def send_email(
        self, to: str, subject: str, html: str, request_id: str
    ) -> dict[str, object]:
        self.calls.append("email")
        assert to == "billing@example.com"
        assert "https://downloads.example/statement.pdf" in html
        return {"message_id": "msg_202608_creator42"}


def request_with_risk(risk_level: RiskLevel) -> StatementRequest:
    return StatementRequest(
        customer_id="creator-studio-42",
        customer_email="billing@example.com",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        risk_level=risk_level,
        payment_events=[
            PaymentEvent(
                occurred_at=datetime(2026, 8, 14, 9, 30, tzinfo=timezone.utc),
                kind="render_minutes",
                amount_usd=Decimal("18.40"),
                reference="render-batch-1842",
            )
        ],
    )


def test_low_risk_statement_hands_pdf_url_to_email() -> None:
    gateway = RecordingGateway()

    result = send_monthly_statement(request_with_risk(RiskLevel.LOW), gateway)

    assert result.status == "sent"
    assert result.message_id == "msg_202608_creator42"
    assert gateway.calls == ["usage", "pdf", "email"]


def test_high_risk_statement_stops_before_customer_contact() -> None:
    gateway = RecordingGateway()

    result = send_monthly_statement(request_with_risk(RiskLevel.HIGH), gateway)

    assert result.status == "manual_review"
    assert gateway.calls == []
