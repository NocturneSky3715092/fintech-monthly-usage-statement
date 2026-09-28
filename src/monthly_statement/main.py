from fastapi import Depends, FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .models import StatementRequest, StatementResult
from .receipt_sender import send_monthly_statement

app = FastAPI(title="Monthly usage statement service")


def get_infrai() -> InfraiClient:
    client = InfraiClient()
    try:
        yield client
    finally:
        client.close()


@app.post("/statements/monthly", response_model=StatementResult)
def create_monthly_statement(
    request: StatementRequest,
    infrai: InfraiClient = Depends(get_infrai),
) -> StatementResult:
    try:
        return send_monthly_statement(request, infrai)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
