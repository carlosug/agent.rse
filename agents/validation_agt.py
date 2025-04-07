import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from groq import Groq
from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import sys
import re
import traceback

sys.path.append(str(Path(__file__).parent.parent))
from tools.tool_models import (
    ValidationResponse, 
    ContainerConfig,
    ContainerType,
    ContainerStep,
    ContainerBestPractice,
    ContainerRecommendations
)
from SUPER.tools import ContainerRecommendationTool

console = Console()


class ContainerValidationAgent:
    """Agent for validating container configurations."""
    
    def __init__(self, workspace_path: str):
        """Initialize container validation agent."""
        self.workspace_path = workspace_path
        self.analysis_files = {}
        # Use our new tool instead of the container searcher
        self.recommendation_tool = ContainerRecommendationTool()

    def ensure_workspace(self) -> None:
        """Ensure workspace directory exists with required files."""
        if not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path)
            console.print(f"[yellow]Created workspace directory: {self.workspace_path}[/yellow]")

    def init_groq_client(self) -> None:
        """Initialize Groq client with API key."""
        CONFIG = dotenv_values("config/.env")
        api_key = CONFIG.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY in config/.env")
        self.client = Groq(api_key=api_key.strip())

    def load_analysis_files(self) -> Dict[str, Any]:
        """Load installation plan and analysis files from the outputs directory."""
        outputs_path = os.path.join(self.workspace_path, "outputs")
        
        plan_path = os.path.join(outputs_path, "installation_plan.json")
        analysis_path = os.path.join(outputs_path, "installation_analysis.json")
        
        if not os.path.exists(plan_path):
            alt_plan_path = os.path.join(self.workspace_path, "installation_plan.json")
            if os.path.exists(alt_plan_path):
                plan_path = alt_plan_path
                
        if not os.path.exists(analysis_path):
            alt_analysis_path = os.path.join(self.workspace_path, "installation_analysis.json")
            if os.path.exists(alt_analysis_path):
                analysis_path = alt_analysis_path
        
        missing_files = []
        if not os.path.exists(plan_path):
            missing_files.append("installation_plan.json")
        if not os.path.exists(analysis_path):
            missing_files.append("installation_analysis.json")
        
        if missing_files:
            console.print("[red]Missing required files:[/red]")
            for file in missing_files:
                console.print(f"[red]- {file}[/red]")
            console.print("\n[yellow]Expected locations:[/yellow]")
            console.print(f"- Plan: {plan_path}")
            console.print(f"- Analysis: {analysis_path}")
            console.print(f"\n[yellow]Also checked: {outputs_path}[/yellow]")
            raise FileNotFoundError(f"Required files not found: {', '.join(missing_files)}")
            
        try:
            with open(plan_path) as f:
                plan = json.load(f)
            with open(analysis_path) as f:
                analysis = json.load(f)
                
            return {"plan": plan, "analysis": analysis}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in analysis files: {str(e)}")

    def get_container_file_recommendations(self) -> List[ContainerBestPractice]:
        """Get Dockerfile recommendations based on analysis."""
        try:
            analysis = self.analysis_files['analysis']
            
            # Use our new tool to get recommendations
            response = self.recommendation_tool.forward({
                "action": "dockerfile",
                "context": self.analysis_files['analysis']
            })
            
            if response.get("status") == "success":
                practices_raw = response.get("practices", [])
            else:
                console.print(f"[red]Error getting Dockerfile practices: {response.get('error')}[/red]")
                practices_raw = []
            
            # Convert string practices to ContainerBestPractice objects
            container_practices = []
            for idx, practice in enumerate(practices_raw):
                container_practices.append(ContainerBestPractice(
                    category="container",
                    recommendation=str(practice),
                    source="container_analysis",
                    priority=idx + 1
                ))
            
            # Add default practices if none found
            if not container_practices:
                container_practices = [
                    ContainerBestPractice(
                        category="container",
                        recommendation="Use multi-stage builds",
                        source="fallback",
                        priority=1
                    ),
                    ContainerBestPractice(
                        category="container",
                        recommendation="Minimize layer count",
                        source="fallback",
                        priority=2
                    ),
                    ContainerBestPractice(
                        category="security",
                        recommendation="Avoid running containers as root",
                        source="fallback",
                        priority=3
                    )
                ]
            
            return container_practices
            
        except Exception as e:
            console.print(f"[red]Error getting container recommendations: {str(e)}[/red]")
            console.print(f"[red]{traceback.format_exc()}[/red]")
            
            # Return default recommendations on error
            return [
                ContainerBestPractice(
                    category="container",
                    recommendation="Use multi-stage builds",
                    source="fallback_error",
                    priority=1
                )
            ]

    def get_script_recommendations(self) -> List[ContainerBestPractice]:
        """Get installation script recommendations."""
        try:
            # Extract relevant context
            context = self._extract_installation_context(
                self.analysis_files.get('analysis', {}),
                self.analysis_files.get('plan', {})
            )
            
            # Use our new tool to get recommendations
            response = self.recommendation_tool.forward({
                "action": "script",
                "context": context
            })
            
            if response.get("status") == "success":
                practices_raw = response.get("practices", [])
            else:
                console.print(f"[red]Error getting script practices: {response.get('error')}[/red]")
                practices_raw = []
            
            # Convert string practices to ContainerBestPractice objects
            script_practices = []
            for idx, practice in enumerate(practices_raw):
                script_practices.append(ContainerBestPractice(
                    category="script",
                    recommendation=str(practice),
                    source="script_analysis",
                    priority=idx + 1
                ))
                
            # Add default practices if none found
            if not script_practices:
                script_practices = [
                    ContainerBestPractice(
                        category="script",
                        recommendation="Validate all installation steps",
                        source="fallback",
                        priority=1
                    )
                ]
                
            return script_practices
            
        except Exception as e:
            console.print(f"[red]Error getting script recommendations: {str(e)}[/red]")
            return []
            
    def _extract_installation_context(self, analysis: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant installation context from JSON files."""
        return {
            "repository": project_name,  # Changed from "somef" to "ExecutionAgent"
            "chosen_method": plan.get("chosen_method"),
            "reason": plan.get("reason"),
            "steps": plan.get("steps", []),
            "commands": analysis.get("commands", []),
            "config_files": analysis.get("config_files", []),
            "dependencies": analysis.get("dependencies", []),
            "environment": analysis.get("environment", []),
            "prerequisites": analysis.get("prerequisites", [])
        }

    def get_combined_recommendations(self) -> ContainerRecommendations:
        """Get combined recommendations for both script and container."""
        try:
            script_practices = self.get_script_recommendations()
            container_practices = self.get_container_file_recommendations()
            
            all_practices = []
            for practice in script_practices + container_practices:
                if isinstance(practice, ContainerBestPractice):
                    all_practices.append(practice)
                else:
                    console.print(f"[yellow]Warning: Invalid practice format: {practice}[/yellow]")
            
            # Get search results
            response = self.recommendation_tool.forward({
                "action": "search",
                "container_type": "docker",  # Default to docker
                "project_type": self.analysis_files['analysis'].get('project_type', 'python')
            })
            
            # Extract the results or provide defaults
            search_results = response.get("results", {})
            if not search_results:
                search_results = {
                    "web_results": [],
                    "confidence_scores": {"docker": 1, "guix": 0, "singularity": 0},
                    "documentation_url": "https://docs.docker.com"
                }
            
            # Create the recommendations object
            recommendations = ContainerRecommendations(
                container_type="docker",
                installation_type=self.analysis_files['plan'].get('chosen_method', 'pip'),
                project_type=self.analysis_files['analysis'].get('project_type', 'python'),
                repository=os.path.basename(self.workspace_path),
                operating_system="Linux",
                method_source='installation_analysis',
                guidelines=self._extract_key_points(search_results),
                confidence_scores=search_results.get('confidence_scores', {"docker": 1, "guix": 0, "singularity": 0}),
                best_practices=all_practices,
                documentation_url=search_results.get('documentation_url', "https://docs.docker.com"),
                web_results=search_results.get('web_results', [])
            )
            
            return recommendations
            
        except Exception as e:
            console.print(f"[red]Error getting combined recommendations: {str(e)}[/red]")
            console.print(f"[red]{traceback.format_exc()}[/red]")
            # Return a fallback recommendation object, not a dict
            return self._get_fallback_recommendations_object()

    def _get_fallback_recommendations_object(self) -> ContainerRecommendations:
        """Get fallback recommendations as a ContainerRecommendations object."""
        return ContainerRecommendations(
            container_type="docker",
            installation_type="pip",
            project_type="python",
            repository=os.path.basename(self.workspace_path),
            operating_system="Linux",
            method_source="fallback",
            guidelines="Fallback to basic Docker container setup",
            confidence_scores={"docker": 1, "guix": 0, "singularity": 0},
            best_practices=[
                ContainerBestPractice(
                    category="container",
                    recommendation="Use multi-stage builds",
                    source="fallback",
                    priority=1
                ),
                ContainerBestPractice(
                    category="container",
                    recommendation="Minimize layer count",
                    source="fallback",
                    priority=2
                )
            ],
            documentation_url="https://docs.docker.com",
            web_results=[]
        )

    def _extract_key_points(self, search_results: Dict[str, Any]) -> str:
        """Extract key points from search results."""
        key_points = []
        
        if stackoverflow_results := search_results.get('stackoverflow', []):
            for result in stackoverflow_results[:3]:
                if result.get('score', 0) > 5:
                    key_points.append(result['title'])
        
        if web_results := search_results.get('web_results', []):
            for result in web_results[:3]:
                if 'best practices' in result['title'].lower():
                    key_points.append(result['title'])
        
        points = '. '.join(key_points)
        if not points:
            points = f"Selected {search_results['container_type']} based on compatibility"
        
        return points

    def _display_recommendations(self, recommendations: Dict[str, Any]) -> None:
        """Display container recommendations in a readable format."""
        console = Console()
        
        console.print("\n[bold blue]Container Recommendations[/bold blue]")
        console.print(f"Container Type: [green]{recommendations.get('container_type', 'docker')}[/green]")
        console.print(f"Installation Type: [green]{recommendations.get('installation_type', 'pip')}[/green]")
        console.print(f"Project Type: [green]{recommendations.get('project_type', 'python')}[/green]")
        
        if confidence := recommendations.get('confidence_scores'):
            console.print("\n[bold]Container Type Confidence:[/bold]")
            for container, score in confidence.items():
                color = "green" if container == recommendations.get('container_type') else "blue"
                console.print(f"- {container}: [{color}]{score:.2f}[/{color}]")
        
        if best_practices := recommendations.get('best_practices'):
            console.print("\n[bold]Best Practices:[/bold]")
            for i, practice in enumerate(best_practices, 1):
                if isinstance(practice, dict):
                    rec = practice.get('recommendation', '')
                    cat = practice.get('category', '')
                    console.print(f"{i}. [{cat}] {rec}")
                else:
                    console.print(f"{i}. {practice}")
                    
        console.print("\n[bold]Installation Plan:[/bold]")
        console.print(Markdown(self._format_installation_steps()))

    def generate_container_files(self, recommendations: Dict[str, Any]) -> None:
        """Generate container files based on recommendations."""
        try:
            outputs_path = os.path.join(self.workspace_path, "outputs")
            if not os.path.exists(outputs_path):
                os.makedirs(outputs_path)
            
            recommendations_path = os.path.join(outputs_path, "write_recommendations.json")
            try:
                with open(recommendations_path, 'w') as f:
                    rec_dict = recommendations.copy()
                    
                    if 'best_practices' in rec_dict and rec_dict['best_practices']:
                        if hasattr(rec_dict['best_practices'][0], 'model_dump'):
                            rec_dict['best_practices'] = [
                                practice.model_dump() for practice in rec_dict['best_practices']
                            ]
                        
                    json.dump(rec_dict, f, indent=2)
                console.print(f"[green]Saved recommendations to {recommendations_path}[/green]")
            except Exception as save_error:
                console.print(f"[red]Error saving recommendations: {str(save_error)}[/red]")
            
            console.print("[yellow]Container file generation is now handled by generate_agt.py[/yellow]")
            console.print("[blue]Please run 'python agents/generate_agt.py' to generate container files[/blue]")
            
        except Exception as e:
            console.print(f"[red]Error generating container files: {str(e)}[/red]")
            console.print(f"[red]{traceback.format_exc()}[/red]")

    def _format_installation_steps(self) -> str:
        """Format installation steps from plan file for use in prompts."""
        try:
            plan = self.analysis_files.get('plan', {})
            if not plan or 'steps' not in plan:
                return "No installation steps found."
                
            steps_text = []
            for step in plan.get('steps', []):
                step_order = step.get('order', '?')
                step_desc = step.get('description', 'No description')
                
                command = step.get('command', '')
                if isinstance(command, list):
                    command_str = "\n".join([f"   $ {cmd}" for cmd in command])
                else:
                    command_str = f"   $ {command}"
                    
                steps_text.append(f"Step {step_order}: {step_desc}\n{command_str}")
                
            return "\n\n".join(steps_text)
        except Exception as e:
            return f"Error formatting steps: {str(e)}"

    def get_container_recommendations(self) -> ContainerRecommendations:
        """Get container recommendations."""
        try:
            # Use our combined_recommendations method which already exists
            return self.get_combined_recommendations()
        except Exception as e:
            console.print(f"[red]Error getting container recommendations: {str(e)}[/red]")
            # Return a fallback recommendation
            fallback_recommendations = self._get_fallback_recommendations_object()
            return fallback_recommendations

def validate_installation(workspace_path: str) -> Dict[str, Any]:
    """Main validation function."""
    try:
        agent = ContainerValidationAgent(workspace_path)
        agent.ensure_workspace()
        
        outputs_path = os.path.join(workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
            console.print(f"[yellow]Created outputs directory: {outputs_path}[/yellow]")
        
        console.print("[blue]Loading analysis files...[/blue]")
        try:
            agent.analysis_files = agent.load_analysis_files()
        except FileNotFoundError as e:
            console.print(f"[red]{str(e)}[/red]")
            console.print("[yellow]Have you run the analyze_agt.py script first?[/yellow]")
            return {
                "status": "error",
                "error": str(e)
            }
        
        console.print("[blue]Getting container recommendations...[/blue]")
        recommendations = agent.get_container_recommendations()
        
        # Ensure recommendations is a ContainerRecommendations object
        if not isinstance(recommendations, ContainerRecommendations):
            console.print("[yellow]Warning: Invalid recommendations format, using fallback[/yellow]")
            recommendations = agent._get_fallback_recommendations_object()
        
        recommendations_path = os.path.join(outputs_path, "write_recommendations.json")
        try:
            # Create a summarized version with just 3 key best practices
            if hasattr(recommendations, 'model_dump'):
                full_data = recommendations.model_dump()
            else:
                full_data = {
                    "container_type": getattr(recommendations, "container_type", "docker"),
                    "installation_type": getattr(recommendations, "installation_type", "pip"),
                    "project_type": getattr(recommendations, "project_type", "python"),
                    "repository": getattr(recommendations, "repository", os.path.basename(workspace_path)),
                    "guidelines": getattr(recommendations, "guidelines", ""),
                    "best_practices": []
                }
            
            # Create a summarized version with at most 3 best practices
            summarized_data = {
                "container_type": full_data.get("container_type", "docker"),
                "installation_type": full_data.get("installation_type", "pip"),
                "project_type": full_data.get("project_type", "python"),
                "repository": full_data.get("repository", os.path.basename(workspace_path)),
                "summary": "Container setup recommendations based on analysis",
                "best_practices": []
            }
            
            # Get up to 3 best practices (prioritizing container ones first)
            all_practices = full_data.get("best_practices", [])
            
            # First get container-specific practices
            container_practices = [p for p in all_practices 
                                   if isinstance(p, dict) and p.get("category") == "container"]
            if not container_practices:
                container_practices = [p for p in all_practices if isinstance(p, dict)]
            
            # Take up to 3 practices
            selected_practices = container_practices[:3]
            
            # If we have fewer than 3, add some script practices
            if len(selected_practices) < 3:
                script_practices = [p for p in all_practices 
                                   if isinstance(p, dict) and p.get("category") == "script"]
                selected_practices.extend(script_practices[:3-len(selected_practices)])
            
            # Still need more? Just take the first ones from the full list
            if len(selected_practices) < 3 and all_practices:
                remaining_count = 3 - len(selected_practices)
                for i in range(min(remaining_count, len(all_practices))):
                    if all_practices[i] not in selected_practices:
                        selected_practices.append(all_practices[i])
            
            summarized_data["best_practices"] = selected_practices
            
            # Write the summarized data to file
            with open(recommendations_path, 'w') as f:
                json.dump(summarized_data, f, indent=2)
            console.print(f"[green]Saved recommendations summary to {recommendations_path}[/green]")
        except Exception as save_error:
            console.print(f"[red]Error saving recommendations: {str(save_error)}[/red]")
            console.print(f"[red]{traceback.format_exc()}[/red]")
        
        # Display full recommendations
        try:
            if hasattr(recommendations, 'model_dump'):
                agent._display_recommendations(recommendations.model_dump())
            else:
                agent._display_recommendations({
                    "container_type": getattr(recommendations, "container_type", "docker"),
                    "installation_type": getattr(recommendations, "installation_type", "pip"),
                    "project_type": getattr(recommendations, "project_type", "python"),
                    "best_practices": []
                })
        except Exception as display_error:
            console.print(f"[red]Error displaying recommendations: {str(display_error)}[/red]")
        
        console.print("[blue]Container file generation is now handled by generate_agt.py[/blue]")
        
        return {
            "status": "success",
            "container_type": getattr(recommendations, "container_type", "docker"),
            "files_generated": [
                os.path.join("outputs", "write_recommendations.json")
            ]
        }
        
    except Exception as e:
        console.print(f"[red]Validation error: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    try:
        # Check for environment file
        if not os.path.exists("config/.env"):
            console.print("[red]Error: config/.env file not found[/red]")
            console.print("Please create config/.env file with your GROQ_API_KEY")
            sys.exit(1)
            
        # Get base experimental workspace path
        experimental_workspace = os.path.abspath(os.path.join(
            Path(__file__).parent.parent,
            "experimental_workspace"
        ))

        # Find all directories in experimental_workspace
        project_name = None
        if os.path.exists(experimental_workspace):
            # Get list of directories (excluding files)
            project_dirs = [d for d in os.listdir(experimental_workspace) 
                          if os.path.isdir(os.path.join(experimental_workspace, d))]
            
            if project_dirs:
                # If multiple projects exist, use the most recently modified one
                project_name = max(project_dirs, 
                                  key=lambda d: os.path.getmtime(os.path.join(experimental_workspace, d)))
                console.print(f"[green]Using most recent project: {project_name}[/green]")
                
                # Check if it has a metadata file to confirm it's a valid project
                metadata_path = os.path.join(experimental_workspace, project_name, "project_meta_data.json")
                if os.path.exists(metadata_path):
                    console.print(f"[green]Found project metadata for {project_name}[/green]")
                    
                    # Optionally read project details from metadata
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            console.print(f"[blue]Project GitHub URL: {metadata.get('github_url', 'Not specified')}[/blue]")
                    except:
                        console.print("[yellow]Could not read project metadata[/yellow]")
                else:
                    console.print("[yellow]No project metadata found, but continuing with most recent folder[/yellow]")
            else:
                console.print("[red]No project directories found in experimental_workspace[/red]")
                sys.exit(1)
        else:
            console.print(f"[red]Error: Experimental workspace not found at {experimental_workspace}[/red]")
            sys.exit(1)
            
        # Get absolute path to the selected project
        workspace_path = os.path.abspath(os.path.join(experimental_workspace, project_name))
        
        # Ensure outputs directory exists
        outputs_path = os.path.join(workspace_path, "outputs")
        if not os.path.exists(outputs_path):
            os.makedirs(outputs_path)
            console.print(f"[yellow]Created outputs directory: {outputs_path}[/yellow]")
        
        # Run validation
        console.print(f"[blue]Validating installation for project: {project_name}[/blue]")
        results = validate_installation(workspace_path)
        
        if results["status"] == "success":
            console.print("[green]Validation completed successfully![/green]")
            console.print(Panel(
                "\n".join(f"- {file}" for file in results["files_generated"]),
                title="Generated Files"
            ))
            console.print("\n[blue]To generate container files, run:[/blue]")
            console.print("[green]python agents/generate_agt.py[/green]")
        else:
            console.print(f"[red]Validation failed: {results.get('error', 'Unknown error')}[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        sys.exit(1)