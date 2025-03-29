from pydantic import BaseModel, Field
import re
from typing import Optional

class DockerfileRequest(BaseModel):
    """Request model for Dockerfile generation."""
    prompt: str = Field(
        description="The prompt describing the desired Dockerfile content"
    )
    model: str = Field(
        default="gemma2-9b-it",
        description="The name of the Groq LLM model to use"
    )

class DockerfileContent(BaseModel):
    """Model for parsing and validating Dockerfile content."""
    raw_content: str = Field(..., description="Raw response from the LLM")
    
    @property
    def dockerfile_code(self) -> str:
        """Extract only the Dockerfile code from the content."""
        pattern = r'```dockerfile\n(.*?)```'
        match = re.search(pattern, self.raw_content, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Fallback: clean the content if no markers found
        clean_content = re.sub(r'^#.*\n?', '', self.raw_content, flags=re.MULTILINE)
        return clean_content.strip()

class DockerfileResponse(BaseModel):
    """Response model for Dockerfile generation."""
    content: str = Field(..., description="The cleaned Dockerfile content")
    filepath: str = Field(..., description="Path where the Dockerfile was saved")
    status: str = Field(default="success", description="Generation status")
    error: Optional[str] = Field(None, description="Error message if any")