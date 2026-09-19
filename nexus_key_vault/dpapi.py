"""Windows DPAPI, through ctypes, with no dependencies.

`CryptProtectData` encrypts with a key derived from the logged-on user's
credentials and held by the OS.  That is the property worth having here:
the sealed bytes are meaningless on another machine, under another Windows
account, or in a backup that leaves this profile behind.

What it is not is a boundary between programs.  Anything running as this
user can call `CryptUnprotectData` on the same blob with the same entropy,
and every MO2 plugin runs as this user, in this process.  The entropy below
is a speed bump for a file that has been carried off, not a secret - it is
sitting in this source file, which ships with the plugin.

pywin32 is deliberately not used: MO2's embedded Python does not always
have it, and a vault that fails to open because an optional dependency is
missing is worse than no vault.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

# Bound to this plugin and this file format, so a blob sealed here is not
# interchangeable with one sealed by something else on the same account.
ENTROPY = b"nexus-key-vault/1"

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class Unavailable(RuntimeError):
    """DPAPI could not be reached - not Windows, or the call failed."""


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]

    @classmethod
    def of(cls, data: bytes) -> "_Blob":
        buf = ctypes.create_string_buffer(data, len(data))
        blob = cls(len(data),
                   ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        # The struct holds a bare pointer, so the buffer has to outlive it;
        # without this the plaintext can be collected mid-call.
        blob._keep = buf
        return blob

    def take(self) -> bytes:
        """Copy the bytes out and hand the OS buffer back."""
        try:
            return ctypes.string_at(self.pbData, self.cbData)
        finally:
            if self.pbData:
                ctypes.windll.kernel32.LocalFree(self.pbData)


def available() -> bool:
    try:
        return hasattr(ctypes.windll.crypt32, "CryptProtectData")
    except (AttributeError, OSError):
        return False


def _call(fn, data: bytes, what: str) -> bytes:
    if not data:
        raise Unavailable("nothing to {}".format(what))
    if not available():
        raise Unavailable(
            "Windows DPAPI is not available on this system, so there is "
            "nowhere safe to keep the key.")
    out = _Blob()
    payload = _Blob.of(data)          # both named, so neither is collected
    entropy = _Blob.of(ENTROPY)       # while the call is still using it
    ok = fn(ctypes.byref(payload), None, ctypes.byref(entropy),
            None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
    if not ok:
        raise Unavailable("Windows could not {} the key (error {}).".format(
            what, ctypes.GetLastError()))
    return out.take()


def seal(secret: bytes) -> bytes:
    """Encrypt for this Windows user. Useless to any other account."""
    return _call(ctypes.windll.crypt32.CryptProtectData, secret, "protect")


def unseal(blob: bytes) -> bytes:
    """Decrypt something `seal` produced on this account.

    Fails for a blob sealed by another user or carried from another
    machine, which is the whole point of using DPAPI rather than a
    constant key compiled into the plugin.
    """
    return _call(ctypes.windll.crypt32.CryptUnprotectData, blob, "read")
