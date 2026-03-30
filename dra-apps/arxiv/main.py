#!/usr/bin/env python
"""
Deep Orchestrator ArXiv Research Application

This application demonstrates the Deep Orchestrator (AdaptiveOrchestrator) for research of ArXiv papers with:
- Dynamic agent creation and caching
- Knowledge extraction and accumulation
- Budget tracking (tokens, cost, time)
- Task queue management with dependencies
- Policy-driven execution control
- Full state visibility throughout execution
"""

import asyncio
import re
from pathlib import Path
from dra.core.common.observer import Observer
from dra.core.common.tasks import BaseTask, GenerateTask, AgentTask
from dra.core.common.utils.io import UserPrompts
from dra.core.common.utils.main import ParserUtil, Runner
from dra.core.common.utils.paths import resolve_path, resolve_and_require_path
from dra.core.common.variables import Variable

def get_server_list() -> list[str]:
    """Define the list of tools and services to use for this app."""
    return [
        "fetch",
        "filesystem",
        "arxiv-mcp",
        "docling",
    ]

def get_extra_observers() -> dict[str, Observer]:
    """
    Define any "extra" observers you want, e.g., for additional logging or tracing.
    To avoid subtle bugs, it is disallowed to add a new observer with the same key
    as an existing observer. Hence, the `Runner` object used below will verify
    there are no "key collisions".
    """
    return {} # none by default

class ArXivParserUtil(ParserUtil):
    def __init__(self, which_app: str, app_name: str, ux_title: str, description: str):
        super().__init__(which_app, app_name, ux_title, description)

    def _do_prompt_for_missing_args(self, up: UserPrompts) -> dict[str, any]:
        """Prompt the user for the query, if necessary."""
        query = self.args.query
        if not query or not query.strip():
            query = up.read_multi_line_input("Input the query for your research")
        
        categories = self.args.categories
        if not categories or not categories.strip():
            categories = up.read_one_line_input("Input any comma-separated ArXiv categories (https://arxiv.org/category_taxonomy), if any, to focus on",
                empty_allowed=True)
        return {
            'query': query,
            'categories': categories,
        }


def define_cli_arguments() -> ParserUtil:
    """
    Start by defining default values for our custom CLI arguments, 
    followed by the names, UX title, etc. for this app.

    Returns:
        ParserUtil:        A utility that handles CLI arguments and common processing steps for them.
    """

    def_arxiv_research_agent_prompt_file = "arxiv_research_agent.md"
    
    which_app   = "arxiv"
    app_name    = "arxiv_deep_research"
    ux_title    = "ArXiv Deep Research Agent"
    description = "ArXiv Deep Research using orchestrated AI agents"
    parser_util = ArXivParserUtil(which_app, app_name, ux_title, description)

    # Define the CLI arguments. It is best to put required arguments first.

    parser_util.parser.add_argument(
        "-q", "--query",
        help=f"A quoted string with your research query. If not provided on the command line, you will be prompted for it."
    )
    parser_util.parser.add_argument(
        "--categories",
        help=f"Optional, comma-separated ArXiv categories (see https://arxiv.org/category_taxonomy). Spaces are allowed within the list."
    )
    parser_util.add_arg_markdown_report_path()
    parser_util.add_arg_markdown_research_report_title()
    parser_util.add_arg_output_dir()
    parser_util.add_arg_templates_dir()
    parser_util.parser.add_argument(
        "--arxiv-research-prompt-path",
        default=def_arxiv_research_agent_prompt_file,
        help=f"Path where the main research agent prompt file is located. (Default: {def_arxiv_research_agent_prompt_file}) {parser_util.read_relative_from('templates-dir')}"
    )
    parser_util.add_arg_markdown_yaml_header_template_path()
    parser_util.add_arg_research_model()
    parser_util.add_arg_provider()
    parser_util.add_arg_mcp_agent_config_path()
    parser_util.add_arg_temperature()
    parser_util.add_arg_max_iterations()
    parser_util.add_arg_max_tokens()
    parser_util.add_arg_max_cost_dollars()
    parser_util.add_arg_max_time_minutes()
    parser_util.add_arg_short_run()
    parser_util.add_arg_verbose()
    
    return parser_util

