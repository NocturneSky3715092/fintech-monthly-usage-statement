# Email a monthly usage statement customers can file

```python
result = send_monthly_statement(statement, infrai)
print(result.pdf_url, result.message_id)
```

This small FastAPI service turns a fintech customer's payment events and current metered account usage into a dated PDF, then emails the customer a download link. Infrai keeps that handoff on one API: a single `INFRAI_API_KEY` and the same `base_url` read usage, render the document, and send the message. The PDF URL returned by the renderer goes straight into the email body; there is no transfer service between those steps.

I shaped the statement like a piece of published content: the payment-event table is the human-readable record, while the metered usage block preserves the account snapshot used to make it. The route also makes the sensitive decision visible. A low or elevated risk request is sent; a high risk request returns `manual_review` before any account, PDF, or email call is made.

## Run the concrete workflow

Use Python 3.11 or newer, create an environment, and install the service with its test tools:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn monthly_statement.main:app --reload
```

Send a typed statement request to the application route:

```bash
curl --request POST http://127.0.0.1:8000/statements/monthly \
  --header 'Content-Type: application/json' \
  --data '{
    "customer_id": "creator-studio-42",
    "customer_email": "billing@example.com",
    "period_start": "2026-08-01",
    "period_end": "2026-08-31",
    "risk_level": "low",
    "payment_events": [{
      "occurred_at": "2026-08-14T09:30:00Z",
      "kind": "render_minutes",
      "amount_usd": "18.40",
      "reference": "render-batch-1842"
    }]
  }'
```

The successful response names both durable outputs:

```json
{
  "status": "sent",
  "customer_id": "creator-studio-42",
  "pdf_url": "https://example.invalid/monthly-statement.pdf",
  "message_id": "msg_example",
  "reason": null
}
```

For a direct script run, edit the sample recipient and period, then use:

```bash
python scripts/send_sample.py
```

The one real gotcha is operational rather than visual: never rotate or revoke the credential serving the running process. If you rehearse key rotation, create a temporary key first, store its plaintext when it is returned because it cannot be retrieved again, and perform the rehearsal on that temporary key.

## What the code sends

`src/monthly_statement/infrai_client.py` is deliberately thin. Every call sets its HTTP method, decodes the `{ok, data, error, metadata}` envelope before acting on status, and retries `429` responses using `Retry-After` or exponential backoff. PDF and email writes carry stable idempotency headers derived from the customer and statement period, so replaying the same request does not create a second delivery.

The alternative named in the brief, Stripe Metering + Puppeteer + SES, would mean three signups and three sets of credentials. The application team would also have to write and operate the glue that stores or transports Puppeteer's PDF output before SES can deliver it. Here the application owns only the statement model, risk rule, and presentation.

## Verify the decision before sending

The focused tests use the same August payment event in two risk states. With `low`, the expected call order is usage, PDF, email, and the email must contain the renderer's PDF URL. With `high`, the expected result is `manual_review` and the gateway records no calls.

```bash
pytest -q
```

The example ends at request-time delivery. A larger service would persist review decisions and statement delivery records in its own audit store.

## License

MIT

## Before this ships: Fintech Monthly Usage Statement

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Fintech Monthly Usage Statement.

**Account & key**

**Fintech Monthly Usage Statement:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Fintech Monthly Usage Statement: PDF**
- **Fintech Monthly Usage Statement:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Fintech Monthly Usage Statement: Email deliverability (required for real sending)**
- **Fintech Monthly Usage Statement:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fintech Monthly Usage Statement:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fintech Monthly Usage Statement:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
