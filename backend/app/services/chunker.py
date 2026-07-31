import re
from typing import List, Dict

class LegalChunker:
    @staticmethod
    def split_pages(pages: List[Dict[str, any]], global_metadata: Dict[str, str] = None) -> List[Dict[str, any]]:
        """
        Intelligently chunks legal documents by structural elements (Markdown headers, Sections, Articles, Clauses).
        Applies global_metadata to every chunk for filtering.
        """
        if global_metadata is None:
            global_metadata = {}

        chunks = []
        global_chunk_idx = 0
        current_section = "General Content"
        
        # Regex to match Markdown headers or legal structural boundaries
        # e.g., "# Header", "## Header", "Section 1", "Article IV", "Clause 2.1"
        header_pattern = re.compile(
            r'^(?:#{1,6}\s+|Section\s+\d+[a-zA-Z]?|Article\s+[IVXLCDM\d]+|Clause\s+\d+(?:\.\d+)?|Chapter\s+[IVXLCDM\d]+)\b', 
            re.IGNORECASE | re.MULTILINE
        )

        for page in pages:
            page_num = page.get("page_number", 1)
            page_text = page.get("text", "").strip()
            if not page_text:
                continue

            # Find all structural boundaries and split the text
            # We keep the delimiters using lookahead/lookbehind or by splitting and interweaving
            # re.split with a capture group keeps the split delimiter in the array
            parts = re.split(r'(^(?:#{1,6}\s+|Section\s+\d+[a-zA-Z]?|Article\s+[IVXLCDM\d]+|Clause\s+\d+(?:\.\d+)?|Chapter\s+[IVXLCDM\d]+)\b.*$)', page_text, flags=re.IGNORECASE | re.MULTILINE)
            
            # parts will look like: [pre-text, header1, text1, header2, text2]
            current_chunk_text = ""
            
            for part in parts:
                if not part.strip():
                    continue
                    
                # If the part is a header
                if header_pattern.match(part):
                    # Save the previous chunk if it exists
                    if current_chunk_text.strip():
                        chunk_metadata = {
                            "chunk_index": global_chunk_idx,
                            "estimated_section": current_section,
                            "page_number": page_num,
                            "character_count": len(current_chunk_text)
                        }
                        chunk_metadata.update(global_metadata)
                        
                        chunks.append({
                            "text": current_chunk_text.strip(),
                            "metadata": chunk_metadata
                        })
                        global_chunk_idx += 1
                        
                    # Update current section context and start a new chunk
                    current_section = part.strip().lstrip('#').strip()
                    current_chunk_text = part + "\n"
                else:
                    current_chunk_text += part

            # Add the final chunk of the page
            if current_chunk_text.strip():
                # If it's too large, we fall back to a reasonable max size split
                max_size = 3000
                if len(current_chunk_text) > max_size:
                    sub_chunks = [current_chunk_text[i:i+max_size] for i in range(0, len(current_chunk_text), max_size)]
                    for sub in sub_chunks:
                        chunk_metadata = {
                            "chunk_index": global_chunk_idx,
                            "estimated_section": current_section,
                            "page_number": page_num,
                            "character_count": len(sub)
                        }
                        chunk_metadata.update(global_metadata)
                        chunks.append({"text": sub.strip(), "metadata": chunk_metadata})
                        global_chunk_idx += 1
                else:
                    chunk_metadata = {
                        "chunk_index": global_chunk_idx,
                        "estimated_section": current_section,
                        "page_number": page_num,
                        "character_count": len(current_chunk_text)
                    }
                    chunk_metadata.update(global_metadata)
                    chunks.append({"text": current_chunk_text.strip(), "metadata": chunk_metadata})
                    global_chunk_idx += 1

        return chunks

    @staticmethod
    def split_text(text: str, global_metadata: Dict[str, str] = None) -> List[Dict[str, any]]:
        return LegalChunker.split_pages([{"page_number": 1, "text": text}], global_metadata)

