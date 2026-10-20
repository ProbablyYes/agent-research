"""Fail-closed persistent accounting. Nanodollars; reservations never refunded.

A verified per-request billing bound is a prerequisite, NOT inferred from price metadata.
No CLI dispatch is provided while the real round's billing gate is unresolved.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import threading
import time

from .probe import ENDPOINT, MODEL, read_key, session

ROUND_ID = 'api-agent-20261020'
BUDGET_NANO = 3_000_000_000
MAX_REQUESTS = 400
LEDGER_PATH = Path('/home/hly/.config/agent-research/api-agent-20261020.sqlite3')


class Halt(RuntimeError):
    """Only static non-sensitive reason codes may cross this boundary."""


class Deadline(BaseException):
    pass


@contextlib.contextmanager
def deadline(seconds=60):
    if threading.current_thread() is not threading.main_thread() or signal.getitimer(signal.ITIMER_REAL)[0]:
        raise Halt('deadline_unavailable')
    old = signal.getsignal(signal.SIGALRM)
    def alarm(*_):
        raise Deadline()
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


class Ledger:
    @classmethod
    def create(cls, path, contract):
        # Explicit create-only; reopening never recreates a lost/reset ledger.
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        db = sqlite3.connect(path)
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.executescript('''
                CREATE TABLE meta (round_id TEXT PRIMARY KEY, contract TEXT NOT NULL, halted TEXT);
                CREATE TABLE requests (
                    request_id TEXT PRIMARY KEY, phase TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL, reserve_nano INTEGER NOT NULL,
                    max_tokens INTEGER NOT NULL, state TEXT NOT NULL,
                    result TEXT, estimated_nano INTEGER);
            ''')
            db.execute('INSERT INTO meta VALUES (?, ?, NULL)', (ROUND_ID, json.dumps(contract, sort_keys=True)))
            db.commit()
        finally:
            db.close()
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        return cls(path)

    def __init__(self, path=LEDGER_PATH):
        self.path = Path(path)
        if not self.path.is_file() or self.path.is_symlink():
            raise Halt('ledger_missing')
        self.db = sqlite3.connect('file:' + str(self.path) + '?mode=rw', uri=True, timeout=5)
        self.db.execute('PRAGMA synchronous=FULL')
        row = self.db.execute('SELECT round_id,contract FROM meta').fetchone()
        if not row or row[0] != ROUND_ID:
            raise Halt('ledger_identity')
        self.contract = json.loads(row[1])

    def close(self): self.db.close()

    def halt(self, reason):
        if not re.fullmatch('[a-z_]+', reason): reason = 'unclassified_failure'
        with self.db:
            self.db.execute('UPDATE meta SET halted=COALESCE(halted,?)', (reason,))

    def summary(self):
        n, reserved, estimated = self.db.execute('SELECT count(*),COALESCE(sum(reserve_nano),0),COALESCE(sum(estimated_nano),0) FROM requests').fetchone()
        return {'round_id': ROUND_ID, 'request_reservations': n, 'reserved_nano_usd': reserved,
                'estimated_nano_usd': estimated, 'budget_nano_usd': BUDGET_NANO,
                'max_requests': MAX_REQUESTS,
                'halted': self.db.execute('SELECT halted FROM meta').fetchone()[0],
                'unresolved_requests': self.db.execute("SELECT count(*) FROM requests WHERE state='reserved'").fetchone()[0]}

    def reserve(self, request_id, phase, payload):
        # BEGIN IMMEDIATE serializes concurrent processes before count/cost check.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            reason = None
            c = self.contract
            n, reserved = self.db.execute('SELECT count(*),COALESCE(sum(reserve_nano),0) FROM requests').fetchone()
            if self.db.execute('SELECT halted FROM meta').fetchone()[0]: reason = 'round_halted'
            elif self.db.execute("SELECT 1 FROM requests WHERE state='reserved'").fetchone(): reason = 'unresolved_request'
            elif self.db.execute('SELECT 1 FROM requests WHERE request_id=?', (request_id,)).fetchone(): reason = 'duplicate_request'
            elif c.get('reliable_billing_bound') is not True: reason = 'unverified_billing_bound'
            elif n >= MAX_REQUESTS: reason = 'request_limit'
            elif phase not in ('smoke', 'pilot'): reason = 'phase_invalid'
            elif not re.fullmatch('[a-zA-Z0-9:_-]{1,160}', request_id): reason = 'request_id_invalid'
            elif set(payload) - {'model','messages','temperature','max_tokens','stream','stop'}: reason = 'payload_fields'
            elif payload.get('model') != MODEL or payload.get('stream') is not False or payload.get('temperature') != 0: reason = 'payload_protocol'
            elif type(payload.get('max_tokens')) is not int or not 1 <= payload['max_tokens'] <= 64: reason = 'output_limit'
            elif (not isinstance(payload.get('messages'),list) or len(payload['messages'])!=1 or
                  set(payload['messages'][0]) != {'role','content'} or payload['messages'][0]['role']!='user' or
                  not isinstance(payload['messages'][0]['content'],str)): reason = 'message_format'
            elif 'stop' in payload and payload['stop'] != ['\n']: reason = 'stop_format'
            values = [c.get(k) for k in ('input_bound','input_nano_per_token','output_nano_per_token')]
            if not reason and any(type(v) is not int or v <= 0 for v in values): reason = 'unknown_rate'
            amount = values[0]*values[1]+payload['max_tokens']*values[2] if not reason else 0
            if not reason and reserved + amount > BUDGET_NANO: reason = 'budget_limit'
            if reason:
                self.db.execute('UPDATE meta SET halted=COALESCE(halted,?)', (reason,))
                self.db.commit()
                raise Halt(reason)
            encoded = json.dumps(payload,sort_keys=True,allow_nan=False).encode()
            self.db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,NULL,NULL)',
                (request_id,phase,hashlib.sha256(encoded).hexdigest(),amount,payload['max_tokens'],'reserved'))
            self.db.commit()  # durable before any external request
            return amount
        except BaseException:
            if self.db.in_transaction: self.db.rollback()
            raise

    def complete(self, request_id, result):
        c = self.contract
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT state,max_tokens,reserve_nano FROM requests WHERE request_id=?',(request_id,)).fetchone()
            usage=result.get('usage',{})
            valid=(row and row[0]=='reserved' and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens','total_tokens')))
            if valid:
                valid=(usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens'] and
                       usage['prompt_tokens']<=c['input_bound'] and usage['completion_tokens']<=row[1])
            if not valid:
                self.db.execute("UPDATE meta SET halted='unknown_or_invalid_usage'");self.db.commit()
                raise Halt('unknown_or_invalid_usage')
            cost=usage['prompt_tokens']*c['input_nano_per_token']+usage['completion_tokens']*c['output_nano_per_token']
            if cost>row[2]: raise Halt('cost_exceeds_reservation')
            self.db.execute("UPDATE requests SET state='completed',result=?,estimated_nano=? WHERE request_id=?",
                            (json.dumps(result,allow_nan=False),cost,request_id))
            self.db.commit()
        except BaseException:
            if self.db.in_transaction: self.db.rollback()
            raise


def strict_action(text, admissible):
    match=re.fullmatch(r'\s*ACTION:\s*([^\r\n]+)\s*',text)
    if not match: raise Halt('action_parse_failure')
    proposed=match.group(1).strip()
    matches=[a for a in admissible if ' '.join(a.lower().split())==' '.join(proposed.lower().split())]
    if len(matches)!=1: raise Halt('action_not_admissible')
    return matches[0]


def guarded_call(ledger, request_id, phase, payload, transport=None, credential_reader=read_key):
    ledger.reserve(request_id,phase,payload)
    own=transport is None
    key=None
    start=time.monotonic()
    try:
        # This is reached only with a verified billing contract; real-round contract is false.
        key=credential_reader()
        if own: transport=session()
        with deadline(60):
            response=transport.post(ENDPOINT,json=payload,headers={'Authorization':'Bearer '+key},
                                    allow_redirects=False,verify=True,timeout=(10,50))
            if response.status_code!=200: raise Halt('http_error')
            data=response.json()
            if data.get('object')!='chat.completion' or data.get('model')!=MODEL: raise Halt('response_protocol')
            choices=data.get('choices')
            if not isinstance(choices,list) or len(choices)!=1: raise Halt('choices_protocol')
            choice=choices[0]; content=choice.get('message',{}).get('content')
            if choice.get('finish_reason')!='stop' or not isinstance(content,str): raise Halt('output_protocol')
            if key in content or re.search(r'sk-[A-Za-z0-9_-]{12,}',content): raise Halt('secret_in_response')
            u=data.get('usage')
            if not isinstance(u,dict): raise Halt('unknown_usage')
            # Unsupported billing-bearing fields require review; don't silently drop them.
            if set(u)-{'prompt_tokens','completion_tokens','total_tokens','prompt_tokens_details','completion_tokens_details'}: raise Halt('unknown_usage_field')
            for name in ('prompt_tokens_details','completion_tokens_details'):
                details=u.get(name) or {}
                allowed={'cached_tokens'} if name=='prompt_tokens_details' else {'reasoning_tokens','audio_tokens','accepted_prediction_tokens','rejected_prediction_tokens'}
                if not isinstance(details,dict) or set(details)-allowed: raise Halt('unknown_usage_detail')
                if any(type(v) is not int or v<0 for v in details.values()): raise Halt('unknown_usage_detail')
                if name=='completion_tokens_details' and any(details.values()): raise Halt('unexpected_billed_tokens')
            result={'model':MODEL,'http_status':200,'text':content,'usage':{k:u.get(k) for k in ('prompt_tokens','completion_tokens','total_tokens')},
                    'latency_seconds':time.monotonic()-start,'bill_verified':False}
            ledger.complete(request_id,result)
            return result
    except BaseException as error:
        code=str(error) if type(error) is Halt else 'deadline_or_transport_failure'
        ledger.halt(code)
        raise Halt(code if re.fullmatch('[a-z_]+',code) else 'unclassified_failure') from None
    finally:
        key=None
        if own and transport is not None: transport.close()


def guarded_action(ledger, request_id, phase, payload, admissible, **kwargs):
    result=guarded_call(ledger,request_id,phase,payload,**kwargs)
    try:
        action=strict_action(result['text'],admissible)
    except Halt:
        # Raw non-secret model output has already been persisted; no env.step occurs.
        ledger.halt('action_parse_failure')
        raise
    return result,action
