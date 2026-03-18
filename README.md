# curl-impersonate-api

A lightweight REST API wrapper around [curl-impersonate](https://github.com/lexiforest/curl-impersonate) that lets any HTTP client make browser-fingerprinted requests without needing curl-impersonate installed locally.

Built on `lexiforest/curl-impersonate:alpine` — the actively maintained fork with Chrome 99–145, Firefox, Safari, and Tor wrappers.

---

## Quick Start

```bash
git clone https://github.com/DavidSpackman/curl-impersonate-api.git
cd curl-impersonate-api
docker compose up -d --build

# Verify it's running
curl http://localhost:5555/health
```

---

## API Reference

### `GET /health`
Returns service status and the default wrapper.

```json
{
  "status": "ok",
  "default_wrapper": "curl_chrome145",
  "available_wrappers": ["curl_chrome145", "curl_chrome142", "..."]
}
```

---

### `GET /wrappers`
Lists all available wrappers in the running container vs. all known wrappers.

```json
{
  "available": ["curl_chrome145", "curl_firefox147", "..."],
  "all_known": ["curl_chrome99", "curl_chrome100", "..."]
}
```

---

### `POST /fetch`
Makes a browser-fingerprinted HTTP request.

**Request body:**
```json
{
  "url": "https://example.com/api",
  "wrapper": "curl_chrome145",
  "method": "GET",
  "headers": {
    "cache-control": "no-cache"
  },
  "data": null
}
```

| Field     | Required | Default                  | Description                                    |
|-----------|----------|--------------------------|------------------------------------------------|
| `url`     | Yes      | —                        | URL to fetch                                   |
| `wrapper` | No       | Highest available Chrome | curl-impersonate wrapper script to use         |
| `method`  | No       | `GET`                    | HTTP method                                    |
| `headers` | No       | `{}`                     | Extra headers layered on top of wrapper defaults |
| `data`    | No       | `null`                   | Request body for POST/PUT (string or JSON object) |

**Response:**
```json
{
  "success": true,
  "wrapper": "curl_chrome145",
  "data": { }
}
```

**Example:**
```bash
curl -X POST http://localhost:5555/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/get",
    "wrapper": "curl_chrome145"
  }'
```

---

## Available Wrappers

| Wrapper                  | Impersonates         |
|--------------------------|----------------------|
| `curl_chrome145`         | Chrome 145           |
| `curl_chrome142`         | Chrome 142           |
| `curl_chrome136`         | Chrome 136           |
| `curl_chrome133a`        | Chrome 133           |
| `curl_chrome131`         | Chrome 131           |
| `curl_chrome131_android` | Chrome 131 Android   |
| `curl_chrome124`         | Chrome 124           |
| `curl_chrome123`         | Chrome 123           |
| `curl_chrome120`         | Chrome 120           |
| `curl_chrome119`         | Chrome 119           |
| `curl_chrome116`         | Chrome 116           |
| `curl_chrome110`         | Chrome 110           |
| `curl_chrome107`         | Chrome 107           |
| `curl_chrome104`         | Chrome 104           |
| `curl_chrome101`         | Chrome 101           |
| `curl_chrome100`         | Chrome 100           |
| `curl_chrome99`          | Chrome 99            |
| `curl_chrome99_android`  | Chrome 99 Android    |
| `curl_edge101`           | Edge 101             |
| `curl_edge99`            | Edge 99              |
| `curl_firefox147`        | Firefox 147          |
| `curl_firefox144`        | Firefox 144          |
| `curl_firefox135`        | Firefox 135          |
| `curl_firefox133`        | Firefox 133          |
| `curl_safari260`         | Safari 26.0          |
| `curl_safari260_ios`     | Safari 26.0 iOS      |
| `curl_safari184`         | Safari 18.4          |
| `curl_safari184_ios`     | Safari 18.4 iOS      |
| `curl_safari180`         | Safari 18.0          |
| `curl_safari180_ios`     | Safari 18.0 iOS      |
| `curl_safari172_ios`     | Safari 17.2 iOS      |
| `curl_safari170`         | Safari 17.0          |
| `curl_safari155`         | Safari 15.5          |
| `curl_safari153`         | Safari 15.3          |
| `curl_tor145`            | Tor 145              |

> The default wrapper is the highest available non-Android Chrome version (`curl_chrome145`).

---

## n8n Integration

Use an **HTTP Request** node pointed at `http://<host>:5555/fetch`:

- **Method:** POST
- **Body type:** JSON
- **Body:**
```json
{
  "url": "{{ $json.url }}",
  "wrapper": "curl_chrome145"
}
```

---

## Testing

```bash
pip install pytest flask requests

# Unit tests (no container needed)
pytest test_app.py -v -m "not integration"

# All tests (container must be running)
pytest test_app.py -v
```

---

## Project Structure

```
curl-impersonate-api/
├── app.py               # Flask API server
├── Dockerfile           # Built on lexiforest/curl-impersonate:alpine
├── docker-compose.yml   # Single-service compose with healthcheck
├── requirements.txt     # Python dependencies
├── test_app.py          # Unit and integration tests
└── README.md
```
