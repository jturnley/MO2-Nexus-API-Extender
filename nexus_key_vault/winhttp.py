"""HTTPS through Windows itself, for when MO2's Python cannot do it.

Python's HTTPS is OpenSSL plus a copy of the Windows certificate store, and
both halves fail on real PCs: MO2's _ssl.pyd cannot load when its
libssl-3-x64.dll is missing or shadowed, and the copied store can lack a
root Windows has simply not downloaded yet, or end a chain at a certificate
that expired years ago. Edge and every other Windows program on the same PC
reach Nexus fine, because they ask Windows.

So does this, as a fallback. WinHTTP is part of Windows, is called through
ctypes, and needs nothing installed. Windows builds and checks the chain
the way Edge does, fetching a missing root from Windows Update when it has
to. Certificate checking is never relaxed: a certificate Windows rejects
fails the request here exactly as it would in a browser.

Only the request is done here. What to send and what the answer means stay
in ``client``, so both transports are held to the same rules - including
that the key never appears in an error message.
"""

from __future__ import annotations

import ctypes
import sys
import urllib.parse

ACCESS_AUTOMATIC_PROXY = 4      # Windows 8.1+: system and per-user proxy
ACCESS_DEFAULT_PROXY = 0        # older: the system proxy only
FLAG_SECURE = 0x00800000
QUERY_STATUS_CODE = 19
QUERY_RAW_HEADERS_CRLF = 22
QUERY_FLAG_NUMBER = 0x20000000
ERROR_INSUFFICIENT_BUFFER = 122

# What a WinHTTP failure means, in the words the client uses for urllib's.
REASONS = {
    12002: "the request timed out",
    12007: "the server name could not be resolved",
    12029: "the connection could not be made",
    12030: "the connection was dropped",
    12152: "the server sent an invalid response",
    12175: "Windows rejected the server's certificate",
}


class WinHttpError(OSError):
    """A request that did not complete. Never carries a header or the URL."""

    def __init__(self, code: int, step: str) -> None:
        reason = REASONS.get(code, "Windows error {}".format(code))
        OSError.__init__(self, "{} ({})".format(reason, step))
        self.code = code


_lib = None


def _winhttp():
    """The loaded DLL with its signatures declared, or None off Windows."""
    global _lib
    if _lib is not None:
        return _lib or None
    if sys.platform != "win32":
        _lib = False
        return None
    try:
        lib = ctypes.WinDLL("winhttp", use_last_error=True)
    except OSError:
        _lib = False
        return None
    from ctypes import wintypes as w
    H = ctypes.c_void_p
    sig = {
        "WinHttpOpen": (H, [w.LPCWSTR, w.DWORD, w.LPCWSTR, w.LPCWSTR,
                            w.DWORD]),
        "WinHttpSetTimeouts": (w.BOOL, [H, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int]),
        "WinHttpConnect": (H, [H, w.LPCWSTR, w.WORD, w.DWORD]),
        "WinHttpOpenRequest": (H, [H, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR,
                                   w.LPCWSTR, ctypes.c_void_p, w.DWORD]),
        "WinHttpSendRequest": (w.BOOL, [H, w.LPCWSTR, w.DWORD,
                                        ctypes.c_void_p, w.DWORD, w.DWORD,
                                        ctypes.c_size_t]),
        "WinHttpReceiveResponse": (w.BOOL, [H, ctypes.c_void_p]),
        "WinHttpQueryHeaders": (w.BOOL, [H, w.DWORD, w.LPCWSTR,
                                         ctypes.c_void_p,
                                         ctypes.POINTER(w.DWORD),
                                         ctypes.POINTER(w.DWORD)]),
        "WinHttpQueryDataAvailable": (w.BOOL, [H, ctypes.POINTER(w.DWORD)]),
        "WinHttpReadData": (w.BOOL, [H, ctypes.c_void_p, w.DWORD,
                                     ctypes.POINTER(w.DWORD)]),
        "WinHttpCloseHandle": (w.BOOL, [H]),
    }
    for name, (restype, argtypes) in sig.items():
        fn = getattr(lib, name)
        fn.restype = restype
        fn.argtypes = argtypes
    _lib = lib
    return lib


def available() -> bool:
    return _winhttp() is not None


