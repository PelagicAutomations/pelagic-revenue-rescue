from html.parser import HTMLParser
from pathlib import Path

class InputNameParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.input_names: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "input":
            name = dict(attrs).get("name")
            if name:
                self.input_names.add(name)


def test_onboarding_form_submits_admin_token():
    parser = InputNameParser()
    template = Path("app/templates/onboarding.html").read_text()
    parser.feed(template)

    assert "token" in parser.input_names
