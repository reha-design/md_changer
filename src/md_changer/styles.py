"""Default CSS and HTML template definitions for Markdown to PDF conversion."""

PDF_CSS = """
@page {
  size: A4;
  margin: 18mm 16mm;
}

* {
  box-sizing: border-box;
}

body {
  color: #202124;
  font-family: "Malgun Gothic", "Apple SD Gothic Neo", "Segoe UI", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.65;
  margin: 0;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

h1, h2, h3, h4, h5, h6 {
  color: #111827;
  line-height: 1.28;
  margin: 1.2em 0 0.45em;
  page-break-after: avoid;
}

h1 {
  border-bottom: 1px solid #d8dee4;
  font-size: 28px;
  padding-bottom: 0.28em;
}

h2 {
  border-bottom: 1px solid #e5e7eb;
  font-size: 22px;
  padding-bottom: 0.22em;
}

h3 {
  font-size: 18px;
}

p, ul, ol, blockquote, pre, table {
  margin: 0.8em 0;
}

a {
  color: #0969da;
  text-decoration: none;
}

blockquote {
  border-left: 4px solid #d0d7de;
  color: #57606a;
  padding: 0.2em 1em;
}

code {
  background: #f6f8fa;
  border-radius: 4px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
  padding: 0.15em 0.35em;
}

pre {
  background: #f6f8fa;
  border: 1px solid #d8dee4;
  border-radius: 6px;
  line-height: 1.45;
  overflow-wrap: anywhere;
  padding: 12px;
  white-space: pre-wrap;
}

pre code {
  background: transparent;
  padding: 0;
}

table {
  border-collapse: collapse;
  display: table;
  page-break-inside: auto;
  width: 100%;
}

tr {
  page-break-inside: avoid;
}

th, td {
  border: 1px solid #d0d7de;
  padding: 7px 9px;
  vertical-align: top;
}

th {
  background: #f6f8fa;
  font-weight: 700;
}

img {
  display: block;
  height: auto;
  margin: 12px 0;
  max-width: 100%;
}

hr {
  border: 0;
  border-top: 1px solid #d8dee4;
  margin: 24px 0;
}
"""
