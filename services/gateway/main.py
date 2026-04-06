from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gateway Service")

CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://localhost:8003")
ARCH_LABEL = "nanoservices-k8s-keda"


def render_gateway_ui() -> str:
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Checkout Gateway</title>
    <style>
        :root {
            color-scheme: light;
            --bg: #f4efe6;
            --panel: #fffaf2;
            --ink: #1f2933;
            --muted: #52606d;
            --accent: #b44d12;
            --accent-dark: #8e3d0e;
            --line: #e6d7c4;
            --ok: #1f7a4c;
            --code: #f7e7d4;
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: Georgia, "Times New Roman", serif;
            background:
                radial-gradient(circle at top left, #fff7ec, transparent 28%),
                linear-gradient(180deg, #f9f4eb 0%, var(--bg) 100%);
            color: var(--ink);
        }

        main {
            max-width: 980px;
            margin: 0 auto;
            padding: 40px 20px 64px;
        }

        .hero {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 18px 40px rgba(86, 63, 27, 0.08);
        }

        h1, h2 { margin: 0 0 12px; }
        p { line-height: 1.6; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 18px;
            margin-top: 22px;
        }

        .card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 20px;
        }

        .endpoint {
            display: inline-block;
            padding: 4px 8px;
            margin-bottom: 10px;
            border-radius: 999px;
            background: var(--code);
            color: var(--accent-dark);
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        a, button {
            transition: transform 140ms ease, background-color 140ms ease;
        }

        a.button, button {
            display: inline-block;
            border: 0;
            border-radius: 12px;
            padding: 12px 16px;
            background: var(--accent);
            color: #fff;
            text-decoration: none;
            font-weight: 700;
            cursor: pointer;
        }

        a.button:hover, button:hover {
            background: var(--accent-dark);
            transform: translateY(-1px);
        }

        form {
            display: grid;
            gap: 12px;
        }

        label {
            display: grid;
            gap: 6px;
            font-weight: 700;
        }

        input {
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px;
            font: inherit;
            background: #fff;
        }

        pre {
            margin: 0;
            padding: 16px;
            border-radius: 16px;
            background: #1e1e1e;
            color: #f5f5f5;
            overflow: auto;
            min-height: 180px;
        }

        .meta {
            color: var(--muted);
            font-size: 0.95rem;
        }
    </style>
</head>
<body>
    <main>
        <section class="hero">
            <h1>Gateway UI</h1>
            <p>This is the public edge component for the checkout system. Use it to verify the architecture label, basic health timing, and submit a browser-driven checkout request.</p>
            <p class="meta">HTML endpoint: <strong>/ui</strong> | Architecture label: <strong>nanoservices-k8s-keda</strong></p>
        </section>

        <section class="grid">
            <article class="card">
                <div class="endpoint">GET /api/arch</div>
                <h2>Architecture Label</h2>
                <p>Opens directly in the browser and returns the gateway architecture label as plain text.</p>
                <a class="button" href="/api/arch" target="_blank" rel="noreferrer">Open /api/arch</a>
            </article>

            <article class="card">
                <div class="endpoint">GET /api/ping</div>
                <h2>Ping</h2>
                <p>Use this for quick health and timing checks from a browser tab or any HTTP client.</p>
                <a class="button" href="/api/ping" target="_blank" rel="noreferrer">Open /api/ping</a>
            </article>

            <article class="card">
                <div class="endpoint">POST /api/checkout</div>
                <h2>Checkout</h2>
                <p>Browsers cannot navigate to a POST endpoint directly, so this form sends the request for you.</p>
                <form id="checkout-form">
                    <label>
                        Item ID
                        <input id="item-id" name="item_id" value="item-1" required>
                    </label>
                    <label>
                        Quantity
                        <input id="quantity" name="quantity" type="number" min="1" value="1" required>
                    </label>
                    <button type="submit">Send POST /api/checkout</button>
                </form>
            </article>
        </section>

        <section class="card" style="margin-top: 18px;">
            <h2>Response</h2>
            <p class="meta">The result of the checkout POST appears below.</p>
            <pre id="result">Waiting for request...</pre>
        </section>
    </main>

    <script>
        const form = document.getElementById("checkout-form");
        const result = document.getElementById("result");

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const itemId = document.getElementById("item-id").value;
            const quantity = Number(document.getElementById("quantity").value);

            result.textContent = "Sending request...";

            try {
                const response = await fetch("/api/checkout", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        items: [{ item_id: itemId, quantity }]
                    })
                });

                const body = await response.json();
                result.textContent = JSON.stringify(
                    {
                        status: response.status,
                        ok: response.ok,
                        body
                    },
                    null,
                    2
                );
            } catch (error) {
                result.textContent = JSON.stringify(
                    {
                        ok: false,
                        error: String(error)
                    },
                    null,
                    2
                );
            }
        });
    </script>
</body>
</html>
        """


@app.get("/", response_class=HTMLResponse)
async def root():
        return render_gateway_ui()


@app.get("/ui", response_class=HTMLResponse)
async def gateway_ui():
        return render_gateway_ui()


@app.get("/api/arch", response_class=PlainTextResponse)
async def get_arch():
        return ARCH_LABEL


@app.get("/api/ping")
async def ping():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/checkout")
async def proxy_checkout(request: Request):
    """
    Public checkout endpoint exposed by the gateway.
    Forwards the JSON body to the checkout service and returns its response.
    """
    request_id = request.headers.get("x-request-id")
    logger.info("request_id=%s method=POST path=/api/checkout", request_id)
    payload = await request.json()

    headers = {"Content-Type": "application/json"}
    if request_id:
        headers["X-Request-Id"] = request_id

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{CHECKOUT_URL}/api/checkout",
                json=payload,
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Checkout service unavailable: {exc}",
        )

    return resp.json()


@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    """
    Basic request ID passthrough; if X-Request-Id is missing, generate a simple one.
    We will propagate this header to downstream services later.
    """
    request_id = request.headers.get("x-request-id")
    if not request_id:
        # Very simple ID for now; can be replaced with UUID later.
        import time

        request_id = f"req-{int(time.time() * 1000)}"

    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)

