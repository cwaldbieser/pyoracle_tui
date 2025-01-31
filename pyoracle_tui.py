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
from textual.widgets import (Button, DataTable, Footer, Header, Select,
                             TabbedContent, TabPane, TextArea)

from sqltui.messages import MessageWidget
from sqltui.oracle import DatabaseError, exec_oracle_query


class SqlApp(App):

    BINDINGS = [
        ("?", "about()", "About"),
        ("f2", "reload_config()", "Reload config"),
        ("f3", "edit", "Edit query"),
        ("x", "export_to_visidata()", "Export to Spreadsheet"),
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
        tab_config = self.config["tab"]
        with TabbedContent(id="tabbed-content"):
            for tab_index, tab_config in tab_config.items():
                with TabPane(tab_index, id=f"pane-{tab_index}"):
                    yield ScrollableContainer(
                        TextArea.code_editor(
                            "",
                            id=f"query-text-{tab_index}",
                            theme="dracula",
                            language="sql",
                            tab_behavior="focus",
                        ),
                    )
                    with Horizontal(classes="button-bar"):
                        yield Button("Execute", id=f"query-execute-{tab_index}")
                    yield DataTable(id=f"data-table-{tab_index}", classes="data-table")

    def on_mount(self):
        self.screen.styles.border = ("heavy", "white")

    def on_button_pressed(self, event):
        if event.button.id.startswith("query-execute"):
            self.clear_table()
            self.toggle_button_state()
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
            fname = self.get_results_file()
            subprocess.call([spreadsheet, fname])
            logzero.loglevel(logzero.DEBUG)

    def action_edit(self):
        tab_index = self.get_tab_index()
        textarea = self.query_one(f"#query-text-{tab_index}")
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

    def get_results_file(self):
        tab_index = self.get_tab_index()
        results_file = self.config["tab"][tab_index].get(
            "results_file", f"/tmp/results.{tab_index}.csv"
        )
        return results_file

    @work(exclusive=True, thread=True)
    def execute_query(self):
        tab_index = self.get_tab_index()
        textarea = self.query_one(f"#query-text-{tab_index}")
        sql = textarea.text
        conn_selector = self.query_one("#connection-selection")
        if conn_selector.is_blank():
            self.call_from_thread(self.toggle_button_state)
            return
        conn_key = conn_selector.value
        connections = self.config["connections"]
        connection = connections[conn_key]
        host = connection["host"]
        database = connection["database"]
        user = connection["user"]
        passwd = connection["passwd"]
        try:
            exec_oracle_query(
                host=host,
                db_name=database,
                user=user,
                passwd=passwd,
                sql=sql,
                fname=self.get_results_file(),
            )
        except DatabaseError as ex:
            self.call_from_thread(self.show_message, f"Database error: {ex}")
            self.call_from_thread(self.toggle_button_state)
            return
        self.call_from_thread(self.populate_table)

        self.call_from_thread(self.toggle_button_state)

    def get_tab_index(self):
        tc = self.query_one("#tabbed-content")
        pane_id = tc.active
        pos = len("pane-")
        tab_index = pane_id[pos:]
        return tab_index

    def clear_table(self):
        tab_index = self.get_tab_index()
        table = self.query_one(f"#data-table-{tab_index}")
        table.clear(columns=True)

    def populate_table(self):
        tab_index = self.get_tab_index()
        table = self.query_one(f"#data-table-{tab_index}")
        results_file = self.get_results_file()
        with open(results_file, "r", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)
            table.add_columns(*headers)
            rows = [row for row in reader]
            table.add_rows(rows)

    def toggle_button_state(self):
        tab_index = self.get_tab_index()
        button = self.query_one(f"#query-execute-{tab_index}")
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
