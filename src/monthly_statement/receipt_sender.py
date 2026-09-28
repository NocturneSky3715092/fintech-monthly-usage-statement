from decimal import Decimal
from html import escape
from .infrai_client import InfraiClient
from .models import RiskLevel, StatementRequest, StatementResult


def send_monthly_statement(
    request: StatementRequest, infrai: InfraiClient
) -> StatementResult:
    if request.risk_level is RiskLevel.HIGH:
        return StatementResult(
            status="manual_review",
            customer_id=request.customer_id,
            reason="high-risk statements require approval before customer contact",
        )

    request_id = (
        f"statement:{request.customer_id}:{request.period_start}:{request.period_end}"
    )
    usage = infrai.account_usage()
    markdown = _statement_markdown(request, usage)
    pdf = infrai.generate_pdf(markdown, request_id)
    pdf_url = _required_string(pdf, "url")

    subject = f"Usage statement: {request.period_start} to {request.period_end}"
    html = (
        f"<p>Your monthly usage statement is ready.</p>"
        f'<p><a href="{escape(pdf_url, quote=True)}">Download the PDF statement</a></p>'
        f"<p>Customer reference: {escape(request.customer_id)}</p>"
    )
    email = infrai.send_email(str(request.customer_email), subject, html, request_id)
    return StatementResult(
        status="sent",
        customer_id=request.customer_id,
        pdf_url=pdf_url,
        message_id=_required_string(email, "message_id"),
    )


def _statement_markdown(
    request: StatementRequest, usage: dict[str, object]
) -> str:
    rows = [
        "| Date | Event | Amount (USD) | Reference |",
        "| --- | --- | ---: | --- |",
    ]
    total = Decimal("0")
    for event in sorted(request.payment_events, key=lambda item: item.occurred_at):
        total += event.amount_usd
        rows.append(
            f"| {event.occurred_at.date()} | {event.kind} | "
            f"{event.amount_usd:.2f} | {event.reference} |"
        )

    return "\n".join(
        [
            "# Monthly usage statement",
            "",
            f"Customer: {request.customer_id}",
            f"Period: {request.period_start} through {request.period_end}",
            "",
            *rows,
            "",
            f"Payment event total: USD {total:.2f}",
            "",
            "## Metered account usage",
            "",
            "```json",
            _stable_usage_text(usage),
            "```",
        ]
    )


def _stable_usage_text(usage: dict[str, object]) -> str:
    import json

    return json.dumps(usage, sort_keys=True, indent=2, default=str)


def _required_string(data: dict[str, object], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Infrai response is missing {name}")
    return value
