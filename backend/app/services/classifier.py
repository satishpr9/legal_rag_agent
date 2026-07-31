import re

def classify_query(query: str) -> str:
    """
    Classifies a legal query into one of the domain-specific template types.
    Done in Python to avoid muddying the LLM's system prompt and reduce token usage.
    """
    query = query.lower()
    
    # Contract / Corporate
    if any(k in query for k in ["contract", "agreement", "clause", "breach", "liability", "termination", "indemnity", "risk", "nda", "moa", "aoa"]):
        return "CONTRACT"
        
    # Criminal Law
    elif any(k in query for k in ["ipc", "crpc", "bns", "bnss", "bsa", "punishment", "offence", "jail", "fine", "police", "fir", "bail", "arrest", "murder", "cheating", "fraud", "criminal"]):
        return "CRIMINAL"
        
    # Case Law
    elif any(k in query for k in ["case", "judgment", "held", "supreme court", "high court", "v.", "vs", "versus", "ratio"]):
        return "CASE"
        
    # Procedural
    elif any(k in query for k in ["procedure", "file", "apply", "steps", "how to", "process", "register", "documents required", "eligibility", "timeline", "fees", "penalty"]):
        return "PROCEDURE"
        
    # Default to general Legal Concept
    else:
        return "LEGAL"
