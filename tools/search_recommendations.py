from typing import Dict, List, Any
from rich.console import Console
from duckduckgo_search import DDGS
from SUPER.tools import Tool
from groq import Groq
from dotenv import dotenv_values
import requests
from pydantic import BaseModel, Field
import json
import re
from googlesearch import search
from bs4 import BeautifulSoup
from urllib.parse import urlparse

console = Console()

# Keep the ContainerBestPractice model for compatibility
class ContainerBestPractice(BaseModel):
    """Class representing a container best practice."""
    category: str = Field(..., description="Practice category")
    recommendation: str = Field(..., description="Practice description")
    source: str = Field(..., description="Source of recommendation")
    priority: int = Field(..., description="Priority level")

    def __str__(self) -> str:
        """String representation of the best practice."""
        return self.recommendation

    @classmethod
    def safe_create(cls, value, index=0) -> 'ContainerBestPractice':
        """Safely create a ContainerBestPractice from various input formats."""
        if isinstance(value, cls):
            # Already the right type
            return value
            
        if isinstance(value, dict):
            # Handle dictionary format
            return cls(
                category=value.get('category', 'container'),
                recommendation=value.get('recommendation', 'Missing recommendation'),
                source=value.get('source', 'container_analysis'),
                priority=value.get('priority', index + 1)
            )
            
        if isinstance(value, str):
            # Handle string format
            return cls(
                category='container',
                recommendation=value,
                source='container_analysis',
                priority=index + 1
            )
        
        # Last resort - convert to string
        return cls(
            category='container',
            recommendation=str(value),
            source='unknown',
            priority=index + 1
        )
        
    @classmethod
    def from_list(cls, items) -> List['ContainerBestPractice']:
        """Convert a list of items (strings, dicts, etc.) to ContainerBestPractice objects."""
        if not items:
            return []
            
        result = []
        for idx, item in enumerate(items):
            try:
                result.append(cls.safe_create(item, idx))
            except Exception as e:
                # Skip items that can't be converted
                console.print(f"[yellow]Warning: Could not convert practice item: {str(e)}[/yellow]")
                continue
                
        return result


