import os
from pathlib import Path
import pdfplumber
import docx


def parse_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def parse_pdf(path: str) -> str:
    text_blocks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_blocks.append(page_text)
    return "\n\n".join(text_blocks).strip()


def parse_docx(path: str) -> str:
    doc = docx.Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs).strip()


def parse_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".txt":
        return parse_txt(path)
    if ext == ".pdf":
        return parse_pdf(path)
    if ext == ".docx":
        return parse_docx(path)
    raise ValueError("不支持的文件类型：%s" % ext)


def split_text(text: str, chunk_size: int = 500, overlap: int = 100, max_chars: int = 2048) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    tokens = normalized.split()
    if len(tokens) == 0:
        return []

    result_chunks = []
    current_tokens = []
    current_length = 0

    for token in tokens:
        token_length = len(token)
        
        # Calculate potential new length if we add this token
        # Include space if current_tokens is not empty
        potential_length = current_length + token_length
        if current_tokens:
            potential_length += 1  # for space
        
        # Check if adding this token would exceed max_chars
        if potential_length > max_chars:
            # If we have tokens, create a chunk
            if current_tokens:
                chunk = " ".join(current_tokens)
                # Double-check length
                if len(chunk) > max_chars:
                    # Chunk is too long, split by max_chars
                    start = 0
                    while start < len(chunk):
                        end = start + max_chars
                        result_chunks.append(chunk[start:end])
                        start = end
                else:
                    result_chunks.append(chunk)
            
            # Handle overlap
            overlap_tokens = []
            if overlap > 0 and current_tokens:
                overlap_tokens = current_tokens[-overlap:]
            
            # Start new chunk with overlap tokens
            current_tokens = overlap_tokens
            current_length = 0
            for t in overlap_tokens:
                current_length += len(t) + 1  # +1 for space
            if current_length > 0:
                current_length -= 1  # remove trailing space
        
        # Add the token
        current_tokens.append(token)
        # Update current length
        if current_length == 0:
            current_length = token_length
        else:
            current_length += 1 + token_length  # +1 for space

    # Process remaining tokens
    if current_tokens:
        chunk = " ".join(current_tokens)
        if len(chunk) > max_chars:
            # Split by max_chars
            start = 0
            while start < len(chunk):
                end = start + max_chars
                result_chunks.append(chunk[start:end])
                start = end
        else:
            result_chunks.append(chunk)

    return result_chunks