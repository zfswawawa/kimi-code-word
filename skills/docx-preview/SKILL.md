---
name: docx-preview
description: Generate and open offline HTML previews of DOCX files. Use when the user asks to preview, view, or inspect a Word document in Kimi Code Desktop's right panel.
---

# DOCX Preview

Use the `render_docx_preview` MCP tool with the complete DOCX path. The tool reads but never modifies the source document and creates a self-contained `<name>.preview.html` next to it by default.

In Kimi Code Desktop, open the returned `preview_path` with the built-in browser when that capability is available. Otherwise, give the user a clickable link to that path.

The viewer works offline and supports ordinary document styles, tables, images, headers, footers, and OMML equations through MathML. It is not the Microsoft Word layout engine; complex pagination, fields, floating objects, and uncommon Word features may render differently. Report visible rendering limitations instead of claiming pixel-perfect fidelity.