class ContainerRecommendationTool(Tool):
    """Tool for getting container best practices and recommendations."""
    
    def __init__(self):
        """Initialize container recommendation tool."""
        self.ddg = DDGS()
        self.init_groq_client()
        
        # Base URLs for different container types
        self.base_urls = {
            'docker': [
                'https://docs.docker.com',
                'https://hub.docker.com',
                'https://github.com/docker/docker.github.io'
            ],
            'guix': [
                'https://guix.gnu.org',
                'https://github.com/guix-mirror/guix'
            ],
            'singularity': [
                'https://docs.sylabs.io',
                'https://github.com/sylabs/singularity'
            ]
        }
    
    def forward(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a recommendation request.
        
        Args:
            request: Dict containing:
                - action: The type of recommendation to get (dockerfile, script, search)
                - container_type: Type of container (docker, guix, singularity)
                - project_type: Type of project
                - context: Additional context for recommendation
                
        Returns:
            Dict with recommendations, practices, and other relevant information
        """
        try:
            action = request.get("action", "search")
            container_type = request.get("container_type", "docker")
            project_type = request.get("project_type", "python")
            context = request.get("context", {})
            
            if action == "dockerfile":
                return {
                    "status": "success",
                    "practices": self._get_dockerfile_practices(context),
                    "error": None
                }
            elif action == "script":
                return {
                    "status": "success",
                    "practices": self._get_installation_script_practices(context),
                    "error": None
                }
            else:  # Default to search
                return {
                    "status": "success",
                    "results": self._search_container_practices(container_type, project_type),
                    "error": None
                }
                
        except Exception as e:
            console.print(f"[red]Error in container recommendation tool: {str(e)}[/red]")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_dockerfile_practices(self, context: Dict[str, Any]) -> List[str]:
        """Get best practices for Dockerfiles as simple strings.
        
        This version returns simple strings to avoid the dict vs string issue
        """
        try:
            # Get project type for more targeted recommendations
            project_type = context.get('language', 'python')
            
            # Use fallback practices if no context provided
            if not context:
                return self._fallback_dockerfile_practices()
                
            # Extract dockerfile practices using AI
            prompt = f"""Based on this project context, provide Dockerfile best practices:
            
            Project type: {project_type}
            Dependencies: {context.get('dependencies', [])}
            Methods: {context.get('methods', [])}
            
            Return ONLY a list of 5-8 best practices for creating a Dockerfile for this project.
            Each best practice should be a specific, actionable recommendation.
            """
            
            response = self._generate_recommendation(prompt)
            
            # Extract practices from the response
            practices = []
            
            # Handle different response formats
            if isinstance(response, dict) and 'practices' in response:
                # Handle structured response with a practices field
                raw_practices = response['practices']
                for practice in raw_practices:
                    if isinstance(practice, str):
                        practices.append(practice)
                    elif isinstance(practice, dict) and 'recommendation' in practice:
                        practices.append(practice['recommendation'])
                    else:
                        # Convert any other format to string
                        practices.append(str(practice))
            elif isinstance(response, list):
                # Handle list response directly
                for practice in response:
                    if isinstance(practice, str):
                        practices.append(practice)
                    elif isinstance(practice, dict) and 'recommendation' in practice:
                        practices.append(practice['recommendation'])
                    else:
                        # Convert any other format to string
                        practices.append(str(practice))
            else:
                # Extract list from text response
                # Split by numbered bullets like "1.", "2.", etc.
                raw_text = str(response)
                bullet_pattern = r'\d+\.\s*(.*?)(?=\d+\.|$)'
                line_pattern = r'(?:^|\n)- (.*?)(?:\n|$)'
                
                matches = re.findall(bullet_pattern, raw_text, re.DOTALL)
                if not matches:
                    matches = re.findall(line_pattern, raw_text, re.DOTALL)
                
                if matches:
                    practices = [m.strip() for m in matches]
                else:
                    # Fall back to splitting by newlines
                    practices = [p.strip() for p in raw_text.split('\n') if p.strip()]
            
            # Ensure we have at least some practices
            if not practices:
                return self._fallback_dockerfile_practices()
                
            # Return cleaned practices as strings
            return [str(p) for p in practices]
            
        except Exception as e:
            console.print(f"[red]Error getting Dockerfile practices: {str(e)}[/red]")
            return self._fallback_dockerfile_practices()

    def _generate_recommendation(self, prompt: str) -> Any:
        """Generate AI recommendation based on prompt."""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=[
                    {"role": "system", "content": "You are a container expert. Provide specific, actionable recommendations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Try to parse as JSON first
            content = response.choices[0].message.content
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, return the text content
                return content
                
        except Exception as e:
            console.print(f"[red]Error generating recommendation: {str(e)}[/red]")
            return []

    def _fallback_dockerfile_practices(self) -> List[str]:
        """Return fallback Dockerfile practices when API fails."""
        return [
            "Use multi-stage builds to minimize image size",
            "Specify exact versions for base images and dependencies",
            "Combine related commands in a single RUN statement to reduce layers",
            "Run containers as non-root users for better security",
            "Use .dockerignore to exclude unnecessary files",
            "Order Dockerfile instructions from least to most frequently changing",
            "Clean up package manager caches after installations",
            "Use environment variables for configuration"
        ]
    
    def _get_installation_script_practices(self, context: Dict[str, Any]) -> List[str]:
        """Get best practices for installation scripts."""
        try:
            # Create detailed search query
            query = (
                f"python {context.get('chosen_method', '')} "
                f"installation script best practices "
                f"for {context.get('repository', '')} "
                f"with {' '.join(context.get('dependencies', []))}"
            )
            
            # Get web content
            web_results = self._search_web_content(query)
            
            if not web_results:
                return self._fallback_script_practices()
                
            # Process results
            content = "\n\n".join([
                f"From {result['domain']}:\n{result['body']}"
                for result in web_results
            ])
            
            # Get recommendations from content
            prompt = f"""Based on these resources:
            {content}
            
            Provide 5 best practices for writing an installation script that:
            1. Handles dependencies: {context.get('dependencies', [])}
            2. Sets up environment: {context.get('environment', [])}
            3. Follows {context.get('chosen_method', '')} method
            4. Implements proper validation
            5. Shows clear progress indicators
            
            Format each practice as a clear, actionable recommendation."""
            
            response = self._generate_recommendation(prompt)
            
            # Process and return recommendations as strings
            if isinstance(response, list):
                return [str(item) for item in response if item]
            elif isinstance(response, str):
                # Split by newlines or bullet points
                lines = response.split('\n')
                return [line.strip().replace('- ', '').replace('* ', '') for line in lines if line.strip()]
            else:
                return self._fallback_script_practices()
            
        except Exception as e:
            console.print(f"[red]Error getting installation script practices: {str(e)}[/red]")
            return self._fallback_script_practices()

    def _fallback_script_practices(self) -> List[str]:
        """Return fallback script practices when API fails."""
        return [
            "Check for required dependencies before installation",
            "Provide clear error messages when requirements are not met",
            "Include progress indicators for long-running operations",
            "Add validation checks after each critical installation step",
            "Create a clean rollback mechanism for failed installations"
        ]

    def _search_container_practices(self, container_type: str, project_type: str) -> Dict[str, Any]:
        """Search for container best practices."""
        try:
            # Get best practices from API
            search_query = f"{container_type} container best practices for {project_type} projects"
            web_results = self._search_web_content(search_query)
            
            # Initialize results dictionary
            results = {
                'web_results': web_results,
                'container_type': container_type,
                'confidence_scores': {
                    'docker': 0,
                    'guix': 0,
                    'singularity': 0
                },
                'documentation_url': self.base_urls.get(container_type, [''])[0]
            }
            
            # Update confidence scores with web results
            results['confidence_scores'][container_type] += len(
                [r for r in web_results if container_type in r['title'].lower()]
            )
            
            # Extract best practices
            best_practices = []
            if web_results:
                content = "\n\n".join([
                    f"From {result['title']}:\n{result['body']}"
                    for result in web_results
                ])
                
                prompt = f"""Based on these search results, provide 5 best practices for using {container_type} containers with {project_type} projects.
                Return each practice as a simple string in a list format."""
                
                response = self._generate_recommendation(prompt)
                
                if isinstance(response, list):
                    best_practices = [str(item) for item in response if item]
                elif isinstance(response, str):
                    # Split by newlines or bullet points
                    lines = response.split('\n')
                    best_practices = [line.strip().replace('- ', '').replace('* ', '') for line in lines if line.strip()]
            
            # Add fallback practices if none found
            if not best_practices:
                best_practices = self._fallback_dockerfile_practices()
            
            results['best_practices'] = best_practices
            
            return results
            
        except Exception as e:
            console.print(f"[red]Error in container search: {str(e)}[/red]")
            return {
                'web_results': [],
                'best_practices': self._fallback_dockerfile_practices(),
                'container_type': container_type,
                'confidence_scores': {'docker': 1, 'guix': 0, 'singularity': 0},
                'documentation_url': self.base_urls.get(container_type, [''])[0]
            }

    def _search_web_content(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search web for content related to query."""
        results = []
        try:
            # Log search query
            console.print(f"[blue]🔍 Searching for: {query}[/blue]")
            
            # Simple DuckDuckGo search for speed and reliability
            search_results = self.ddg.text(query, max_results=num_results)
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'domain': urlparse(result.get('link', '')).netloc,
                    'body': result.get('body', '')[:500]
                })
            
        except Exception as search_error:
            console.print(f"[red]❌ Search error: {str(search_error)}[/red]")
            
        return results