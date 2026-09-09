import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import Error, TimeoutError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from md_changer import core


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.scripts = []
        self.sources = []
        self.script_text = []
        self.in_script = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.in_script = True
            self.scripts.append(attrs)
        if "data-md-changer-source" in attrs:
            self.sources.append(attrs["data-md-changer-source"])

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.script_text.append(data)


def file_uri_path(uri):
    path = unquote(urlparse(uri).path)
    if sys.platform == "win32":
        path = path.lstrip("/")
    return Path(path)


class FakePage:
    def __init__(self, *, failure=None, state=None):
        self.failure = failure
        self.state = state or {"status": "success", "error": None}
        self.events = []
        self.closed = False
        self.html_path = None

    def goto(self, uri, **kwargs):
        self.html_path = file_uri_path(uri)
        self.document = Document(self.html_path.read_text(encoding="utf-8"))
        self.events.append("goto")
        if self.failure == "goto":
            raise Error("navigation failed")

    def wait_for_function(self, expression, *, timeout):
        self.events.append(("wait", expression, timeout))
        if self.failure == "timeout":
            raise TimeoutError("test timeout")

    def evaluate(self, expression):
        if "document.fonts.ready" in expression:
            self.events.append("fonts")
            return None
        self.events.append("state")
        return self.state

    def pdf(self, *, path, **kwargs):
        self.events.append("pdf")
        if self.failure == "pdf":
            raise Error("PDF failed")
        Path(path).write_bytes(b"pdf")

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, pages=None):
        self.pages = iter(pages or [FakePage()])
        self.options = []

    def new_page(self, **options):
        self.options.append(options)
        return next(self.pages)


class MermaidHtmlTests(unittest.TestCase):
    def test_only_mermaid_fences_transform_and_preserve_diagram_text(self):
        diagram = 'graph TD\n A["<img src=x onerror=alert(1)>"] --> B\n'
        result = core.build_html(
            "```mermaid\n" + diagram + "```\n\n```python\nprint('<tag>')\n```",
            Path("notes.md"),
        )
        document = Document(result)
        self.assertEqual(document.sources, [diagram])
        self.assertIn('<pre><code class="language-python">print(\'&lt;tag&gt;\')\n</code></pre>', result)
        self.assertNotIn("<img src=x", result)

    def test_ordinary_and_similarly_named_code_has_no_runtime(self):
        result = core.build_html("```mermaid-extra\ngraph TD\n```\n\n    mermaid\n", Path("x.md"))
        self.assertEqual(Document(result).scripts, [])
        self.assertIn('class="language-mermaid-extra"', result)
        self.assertIn("<pre><code>mermaid\n</code></pre>", result)

    def test_mermaid_injects_existing_local_runtime(self):
        document = Document(core.build_html("```mermaid\ngraph TD; A-->B\n```", Path("x.md")))
        external = [script["src"] for script in document.scripts if "src" in script]
        self.assertEqual(len(external), 1)
        self.assertEqual(urlparse(external[0]).scheme, "file")
        self.assertTrue(file_uri_path(external[0]).is_file())

    def run_bootstrap(self, *, outcome="success", theme="modern"):
        diagram = 'graph TD\n A["<b>unsafe</b>"]-->B\n'
        document = Document(core.build_html("```mermaid\n" + diagram + "```", Path("x.md"), theme=theme))
        self.assertTrue(document.script_text, "Mermaid initialization is missing")
        harness = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const captures = {};
