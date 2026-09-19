"""Getting keys out of the places that keep them in plain text.

MO2 plugin settings are stored in ``ModOrganizer.ini``, unencrypted.  That
is fine for a window size and wrong for a credential: the file gets copied
into instance backups, pasted into support threads, and synced to wherever
the profile folder is being backed up to.

So the vault sweeps the settings it knows about, offers to take the key
over, and blanks the original.  Blanking matters more than importing - a
key living in two places is worse than one, and the copy left behind is
the readable one.
"""

from __future__ import annotations

# (plugin name, setting name) pairs known to have held a Nexus key.
#
# These are *plugin* settings - the [Plugins] section of the ini, written by
# a plugin for its own use - and `pluginSetting` cannot reach anything else.
# MO2's own Nexus credential is not here and is not touched: it lives in
# MO2's own settings, is managed by the Nexus login in MO2's settings
# dialog, and clearing it would break downloads, endorsements and update
# checks. Nothing may be added to this list that another program reads.
KNOWN = (
    ("MO2 DAG Sorter", "nexus_api_key"),
)


def found(organizer, known=KNOWN) -> list[tuple[str, str, str]]:
    """Plain-text keys sitting in other plugins' settings, if any."""
    out: list[tuple[str, str, str]] = []
    for owner, setting in known:
        try:
            value = str(organizer.pluginSetting(owner, setting) or "").strip()
        except Exception:
            # That plugin is not installed, or never had the setting. What
            # MO2 does here differs between builds, hence the broad catch.
            continue
        if value:
            out.append((owner, setting, value))
    return out


def clear(organizer, owner: str, setting: str) -> bool:
    """Blank one plain-text setting. True if it is now empty."""
    try:
        organizer.setPluginSetting(owner, setting, "")
        return True
    except Exception:
        return False
