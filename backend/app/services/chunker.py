import re
from typing import List, Dict

class LegalChunker:
    @staticmethod
    def _recursive_split(sub_text: str, chunk_size: int, chunk_overlap: int, separators: List[str]) -> List[str]:
        if len(sub_text) <= chunk_size:
            return [sub_text]
        
        for sep in separators:
            if not sep:
                return [sub_text[i:i+chunk_size] for i in range(0, len(sub_text), chunk_size - chunk_overlap)]
            
            parts = sub_text.split(sep)
            if len(parts) > 1:
                result_chunks = []
                current_chunk = ""
                for part in parts:
                    if len(current_chunk) + len(part) + len(sep) <= chunk_size:
                        current_chunk += (sep if current_chunk else "") + part
                    else:
                        if current_chunk:
                            result_chunks.append(current_chunk)
                        if len(part) > chunk_size:
                            result_chunks.extend(LegalChunker._recursive_split(part, chunk_size, chunk_overlap, separators))
                            current_chunk = ""
                        else:
                            current_chunk = part
                if current_chunk:
                    result_chunks.append(current_chunk)
                return result_chunks
        return [sub_text]

    @staticmethod
    def split_pages(pages: List[Dict[str, any]], chunk_size: int = 1500, chunk_overlap: int = 200) -> List[Dict[str, any]]:
        """
        Splits page-level document dictionaries, tracking page_number and hierarchical sections.
        """
        separators = ["\n\n\n", "\n\n", "\n", ". ", " ", ""]
        chunks = []
        global_chunk_idx = 0
        current_section = "General Content"
        
        # Regex to match headers at the START of a line
        header_pattern = re.compile(r'^\s*(?:Section\s+\d+[a-zA-Z]?|Article\s+[IVXLCDM\d]+|Clause\s+\d+(?:\.\d+)?|Chapter\s+[IVXLCDM\d]+)\b', re.IGNORECASE | re.MULTILINE)

        for page in pages:
            page_num = page.get("page_number", 1)
            page_text = page.get("text", "").strip()
            if not page_text:
                continue

            # Find all headers on this page to update context
            raw_chunks = LegalChunker._recursive_split(page_text, chunk_size, chunk_overlap, separators)
            
            for chunk in raw_chunks:
                if not chunk.strip():
                    continue
                
                # Check if this chunk contains a new header at the start of a line
                matches = list(header_pattern.finditer(chunk))
                if matches:
                    # Take the last header found in this chunk as the active section context
                    current_section = matches[-1].group(0).strip()
                
                chunks.append({
                    "text": chunk,
                    "metadata": {
                        "chunk_index": global_chunk_idx,
                        "estimated_section": current_section,
                        "page_number": page_num,
                        "character_count": len(chunk)
                    }
                })
                global_chunk_idx += 1

        return chunks

    @staticmethod
    def split_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[Dict[str, any]]:
        """
        Splits plain text string, defaulting page_number to 1.
        """
        return LegalChunker.split_pages([{"page_number": 1, "text": text}], chunk_size, chunk_overlap)

