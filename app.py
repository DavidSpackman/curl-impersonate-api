from flask import Flask, request, jsonify
import subprocess
import json
import shutil
import os

app = Flask(__name__)

# All wrapper scripts available in lexiforest/curl-impersonate:alpine
# Ordered lowest→highest so reversed() picks the highest available as default
CHROME_WRAPPERS = [
    'curl_chrome99', 'curl_chrome99_android',
    'curl_chrome100', 'curl_chrome101', 'curl_chrome104',
    'curl_chrome107', 'curl_chrome110', 'curl_chrome116',
    'curl_chrome119', 'curl_chrome120', 'curl_chrome123',
    'curl_chrome124', 'curl_chrome131', 'curl_chrome131_android',
    'curl_chrome133a', 'curl_chrome136', 'curl_chrome142', 'curl_chrome145',
]

FIREFOX_WRAPPERS = [
    'curl_firefox133', 'curl_firefox135', 'curl_firefox144', 'curl_firefox147',
]

SAFARI_WRAPPERS = [
    'curl_safari153', 'curl_safari155', 'curl_safari170',
    'curl_safari172_ios', 'curl_safari180', 'curl_safari180_ios',
    'curl_safari184', 'curl_safari184_ios', 'curl_safari260', 'curl_safari260_ios',
]

ALL_WRAPPERS = CHROME_WRAPPERS + FIREFOX_WRAPPERS + SAFARI_WRAPPERS

def get_available_wrappers():
    return [w for w in ALL_WRAPPERS if shutil.which(w)]

def get_default_wrapper():
    # Pick the highest Chrome version available (list is ordered lowest→highest)
    for w in reversed(CHROME_WRAPPERS):
        if shutil.which(w):
            return w
    raise RuntimeError("No curl-impersonate wrapper scripts found")

@app.route('/health', methods=['GET'])
def health():
    available = get_available_wrappers()
    try:
        default = get_default_wrapper()
    except RuntimeError:
        default = None
    return jsonify({
        'status': 'ok' if available else 'error',
        'default_wrapper': default,
        'available_wrappers': available
    })

@app.route('/wrappers', methods=['GET'])
def list_wrappers():
    """List all available wrapper scripts in this container."""
    return jsonify({
        'available': get_available_wrappers(),
        'all_known': ALL_WRAPPERS
    })

@app.route('/fetch', methods=['POST'])
def fetch():
    """
    POST body (JSON):
      url        (required) - the URL to fetch
      wrapper    (optional) - wrapper script to use e.g. "curl_chrome145", "curl_firefox147"
                              defaults to highest available Chrome version
      headers    (optional) - dict of extra headers to add/override
      method     (optional) - HTTP method, default GET
      data       (optional) - request body for POST/PUT

    Note: The wrapper scripts already set browser-accurate headers and TLS fingerprints.
    Any headers you pass are ADDED on top of the wrapper's defaults (or override them).
    """
    body = request.json
    if not body or 'url' not in body:
        return jsonify({'error': 'url is required'}), 400

    url = body['url']
    extra_headers = body.get('headers', {})
    method = body.get('method', 'GET').upper()
    post_data = body.get('data', None)
    wrapper = body.get('wrapper', None)

    # Resolve wrapper
    if wrapper:
        if not shutil.which(wrapper):
            available = get_available_wrappers()
            return jsonify({
                'error': f'Wrapper "{wrapper}" not found in this container',
                'available_wrappers': available
            }), 400
    else:
        try:
            wrapper = get_default_wrapper()
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    # Build command - wrapper scripts handle TLS + default headers automatically
    cmd = [wrapper, '-s', '-X', method, url]

    # Add any extra/override headers on top of what the wrapper provides
    for k, v in extra_headers.items():
        cmd += ['-H', f'{k}: {v}']

    if post_data:
        cmd += ['-d', json.dumps(post_data) if isinstance(post_data, dict) else post_data]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return jsonify({
                'success': False,
                'wrapper': wrapper,
                'error': result.stderr,
                'returncode': result.returncode
            }), 502

        # Try to parse response as JSON, fall back to raw text
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = result.stdout

        return jsonify({
            'success': True,
            'wrapper': wrapper,
            'data': data
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Request timed out after 30s'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=False)
