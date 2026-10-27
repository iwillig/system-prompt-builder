# Research: Markdown prompt bodies as XML values

**Scope:** strict XML source files whose parsed element text contains Markdown.
This is an alternative to the pseudo-XML section design in
[the prompt section plan](../plans/sloppy-xml-prompt-sections.md), not the
selected authoring format.

## Conclusion

XML can hold Markdown as an element's **character data**. An XML parser would decode that data to a Python string; SPB could then pass the string to its existing Mustache renderer. This is a new prompt source format, not a way to make Markdown itself into XML markup. Use a text-only `<body>` element, define a small metadata grammar, and keep the rendered artifact as plain text. Do not implement the format until the source-format and whitespace rules are chosen. [XML character data][xml-data] [ElementTree elements][etree-elements] [SPB renderer][renderer]

For example, this is a *possible* source format, not a supported one:

```xml
<?xml version="1.0" encoding="utf-8"?>
<prompt>
  <name>Project assistant</name>
  <version>1.0.0</version>
  <body><![CDATA[# Project assistant

Work in {{harness.name}}.
Use <tool> only when needed; write A & B literally.
]]></body>
</prompt>
```

`<body>` contains one text value. After parsing, its value includes the heading, blank line, Mustache tag, `<tool>`, and `&`. CDATA is only an authoring convenience: escaped text such as `Use &lt;tool&gt; and A &amp; B` produces the same parsed characters. CDATA cannot contain `]]>` as one uninterrupted section or nest; escaping or splitting sections is necessary in that case. ElementTree gives the same element text for escaped text and CDATA. [XML character data][xml-data] [CDATA sections][xml-cdata] [ElementTree elements][etree-elements]

## Format constraints

- Put multiline Markdown in element text, not an attribute: XML normalizes whitespace in attribute values. XML also converts CRLF and lone CR to LF before parsing, so parsed text is not guaranteed to have the same bytes as its source. [Attribute normalization][xml-attrs] [Line endings][xml-lines]
- Treat whitespace inside `<body>` as content. Do not automatically indent, dedent, or strip it during parsing; leading newlines and spaces are visible to Markdown and Mustache. XML processors pass character data to applications, while `xml:space="preserve"` expresses author intent rather than supplying an automatic formatting rule. SPB currently calls `rstrip()` on the rendered body, which remains an independent output rule. [XML whitespace][xml-space] [SPB renderer][renderer]
- Reject child elements inside `<body>` if the contract is a single Markdown value. In ElementTree, `.text` stops at the first child and later text lives in `.tail`; `itertext()` concatenates mixed content but would silently discard the markup boundary. [ElementTree text and tail][etree-elements]
- Specify one root and exact child names/cardinality for `name`, `version`, `body`, `skills`, and variable declarations; reject missing, duplicate, and unknown fields. XML syntax validity alone does not enforce SPB's existing metadata rules. This is an SPB design requirement, inferred from the current front-matter and variable validation. [SPB parser][parser] [SPB variable rules][variables]
- Parse XML **before** Mustache interpolation when the output is plain text. Rendering the raw XML template first could insert `<` or `&` and make it invalid XML. After parsing, normal Mustache tags HTML-escape interpolated values, whereas triple tags leave them unescaped; keep or explicitly revise that existing rule. [Mustache interpolation specification][mustache] [SPB renderer][renderer]
- Decide how to handle DTDs, entities, and input size before accepting XML from other repositories. Python warns that XML input can exhaust resources; `defusedxml.ElementTree` provides parsing functions with `forbid_dtd=True`, `forbid_entities=True`, and `forbid_external=True`. Merely avoiding external network access does not make entity expansion harmless. [Python XML security][xml-security] [defusedxml documentation][defused]

## SPB integration work

1. Define the XML grammar and a parser that produces the same `(metadata, body)` values as today's Markdown/YAML parser. `render_prompt()` and `validate_project()` both call `_read_prompt()`. Keep skill resolution, required-variable checks, and semantic version checks downstream. [SPB parser][parser] [SPB renderer][renderer]
2. Decide whether `.spb/prompts/` accepts both `.md` and `.xml` or XML alone. Change the validation file discovery and CLI prompt examples accordingly. The CLI accepts an existing file path, but validation currently scans only `**/*.md`. [SPB validation][validation] [SPB CLI][cli]
3. Decide whether `spb init` generates XML and whether skill files stay Markdown. The starter source is currently YAML-front-matter Markdown; local skills are independent Markdown files. [SPB initialization][init] [SPB skill resolution][skills]
4. Keep artifact naming and provenance explicit. The CLI currently writes `build/<harness>/<source-stem>.md`, records the original source path and a SHA-256 of its decoded source text, and writes a digest of rendered content. An XML source can retain those behaviors, but escaping-only source edits would change the source hash without changing the rendered hash. [SPB CLI output][cli] [SPB manifest][manifest]
5. Test escaped text versus CDATA, `]]>`, Mustache sections and triple tags, newlines/indentation, empty and nested bodies, duplicate metadata, XML parse errors, hostile DTDs/entities, source hashes, validation discovery, and equivalent rendered Markdown. The first five text cases follow directly from XML and ElementTree behavior above; the rest exercise the current SPB contracts. [XML CDATA][xml-cdata] [XML whitespace][xml-space] [SPB parser][parser]

## Open decisions

- Is XML an additional source format or a replacement for `.md`? Does the starter project switch to XML?
- Should `<body>` preserve its parsed text exactly, or should authors opt into a specified indentation rule? The latter would change prompt whitespace.
- Should metadata remain in XML elements, or should XML wrap only the Markdown body while YAML stays the metadata source? The example above assumes one XML document owns both.

[xml-data]: https://www.w3.org/TR/2008/REC-xml-20081126/#syntax
[xml-cdata]: https://www.w3.org/TR/2008/REC-xml-20081126/#sec-cdata-sect
[xml-attrs]: https://www.w3.org/TR/2008/REC-xml-20081126/#sec-attribute-types
[xml-lines]: https://www.w3.org/TR/2008/REC-xml-20081126/#sec-line-ends
[xml-space]: https://www.w3.org/TR/2008/REC-xml-20081126/#sec-white-space
[etree-elements]: https://docs.python.org/3.14/library/xml.etree.elementtree.html#element-objects
[xml-security]: https://docs.python.org/3.14/library/xml.html#xml-security
[defused]: https://github.com/tiran/defusedxml/blob/main/README.md#defusedxml
[mustache]: https://github.com/mustache/spec/blob/master/specs/interpolation.yml
[renderer]: ../../src/spb/rendering.py
[parser]: ../../src/spb/rendering.py
[variables]: ../../src/spb/rendering.py
[validation]: ../../src/spb/rendering.py
[skills]: ../../src/spb/rendering.py
[init]: ../../src/spb/initialization.py
[cli]: ../../src/spb/cli.py
[manifest]: ../../src/spb/cli.py
