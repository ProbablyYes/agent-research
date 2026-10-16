"""One paid request at most, across invocations; no Agent collection entrypoint."""
import json
import os
from pathlib import Path
import stat
import time
from urllib.parse import urlsplit

import requests

ROOT = Path('/home/hly/agent-research')
KEY = Path('/home/hly/.config/agent-research/ofox.key')
STATE = Path('/home/hly/.config/agent-research/ofox-connectivity-attempt.json')
ENDPOINT = 'https://api.ofox.ai/v1/chat/completions'
MODEL = 'openai/gpt-4o-mini'


def read_key(path=KEY):
    # Never put secret contents or OS exception strings into logs.
    if path.parent.is_symlink() or stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise ValueError('credential_directory_permissions')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o600:
            raise ValueError('credential_file_permissions')
        value = os.read(fd, 4096).decode().strip()
    finally:
        os.close(fd)
    if not value or any(c.isspace() for c in value) or len(value) >= 4096:
        raise ValueError('credential_format')
    return value


def session():
    s = requests.Session()
    s.trust_env = False  # No netrc or inherited authentication/CA overrides.
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:
        p = urlsplit(proxy)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            raise ValueError('unsupported_proxy_configuration')
        s.proxies = {'https': proxy}  # HTTPS CONNECT; destination TLS remains verified.
    s.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))
    return s


def probe(key, transport, state=STATE):
    # Exclusive, fsynced reservation BEFORE transmission. Timeout/crash consumes the slot.
    fd = os.open(state, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'attempt_reserved': True, 'max_requests': 1}, f)
        f.flush()
        os.fsync(f.fileno())
    payload = {'model': MODEL, 'messages': [{'role': 'user', 'content': 'Reply with exactly: OK'}],
               'temperature': 0, 'max_tokens': 16, 'stream': False}
    result = {'status': 'ATTEMPTED', 'model_requested': MODEL, 'endpoint': ENDPOINT,
              'max_tokens': 16, 'http_status': None, 'normal_return': False,
              'request_count_upper_bound': 1, 'retry_count': 0, 'redirects_followed': 0,
              'usage': None, 'estimated_usd': None, 'bill_verified': False}
    start = time.monotonic()
    try:
        r = transport.post(ENDPOINT, json=payload, headers={'Authorization': 'Bearer ' + key},
                           timeout=(10, 60), allow_redirects=False, verify=True)
        result['http_status'] = r.status_code
        if r.status_code != 200:
            result['failure'] = 'non_200_body_suppressed'
            return result
        data = r.json()
        # Only explicitly safe scalars are persisted. No raw body/headers/exception messages.
        response_model = data.get('model')
        allowed = {MODEL, 'gpt-4o-mini', 'gpt-4o-mini-2024-07-18', 'openai/gpt-4o-mini-2024-07-18'}
        result['model_response'] = response_model if response_model in allowed else 'UNRECOGNIZED_REDACTED'
        result['response_format'] = 'chat.completion' if data.get('object') == 'chat.completion' else 'OTHER'
        choice = data['choices'][0]
        content = choice['message']['content']
        result['exact_ok'] = isinstance(content, str) and content.strip() == 'OK'
        result['finish_reason'] = choice.get('finish_reason') if choice.get('finish_reason') in ('stop', 'length', 'content_filter') else 'OTHER'
        usage = data.get('usage')
        if isinstance(usage, dict):
            result['usage'] = {k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                               if type(usage.get(k)) is int and usage[k] >= 0}
            if all(k in result['usage'] for k in ('prompt_tokens', 'completion_tokens')):
                result['estimated_usd'] = result['usage']['prompt_tokens'] * .00000015 + result['usage']['completion_tokens'] * .0000006
        result['normal_return'] = bool(result['exact_ok'] and response_model in allowed and result['response_format'] == 'chat.completion')
        if not result['normal_return']:
            result['failure'] = 'unexpected_response_no_retry'
    except Exception as exc:
        result['failure'] = 'transport_or_schema_error'
        result['error_type'] = type(exc).__name__
    finally:
        result['latency_seconds'] = round(time.monotonic() - start, 6)
    return result


def main():
    output = ROOT / 'reports/evidence/api_preflight/connection_result.json'
    if output.exists():
        print('Existing connection result: refusing another invocation')
        return
    try:
        key = read_key()
        s = session()
    except Exception as exc:
        print(json.dumps({'status': 'BLOCKED_BEFORE_REQUEST', 'error_type': type(exc).__name__, 'paid_requests': 0}))
        return
    try:
        result = probe(key, s)
    except FileExistsError:
        print('Attempt already reserved: no request sent; do not remove reservation')
        return
    finally:
        s.close()
        key = None
    with output.open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
