from textual.reactive import reactive
from textual.widgets import Static
from textual.css.query import QueryError


class MessageWidget(Static):

    message = reactive("Application started.")

    def watch_message(self):
        try:
            mb = self.query_one(MessageBox)
        except QueryError:
            return
        mb.update(self.message)

    def compose(self):
        yield MessageBox(self.message)


class MessageBox(Static):
    pass
