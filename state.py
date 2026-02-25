from typing import TypedDict, List, Annotated, Optional
import operator
from pydantic import BaseModel, Field

class SectionResult(TypedDict):
    """The result from a single writer worker."""
    title: str
    content: str
    index: int

class DocumentState(TypedDict):
    # Core Context
    contract_topic: str
    file_path: str
    
    # Map-Reduce State (Agent 1)
    sections_to_write: List[str]  
    completed_sections: Annotated[int, operator.add] 
    # Use operator.add on lists to accumulate worker results
    generated_sections: Annotated[List[SectionResult], operator.add]
    
    # QA & CoT State (Agent 2)
    qa_query: Optional[str]
    thought_process: Optional[str]
    final_answer: Optional[str]

class WorkerState(TypedDict):
    """State strictly for the isolated worker nodes executing via Send()"""
    section_topic: str
    index: int

class SectionOutline(BaseModel):
    """Structured output for the document outline."""
    sections: List[str] = Field(description="List of detailed legal section titles.")
