# AutoINSTALL: Automatize Install Software

## Idea
- equip our Assistant with tools to extract this information from the project directly.
- Instead of asking the user, an assistant can ask for a tool instead.

## Workflow

Interplay between the *Assistants* and the *Tool* agents

### Assistants (personas)
In this workflow we are giving 4 different personas (and prompts templates) to the AI model:
- An **AI Planner**.
- An **AI Researcher**.
- An **AI Writer**.
- An **AI Validator**.

The workflow starts by cloning the given project and generating a list of all files (except the ones inside the .git folder).


### Tools
In addition to these new prompts, we will also supply the LLM with two function definitions. There are 4 tool usages in this project:
- `analyse_project_tool`:
- `write_files_tool`:
- `search_tool`: searchers a given query on google 
<!-- - reddit_scrapper: Scrapes a given subreddit for a number of posts.
- search_tool: Searches a given query on Google.
- scrape_tool: Scrapes a given webpage.
- reddit_commenter: Comments given Reddit post. -->

## Features
- No cost API usage.
- Leverage of Meta's Llama 3.3 70B model.
- Automatization of reddit commenting.