def process_cli_arguments(parser_util: ParserUtil):
    """
    Process the actual supplied arguments, resolve the common input and output paths
    like for `--markdown-report` and `--markdown-yaml-header`, etc. (See the discussion
    in the project README.md.)
    """

    parser_util.process_args()

    # Custom paths for this app.
    # For example, the help for this option (and most output options) tells the user
    # that if the argument doesn't have a path prefix, we will write to the location
    # specified by `--output-dir`. We call `resolve_path` to handle this. (This is done
    # for you in `parser_util.process_args()` for common arguments like `--markdown-report`
    # Obviously an 
    # output file isn't expected to exist yet, so `resolve_and_require_path` isn't called!
    
    output_dir_path = parser_util.processed_args['output_dir_path']    
    templates_dir_path = parser_util.processed_args['templates_dir_path']
    # This must exist:
    arxiv_research_prompt_path = resolve_and_require_path(
        parser_util.args.arxiv_research_prompt_path, templates_dir_path)

    parser_util.processed_args['arxiv_research_prompt_path'] = \
        arxiv_research_prompt_path

def create_variables(parser_util: ParserUtil) -> dict[str, Variable]:
    """
    The variables dict contains values used throughout the app, including labels 
    for display purposes and a format feature for rendering the values as plain text,
    Markdown-appropriate (e.g., `foo` for code), etc. The returned `Variable` dictionary
    is used more or less like typical Python function `**kvs`.
    Because the variables are also used for display purposes, we declare them somewhat in
    the order of most interest to the user, starting with application-specific definitions.

    Args:
        parser_util (ParserUtil):  A utility that handles CLI arguments and common processing steps for them.

    Return:
        dict[str, Variable]:       A dictionary of `Variable`s used throughout the app.
    """
    # The variables dict contains values used by the app components, labels 
    # for display purposes and a format for knowing how to render the value.
    # Start with definitions we want to see at the top:
    variables_list = [
        Variable("start_time",    parser_util.processed_args['start_time']),
        Variable("query",         parser_util.processed_args['query'], kind='str'),
        Variable("categories",      parser_util.processed_args['categories'], kind='str'),
        Variable("research_report_title",  parser_util.processed_args['research_report_title'], kind='str'),
    ]
    # Add common values across apps:
    variables_list.extend(parser_util.common_variables())
    
    # Finish with the remaining custom variables for this app and "verbose" variables:
    variables_list.extend([
        Variable("arxiv_research_prompt_path", parser_util.processed_args["arxiv_research_prompt_path"], kind='file'),
    ])
    variables_list.extend(parser_util.only_verbose_common_vars())

    return dict([(v.key, v) for v in variables_list])

def make_tasks(parser_util: ParserUtil, variables: dict[str, Variable]) -> list[BaseTask]:
    """
    Create the tasks for this research agent. All applications will start with a 
    `GenerateTask` to drive the `mcp-agent` "Deep Orchestrator" that invokes the tools
    and MCP services (discussed below) to do the basic research, aggregate the results 
    and generate a report at the end.
    Additional `AgentTask`s and `GenerateTask`s might be used for additional processing.
    In the finance app, an `AgentTask` is used to generate an Excel spreadsheet with the 
    results.

    Args:
        parser_util (ParserUtil):         A utility that handles CLI arguments and common processing steps for them.
        variables (dict[str, Variable]):  A dictionary of `Variable`s used throughout the app.

    Return:
        list[BaseTask]:                   A list of the tasks to do.
    """

    tasks = [
        GenerateTask(
            name="arxiv_research",
            title="📊 ArXiv Research Result",
            model_name=parser_util.args.research_model,
            prompt_template_path=variables['arxiv_research_prompt_path'].value,
            output_dir_path=variables['output_dir_path'].value,
            properties=variables),
    ]
    return tasks

if __name__ == "__main__":
    parser_util = define_cli_arguments()
    process_cli_arguments(parser_util)
    variables = create_variables(parser_util)
    tasks = make_tasks(parser_util, variables)
    runner = Runner(
        tasks, get_server_list(), get_extra_observers(), parser_util, variables)
    asyncio.run(runner.run())
