"""Server-only configuration and allowlisted Zoko text sending."""
import json
import re
from database import session_scope
from models import SendIntent
import uuid
from datetime import datetime, timezone
import urllib.request
import urllib.error
from pathlib import Path

class SendRejected(RuntimeError):
    """A definitive API rejection; safe to offer a manual retry."""


ENV = Path(__file__).resolve().parent.parent / '.env'


def config():
    values = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('\"\'')
    return values


def phone(value):
    if not isinstance(value, str) or not re.fullmatch(r'\+?[0-9 ()-]+', value):
        return None
    digits = re.sub(r'[^0-9]', '', value)
    return digits if 7 <= len(digits) <= 15 else None


def allowed(recipient, settings):
    number = phone(recipient)
    entries = {phone(x.strip()) for x in settings.get('ZOKO_ALLOWED_RECIPIENTS', '').split(',')}
    return bool(number and number in entries)


def send(recipient, message, settings=None, agent=None, data_dir=None):
    settings = config() if settings is None else settings
    if not allowed(recipient, settings):
        raise ValueError('Sending is blocked for this recipient.')
    key = settings.get('ZOKO_API_KEY', '')
    if not key or key.startswith('replace_'):
        raise ValueError('Set the Zoko API key in the local .env file.')
    if not isinstance(message, str) or not message.strip() or len(message) > 4096:
        raise ValueError('Enter a message between 1 and 4096 characters.')
    request = urllib.request.Request('https://chat.zoko.io/v2/message',
        data=json.dumps({'channel': 'whatsapp', 'recipient': phone(recipient),
                         'type': 'text', 'message': message.strip()}).encode(),
        headers={'apikey': key, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    intent_id = str(uuid.uuid4())
    data_dir = ENV.parent / 'backend/data' if data_dir is None else data_dir
    if agent:
        with session_scope(data_dir, write=True) as session:
            session.add(SendIntent(id=intent_id, created_at=datetime.now(timezone.utc).isoformat(),
                agent_id=agent['id'], agent_name=agent.get('name'), agent_email=agent.get('email'), status='pending'))
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
            try:
                result = json.loads(raw)
            except (ValueError, TypeError):
                result = {}
            message_id = result.get('id') if isinstance(result, dict) else None
            if agent:
                with session_scope(data_dir, write=True) as session:
                    intent = session.get(SendIntent, intent_id)
                    intent.message_id = message_id if isinstance(message_id, str) else None
                    intent.status = 'accepted'
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise SendRejected('Zoko rejected the API key (HTTP 401). Update ZOKO_API_KEY in the local .env file with the current key from this store’s API settings, then retry.') from None
        raise (SendRejected if error.code < 500 else RuntimeError)(f'Zoko rejected the request (HTTP {error.code}). Check credentials, limits and the WhatsApp reply window.') from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError('Send status is uncertain. Check WhatsApp before trying again; no automatic retry was made.') from None
    notice = 'Accepted by Zoko. Refresh shortly to see the webhook update.'
    if agent and not isinstance(message_id, str):
        notice += ' Agent attribution is pending: Zoko did not return a usable message ID.'
    return {'accepted': True, 'message': notice, 'message_id': message_id if isinstance(message_id, str) else None}
