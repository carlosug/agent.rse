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
        # Look for content between ```dockerfile and ``` markers
        dockerfile_pattern = r'```dockerfile\n(.*?)```'
        dockerfile_match = re.search(dockerfile_pattern, self.raw_content, re.DOTALL)
        
        if dockerfile_match:
            return dockerfile_match.group(1).strip()
        
        # Alternative pattern for just ``` markers
        code_pattern = r'```\n(.*?)```'
        code_match = re.search(code_pattern, self.raw_content, re.DOTALL)
        
        if code_match:
            return code_match.group(1).strip()
        
        # If no markers found, remove markdown and explanatory text
        lines = self.raw_content.split('\n')
        dockerfile_lines = []
        for line in lines:
            # Skip explanatory text and empty lines
            if line.strip() and not line.startswith(('#', 'To ', 'However', 'Remember', 'And')):
                dockerfile_lines.append(line)
        
        return '\n'.join(dockerfile_lines).strip()

class DockerfileResponse(BaseModel):
    """Response model for Dockerfile generation."""
    content: str = Field(..., description="The cleaned Dockerfile content")
    filepath: str = Field(..., description="Path where the Dockerfile was saved")
    status: str = Field(default="success", description="Generation status")
    error: Optional[str] = Field(None, description="Error message if any")