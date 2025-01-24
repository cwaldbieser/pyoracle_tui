#! /usr/bin/env python
import csv
import os
import pathlib
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager, redirect_stderr, redirect_stdout

import logzero
from logzero import logger
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, DataTable, Footer, Header, Select, TextArea

from sqltui.messages import MessageWidget
from sqltui.oracle import exec_oracle_query


class SqlApp(App):

    BINDINGS = [
        ("?", "about()", "About"),
        ("f2", "reload_config()", "Reload config"),
        ("f3", "edit", "Edit query"),
        ("X", "export_to_visidata()", "Export to VisiData"),
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
        yield Select(options, id="connection-selection")
        yield ScrollableContainer(
            TextArea.code_editor(
                "",
                id="query-text",
                theme="dracula",
                language="sql",
                tab_behavior="focus",
            ),
            id="query-text-area",
        )
        with Horizontal(id="query-buttonbar", classes="button-bar"):
            yield Button("Execute", id="query-execute")
        yield DataTable(id="data-table")

    def on_mount(self):
        self.screen.styles.border = ("heavy", "white")

    def on_button_pressed(self, event):
        if event.button.id == "query-execute":
            self.execute_query()

    def action_about(self):
        message = "Oracle SQL TUI by Carl Waldbieser 2025"
        self.show_message(message)

    def action_reload_config(self):
        app.config = load_config()
        self.show_message("Configuration reloaded.")

    def action_export_to_visidata(self):
        with self.app.suspend():
            logzero.loglevel(logzero.CRITICAL)
            spreadsheet = os.environ.get("SPREADSHEET", "visidata")
            fname = "/tmp/results.csv"
            subprocess.call([spreadsheet, fname])
            logzero.loglevel(logzero.DEBUG)

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

    @work(exclusive=True, thread=True)
    def execute_query(self):
        textarea = self.query_one("#query-text")
        sql = textarea.text
        conn_selector = self.query_one("#connection-selection")
        if conn_selector.is_blank():
            return
        conn_key = conn_selector.value
        connections = self.config["connections"]
        connection = connections[conn_key]
        host = connection["host"]
        database = connection["database"]
        user = connection["user"]
        passwd = connection["passwd"]
        self.call_from_thread(self.toggle_button_state)
        exec_oracle_query(
            host=host, db_name=database, user=user, passwd=passwd, sql=sql
        )
        self.call_from_thread(self.populate_table)

        self.call_from_thread(self.toggle_button_state)
        # self.call_from_thread(self.show_message, "Query complete.")

    def populate_table(self):
        table = self.query_one("#data-table")
        table.clear(columns=True)
        with open("/tmp/results.csv", "r", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)
            table.add_columns(*headers)
            rows = [row for row in reader]
            table.add_rows(rows)

    def toggle_button_state(self):
        button = self.query_one("#query-execute")
        button.disabled = not button.disabled

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
