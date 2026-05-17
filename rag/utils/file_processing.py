import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class FileProcessingError(Exception):
    """Base error raised for document processing failures."""


class UnsupportedFileTypeError(FileProcessingError):
    """Raised when a file extension is not supported by the processing pipeline."""


class LoaderError(FileProcessingError):
    """Raised when a loader fails to read source documents."""


class ChunkingError(FileProcessingError):
    """Raised when text chunking fails unexpectedly."""


class DocumentProcessingUtility:
    """Loads, cleans, and chunks source documents using LangChain components."""

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    @classmethod
    def process_file(cls, file_path: str):
        """Return cleaned text and chunk payloads for a supported file."""
        source_path = Path(file_path)
        extension = source_path.suffix.lower()

        try:
            raw_text = cls._load_text(source_path, extension)
            cleaned_text = cls._clean_text(raw_text)
            chunks = cls._chunk_text(cleaned_text)
            return cleaned_text, chunks
        except FileProcessingError:
            raise
        except Exception as exc:
            raise FileProcessingError(str(exc)) from exc

    @classmethod
    def _load_text(cls, source_path: Path, extension: str) -> str:
        loader = cls._resolve_loader(source_path, extension)
        try:
            documents = loader.load()
        except Exception as exc:
            raise LoaderError(f'Failed to load document: {exc}') from exc

        merged_text = '\n'.join((doc.page_content or '') for doc in documents)
        if not merged_text.strip():
            raise LoaderError('Loaded document is empty after extraction.')
        return merged_text

    @staticmethod
    def _resolve_loader(source_path: Path, extension: str):
        # Markdown and plain text both use TextLoader.
        if extension in {'.md', '.txt'}:
            return TextLoader(str(source_path), encoding='utf-8', autodetect_encoding=True)
        if extension == '.pdf':
            return PyPDFLoader(str(source_path))
        raise UnsupportedFileTypeError('Unsupported file type. Allowed: .md, .txt, .pdf')

    @staticmethod
    def _clean_text(text: str) -> str:
        # Normalize line endings and collapse excessive spacing for cleaner chunks.
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        normalized = re.sub(r'[ \t]+', ' ', normalized)
        return normalized.strip()

    @classmethod
    def _chunk_text(cls, text: str):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cls.CHUNK_SIZE,
            chunk_overlap=cls.CHUNK_OVERLAP,
            separators=['\n\n', '\n', '. ', ' ', ''],
        )
        try:
            chunks = splitter.split_text(text)
        except Exception as exc:
            raise ChunkingError(f'Chunking failed: {exc}') from exc

        if not chunks:
            raise ChunkingError('No chunks were produced from the provided document.')

        return [
            {
                'chunk_index': index,
                'content': content,
                'metadata': {
                    'chunk_size': len(content),
                    'chunk_overlap': cls.CHUNK_OVERLAP,
                    'strategy': 'RecursiveCharacterTextSplitter',
                },
            }
            for index, content in enumerate(chunks)
        ]
