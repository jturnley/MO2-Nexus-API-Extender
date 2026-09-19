"""The MO2 tool plugin. Everything of substance is in the other modules.

This file is deliberately thin: it is the only part that cannot be tested
without MO2 running, so the less of it there is, the better.
"""

from __future__ import annotations

import mobase
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QMessageBox

from . import api, ui

NAME = "Nexus API Key Vault"
DEFAULT_DOMAIN = "skyrimspecialedition"


class NexusKeyVault(mobase.IPluginTool):
    def __init__(self) -> None:
        super().__init__()
        self._organizer = None

    def init(self, organizer: "mobase.IOrganizer") -> bool:
        self._organizer = organizer
        return True

    def name(self) -> str:
        return NAME

    def author(self) -> str:
        return "jturnley"

    def description(self) -> str:
        return self.tr(
            "Keeps one Nexus API key, encrypted for your Windows account, "
            "and lends it to other MO2 plugins so they can use the current "
            "Nexus API instead of what MO2's built-in v1 connection hands "
            "them.")

    def version(self) -> "mobase.VersionInfo":
        return mobase.VersionInfo(1, 1, 0, mobase.ReleaseType.FINAL)

    def settings(self) -> list:
        return [
            mobase.PluginSetting(
                "game_domain",
                self.tr("Nexus domain used when testing a key, e.g. "
                        "skyrimspecialedition."),
                DEFAULT_DOMAIN),
        ]

    def displayName(self) -> str:
        return self.tr("Nexus API Key")

    def tooltip(self) -> str:
        return self.tr("Store one Nexus key for every plugin to share")

    def icon(self):
        from PyQt6.QtGui import QIcon
        return QIcon()

    def setParentWidget(self, widget) -> None:
        self._parent = widget

    def display(self) -> None:
        organizer = self._organizer
        domain = str(organizer.pluginSetting(NAME, "game_domain")
                     or DEFAULT_DOMAIN).strip() or DEFAULT_DOMAIN
        try:
            dialog = ui.VaultDialog(organizer, domain,
                                    api.storage(organizer),
                                    getattr(self, "_parent", None))
        except Exception as exc:                  # a broken vault file
            QMessageBox.warning(
                getattr(self, "_parent", None), NAME,
                "The vault could not be opened: {}".format(exc))
            return
        dialog.exec()

    def tr(self, text: str) -> str:
        return QCoreApplication.translate("NexusKeyVault", text)


def createPlugin() -> "mobase.IPlugin":
    return NexusKeyVault()


def createPlugins() -> list:
    return [NexusKeyVault()]
