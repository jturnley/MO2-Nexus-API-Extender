"""The one window this plugin has.

Two halves: the key, and the record of who has asked for it.  The second
half is the reason this is a plugin rather than a text box - a credential
several plugins share should come with somewhere to see that sharing.

Nothing in here ever displays the key.  The field is masked, is never
pre-filled from storage, and the status line describes what is stored
instead of showing it.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog,
                             QDialogButtonBox, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout)

import time

from . import client as client_mod
from . import dpapi, migrate, vault as vault_mod
from .vault import masked

NAME = "Nexus API Key Vault"


class VaultDialog(QDialog):
    def __init__(self, organizer, domain: str, path: str, parent=None) -> None:
        super().__init__(parent)
        self._organizer = organizer
        self._domain = domain
        self._vault = vault_mod.Vault(path)
        self.setWindowTitle(NAME)
        self.resize(680, 620)

        layout = QVBoxLayout(self)
        self._status = QLabel("", self)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        layout.addWidget(self._key_box())
        layout.addWidget(self._callers_box(), 1)

        self._result = QLabel("", self)
        self._result.setWordWrap(True)
        layout.addWidget(self._result)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh()
        self._offer_migration()

    # ---- the key -------------------------------------------------------

    def _key_box(self) -> QGroupBox:
        box = QGroupBox("Your Nexus key", self)
        inner = QVBoxLayout(box)

        row = QHBoxLayout()
        row.addWidget(QLabel("Key:", box))
        self._field = QLineEdit(box)
        self._field.setEchoMode(QLineEdit.EchoMode.Password)
        self._field.setPlaceholderText("Paste a key here to store it")
        row.addWidget(self._field, 1)
        inner.addLayout(row)

        show = QCheckBox("Show what I am typing", box)
        show.toggled.connect(
            lambda on: self._field.setEchoMode(
                QLineEdit.EchoMode.Normal if on
                else QLineEdit.EchoMode.Password))
        inner.addWidget(show)

        row = QHBoxLayout()
        self._use_phrase = QCheckBox("Protect with a passphrase:", box)
        row.addWidget(self._use_phrase)
        self._phrase = QLineEdit(box)
        self._phrase.setEchoMode(QLineEdit.EchoMode.Password)
        self._phrase.setEnabled(False)
        row.addWidget(self._phrase, 1)
        self._use_phrase.toggled.connect(self._phrase.setEnabled)
        inner.addLayout(row)

        self._phrase_note = QLabel("", box)
        self._phrase_note.setWordWrap(True)
        inner.addWidget(self._phrase_note)

        row = QHBoxLayout()
        for label, slot in (("Save", self._save), ("Test", self._test),
                            ("Unlock", self._unlock),
                            ("Remove stored key", self._clear)):
            button = QPushButton(label, box)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        inner.addLayout(row)

        note = QLabel(
            "Get one from nexusmods.com -> your profile -> Site preferences "
            "-> API keys.\n\nIt is written to the vault's own file, not to "
            "ModOrganizer.ini, where plugin settings are kept in plain text.",
            box)
        note.setWordWrap(True)
        inner.addWidget(note)
        return box

    def _describe_protection(self) -> None:
        """Say what this platform can actually offer. Never more."""
        if self._vault.scheme == vault_mod.MACHINE:
            self._phrase_note.setText(
                "Running under Wine, where there is no OS secret to borrow. "
                "Without a passphrase the key is only obfuscated: tied to "
                "this machine and folder, so a copied file is useless - but "
                "readable in place by anything that can read this plugin's "
                "source. A passphrase is the only real protection here, and "
                "is asked for once per session.")
        elif self._vault.scheme == vault_mod.PASSPHRASE:
            self._phrase_note.setText(
                "The key is encrypted with your passphrase. Nothing on this "
                "disk can open it without that, and if you forget it the "
                "key is gone - generate a new one on Nexus.")
        else:
            self._phrase_note.setText(
                "Windows encrypts the key for this user account. A "
                "passphrase is optional here, and protects it even from "
                "someone who has your unlocked Windows account.")

    def _refresh(self) -> None:
        self._describe_protection()
        if self._vault.rewrapped:
            self._vault.rewrapped = False
            QMessageBox.warning(
                self, NAME,
                "Your key was stored by an earlier version through Wine's "
                "version of Windows encryption, which looks like encryption "
                "but is openable by anyone holding the file.\n\nIt has been "
                "re-stored under this version's scheme. If that file was "
                "ever backed up, shared or put in a support archive, treat "
                "the key as exposed and generate a new one on Nexus.")
        if not self._vault.has_key:
            self._status.setText(
                "No key stored. Plugins asking for one are being told there "
                "is none, and are expected to carry on without it.")
            return
        if self._vault.needs_passphrase:
            self._status.setText(
                "A key is stored, protected with a passphrase. Type it "
                "above and press Unlock to make it available to plugins "
                "for this session.")
            return
        try:
            self._status.setText("A key is stored ({}), {}.".format(
                masked(self._vault.read()), self._vault.protection()))
        except vault_mod.Locked as exc:
            self._status.setText(
                "There is a key here that cannot be opened on this system "
                "- most likely the file came from another machine, account "
                "or folder. Remove it and paste the key again. ({})"
                .format(exc))

    def _unlock(self) -> None:
        """Hand the vault a passphrase for a key already stored."""
        if not self._vault.needs_passphrase:
            QMessageBox.information(
                self, NAME, "Nothing is waiting on a passphrase.")
            return
        typed = self._phrase.text()
        if not typed:
            QMessageBox.information(
                self, NAME, "Type the passphrase first.")
            return
        self._vault.use_passphrase(typed)
        try:
            self._vault.read()
        except vault_mod.Locked as exc:
            self._vault.use_passphrase("")
            QMessageBox.warning(self, NAME, str(exc))
            return
        self._phrase.clear()
        self._refresh()

    def _save(self) -> None:
        typed = self._field.text().strip()
        if not typed:
            QMessageBox.information(
                self, NAME, "Nothing was typed, so nothing has changed.")
            return
        phrase = self._phrase.text() if self._use_phrase.isChecked() else ""
        if self._use_phrase.isChecked() and not phrase:
            QMessageBox.information(
                self, NAME,
                "Type a passphrase, or clear the checkbox to store without "
                "one.")
            return
        try:
            self._vault.store(typed, phrase)
        except (dpapi.Unavailable, ValueError) as exc:
            QMessageBox.warning(self, NAME, "Not stored: {}".format(exc))
            return
        self._field.clear()
        self._phrase.clear()
        self._refresh()
        QMessageBox.information(
            self, NAME, "Stored ({}), {}.".format(
                masked(typed), self._vault.protection()))

    def _test(self) -> None:
        typed = self._field.text().strip()
        try:
            key = typed or self._vault.read()
        except vault_mod.Locked as exc:
            self._result.setText(str(exc))
            return
        if not key:
            self._result.setText(
                "Nothing to test - the box is empty and no key is stored.")
            return
        self._result.setText("Checking...")
        self._result.repaint()
        probe = client_mod.NexusClient(key, user_agent="Nexus-Key-Vault/1.0")
        try:
            categories = probe.categories(self._domain)
        except client_mod.NexusError as exc:
            self._result.setText("That key did not work: {}".format(exc))
            return
        self._result.setText(
            "Works - Nexus returned {} categories for {} over v1. The "
            "same key reaches v3; v2's public queries need none."
            .format(len(categories), self._domain))

    def _clear(self) -> None:
        if not self._vault.has_key:
            return
        if QMessageBox.question(
                self, NAME,
                "Remove the stored key? Plugins asking for one will be told "
                "there is none.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self._vault.clear()
        self._refresh()

    # ---- who has asked -------------------------------------------------

    def _callers_box(self) -> QGroupBox:
        box = QGroupBox("Plugins that have asked for it", self)
        inner = QVBoxLayout(box)
        inner.addWidget(QLabel(
            "Every plugin runs inside MO2 as you do, so this list is a "
            "record rather than a lock: a plugin determined to read the key "
            "would not have to ask. Denying one stops any plugin using the "
            "published way in.", box))

        self._table = QTableWidget(0, 4, box)
        self._table.setHorizontalHeaderLabels(
            ["Plugin", "Times asked", "Last asked", "Allowed"])
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        inner.addWidget(self._table, 1)

        row = QHBoxLayout()
        for label, slot in (("Allow", lambda: self._set(True)),
                            ("Deny", lambda: self._set(False)),
                            ("Forget", self._forget)):
            button = QPushButton(label, box)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        inner.addLayout(row)

        self._fill_callers()
        return box

    def _fill_callers(self) -> None:
        names = sorted(self._vault.asked)
        self._table.setRowCount(len(names))
        for row, name in enumerate(names):
            entry = self._vault.asked[name]
            when = entry.get("last") or 0
            stamp = time.strftime("%Y-%m-%d %H:%M",
                                  time.localtime(when)) if when else "-"
            for column, text in enumerate((
                    name, str(entry.get("count") or 0), stamp,
                    "yes" if entry.get("allowed", True) else "NO")):
                self._table.setItem(row, column, QTableWidgetItem(text))
        if names:
            self._table.selectRow(0)

    def _selected(self) -> str:
        row = self._table.currentRow()
        item = self._table.item(row, 0) if row >= 0 else None
        return item.text() if item else ""

    def _set(self, allowed: bool) -> None:
        name = self._selected()
        if name:
            self._vault.set_allowed(name, allowed)
            self._fill_callers()

    def _forget(self) -> None:
        name = self._selected()
        if name:
            self._vault.forget(name)
            self._fill_callers()

    # ---- plain text left elsewhere -------------------------------------

    def _offer_migration(self) -> None:
        """Take over any key still sitting unencrypted in the MO2 ini."""
        stragglers = migrate.found(self._organizer)
        if not stragglers:
            return
        owners = ", ".join(owner for owner, _, _ in stragglers)
        if QMessageBox.question(
                self, NAME,
                "These plugins keep a Nexus key of their own in plain "
                "text in ModOrganizer.ini: {}.\n\nThe ini is not "
                "encrypted, so that copy can be read by anything that "
                "can read the file - including anyone you send an "
                "instance backup to.\n\nMove it into the vault and "
                "blank the plain-text copy?\n\nThis touches only "
                "those plugins' own settings. MO2's own Nexus login is "
                "stored separately and is not affected: downloads, "
                "endorsements and update checks keep working."
                .format(owners),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
        ) != QMessageBox.StandardButton.Yes:
            return
        moved, cleared = 0, 0
        for owner, setting, value in stragglers:
            if not self._vault.has_key:
                try:
                    self._vault.store(value)
                    moved += 1
                except (dpapi.Unavailable, ValueError):
                    continue
            if migrate.clear(self._organizer, owner, setting):
                cleared += 1
        self._refresh()
        QMessageBox.information(
            self, NAME,
            "{} key(s) taken into the vault, {} plain-text copy(ies) "
            "blanked.\n\nMO2 rewrites its ini on exit, so the old value may "
            "still be visible in the file until you close MO2.".format(
                moved, cleared))
