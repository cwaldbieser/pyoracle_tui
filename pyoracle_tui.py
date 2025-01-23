#! /usr/bin/env python
import os
import pathlib
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager, redirect_stderr, redirect_stdout

import logzero
from logzero import logger
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, Footer, Header, TextArea, Select

from sqltui.messages import MessageWidget


class SqlApp(App):

    BINDINGS = [
        ("?", "about()", "About"),
        ("f2", "reload_config()", "Reload config"),
        ("f3", "edit", "Edit query"),
    ]
    CSS_PATH = "app.css"
    TITLE = "Oracle SQL TUI"
    config = None

    def compose(self) -> ComposeResult:
        mw = MessageWidget()
        mw.add_class("message")
        mw.add_class("hidden")
        yield mw
        yield Header("Oracle SQL TUI")
        yield Footer()
        connections = self.config["connections"]
        options = []
        for conn_key, connection in connections.items():
            options.append((connection["desc"], conn_key))
        yield Select(options)
        yield ScrollableContainer(
            TextArea.code_editor("", id="query-text", theme="dracula", language="sql"),
            id="query-text-area",
        )
        with Horizontal(id="query-buttonbar"):
            yield Button("Execute", id="query-execute")

    def on_mount(self):
        self.screen.styles.border = ("heavy", "white")

    def action_about(self):
        message = "Oracle SQL TUI by Carl Waldbieser 2025"
        self.show_message(message)

    def action_reload_config(self):
        app.config = load_config()
        self.show_message("Configuration reloaded.")

    def action_edit(self):
        textarea = self.query_one("#query-text")
        EDITOR = os.environ.get("EDITOR", "vim")
        logger.debug(f"EDITOR is: {EDITOR}")
        with tempfile.NamedTemporaryFile("r+", suffix=".sql", delete=False) as tf:
            tf.write(textarea.text)
            tfname = tf.name
        try:
            with self.app.suspend():
                logzero.loglevel(logzero.CRITICAL)
                subprocess.call([EDITOR, tfname])
            logzero.loglevel(logzero.DEBUG)
            with open(tfname, "r") as tf:
                textarea.text = tf.read()
        finally:
            os.unlink(tfname)

    def show_message(self, message, seconds=5.0):
        """
        Show a one line message floating over the middle of the application for
        `seconds` seconds.
        """
        mw = self.query_one(MessageWidget)
        mw.message = message
        mw.remove_class("hidden")

        def hideit():
            mw.add_class("hidden")

        self.set_interval(seconds, hideit, repeat=1)

    @contextmanager
    def suspend(self):
        driver = self._driver

        if driver is not None:
            driver.stop_application_mode()
            with redirect_stdout(sys.__stdout__), redirect_stderr(sys.__stderr__):
                yield
            driver.start_application_mode()
            self.refresh()


def load_config():
    """
    Load configuration.
    """
    home = os.environ["HOME"]
    p = pathlib.Path(f"{home}/.config/pyoracle_tui/pyoracle_tui.toml")
    with open(p, "rb") as f:
        config = tomllib.load(f)
    return config


if __name__ == "__main__":
    app = SqlApp()
    app.config = load_config()
    app.run()
