"""HTTPS to Nexus that does not depend on the state of one PC's cert store.

MO2's Python verifies a server against whatever Windows happens to hold:
every certificate in the ROOT store and in the intermediate CA store. Two
things on a perfectly healthy PC break that for Nexus, whose chain ends at
Let's Encrypt's ISRG Root X1:

* Windows fetches root certificates on demand, the first time something
  that uses Windows' own TLS needs one. Python never asks, so a PC whose
  browser has not happened to need ISRG Root X1 does not have it.
* Many PCs still carry the old ISRG Root X1 cross-signed by DST Root CA X3
  in the CA store. That copy expired on 30 September 2024. When it is the
  only ISRG Root X1 OpenSSL can find, the chain ends there and the answer
  is "certificate has expired" - for a site whose own certificate is fine.

So ISRG Root X1 ships here, and is added to the system's roots rather than
replacing them. Verification stays on. Nothing is trusted that a current
browser does not trust, and if Nexus ever moves to another CA the system
store is still consulted exactly as before.

ISRG Root X1 is valid until 4 June 2035.
"""

from __future__ import annotations

try:
    import ssl
except ImportError:
    # MO2's Python without a working _ssl module - its _ssl.pyd or the
    # libssl-3-x64.dll beside ModOrganizer.exe missing, renamed or
    # shadowed by another copy. There is no HTTPS at all then, and this
    # module must not take the plugin down with it: it loads, and every
    # request fails with a message that says why.
    ssl = None

NO_SSL = ("MO2's Python could not load its SSL module, so it cannot make "
          "any HTTPS request. Check that libssl-3-x64.dll and "
          "libcrypto-3-x64.dll are next to ModOrganizer.exe, or reinstall "
          "MO2.")

ISRG_ROOT_X1_SHA256 = "96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6"

ISRG_ROOT_X1 = """-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
"""

_context = None


def available() -> bool:
    """Can this Python make HTTPS requests at all?"""
    return ssl is not None


def context():
    """The context every Nexus request uses: system roots + ISRG Root X1.

    None when there is no SSL support, which urllib accepts and then fails
    on cleanly at request time.
    """
    global _context
    if ssl is None:
        return None
    if _context is None:
        ctx = ssl.create_default_context()
        try:
            ctx.load_verify_locations(cadata=ISRG_ROOT_X1)
        except (ssl.SSLError, ValueError):
            pass                    # the system store alone, as before
        _context = ctx
    return _context


def certificate_problem(exc) -> str | None:
    """Why the certificate check failed, or None if that is not what failed.

    urllib wraps the TLS failure in a URLError; the reason inside is what
    says whether this was the certificate or the line.
    """
    if ssl is None:
        return None
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return reason.verify_message or str(reason)
    return None
