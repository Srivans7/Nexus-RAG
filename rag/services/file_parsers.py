from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader


class UnsupportedFileTypeError(Exception):
    """Raised when the parser receives an unsupported file type."""


class FileParser:
    """Parses supported source documents into plain text."""

    @staticmethod
    def parse(file_path: str, file_type: str) -> str:
        parser_map = {
            'md': FileParser._parse_text_file,
            'txt': FileParser._parse_text_file,
            'pdf': FileParser._parse_pdf_file,
        }
        parser = parser_map.get(file_type)
        if parser is None:
            raise UnsupportedFileTypeError(f'Unsupported file type: {file_type}')
        return parser(file_path)

    @staticmethod
    def _parse_text_file(file_path: str) -> str:
        return Path(file_path).read_text(encoding='utf-8', errors='ignore')

    @staticmethod
    def _parse_pdf_file(file_path: str) -> str:
        reader = PdfReader(file_path)
        pages_text = [page.extract_text() or '' for page in reader.pages]
        raw = '\n'.join(pages_text)
        return FileParser._clean_pdf_text(raw)

    @staticmethod
    def _clean_pdf_text(text: str) -> str:
        """Remove mangled font symbols and non-printable characters from PDF text."""
        # Normalize unicode (NFKC converts ligatures, special letters, etc.)
        text = unicodedata.normalize('NFKC', text)
        # Strip characters that are not printable ASCII, common Latin, or whitespace
        text = re.sub(r'[^\x20-\x7E\n\t\u00C0-\u024F]', ' ', text)
        # Collapse runs of whitespace (but preserve newlines)
        text = re.sub(r'[ \t]+', ' ', text)
        # Collapse more than 2 consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
