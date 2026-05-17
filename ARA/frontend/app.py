from io import BytesIO
import html
import re
import textwrap
import zipfile

import requests
# pyrefly: ignore [missing-import]
import streamlit as st


BACKEND_URL = "http://localhost:8002/research"


def safe_filename(value):
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return name.strip("_") or "research"


def markdown_to_lines(markdown_text):
    lines = []
    for raw_line in markdown_text.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append({"text": "", "bold": False})
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            lines.append({"text": strip_markdown(heading.group(2)), "bold": True})
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        if bullet:
            lines.append({"text": f"- {strip_markdown(bullet.group(1))}", "bold": False})
            continue

        numbered = re.match(r"^(\d+)\.\s+(.+)$", line)
        if numbered:
            lines.append(
                {"text": f"{numbered.group(1)}. {strip_markdown(numbered.group(2))}", "bold": False}
            )
            continue

        lines.append({"text": strip_markdown(line), "bold": is_bold_only(line)})
    return lines


def strip_markdown(value):
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[*_`>#]", "", value)
    return value.strip()


def is_bold_only(value):
    text = value.strip()
    return bool(re.fullmatch(r"(\*\*|__)(.+)(\*\*|__)", text))


def pdf_escape(value):
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(markdown_text):
    pages = []
    content = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
    y = 780

    def finish_page():
        content.append("ET")
        pages.append("\n".join(content).encode("latin-1", errors="replace"))

    for item in markdown_to_lines(markdown_text):
        if item["text"]:
            font = "/F2 13 Tf" if item["bold"] else "/F1 11 Tf"
            wrap_width = 82 if item["bold"] else 95
            for wrapped in textwrap.wrap(item["text"], width=wrap_width) or [""]:
                if y < 60:
                    finish_page()
                    content = ["BT", font, "14 TL", "50 780 Td"]
                    y = 780
                content.append(font)
                content.append(f"({pdf_escape(wrapped)}) Tj")
                content.append("T*")
                y -= 14
            if item["bold"]:
                content.append("T*")
                y -= 14
        else:
            content.append("T*")
            y -= 14

    finish_page()

    page_count = len(pages)
    page_object_ids = [3 + index for index in range(page_count)]
    font_regular_id = 3 + page_count
    font_bold_id = 4 + page_count
    content_object_ids = [5 + page_count + index for index in range(page_count)]
    page_refs = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{page_refs}] /Count {page_count} >>".encode("ascii"),
    ]
    for page_id, content_id in zip(page_object_ids, content_object_ids):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>".encode("ascii")
        )
    objects.extend(
        [
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
    )
    for stream in pages:
        objects.append(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )

    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{index} 0 obj\n".encode("ascii"))
        pdf.write(obj)
        pdf.write(b"\nendobj\n")
    xref_start = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode(
            "ascii"
        )
    )
    return pdf.getvalue()


def document_xml(markdown_text):
    paragraphs = []
    for item in markdown_to_lines(markdown_text):
        text = html.escape(item["text"])
        bold = "<w:b/>" if item["bold"] else ""
        paragraphs.append(
            "<w:p><w:r><w:rPr>"
            f"{bold}"
            "</w:rPr><w:t xml:space=\"preserve\">"
            f"{text}"
            "</w:t></w:r></w:p>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"{''.join(paragraphs)}"
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" "
        "w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr>"
        "</w:body></w:document>"
    )


def build_docx(markdown_text):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        docx.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>',
        )
        docx.writestr("word/document.xml", document_xml(markdown_text))
    return buffer.getvalue()


st.set_page_config(page_title="AI Research Assistant", page_icon="🔬", layout="wide")

st.markdown(
    """
<style>
    body, .stApp, .main-title, .report-container, .report-container * {
        color: #ffffff;
    }
    .main-title {
        font-family: 'Inter', sans-serif;
        text-align: center;
        padding: 20px;
        font-weight: 700;
    }
    .stButton>button, .stDownloadButton>button {
        width: 100%;
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #000000;
        border-radius: 6px;
        min-height: 44px;
        font-size: 16px;
        font-weight: 700;
    }
    .report-container {
        background-color: #ffffff;
        padding: 20px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<h1 class='main-title'>Autonomous AI Research Assistant Team</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; font-size: 18px; color: #ffffff;'>"
    "Enter your research topic, and our multi-agent team will gather, analyze, and synthesize a comprehensive report with citations."
    "</p>",
    unsafe_allow_html=True,
)

st.divider()

if "report" not in st.session_state:
    st.session_state.report = ""
if "query" not in st.session_state:
    st.session_state.query = "Transformer Architectures in NLP"

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    query = st.text_input("Research Topic / Query", st.session_state.query)

    if st.button("Start Research"):
        if query:
            with st.spinner(
                "The AI team is working... Coordinating -> Searching -> Analyzing -> Synthesizing -> Citing. This may take a minute."
            ):
                try:
                    response = requests.post(BACKEND_URL, json={"query": query}, timeout=180)
                    if response.status_code == 200:
                        st.session_state.query = query
                        st.session_state.report = response.json().get("final_report", "")
                        st.markdown("**Research Complete!**")
                    else:
                        st.markdown(f"**Error from backend:** {response.text}")
                except Exception as e:
                    st.markdown(f"**Failed to connect to backend:** {e}. Is the FastAPI server running?")
        else:
            st.markdown("**Please enter a research topic first.**")

if st.session_state.report:
    report = st.session_state.report
    filename = safe_filename(st.session_state.query)

    st.markdown("### Final Research Report")
    st.markdown("<div class='report-container'>", unsafe_allow_html=True)
    st.markdown(report)
    st.markdown("</div>", unsafe_allow_html=True)

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button(
            label="Download Markdown",
            data=report,
            file_name=f"{filename}_report.md",
            mime="text/markdown",
        )
    with dl2:
        st.download_button(
            label="Download PDF",
            data=build_pdf(report),
            file_name=f"{filename}_report.pdf",
            mime="application/pdf",
        )
    with dl3:
        st.download_button(
            label="Download Word",
            data=build_docx(report),
            file_name=f"{filename}_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
