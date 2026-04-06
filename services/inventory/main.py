from fastapi import FastAPI, HTTPException, Request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Inventory Service")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stock")
async def get_stock(item_id: str, request: Request = None):
    """
    Simple in-memory stock:
    - "item-1": 100
    - "item-2": 0 (out of stock example)
    """
    request_id = "unknown"
    if request:
        request_id = request.headers.get("x-request-id", "unknown")
    logger.info("request_id=%s method=GET path=/stock item_id=%s", request_id, item_id)

    stock_data = {"item-1": 100, "item-2": 0}
    stock = stock_data.get(item_id)

    if stock is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"item_id": item_id, "available": stock}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002)
