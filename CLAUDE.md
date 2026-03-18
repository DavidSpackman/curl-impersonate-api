# curl-impersonate-api

A lightweight REST API wrapper around [curl-impersonate](https://github.com/lwthiker/curl-impersonate) that allows any HTTP client (e.g. n8n, scripts, apps) to make browser-fingerprinted requests without needing curl-impersonate installed locally.

---

## Project Structure

```
curl-impersonate-api/
├── app.py                  # Flask API server
├── Dockerfile              # Built on lwthiker/curl-impersonate:0.6-chrome
├── docker-compose.yml      # Single-service compose for local deployment
├── CLAUDE.md               # This file
└── README.md               # Usage documentation
```

---

## Stack

- **Base image**: `lwthiker/curl-impersonate:0.6-chrome` (Alpine Linux)
- **Language**: Python 3
- **Framework**: Flask
- **Transport**: HTTP REST (JSON in, JSON out)
- **Port**: 5555

---

## API Endpoints

### `GET /health`
Returns service status and available wrapper scripts.

**Response:**
```json
{
  "status": "ok",
  "default_wrapper": "curl_chrome116",
  "available_wrappers": ["curl_chrome116", "curl_chrome110", "curl_edge101"]
}
```

---

### `GET /wrappers`
Lists all known and available wrapper scripts in the running container.

**Response:**
```json
{
  "available": ["curl_chrome116", "curl_chrome110"],
  "all_known": ["curl_chrome99", "curl_chrome100", "..."]
}
```

---

### `POST /fetch`
Makes a browser-fingerprinted HTTP request via curl-impersonate.

**Request body:**
```json
{
  "url": "https://example.com/api",
  "wrapper": "curl_chrome116",
  "method": "GET",
  "headers": {
    "cache-control": "no-cache"
  },
  "data": {}
}
```

| Field     | Required | Default                      | Description                                      |
|-----------|----------|------------------------------|--------------------------------------------------|
| `url`     | Yes      | —                            | URL to fetch                                     |
| `wrapper` | No       | Highest available Chrome     | curl-impersonate wrapper script to use           |
| `method`  | No       | `GET`                        | HTTP method                                      |
| `headers` | No       | `{}`                         | Extra headers added on top of wrapper defaults   |
| `data`    | No       | `null`                       | Request body for POST/PUT (string or JSON obj)   |

**Response:**
```json
{
  "success": true,
  "wrapper": "curl_chrome116",
  "data": { }
}
```

---

## Wrapper Scripts

The wrapper scripts are the core feature of curl-impersonate. Each script pre-sets the correct TLS ciphers, HTTP/2 settings, and browser headers so the fingerprint matches that exact browser version. Headers passed via the API are layered on top.

### Available in `0.6-chrome` image

| Wrapper               | Impersonates         |
|-----------------------|----------------------|
| `curl_chrome116`      | Chrome 116           |
| `curl_chrome110`      | Chrome 110           |
| `curl_chrome107`      | Chrome 107           |
| `curl_chrome104`      | Chrome 104           |
| `curl_chrome101`      | Chrome 101           |
| `curl_chrome100`      | Chrome 100           |
| `curl_chrome99`       | Chrome 99            |
| `curl_chrome99_android` | Chrome 99 Android  |
| `curl_edge101`        | Edge 101             |
| `curl_edge99`         | Edge 99              |
| `curl_safari15_5`     | Safari 15.5          |
| `curl_safari15_3`     | Safari 15.3          |

> Firefox wrappers (`curl_ff*`) require the `0.6-ff` image instead.

---

## Build & Run

```bash
# Build and start
docker compose up -d --build

# Check it's running
curl http://localhost:5555/health

# Test a fetch
curl -X POST http://localhost:5555/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/get",
    "wrapper": "curl_chrome116"
  }'
```

---

## Development Tasks

### Phase 1 — Core (done)
- [x] Flask app with `/health`, `/wrappers`, `/fetch` endpoints
- [x] Wrapper script selection with fallback to default
- [x] Extra header support layered on top of wrapper defaults
- [x] JSON response parsing with raw text fallback
- [x] Timeout and error handling
- [x] Dockerfile based on `lwthiker/curl-impersonate:0.6-chrome`
- [x] docker-compose.yml for local deployment

### Phase 2 — Improvements
- [ ] Add support for `0.6-ff` (Firefox) image via a second compose profile
- [ ] Add optional response headers passthrough (return status code + response headers)
- [ ] Add request logging with timestamp, wrapper used, URL, response code
- [ ] Add `GET /fetch` support for simple URL queries without a POST body
- [ ] Environment variable config (port, default wrapper, timeout)

### Phase 3 — Hardening
- [ ] Add optional API key auth via `X-API-Key` header and env var
- [ ] Rate limiting per client IP
- [ ] Input validation and URL sanitisation
- [ ] Health check in docker-compose
- [ ] README with full usage docs and n8n integration guide

---

## n8n Integration

Use an **HTTP Request** node pointed at `http://<your-nuc-ip>:5555/fetch` with:
- Method: `POST`
- Body type: `JSON`
- Body: see `/fetch` request body above

Use n8n expressions to make the URL or date ranges dynamic before passing them to this service.

---

## Notes

- The container runs curl-impersonate natively — no Docker-in-Docker required
- Each `/fetch` call is stateless — no session or cookie persistence between calls
- Wrapper scripts handle TLS fingerprinting automatically; you do not need to pass browser headers manually