global.window = global;
const node = {
  dataset: { mdChangerSource: input.source },
  set textContent(value) { captures.text = value; },
  set innerHTML(value) { throw new Error('raw source must never use innerHTML'); },
  removeAttribute() {}
};
global.document = { querySelectorAll: () => [node], fonts: {ready: Promise.resolve()} };
global.mermaid = {
  initialize(config) { captures.config = config; },
  async run(options) {
    captures.options = options;
    if (input.outcome === 'error') throw new Error('Parse error on line 2');
  }
};
eval(input.script);
setImmediate(() => process.stdout.write(JSON.stringify({captures, state: window.__mdChangerMermaid})));
"""
        execution = subprocess.run(
            ["node", "-e", harness], input=json.dumps({"script": "\n".join(document.script_text), "source": diagram, "outcome": outcome}),
            capture_output=True, text=True, check=True,
        )
        return json.loads(execution.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to execute the bootstrap behavior test")
    def test_bootstrap_passes_text_content_and_strict_theme_config_then_completes(self):
        result = self.run_bootstrap()
        self.assertEqual(result["captures"]["text"], 'graph TD\n A["<b>unsafe</b>"]-->B\n')
        config = result["captures"]["config"]
        self.assertFalse(config["startOnLoad"])
        self.assertEqual(config["securityLevel"], "strict")
        self.assertTrue(config["suppressErrorRendering"])
        self.assertEqual(config["theme"], "base")
        self.assertEqual(config["themeVariables"]["primaryColor"], "#dbeafe")
        self.assertEqual(result["state"]["status"], "success")

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to execute the bootstrap behavior test")
    def test_bootstrap_reports_rejected_run_without_unhandled_rejection(self):
        result = self.run_bootstrap(outcome="error")
        self.assertEqual(result["state"]["status"], "error")
        self.assertIn("Parse error", result["state"]["error"])


class MermaidConversionTests(unittest.TestCase):
    def convert(self, page, text="```mermaid\ngraph TD; A-->B\n```"):
        source = self.directory / "notes.md"
        source.write_text(text, encoding="utf-8")
        return core.convert_markdown_to_pdf(source, self.directory, FakeBrowser([page]))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_waits_for_mermaid_and_fonts_before_pdf_and_cleans_up(self):
        page = FakePage()
        output = self.convert(page)
        self.assertTrue(output.is_file())
        waits = [event for event in page.events if isinstance(event, tuple)]
        self.assertEqual(len(waits), 1)
        self.assertLessEqual(waits[0][2], 30000)
        self.assertIn("__mdChangerMermaid", waits[0][1])
        self.assertLess(page.events.index("state"), page.events.index("pdf"))
        self.assertLess(page.events.index("fonts"), page.events.index("pdf"))
        self.assertTrue(page.closed)
        self.assertFalse(page.html_path.exists())

    def test_plain_markdown_waits_for_fonts_without_mermaid_completion_wait(self):
        page = FakePage()
        self.convert(page, "# Plain")
        self.assertEqual(page.events, ["goto", "fonts", "pdf"])

    def test_conversion_disables_render_time_network_access(self):
        source = self.directory / "offline.md"
        source.write_text("```mermaid\ngraph TD; A-->B\n```", encoding="utf-8")
        browser = FakeBrowser()
        core.convert_markdown_to_pdf(source, self.directory, browser)
        self.assertEqual(browser.options, [{"offline": True}])

    def test_mermaid_attribute_in_ordinary_html_does_not_trigger_render_wait(self):
        page = FakePage()
        self.convert(page, '<div data-md-changer-source="example">Ordinary HTML</div>')
        self.assertEqual(page.events, ["goto", "fonts", "pdf"])

    def test_parse_failure_does_not_print_and_cleans_up(self):
        page = FakePage(state={"status": "error", "error": "Parse error on line 2"})
        with self.assertRaisesRegex(RuntimeError, "Mermaid.*Parse error"):
            self.convert(page)
        self.assertNotIn("pdf", page.events)
        self.assertTrue(page.closed)
        self.assertFalse(page.html_path.exists())

    def test_timeout_has_clear_error_and_cleans_up(self):
        page = FakePage(failure="timeout")
        with self.assertRaisesRegex(RuntimeError, "Mermaid.*30"):
            self.convert(page)
        self.assertNotIn("pdf", page.events)
        self.assertTrue(page.closed)
        self.assertFalse(page.html_path.exists())

    def test_navigation_and_pdf_failure_close_page_and_delete_html(self):
        for failure in ("goto", "pdf"):
            with self.subTest(failure=failure):
                page = FakePage(failure=failure)
                with self.assertRaises(Error):
                    self.convert(page)
                self.assertTrue(page.closed)
                self.assertFalse(page.html_path.exists())


if __name__ == "__main__":
    unittest.main()
