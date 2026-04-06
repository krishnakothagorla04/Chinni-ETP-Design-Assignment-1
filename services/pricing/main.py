from fastapi import FastAPI, Request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pricing Service")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/price")
async def get_price(item_id: str, quantity: int = 1, request: Request = None):
    """
    Very simple pricing:
    - base price 10 per item
    - bulk discount for quantity >= 10
    """
    request_id = "unknown"
    if request:
        request_id = request.headers.get("x-request-id", "unknown")
    logger.info("request_id=%s method=GET path=/price item_id=%s quantity=%d", request_id, item_id, quantity)

    base_price = 10.0
    total = base_price * quantity

    if quantity >= 10:
        total *= 0.9  # 10% discount

    return {"item_id": item_id, "quantity": quantity, "total_price": total}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001)
