import re
from typing import List, Dict

class LegalChunker:
    @staticmethod
    def split_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[Dict[str, any]]:
        """
        Splits text recursively based on legal document separators (Articles, Sections, Paragraphs).
        Returns a list of chunks, each containing the chunk text and estimated metadata like section.
        """
        # Define separators in order of preference
        separators = ["\n\n\n", "\n\n", "\n", ". ", " ", ""]
        
        chunks = []
        current_idx = 0
        
        # Simple recursive splitting implementation
        def recursive_split(sub_text: str, current_offset: int) -> List[str]:
            if len(sub_text) <= chunk_size:
                return [sub_text]
            
            # Find best separator
            for sep in separators:
                if not sep:
                    # If no separator worked, split by size
                    return [sub_text[i:i+chunk_size] for i in range(0, len(sub_text), chunk_size - chunk_overlap)]
                
                # Split and check sizes
                parts = sub_text.split(sep)
                if len(parts) > 1:
                    # Reconstruct chunks based on parts
                    result_chunks = []
                    current_chunk = ""
                    for part in parts:
                        if len(current_chunk) + len(part) + len(sep) <= chunk_size:
                            current_chunk += (sep if current_chunk else "") + part
                        else:
                            if current_chunk:
                                result_chunks.append(current_chunk)
                            # If a single part is larger than chunk_size, split it recursively
                            if len(part) > chunk_size:
                                result_chunks.extend(recursive_split(part, 0))
                                current_chunk = ""
                            else:
                                current_chunk = part
                    if current_chunk:
                        result_chunks.append(current_chunk)
                    return result_chunks
            return [sub_text]

        raw_chunks = recursive_split(text, 0)
        
        # Process chunks to add section/clause estimation metadata
        for idx, chunk in enumerate(raw_chunks):
            # Try to extract section or article headers (e.g., "Section 12", "Article IV", "Clause 2.1")
            section_match = re.search(r'(Section\s+\d+|Article\s+[I|V|X|L|C|D|M\d]+|Clause\s+\d+(\.\d+)?)', chunk, re.IGNORECASE)
            detected_section = section_match.group(0) if section_match else f"General Content (Chunk {idx+1})"
            
            chunks.append({
                "text": chunk,
                "metadata": {
                    "chunk_index": idx,
                    "estimated_section": detected_section,
                    "character_count": len(chunk)
                }
            })
            
        return chunks
