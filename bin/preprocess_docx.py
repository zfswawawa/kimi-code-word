import posixpath
import re
import sys
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python_packages"))
from mtef_py.mtef import MTEF


def convert_wmf(data):
    image = Image.open(BytesIO(data))
    image.load(dpi=288)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def replace_object_image(match):
    xml = match.group(0)
    rel = re.search(r'<v:imagedata\b[^>]*\br:id="([^"]+)"', xml)
    width = re.search(r"width:([\d.]+)pt", xml)
    height = re.search(r"height:([\d.]+)pt", xml)
    if not rel or not width or not height:
        return ""
    rel_id = rel.group(1)
    cx = round(float(width.group(1)) * 12700)
    cy = round(float(height.group(1)) * 12700)
    doc_id = re.sub(r"\D", "", rel_id) or "1"
    return f'''<w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{doc_id}" name="Equation {doc_id}"/><wp:cNvGraphicFramePr/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="{rel_id}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>'''


def replace_object(match, ole_objects):
    xml = match.group(0)
    ole = re.search(r'<o:OLEObject\b[^>]*\br:id="([^"]+)"', xml)
    if ole and ole.group(1) in ole_objects:
        try:
            equation, error = MTEF.OpenBytes(ole_objects[ole.group(1)])
            if error is None:
                latex = equation.Translate().strip()
                latex = latex.replace(r"{\text{[U+ef07]}}", r"\cdot ")
                if latex:
                    return f'<w:t xml:space="preserve">{escape(latex)}</w:t>'
        except Exception:
            pass
    return replace_object_image(match)


def load_ole_objects(src):
    objects = {}
    for info in src.infolist():
        if not info.filename.endswith(".rels"):
            continue
        text = src.read(info.filename).decode("utf-8")
        for tag in re.findall(r"<Relationship\b[^>]*>", text):
            rel_id = re.search(r'\bId="([^"]+)"', tag)
            target = re.search(r'\bTarget="([^"]+)"', tag)
            if rel_id and target and "oleObject" in target.group(1):
                name = posixpath.normpath(posixpath.join("word", target.group(1)))
                if name in src.namelist():
                    objects[rel_id.group(1)] = src.read(name)
    return objects


def convert_xml(name, data, ole_objects):
    if not (name.endswith(".rels") or name.endswith(".xml")):
        return data
    text = data.decode("utf-8")
    if name.endswith(".rels"):
        return re.sub(r"(?i)\.wmf\b", ".png", text).encode("utf-8")
    if name.startswith("word/") and name.endswith(".xml") and "<w:object" in text:
        text = re.sub(r"<w:object\b[^>]*>.*?</w:object>", lambda match: replace_object(match, ole_objects), text, flags=re.DOTALL)
        return text.encode("utf-8")
    if name == "[Content_Types].xml" and 'Extension="png"' not in text:
        text = text.replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
        return text.encode("utf-8")
    return data


def main():
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    with ZipFile(source, "r") as src:
        ole_objects = load_ole_objects(src)
        with ZipFile(target, "w", ZIP_DEFLATED) as dst:
            for info in src.infolist():
                name = info.filename
                data = src.read(name)
                if name.lower().endswith(".wmf"):
                    name = name[:-4] + ".png"
                    data = convert_wmf(data)
                else:
                    data = convert_xml(info.filename, data, ole_objects)
                dst.writestr(name, data)


if __name__ == "__main__":
    main()