def header_block(headers: dict) -> str:
    """Request headers as WinHTTP takes them: one CRLF-ended line each.

    The user agent is left out because it is set on the session, and a
    header name or value carrying a line break is refused outright rather
    than allowed to start a header of its own.
    """
    lines = []
    for name, value in headers.items():
        if name.lower() == "user-agent":
            continue
        name, value = str(name), str(value)
        if any(c in name + value for c in "\r\n"):
            raise ValueError("a header contains a line break")
        lines.append("{}: {}\r\n".format(name, value))
    return "".join(lines)


def parse_headers(raw: str) -> dict:
    """{lowercased name: value} from WinHTTP's CRLF header text."""
    out = {}
    for line in raw.split("\r\n")[1:]:          # the first is the status line
        name, sep, value = line.partition(":")
        if sep and name.strip():
            out[name.strip().lower()] = value.strip()
    return out


def request(url: str, method: str = "GET", headers: dict | None = None,
            body: bytes | None = None, timeout: float = 15.0,
            user_agent: str = "MO2-Plugin/1.0"):
    """(status, {lowercased header: value}, body bytes) for one HTTPS call.

    An HTTP error status is returned, not raised - it is an answer, and the
    client already knows what each one means. Anything that stops the
    answer arriving raises :class:`WinHttpError`.
    """
    lib = _winhttp()
    if lib is None:
        raise WinHttpError(0, "WinHTTP is not available")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("only https URLs are sent through WinHTTP")
    target = parts.path or "/"
    if parts.query:
        target += "?" + parts.query
    block = header_block(headers or {})
    data = body or b""
    ms = max(1, int(timeout * 1000))

    def fail(step):
        raise WinHttpError(ctypes.get_last_error(), step)

    handles = []
    try:
        session = lib.WinHttpOpen(user_agent, ACCESS_AUTOMATIC_PROXY,
                                  None, None, 0)
        if not session:
            session = lib.WinHttpOpen(user_agent, ACCESS_DEFAULT_PROXY,
                                      None, None, 0)
        if not session:
            fail("open")
        handles.append(session)
        lib.WinHttpSetTimeouts(session, ms, ms, ms, ms)
        connect = lib.WinHttpConnect(session, parts.hostname,
                                     parts.port or 443, 0)
        if not connect:
            fail("connect")
        handles.append(connect)
        req = lib.WinHttpOpenRequest(connect, method, target, None, None,
                                     None, FLAG_SECURE)
        if not req:
            fail("request")
        handles.append(req)
        buf = ctypes.create_string_buffer(data, len(data)) if data else None
        if not lib.WinHttpSendRequest(req, block or None, len(block),
                                      buf, len(data), len(data), 0):
            fail("send")
        if not lib.WinHttpReceiveResponse(req, None):
            fail("receive")

        status = ctypes.c_uint32(0)
        size = ctypes.c_uint32(4)
        if not lib.WinHttpQueryHeaders(
                req, QUERY_STATUS_CODE | QUERY_FLAG_NUMBER, None,
                ctypes.byref(status), ctypes.byref(size), None):
            fail("status")

        size = ctypes.c_uint32(0)
        lib.WinHttpQueryHeaders(req, QUERY_RAW_HEADERS_CRLF, None, None,
                                ctypes.byref(size), None)
        raw_headers = ""
        if ctypes.get_last_error() == ERROR_INSUFFICIENT_BUFFER and size.value:
            text = ctypes.create_unicode_buffer(size.value // 2 + 1)
            if lib.WinHttpQueryHeaders(req, QUERY_RAW_HEADERS_CRLF, None,
                                       text, ctypes.byref(size), None):
                raw_headers = text.value

        chunks = []
        while True:
            avail = ctypes.c_uint32(0)
            if not lib.WinHttpQueryDataAvailable(req, ctypes.byref(avail)):
                fail("read")
            if not avail.value:
                break
            chunk = ctypes.create_string_buffer(avail.value)
            got = ctypes.c_uint32(0)
            if not lib.WinHttpReadData(req, chunk, avail.value,
                                       ctypes.byref(got)):
                fail("read")
            if not got.value:
                break
            chunks.append(chunk.raw[:got.value])
        return status.value, parse_headers(raw_headers), b"".join(chunks)
    finally:
        for handle in reversed(handles):
            lib.WinHttpCloseHandle(handle)
