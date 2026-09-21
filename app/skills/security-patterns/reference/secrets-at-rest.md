# Secrets at Rest

No token, password, API key, client secret or licence key sits in a database,
queue or log in plaintext. A leaked dump or backup must not hand out working
credentials.

## Pick the protection by what the code does with the value

| The code later... | Store | Example values |
|---|---|---|
| only compares a presented value | keyed HMAC ("blind index"), never the value | password-reset, e-mail verification, invitation, refresh and API tokens |
| reads it back | authenticated encryption | integration credentials (payment, SMS, e-invoicing), card tokens, OAuth refresh tokens of a third party |
| reads it back AND looks rows up by it | ciphertext + a keyed-HMAC column that carries the lookup and the unique index | device API keys, licence keys |
| is a user password | a password hash (argon2id, bcrypt) | login passwords |

A plain SHA-256 of a token is not enough when the token space is small or
guessable; use HMAC with a key the database does not hold.

## Key handling

- One master key per environment, from the environment or a secret manager,
  never from the database. Derive subkeys with HKDF, one per purpose
  (`encrypt`, `index/<purpose>`), so one leaked subkey says nothing about another.
- Write a key id into every ciphertext and hash (`enc:v1:<kid>:...`,
  `h1:<kid>:...`). A value then names the key it needs, and rotation works.
- Rotation: the retired key moves to a `*_PREVIOUS` slot (read-only), a job
  re-encrypts every envelope and recomputes every index with the new key.
  Hash-only tokens cannot be re-keyed (their plaintext is gone): keep the
  previous key until the longest-lived token expires.
- Fail closed: a missing or malformed key stops the first read or write of a
  secret with a message that names the variable. Never fall back to plaintext.
- Back the key up next to the database backups. A lost key is lost data.

## Python (SQLAlchemy)

```python
import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.types import String, Text, TypeDecorator

MASTER = base64.b64decode(os.environ["DATA_ENCRYPTION_KEY"])  # 32 random bytes


def _subkey(info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(MASTER)


ENC_KEY = _subkey(b"secrets-at-rest/v1/encrypt")
KEY_ID = _subkey(b"secrets-at-rest/v1/key-id")[:4].hex()


def encrypt(plaintext: str) -> str:
    header = f"enc:v1:{KEY_ID}"
    nonce = os.urandom(12)
    sealed = AESGCM(ENC_KEY).encrypt(nonce, plaintext.encode(), header.encode())
    return f"{header}:{base64.urlsafe_b64encode(nonce + sealed).decode()}"


def decrypt(stored: str) -> str:
    _, _, key_id, payload = stored.split(":", 3)
    if key_id != KEY_ID:
        raise LookupError(f"value written with key {key_id}; set the previous key to read it")
    raw = base64.urlsafe_b64decode(payload)
    # InvalidTag on tampering: never treat a failed decrypt as legacy plaintext.
    return AESGCM(ENC_KEY).decrypt(raw[:12], raw[12:], f"enc:v1:{key_id}".encode()).decode()


def blind_index(value: str, purpose: str) -> str:
    key = _subkey(b"secrets-at-rest/v1/index/" + purpose.encode())
    digest = hmac.new(key, value.encode(), hashlib.sha256).digest()
    return f"h1:{KEY_ID}:{base64.urlsafe_b64encode(digest).decode().rstrip('=')}"


class EncryptedText(TypeDecorator):
    """Read-back secret: the Python side is always plaintext, the column always ciphertext."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value if value in (None, "") else encrypt(value)

    def process_result_value(self, value, dialect):
        return value if value in (None, "") else decrypt(value)


class HashedToken(TypeDecorator):
    """Compare-only token: binds hash too, so `where(Model.token == presented)` just works."""

    impl = String
    cache_ok = True

    def __init__(self, purpose: str) -> None:
        super().__init__(64)  # "h1:" + 8-char key id + ":" + 43-char digest = 55
        self.purpose = purpose

    def process_bind_param(self, value, dialect):
        return None if value is None else blind_index(value, self.purpose)
```

During a rotation `HashedToken` only hashes with the current key; look tokens up
with `column.in_([...])` over the current and previous key's hashes until the
previous key is retired.

## PHP (Doctrine)

- A custom DBAL type (`encrypted_text`, a `TextType` subclass) encrypts in
  `convertToDatabaseValue()` and decrypts in `convertToPHPValue()`, with
  libsodium XChaCha20-Poly1305 (`sodium_crypto_aead_xchacha20poly1305_ietf_*`)
  and the envelope header as associated data. A DBAL type cannot take
  constructor dependencies: hand it the cipher from the bundle's `boot()`.
- Attributes mark derived columns (`#[HashedToken(purpose)]`,
  `#[BlindIndexOf(field, purpose)]`), and one `onFlush` listener recomputes them
  from the mapping, so no service, fixture or test can write a token in clear.
- Messenger: set `framework.messenger.serializer.default_serializer` to an
  encrypting serializer. Queued and failed messages carry live reset and
  booking links; the Doctrine `failed` queue keeps them for weeks.

## Migrating existing plaintext

1. The schema migration widens columns to TEXT and moves lookups and unique
   indexes to the hash columns. It converts no data: a migration has no key.
2. An idempotent command (`--dry-run` first) encrypts or hashes legacy rows in
   keyset-paged, compare-and-set UPDATEs, and runs right after the migrations on
   deploy. Until it has run, reads accept legacy plaintext; writes always protect.
3. A second migration redacts the same values from audit and request logs, where
   they were copied before.
4. Rotate every credential that was ever stored in clear; the old value may
   survive in backups and log archives.

## Enforce it with a test over the mapping

```python
import re

from myapp.db import Base
from myapp.secrets import EncryptedText, HashedToken

SECRET_NAME = re.compile(r"token|secret|password|passwd|apikey|privatekey|licen[cs]ekey|credential|signingkey|accesskey")
NOT_SECRETS = {"users.password_hash": "argon2id hash, not the password"}


def test_no_secret_looking_column_is_plaintext():
    offenders, explained = [], set()
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            key = f"{table.name}.{column.name}"
            if not SECRET_NAME.search(column.name.replace("_", "").lower()):
                continue
            if isinstance(column.type, (EncryptedText, HashedToken)):
                continue
            if key in NOT_SECRETS:
                explained.add(key)
                continue
            offenders.append(key)
    assert offenders == [], "encrypt or hash these, or explain them in NOT_SECRETS: " + ", ".join(offenders)
    assert explained == set(NOT_SECRETS), f"stale NOT_SECRETS entries: {set(NOT_SECRETS) - explained}"
```

Also check that the queue serializer is the encrypting one and that every
secret-looking settings key is in the encrypted-keys list. The check is by name:
a credential stored under a neutral name (`code`, `value`) is still the author's
job. Plant one violation once to see the test fail before trusting it.

## Gotchas

- A secret derived from the framework's app secret (unsubscribe or signed links)
  dies when that secret rotates. Give each long-lived link family its own key.
- Comparing a presented value against a stored hash that begins with `h1:` must
  never succeed: a stolen hash is not a credential.
- `''` and `NULL` usually mean "not configured"; store them as-is rather than
  encrypting an empty string.
- Encrypted columns cannot be searched, sorted or indexed. If a feature needs
  that, it needs a blind index, not plaintext.
