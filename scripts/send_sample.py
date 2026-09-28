from datetime import date, datetime, timezone
from decimal import Decimal

from monthly_statement.infrai_client import InfraiClient
from monthly_statement.models import PaymentEvent, RiskLevel, StatementRequest
from monthly_statement.receipt_sender import send_monthly_statement


def main() -> None:
    request = StatementRequest(
        customer_id="creator-studio-42",
        customer_email="billing@example.com",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        risk_level=RiskLevel.LOW,
        payment_events=[
            PaymentEvent(
                occurred_at=datetime(2026, 8, 14, 9, 30, tzinfo=timezone.utc),
                kind="render_minutes",
                amount_usd=Decimal("18.40"),
                reference="render-batch-1842",
            )
        ],
    )
    client = InfraiClient()
    try:
        print(send_monthly_statement(request, client).model_dump_json(indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
