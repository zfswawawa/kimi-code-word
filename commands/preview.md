---
description: 在右侧内置浏览器中离线预览DOCX文档
---

使用 `render_docx_preview` 工具为以下DOCX文件生成离线预览：$ARGUMENTS

要求：
1. 不要修改原DOCX。路径包含空格时作为一个完整路径传给工具。
2. 在Kimi Code Desktop中，如果内置浏览器工具可用，直接用它打开工具返回的 `preview_path`，让预览显示在右侧面板。
3. 如果无法主动打开浏览器，返回指向 `preview_path` 的可点击链接，并提示用户点击链接预览。
4. 简短说明这是HTML近似渲染，复杂分页可能与Word略有差异。不要只复述工具输出而不打开预览。
