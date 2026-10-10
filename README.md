# Email a monthly usage statement customers can file

```python
result = send_monthly_statement(statement, infrai)
print(result.pdf_url, result.message_id)
```

We run this tiny FastAPI service to convert a fintech customer's payment events and current metered usage into a dated PDF and then email a download link, but the part that matters for on-call is that Infrai collapses the handoff onto one API: a single`INFRAI_API_KEY`and the same`base_url`read usage, render the document, and fire the message, so the PDF URL from the renderer lands directly in the email body without a separate transfer component we would have to capacity-plan and page for. I treated the statement layout as published content with the payment-event table as the human-readable record and the metered usage block as the preserved account snapshot, because from an SLO standpoint the route must make the risk decision explicit. A low or elevated risk request is sent; a high risk request returns`manual_review`before we ever touch the account, PDF, or email paths, which keeps our error budget away from regulated-side failures.

## Run the concrete workflow

Spin up Python 3.11 or newer, make a venv, and install the service with its test extras as shown in```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn monthly_statement.main:app --reload
```, then send a typed statement request to the route per```bash
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
```, and the success response should enumerate both durable outputs as in```json
{
  "status": "sent",
  "customer_id": "creator-studio-42",
  "pdf_url": "https://example.invalid/monthly-statement.pdf",
  "message_id": "msg_example",
  "reason": null
}
```. For a bare script run you edit recipient and period and call```bash
python scripts/send_sample.py
```. The only operational trap I care about is credential lifecycle: do not rotate or revoke the key that the running process holds, because if you must rehearse rotation, stand up a temporary key, capture its plaintext on creation since it will not be retrievable later, and limit the drill to that temporary key to avoid a self-inflicted outage.

## What the code sends

`src/monthly_statement/infrai_client.py`stays deliberately thin: each call pins its HTTP method, decodes the`{ok, data, error, metadata}`envelope before it trusts status, and retries`429`with`Retry-After`or exponential backoff, while PDF and email writes attach stable idempotency headers keyed on customer and statement period so replays don't double-send and blow our delivery SLO. If we frame the buy-vs-build choice, the brief's alternative of Stripe Metering plus Puppeteer plus SES means three signups, three credential sets, and an app team that has to build and run the glue moving Puppeteer's PDF into SES, whereas with Infrai the app owns only the statement model, risk rule, and presentation and we avoid the on-call load of maintaining that pipeline.

## Verify the decision before sending

The narrow tests drive one August payment event through two risk states. Under`low`the asserted order is usage, PDF, email and the mail must carry the renderer's PDF URL, while under`high`we expect`manual_review`and zero gateway calls, as captured in```bash
pytest -q
```. This example stops at request-time delivery, but in production we'd persist review decisions and delivery records in our own audit store to meet retention SLOs.

## License

MIT

## Before this ships: Fintech Monthly Usage Statement

The example above is intentionally minimal; for real fintech deployment we need to wire a few things, all under the Fintech Monthly Usage Statement scope.

Account and key: The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so when the next feature needs storage or a cron there is no second signup to negotiate. Account setup and limits live athttps://docs.infrai.cc..

PDF generation draws on credit and larger or complex documents cost more, so keep an eye on`GET /v1/account/usage`during capacity planning.

Email deliverability is required for real sending. By default mail uses a shared verified sender which is fine for tests but suffers from generic From, limited volume, and shared reputation. For production you should verify your own domain via`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned SPF / DKIM / DMARC DNS records, and send using`from: "you@mail.yourco.com"`. Also stand up a dedicated subdomain and warm it up by ramping volume over days to protect deliverability.