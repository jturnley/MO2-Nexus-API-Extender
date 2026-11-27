"""Translation, without making the API depend on Qt.

Most of this package must import with no Qt at all: other plugins call
:mod:`api` from worker threads, and the tests run with no MO2.  So nothing
here imports PyQt6.  :func:`translate` uses Qt only when something else has
already loaded it, which inside MO2 is always, and otherwise hands back the
English text - exactly what the code returned before it was translatable.

Strings are written as ``translate("Context", "Full sentence {}.")`` and
formatted *after* translation, never assembled from fragments: word order
is not the same in every language, and a translator can only move a ``{}``
they can see.  Counts use Qt's ``%n`` with ``n=`` so languages with more
than one plural form (Russian has three) can say them properly.

Tables built at import time, before a translator exists, mark their
strings with :func:`QT_TRANSLATE_NOOP` so ``pylupdate6`` still finds them,
and translate at the point of use.

    pylupdate6 nexus_key_vault -ts nexus_key_vault/translations/nexus_key_vault_ru.ts
"""

from __future__ import annotations

import os
import sys

PREFIX = "nexus_key_vault_"
FOLDER = "translations"

_installed = []         # held so Qt's translators are not garbage collected


def QT_TRANSLATE_NOOP(context: str, text: str) -> str:
    """Mark a string for extraction without translating it yet."""
    return text


def translate(context: str, text: str, disambiguation: str | None = None,
              n: int = -1) -> str:
    """``text`` in MO2's language, or as given when Qt is not loaded."""
    core = sys.modules.get("PyQt6.QtCore")
    if core is not None:
        try:
            return core.QCoreApplication.translate(
                context, text, disambiguation, n)
        except Exception:
            pass
    if n >= 0:
        text = text.replace("%n", str(n))
    return text


# ---- loading a translation (Qt side only) ------------------------------


def _ini_language(path: str) -> str:
    """``language=`` from the [Settings] section of a ModOrganizer.ini.

    Read by hand rather than with configparser: MO2's ini is Qt's format,
    with keys and values configparser does not always accept, and one bad
    line elsewhere should not cost the user their language.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            section = ""
            for line in fh:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip().lower()
                elif section == "settings" and "=" in line:
                    name, _, value = line.partition("=")
                    if name.strip().lower() == "language":
                        return value.strip().strip('"')
    except OSError:
        pass
    return ""


def mo2_language(organizer=None) -> str:
    """The language MO2 is showing, e.g. ``ru`` or ``pt_BR``; "" if unknown.

    MO2 does not offer this through ``mobase``, so it comes from the
    instance's ModOrganizer.ini: next to the instance's base directory,
    or beside ModOrganizer.exe for a portable install.
    """
    places = []
    try:
        if organizer is not None:
            places.append(organizer.basePath())
    except Exception:
        pass
    try:
        from PyQt6.QtCore import QCoreApplication
        places.append(QCoreApplication.applicationDirPath())
    except Exception:
        pass
    for folder in places:
        if folder:
            found = _ini_language(os.path.join(str(folder), "ModOrganizer.ini"))
            if found:
                return found
    return ""


def install(organizer=None, folder: str | None = None) -> str:
    """Load this plugin's translation for MO2's language, once per run.

    Looks in the plugin's own ``translations`` folder, so a translated
    release is still one folder to copy.  MO2 itself also loads
    ``translations/nexus_key_vault_<lang>.qm`` from its own folder; having
    both installed is harmless.  Returns the file loaded, or "".
    """
    if _installed:
        return _installed[0][1]
    try:
        from PyQt6.QtCore import QCoreApplication, QLocale, QTranslator
    except Exception:
        return ""
    folder = folder or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    FOLDER)
    if not os.path.isdir(folder):
        return ""
    language = mo2_language(organizer) or QLocale().name()
    if not language or language.lower().startswith("en"):
        return ""
    translator = QTranslator()
    # load() falls back on its own: pt_BR, then pt.
    if not translator.load(PREFIX + language, folder):
        return ""
    app = QCoreApplication.instance()
    if app is None or not app.installTranslator(translator):
        return ""
    loaded = translator.filePath() or os.path.join(folder, PREFIX + language)
    _installed.append((translator, loaded))
    return loaded
