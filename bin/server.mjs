import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import JSZip from "jszip";
import { readFile, realpath, stat, writeFile, mkdtemp, rm } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import os from "node:os";
import path from "node:path";

const MAX_DOCX_BYTES = 100 * 1024 * 1024;
const templateUrl = new URL("../viewer/template.html", import.meta.url);
const jszipUrl = new URL("../viewer/vendor/jszip.min.js", import.meta.url);
const docxPreviewUrl = new URL("../viewer/vendor/docx-preview.min.js", import.meta.url);
const mathjaxUrl = new URL("../viewer/vendor/tex-svg.js", import.meta.url);
const preprocessorPath = fileURLToPath(new URL("./preprocess_docx.py", import.meta.url));
const execFileAsync = promisify(execFile);

function htmlEscape(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

async function normalizeDocx(sourcePath, originalBytes) {
  const zip = await JSZip.loadAsync(originalBytes);
  const documentXml = await zip.file("word/document.xml")?.async("string");
  const needsLegacyConversion = Object.keys(zip.files).some(name => name.toLowerCase().endsWith(".wmf"))
    || documentXml?.includes("<w:object");
  if (!needsLegacyConversion) return { bytes: originalBytes, converted: false };

  const tempDir = await mkdtemp(path.join(os.tmpdir(), "kimi-docx-preview-"));
  const normalizedPath = path.join(tempDir, "normalized.docx");
  try {
    await execFileAsync(process.env.PYTHON || "python", [preprocessorPath, sourcePath, normalizedPath], {
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024
    });
    return { bytes: await readFile(normalizedPath), converted: true };
  } catch (error) {
    const detail = error.stderr?.trim() || error.message;
    throw new Error(`OLE/WMF对象转换失败。预览此类公式需要Python和Pillow。${detail}`);
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

async function renderPreview({ docx_path, output_path }) {
  const requestedPath = path.resolve(docx_path);
  const sourcePath = await realpath(requestedPath);
  if (path.extname(sourcePath).toLowerCase() !== ".docx") {
    throw new Error("仅支持 .docx 文件，旧版 .doc 请先在Word中另存为 .docx");
  }
  const sourceStat = await stat(sourcePath);
  if (!sourceStat.isFile()) throw new Error("输入路径不是普通文件");
  if (sourceStat.size === 0) throw new Error("DOCX文件为空");
  if (sourceStat.size > MAX_DOCX_BYTES) throw new Error("DOCX超过100 MiB预览限制");

  const parsed = path.parse(sourcePath);
  const previewPath = output_path
    ? path.resolve(output_path)
    : path.join(parsed.dir, `${parsed.name}.preview.html`);
  if (!previewPath.toLowerCase().endsWith(".preview.html")) {
    throw new Error("输出路径必须以 .preview.html 结尾，以避免覆盖其他文件");
  }
  if (path.resolve(previewPath) === path.resolve(sourcePath)) {
    throw new Error("预览输出不能覆盖原DOCX");
  }

  const [template, jszip, docxPreview, mathjax, originalBytes] = await Promise.all([
    readFile(templateUrl, "utf8"),
    readFile(jszipUrl, "utf8"),
    readFile(docxPreviewUrl, "utf8"),
    readFile(mathjaxUrl, "utf8"),
    readFile(sourcePath)
  ]);
  const normalized = await normalizeDocx(sourcePath, originalBytes);
  const title = htmlEscape(parsed.base);
  const html = template
    .replace("/*__JSZIP__*/", () => jszip.replaceAll("//# sourceMappingURL=", "// disabled-source-map: "))
    .replace("/*__DOCX_PREVIEW__*/", () => docxPreview.replaceAll("//# sourceMappingURL=", "// disabled-source-map: "))
    .replace("/*__MATHJAX__*/", () => mathjax.replaceAll("//# sourceMappingURL=", "// disabled-source-map: "))
    .replaceAll("__DOCUMENT_TITLE__", () => title)
    .replace("__DOCX_BASE64__", () => normalized.bytes.toString("base64"));
  await writeFile(previewPath, html, "utf8");
  const previewStat = await stat(previewPath);
  return {
    source_path: sourcePath,
    preview_path: previewPath,
    docx_bytes: sourceStat.size,
    preview_bytes: previewStat.size,
    legacy_objects_converted: normalized.converted
  };
}

const server = new McpServer({ name: "kimi-docx-preview", version: "1.0.0" });
server.registerTool("render_docx_preview", {
  title: "生成离线DOCX预览",
  description: "将DOCX转换为自包含HTML，供Kimi Code右侧内置浏览器打开。原DOCX只读，预览完全离线。",
  inputSchema: {
    docx_path: z.string().min(1).describe("DOCX文件的完整路径"),
    output_path: z.string().optional().describe("可选输出路径，必须以.preview.html结尾")
  }
}, async args => {
  const result = await renderPreview(args);
  return { content: [{ type: "text", text: JSON.stringify(result) }] };
});

await server.connect(new StdioServerTransport());
