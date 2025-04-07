import requests
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from bs4 import BeautifulSoup
import re
import urllib.parse
import os
from dotenv import dotenv_values

console = Console()

class ErrorSearchTool:
    """Tool for searching solutions to errors online."""
    
    def __init__(self):
        self.base_url = "https://api.stackexchange.com/2.3/search"
        self.google_url = "https://www.google.com/search"
        
    def clean_error_message(self, error: str) -> str:
        """Clean error message for search."""
        # Remove file paths and line numbers
        cleaned = re.sub(r'File ".*?", line \d+,?\s*', '', error)
        # Remove specific values
        cleaned = re.sub(r'"[^"]*"', '"VALUE"', cleaned)
        return cleaned.strip()
    
    def search_stackoverflow(self, error_message: str) -> List[Dict[str, str]]:
        """Search Stack Overflow for error solutions."""
        try:
            params = {
                'site': 'stackoverflow',
                'intitle': self.clean_error_message(error_message),
                'sort': 'votes',
                'pagesize': 5,
                'order': 'desc'
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            results = response.json().get('items', [])
            return [
                {
                    'title': item['title'],
                    'link': item['link'],
                    'score': item['score']
                }
                for item in results
            ]
        except Exception as e:
            console.print(f"[red]Error searching Stack Overflow: {str(e)}[/red]")
            return []
    
    def search_google(self, error_message: str) -> List[Dict[str, str]]:
        """Search Google for error solutions."""
        try:
            params = {
                'q': f"python {self.clean_error_message(error_message)} solution",
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(
                self.google_url,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.find_all('div', class_='g')[:5]:
                title_elem = result.find('h3')
                link_elem = result.find('a')
                
                if title_elem and link_elem:
                    results.append({
                        'title': title_elem.text,
                        'link': link_elem['href']
                    })
            
            return results
        except Exception as e:
            console.print(f"[red]Error searching Google: {str(e)}[/red]")
            return []

class InstallationSearchTool(ErrorSearchTool):
    """Extended search tool for installation plan validation."""
    
    def search_installation_method(self, package: str, method: str) -> List[Dict[str, str]]:
        """Search for installation method validation."""
        try:
            params = {
                'site': 'stackoverflow',
                'intitle': f"how to install {package} {method}",
                'tagged': f'python;{method}',
                'sort': 'votes',
                'pagesize': 3
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            return [
                {
                    'title': item['title'],
                    'link': item['link'],
                    'score': item['score']
                }
                for item in response.json().get('items', [])
            ]
        except Exception as e:
            console.print(f"[red]Error validating installation method: {str(e)}[/red]")
            return []

class ContainerSearchTool(ErrorSearchTool):
    """Tool for searching container-related information."""
    
    def __init__(self):
        super().__init__()
        config = dotenv_values("config/.env")
        self.google_api_key = config.get('GOOGLE_API_KEY')
        self.google_cse_id = config.get('GOOGLE_CSE_ID')
        
        if not self.google_api_key:
            console.print("[red]Warning: GOOGLE_API_KEY not found in .env[/red]")
        if not self.google_cse_id:
            console.print("[red]Warning: GOOGLE_CSE_ID not found in .env[/red]")

    def search_container_practices(self, container_type: str, project_type: str) -> Dict[str, Any]:
        """Search for container best practices."""
        try:
            # Stack Overflow search
            so_params = {
                'site': 'stackoverflow',
                'tagged': f'{container_type};{project_type}',
                'sort': 'votes',
                'intitle': f'best practices {container_type} container',
                'pagesize': 5
            }
            
            so_response = requests.get(self.base_url, params=so_params)
            so_response.raise_for_status()
            
            # Google Custom Search
            google_query = f"{container_type} container best practices for {project_type}"
            google_url = "https://www.googleapis.com/customsearch/v1"
            google_params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': google_query,
                'num': 5
            }
            
            google_response = requests.get(google_url, params=google_params)
            google_response.raise_for_status()
            
            # Process results
            results = {
                'stackoverflow': [],
                'google': [],
                'query_info': {
                    'container_type': container_type,
                    'project_type': project_type,
                    'google_query': google_query
                }
            }
            
            # Add Stack Overflow results
            if items := so_response.json().get('items', []):
                results['stackoverflow'] = [
                    {
                        'title': item['title'],
                        'link': item['link'],
                        'score': item.get('score', 0),
                        'answer_count': item.get('answer_count', 0)
                    }
                    for item in items
                ]
            
            # Add Google results
            if items := google_response.json().get('items', []):
                results['google'] = [
                    {
                        'title': item['title'],
                        'link': item['link'],
                        'snippet': item.get('snippet', ''),
                        'source': 'google'
                    }
                    for item in items
                ]
            
            return results
            
        except Exception as e:
            console.print(f"[red]Error in container search: {str(e)}[/red]")
            # Log detailed error for debugging
            console.print(Panel(
                str(e),
                title="[red]Search Error Details[/red]"
            ))
            return {'stackoverflow': [], 'google': [], 'error': str(e)}

class InstallationPlanValidator:
    """Validator for installation plans using web searches."""
    
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.error_searcher = ErrorSearchTool()
        self.install_searcher = InstallationSearchTool()
        
    def validate_method(self, method: str) -> Dict[str, Any]:
        """Validate installation method against multiple sources."""
        try:
            so_results = self.install_searcher.search_installation_method(
                self.package_name, method
            )
            
            google_query = f"how to install {self.package_name} using {method}"
            google_results = self.error_searcher.search_google(google_query)
            
            # Return standardized validation structure
            return {
                'validation_type': 'method',
                'method': method,
                'results': {
                    'stackoverflow': so_results,
                    'google': google_results
                },
                'confidence_score': len(so_results) + len(google_results)
            }
        except Exception as e:
            console.print(f"[red]Method validation error: {str(e)}[/red]")
            return {
                'validation_type': 'method',
                'method': method,
                'results': {'stackoverflow': [], 'google': []},
                'confidence_score': 0,
                'error': str(e)
            }

    def validate_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single installation step."""
        try:
            step_order = step.get('order', 0)
            step_method = step.get('method', 'unknown')
            
            validation = {
                'step': {  # Changed from 'step_info' to 'step'
                    'order': step_order,
                    'method': step_method,
                    'description': step.get('description', '')
                },
                'validations': [],
                'suggestions': [],
                'confidence_score': 0
            }

            # Validate command if present
            if command := step.get('command'):
                so_query = f"{self.package_name} {step_method} {command}"
                cmd_results = self.error_searcher.search_stackoverflow(so_query)
                if cmd_results:
                    validation['validations'].extend(cmd_results)
                    validation['confidence_score'] += len(cmd_results)

            # Validate step description
            if description := step.get('description'):
                google_query = f"{self.package_name} {step_method} {description}"
                desc_results = self.error_searcher.search_google(google_query)
                if desc_results:
                    validation['suggestions'].extend(desc_results)
                    validation['confidence_score'] += len(desc_results)

            return validation

        except Exception as e:
            console.print(f"[red]Step validation error: {str(e)}[/red]")
            return {
                'step': {  # Changed from 'step_info' to 'step'
                    'order': step.get('order', 0),
                    'method': step.get('method', 'unknown'),
                    'description': step.get('description', '')
                },
                'validations': [],
                'suggestions': [],
                'confidence_score': 0,
                'error': str(e)
            }

    def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate entire installation plan."""
        try:
            # Create standardized validation response
            validation_results = {
                'overall_confidence': 0,
                'method_validation': None,
                'step_validations': [],
                'validation_summary': {
                    'total_steps': 0,
                    'validated_steps': 0,
                    'confidence_by_step': {}
                }
            }

            # Validate installation method
            if method := plan.get('chosen_method'):
                method_validation = self.validate_method(method)
                validation_results['method_validation'] = method_validation
                validation_results['overall_confidence'] += method_validation['confidence_score']

            # Validate each step
            if steps := plan.get('steps', []):
                validation_results['validation_summary']['total_steps'] = len(steps)
                
                for step in steps:
                    step_validation = self.validate_step(step)
                    validation_results['step_validations'].append(step_validation)
                    
                    if step_validation['confidence_score'] > 0:
                        validation_results['validation_summary']['validated_steps'] += 1
                        
                    step_order = step.get('order', 0)
                    validation_results['validation_summary']['confidence_by_step'][step_order] = \
                        step_validation['confidence_score']
                    
                    validation_results['overall_confidence'] += step_validation['confidence_score']

            # Display validation results
            self._display_validation_results(validation_results)
            
            return validation_results

        except Exception as e:
            console.print(f"[red]Plan validation error: {str(e)}[/red]")
            return {
                'overall_confidence': 0,
                'method_validation': None,
                'step_validations': [],
                'validation_summary': {
                    'total_steps': 0,
                    'validated_steps': 0,
                    'confidence_by_step': {}
                },
                'error': str(e)
            }

    def _display_validation_results(self, results: Dict[str, Any]) -> None:
        """Display formatted validation results."""
        console.print("\n[yellow]Installation Plan Validation Results:[/yellow]")
        
        # Method validation
        method_results = results.get('method_validation', {})
        if method_results:
            console.print(Panel(
                "\n".join([
                    "[blue]Stack Overflow Results:[/blue]",
                    *[f"- {r['title']}" for r in method_results.get('results', {}).get('stackoverflow', [])[:2]],
                    "\n[blue]Google Results:[/blue]",
                    *[f"- {r['title']}" for r in method_results.get('results', {}).get('google', [])[:2]]
                ]),
                title=f"Method Validation (Confidence: {method_results.get('confidence_score', 0)})"
            ))
        
        # Steps validation
        if step_validations := results.get('step_validations', []):
            for step_validation in step_validations:
                step_info = step_validation.get('step', {})  # Changed from 'step_info' to 'step'
                validations = step_validation.get('validations', [])
                suggestions = step_validation.get('suggestions', [])
                
                if validations or suggestions:
                    step_order = step_info.get('order', '?')
                    step_method = step_info.get('method', 'unknown')
                    
                    console.print(Panel(
                        "\n".join([
                            "[blue]Command Validations:[/blue]" if validations else "",
                            *[f"- {v['title']}" for v in validations[:2]],
                            "\n[blue]Step Suggestions:[/blue]" if suggestions else "",
                            *[f"- {s['title']}" for s in suggestions[:2]]
                        ]),
                        title=f"Step {step_order} ({step_method}) Validation"
                    ))

def search_error_solutions(error_message: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Search for solutions to an error message.
    
    Args:
        error_message (str): The error message to search for
        
    Returns:
        Dict[str, List[Dict[str, str]]]: Search results from different sources
    """
    searcher = ErrorSearchTool()
    
    # Display search query
    console.print("[blue]Searching for solutions...[/blue]")
    console.print(Panel(error_message, title="Error Message"))
    
    # Search both sources
    so_results = searcher.search_stackoverflow(error_message)
    google_results = searcher.search_google(error_message)
    
    # Display results
    if so_results:
        console.print("\n[yellow]Stack Overflow Solutions:[/yellow]")
        for result in so_results:
            console.print(Panel(
                f"[blue]{result['title']}[/blue]\n{result['link']}",
                title=f"Score: {result.get('score', 'N/A')}"
            ))
    
    if google_results:
        console.print("\n[yellow]Google Search Results:[/yellow]")
        for result in google_results:
            console.print(Panel(
                f"[blue]{result['title']}[/blue]\n{result['link']}"
            ))
    
    return {
        'stackoverflow': so_results,
        'google': google_results
    }

def validate_installation_plan(package_name: str, plan: Dict) -> Dict[str, Any]:
    """
    Validate installation plan against online resources.
    
    Args:
        package_name: Name of the package to install
        plan: Installation plan dictionary
    """
    validator = InstallationPlanValidator(package_name)
    return validator.validate_plan(plan)