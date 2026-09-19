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

**Wine is refused on purpose.**  Wine implements these two calls, so
everything here succeeds under Proton and nothing looks wrong - but Wine
cannot know the real keying mechanism, so it derives one from the
username, a salt kept in the blob, the caller's entropy, and a constant
in its own public source.  Ours is public too.  That makes the sealed
file openable by anyone who has it, which is precisely the threat this
module was chosen to answer.  `available()` therefore returns False under
Wine and the vault falls back to :mod:`portable`, which is honest about
what it can offer.  `unseal_regardless` exists only so a key stored by an
older version under Wine can be read once and re-wrapped.
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


def wine() -> str:
    """Wine's version string, or "" on real Windows.

    `wine_get_version` is Wine's own marker: it exports it precisely so
    software that needs to know can ask.
    """
    try:
        fn = ctypes.windll.ntdll.wine_get_version
    except (AttributeError, OSError):
        return ""
    try:
        fn.restype = ctypes.c_char_p
        return (fn() or b"").decode("utf-8", "replace")
    except OSError:
        # It is there, so this is Wine, even if the call misbehaved.
        return "unknown"


def present() -> bool:
    """Are the calls there at all - Wine included."""
    try:
        return hasattr(ctypes.windll.crypt32, "CryptProtectData")
    except (AttributeError, OSError):
        return False


def available() -> bool:
    """Is there *real* DPAPI here, worth the claim the vault makes."""
    return present() and not wine()


def _call(fn, data: bytes, what: str, trusted: bool = True) -> bytes:
    if not data:
        raise Unavailable("nothing to {}".format(what))
    if not (available() if trusted else present()):
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


def unseal_regardless(blob: bytes) -> bytes:
    """Read a blob even under Wine, for migration and nothing else.

    An earlier version stored keys through Wine's DPAPI.  Those users
    still need their key back so it can be re-wrapped properly, and
    refusing to read it would strand them for the sake of a principle
    that has already been broken by the file existing.
    """
    return _call(ctypes.windll.crypt32.CryptUnprotectData, blob, "read",
                 trusted=False)
