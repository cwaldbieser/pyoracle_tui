
PyOracle TUI
============

A terminal user interface for eexecuting SQL queries against an Oracle database.

Requirements:

- Python 3.12+
- Oracle Instant Client

Setup when using `pipenv`
-------------------------

Create a `.env` file that appends the Oracle instant client location to LD_LIBRARY_PATH.
e.g.

.. code-block:: sh

   LD_LIBRARY_PATH=/home/myuser/.local/opt/oracle/instantclient_21.1:"$LD_LIBRARY_PATH"

Confguring Tabs
---------------

In `~/.config/pyoracle_tui/pyoracle_tui.toml`.
Basic structure is:

.. code-block:: toml

    [tab.1]
    sql_file = "/tmp/pyoracle.01.sql"
    results_file = "/tmp/pyoracle-results.01.csv"

    [tab.2]
    sql_file = "/tmp/pyoracle.02.sql"
    results_file = "/tmp/pyoracle-results.02.csv"


Configuring connections
-----------------------

In `~/.config/pyoracle_tui/pyoracle_tui.toml`.
Basic structure is:

.. code-block:: toml

    [connections.conn01]
    desc = "XYZZY Connection"
    host = "xyzzy.example.org"
    database = "magic"
    user = "wizard"
    passwd = "pr3$to!"

    [connections.conn02]
    desc = "FROTZ Connection"
    host = "zork.examle.com"
    database = "gue"
    user = "adventurer"
    passwd = "bra$$lantern"

Environment Variables
---------------------

- EDITOR - external editor to use for composing queries.
- SPREADSHEET - external spreadsheet application to use for exporting data.

Example Commandline
-------------------

.. code-block:: shell

   $ pipenv run textual run ./pyoracle_tui.py

