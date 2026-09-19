"""Sealing the key without help from the OS, using only the stdlib.

This exists for Wine.  MO2 has no native Linux or macOS build, so those
users run it under Wine or Proton - and Wine *does* implement DPAPI, which
is the trap.  Nothing errors.  A key is stored, the dialog says encrypted,
and the file looks sealed.  But Wine derives its key from the username, a
salt kept inside the blob, the caller's entropy, and a constant written
into Wine's own public source.  Ours is in *our* public source.  Every
input is either published or sitting in the file, so anyone holding the
file can open it.

That is exactly the threat DPAPI was chosen to close - the backup, the
support archive, the synced profile folder.  Accepting Wine's version
would mean making a claim on Linux that is not true, which is worse than
having no vault there at all.  So on Wine this module is used instead and
:mod:`dpapi` is refused.

What this can honestly offer depends on where the key comes from:

    passphrase   real.  The secret is in the user's head, scrypt-stretched,
                 and nothing on disk can open the file without it.
    machine      obfuscation, and labelled that way everywhere it is used.
                 It defeats a file that has been carried off - to another
                 machine, another account, another folder - because the
                 path and host are mixed in.  It does not defeat someone
                 who reads this file, and this file ships with the plugin.

There is no third option.  If the plugin can open the vault unattended
then everything needed to open it is on the disk, and whatever copies the
file copies that too.  Real DPAPI escapes this only by keeping a secret
outside the file, in the OS, and on Wine there is no such secret to
borrow.  Saying so plainly is the point.

The construction is deliberately boring and built from hashlib and hmac:
scrypt to stretch, HMAC-SHA256 in counter mode for a keystream, and
encrypt-then-MAC so a damaged or edited file is rejected rather than
decrypted into nonsense.  No AES implementation to get wrong, nothing to
install, and short enough to audit in one sitting.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import platform
import secrets

MAGIC = b"NKV2"
SALT = 16
NONCE = 12
TAG = 32

SCHEME_MACHINE = 1
SCHEME_PASSPHRASE = 2

NAMES = {
    SCHEME_MACHINE: "portable-machine",
    SCHEME_PASSPHRASE: "portable-passphrase",
}


class Tampered(Exception):
    """The file was edited, truncated, or is not ours."""


class WrongSecret(Exception):
    """The passphrase or machine does not match the one that sealed it."""


def _derive(material: bytes, salt: bytes, scheme: int) -> tuple[bytes, bytes]:
    """Stretch the material into an encryption key and a MAC key.

    A passphrase gets the expensive parameters because it is guessable and
    stretching is the only thing standing in the way.  Machine material is
    not secret at all, so spending a quarter-second on it would buy
    nothing but a slower MO2 start.
    """
    hard = scheme == SCHEME_PASSPHRASE
    n = 1 << (16 if hard else 14)
    r, p = 8, 1
    # OpenSSL's default cap is 32 MiB, which n=2**16 exceeds - without
    # this the call fails rather than running slowly.
    maxmem = 128 * n * r * 2
    out = hashlib.scrypt(material, salt=salt, n=n, r=r, p=p,
                         dklen=64, maxmem=maxmem)
    return out[:32], out[32:]


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(4, "big"),
                        hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def machine_material(path: str) -> bytes:
    """Identifiers that travel badly, which is the whole idea.

    None of this is secret.  It is chosen so that the sealed file stops
    working when it is separated from the machine and the install it was
    written on, because that separation - a backup, an archive, a pasted
    folder - is the thing actually worth defending against here.
    """
    parts = [
        "nexus-key-vault/machine/2",
        platform.node(),
        os.environ.get("USERNAME") or os.environ.get("USER") or "",
        os.environ.get("USERDOMAIN") or "",
        os.path.normcase(os.path.abspath(os.path.dirname(path))),
    ]
    return "\x00".join(parts).encode("utf-8", "replace")


def seal(secret: bytes, material: bytes, scheme: int) -> bytes:
    if not secret:
        raise ValueError("nothing to seal")
    salt = secrets.token_bytes(SALT)
    nonce = secrets.token_bytes(NONCE)
    enc, mac = _derive(material, salt, scheme)
    header = MAGIC + bytes([scheme]) + salt + nonce
    stream = _keystream(enc, nonce, len(secret))
    cipher = bytes(a ^ b for a, b in zip(secret, stream))
    tag = hmac.new(mac, header + cipher, hashlib.sha256).digest()
    return header + cipher + tag


def scheme_of(blob: bytes) -> int:
    """Which scheme sealed this, so the caller knows what to ask for."""
    if len(blob) < len(MAGIC) + 1 or not blob.startswith(MAGIC):
        raise Tampered("This is not a vault file written by this plugin.")
    scheme = blob[len(MAGIC)]
    if scheme not in NAMES:
        raise Tampered("This vault file uses a scheme this version does "
                       "not know about.")
    return scheme


def unseal(blob: bytes, material: bytes) -> bytes:
    scheme = scheme_of(blob)
    head = len(MAGIC) + 1
    if len(blob) < head + SALT + NONCE + TAG:
        raise Tampered("The vault file is too short to be complete.")
    salt = blob[head:head + SALT]
    nonce = blob[head + SALT:head + SALT + NONCE]
    cipher = blob[head + SALT + NONCE:-TAG]
    tag = blob[-TAG:]
    enc, mac = _derive(material, salt, scheme)
    expected = hmac.new(mac, blob[:-TAG], hashlib.sha256).digest()
    # Constant time, and before decrypting: a failed tag means either the
    # wrong secret or an edited file, and we should not act on the bytes
    # either way.
    if not hmac.compare_digest(tag, expected):
        raise WrongSecret(
            "The vault could not be opened with this "
            + ("passphrase." if scheme == SCHEME_PASSPHRASE
               else "machine and install folder."))
    stream = _keystream(enc, nonce, len(cipher))
    return bytes(a ^ b for a, b in zip(cipher, stream))
