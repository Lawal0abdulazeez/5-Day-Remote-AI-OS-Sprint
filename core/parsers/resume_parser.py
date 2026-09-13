import os
import re
from typing import Tuple
import pypdf
import docx


class DocumentParsingError(Exception):
    pass


class ResumeParser:
    """
    Layout-aware multi-format document parser extracting clean text
    from PDF, DOCX, and plain text files with error fallbacks.
    """

    @classmethod
    def parse_file(cls, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise DocumentParsingError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            return cls._parse_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return cls._parse_docx(file_path)
        elif ext in [".txt", ".md", ".rtf"]:
            return cls._parse_text(file_path)
        else:
            raise DocumentParsingError(f"Unsupported file format '{ext}'. Supported: .pdf, .docx, .txt, .md")

    @classmethod
    def _parse_pdf(cls, file_path: str) -> str:
        try:
            reader = pypdf.PdfReader(file_path)
            if len(reader.pages) == 0:
                raise DocumentParsingError("PDF file is empty (0 pages).")
            
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    extracted_pages.append(text)
            
            full_text = "\n\n".join(extracted_pages).strip()
            if not full_text:
                raise DocumentParsingError("PDF contains no extractable text. Scanned OCR or image document detected.")
            
            return cls._normalize_whitespace(full_text)
        except Exception as e:
            if isinstance(e, DocumentParsingError):
                raise
            raise DocumentParsingError(f"Failed to parse PDF document: {str(e)}")

    @classmethod
    def _parse_docx(cls, file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            
            # Also extract text from tables if any
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
                        
            full_text = "\n".join(paragraphs).strip()
            if not full_text:
                raise DocumentParsingError("DOCX file contains no extractable text.")
                
            return cls._normalize_whitespace(full_text)
        except Exception as e:
            if isinstance(e, DocumentParsingError):
                raise
            raise DocumentParsingError(f"Failed to parse DOCX document: {str(e)}")

    @classmethod
    def _parse_text(cls, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if not content:
                raise DocumentParsingError("Text file is empty.")
            return cls._normalize_whitespace(content)
        except Exception as e:
            if isinstance(e, DocumentParsingError):
                raise
            raise DocumentParsingError(f"Failed to read text file: {str(e)}")

    @classmethod
    def _normalize_whitespace(cls, text: str) -> str:
        # Normalize non-breaking spaces and irregular unicode spaces
        text = text.replace('\xa0', ' ').replace('\u200b', '')
        # Collapse excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
