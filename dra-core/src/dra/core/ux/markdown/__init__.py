"""
The Markdown-formatted streaming output version of Deep Orchestrator Research Example
"""
# Allow types to self-reference during their definitions.
from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import cast, no_type_check, Any, Generic, Optional

from mcp_agent.workflows.deep_orchestrator.orchestrator import DeepOrchestrator
from openai.types.chat import ChatCompletionMessage
from anthropic.types import Message

from dra.core.common.observer import Observer
from dra.core.common.deep_research import DeepResearch
from dra.core.common.tasks import BaseTask, GenerateTask, AgentTask, TaskStatus
from dra.core.common.utils.strings import MarkdownUtil, clean_json_string, replace_variables
from dra.core.common.variables import Variable, VariableFormat

from dra.core.ux.markdown.elements import (
    MarkdownElement,
    MarkdownSection,
    MarkdownTable,
    MarkdownTree)

class MarkdownDeepOrchestratorMonitor():
    """Markdown-based monitor to expose all internal state of the Deep Orchestrator."""
    # TODO: Merge with MarkdownObserver

    def __init__(self, orchestrator: Optional[DeepOrchestrator]):
        self.orchestrator = orchestrator
        self.start_time = time.time()
        self.execution_time = self.start_time - self.start_time

    def get_budget_table(self) -> MarkdownTable:
        """Get budget status as a Markdown Table"""
        table = MarkdownTable(title="💰 Budget")
        table.add_columns_with_justifications([
            ("Resource", 'left'),
            ("Used",     'right'),
            ("Limit",    'right'),
            ("Usage %",  'right'),
        ])

        if not self.orchestrator:
            table.add_row([
                "No Data!", "No Data!", "No Data!", "No Data!",])
        else:            
            budget = self.orchestrator.budget
            usage = budget.get_usage_pct()
            budget.get_remaining()

            # Tokens
            table.add_row([
                "Tokens",
                f"{budget.tokens_used:,}",
                f"{budget.max_tokens:,}",
                f"{usage['tokens']:.1%}",
            ])

            # Cost
            table.add_row([
                "Cost",
                f"${budget.cost_incurred:.3f}",
                f"${budget.max_cost:.2f}",
                f"{usage['cost']:.1%}",
            ])

            # Time
            elapsed = datetime.now(budget.start_time.tzinfo) - budget.start_time
            elapsed_minutes = elapsed.total_seconds() / 60
            table.add_row([
                "Time",
                f"{elapsed_minutes:.1f} min",
                f"{budget.max_time_minutes} min",
                f"{usage['time']:.1%}",
            ])

        return table

    def get_queue_tree(self) -> MarkdownTree:
        """Get task queue as a Markdown Tree"""
        tree = MarkdownTree(label = "📋 Task Queue")
        
        if not self.orchestrator:
            tree.add("❌ No data!")
        else:
            queue = self.orchestrator.queue
            # Completed steps
            if queue.completed_steps:
                completed = tree.add("✅ Completed Steps")
                for step in queue.completed_steps[-2:]:  # Last 2 steps only
                    step_node = completed.add(f"{step.description[:60]}...")
                    # Show first 3 tasks if many, otherwise all
                    tasks_to_show = step.tasks[:3] if len(step.tasks) > 3 else step.tasks
                    for task in tasks_to_show:
                        if task.status == "completed":
                            icon = "✓"
                        elif task.status == "failed":
                            icon = "✗"
                        else:
                            icon = "•"
                        step_node.add(f"{task.description[:40]}...")
                    if len(step.tasks) > 3:
                        step_node.add(f"... +{len(step.tasks) - 3} more tasks")

            # Current/Active step - prioritize showing active and failed tasks
            current_step = queue.get_next_step()
            if current_step:
                active = tree.add("▶ Active Step")
                active_node = active.add(f"{current_step.description[:60]}...")

                # Sort tasks to prioritize: in_progress > failed > pending > completed
                def task_priority(task):
                    priorities = {
                        "in_progress": 0,
                        "failed": 1,
                        "pending": 2,
                        "completed": 3,
                    }
                    return priorities.get(task.status, 4)

                sorted_tasks = sorted(current_step.tasks, key=task_priority)
                tasks_to_show = sorted_tasks[:5]  # Show up to 5 for active step

                for task in tasks_to_show:
                    if task.status == "in_progress":
                        icon = "⟳"
                    elif task.status == "failed":
                        icon = "✗"
                    elif task.status == "completed":
                        icon = "✓"
                    else:
                        icon = "•"
                    active_node.add(f"{icon} {task.description[:40]}...")

                # Show remaining count with status breakdown if needed
                remaining = len(current_step.tasks) - len(tasks_to_show)
                if remaining > 0:
                    # Count by status for the remaining tasks
                    status_counts = {}
                    for task in sorted_tasks[4:]:
                        status_counts[task.status] = status_counts.get(task.status, 0) + 1

                    if status_counts:
                        parts = []
                        if status_counts.get("pending", 0) > 0:
                            parts.append(f"{status_counts['pending']} pending")
                        if status_counts.get("completed", 0) > 0:
                            parts.append(f"{status_counts['completed']} done")
                        active_node.add(
                            f"... +{remaining} more ({', '.join(parts)})"
                        )

            # Pending steps (just count)
            if queue.pending_steps:
                _pending = tree.add(f"⏳ {len(queue.pending_steps)} Pending Steps")

            # Failed tasks summary if any
            if queue.failed_task_names:
                failed = tree.add(f"❌ {len(queue.failed_task_names)} Failed Tasks")
                for task_name in list(queue.failed_task_names)[:2]:
                    failed.add(f"{task_name}")

            # Queue summary
            tree.add(f"📊 {queue.get_progress_summary()}")

        return tree

    def get_plan_table(self) -> MarkdownTable:
        """Get the current plan as a Markdown Table"""
        table = MarkdownTable(title="📝 Current Plan")
        table.add_columns(["Step", "Description", "Tasks", "Status"])

        if (
            not hasattr(self.orchestrator, "current_plan")
            or not self.orchestrator.current_plan
        ):
            table.add_row(["-", "No plan created yet", "-", "-"])
            return table

        plan = self.orchestrator.current_plan
        queue = self.orchestrator.queue

        for i, step in enumerate(plan.steps, 1):
            # Determine status
            if step in queue.completed_steps:
                status = "✓ Done"
            elif step == queue.get_next_step():
                status = "→ Active"
            else:
                status = "Pending"

            table.add_row([
                str(i),
                step.description[:60] + "..."
                if len(step.description) > 60 
                else step.description,
                str(len(step.tasks)),
                status,
            ])

        return table

    def get_memory_table(self) -> MarkdownTable:
        """Get memory status as a Markdown table"""
        table = MarkdownTable(title="🧠 Memory",
            columns_with_justifications = [("Quantity", 'left'), ("Value", 'right')])

        if not self.orchestrator:
            artifacts            = "No Data!"
            knowledge_items      = "No Data!"
            task_results         = "No Data!"
            knowledge_categories = "No Data!"
            estimated_tokens     = "No Data!"
        else:
            stats = self.orchestrator.memory.get_stats()
            artifacts            = stats['artifacts']
            knowledge_items      = stats['knowledge_items']
            task_results         = stats['task_results']
            knowledge_categories = stats['knowledge_categories']
            estimated_tokens     = stats['estimated_tokens']

        table.add_row(["Artifacts",       artifacts])
        table.add_row(["Knowledge Items", knowledge_items])
        table.add_row(["Task Results",    task_results])
        table.add_row(["Categories",      knowledge_categories])
        table.add_row(["Est. Tokens",     estimated_tokens])
        return table

    def get_knowledge_table(self) -> MarkdownTable:
        """Get recent knowledge items"""

        table = MarkdownTable(title="🧠 Recent Memory Knowledge (last three...)",
            columns_with_justifications = [("Quantity", 'left'), ("Value", 'right')])

        if not self.orchestrator:
            table.add_row(["No Data!", ""])
        else:
            memory = self.orchestrator.memory
            if memory.knowledge:
                for item in memory.knowledge[-3:]:
                    valstr = str(item.value)
                    valstr400 = valstr[:400]
                    if valstr400 != valstr:
                        valstr400 = valstr400 + "..."
                    table.add_row([item.key[:40], valstr400])
            else:
                table.add_row(["None", ""])

        return table

    def get_agents_table(self) -> MarkdownTable:
        """Get agent cache status as a Markdown Table"""
        table = MarkdownTable(title="🤖 Agent Cache",
            columns_with_justifications = [("Metric", 'left'), ("Value", 'right')])

        if not self.orchestrator:
            cached_agents = "No Data!"
            cache_hits    = "No Data!"
            cache_misses  = "No Data!"
            hit_rate_str  = "No Data!"
            recents       = []
        else:
            cache = self.orchestrator.agent_cache
            cached_agents = str(len(cache.cache))
            cache_hits    = str(cache.hits)
            cache_misses  = str(cache.misses)
            hit_rate_str  = ''
            if cache.hits + cache.misses > 0:
                hit_rate = cache.hits / (cache.hits + cache.misses)
                hit_rate_str = f"{hit_rate:.1%}"

            # Show cached agent names
            recents = []
            if cache.cache:
                agent_names = []
                items = list(cache.cache.items())
                for key, agent in items[:3]:
                    agent_names.append(agent.name)
                if agent_names:
                    recents.append(", ".join(agent_names))

        table.add_row(["Cached Agents", cached_agents])
        table.add_row(["Cache Hits",    cache_hits])
        table.add_row(["Cache Misses",  cache_misses])
        if hit_rate_str:
            table.add_row(["Hit Rate",  hit_rate_str])
        if recents:
            for recent in recents:
                table.add_row(["Recent", recent])

        return table

    def get_policy_table(self) -> MarkdownTable:
        """Get policy engine status as a Markdown section"""
        table = MarkdownTable(title="⚙️ Policy Engine", 
            columns_with_justifications=[('Quantity', 'left'),('Value', 'right')])

        if not self.orchestrator:
            failures        = "No Data!"
            total_successes = "No Data!"
            total_failures  = "No Data!"
            failure_rate    = "No Data!"
        else:
            policy = self.orchestrator.policy
            failures        = policy.consecutive_failures/policy.max_consecutive_failures
            total_successes = policy.total_successes
            total_failures  = policy.total_failures
            failure_rate    = f"{policy.get_failure_rate():.1%}"

        table.add_row(["Consecutive Failures", failures])
        table.add_row(["Total Successes",      total_successes])
        table.add_row(["Total Failures",       total_failures])
        table.add_row(["Failure Rate",         failure_rate])
        return table

    def get_status_summary_table(self) -> MarkdownTable:
        """Get overall status summary as a Markdown table."""
        exec_time = self.update_execution_time()
        table = MarkdownTable(title="📊 Status", 
            columns_with_justifications=[('Quantity', 'left'),('Value', 'right')])

        if not self.orchestrator:
            objective = "No Data!"
            iteration = "No Data!"
            replans   = "No Data!"
            elapsed   = "No Data!"
        else:
            objective = f"{self.orchestrator.objective[:50]}... (see full objective below)"
            iteration = self.orchestrator.iteration/self.orchestrator.config.execution.max_iterations
            replans   = self.orchestrator.replan_count/self.orchestrator.config.execution.max_replans
            elapsed   = exec_time

        table.add_row(["Objective", objective])
        table.add_row(["Iteration", iteration])
        table.add_row(["Replans",   replans])
        table.add_row(["Elapsed",   elapsed])
        return table

    def get_objective_section(self) -> MarkdownSection:
        content = [
            "The _full objective_ abbreviated in the table above is shown next.",
            "\n",
        ]
        if not self.orchestrator:
            content.extend(["\n", "Objective information not available!", "\n"])
        else:
            lines = self.orchestrator.objective.split('\n')
            content.extend([f"> {line}" for line in lines])
            content.extend(["\n", "(End of the objective listing...)"])

        objective = MarkdownSection(title="Full Objective", content=content)
        return objective

    def update_execution_time(self) -> float:
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time
        return self.execution_time

class MarkdownObserver(Observer[DeepResearch]):
    """
    A Markdown "display", which is used to produce a markdown-formatted report
    at the end of execution. No output is generated during execution, unlike 
    RichDisplay, for example. Hence, this could just be an Observer.

    If the user doesn't want a report, don't instantiate this object, as it will use
    a default output path to write the file, if none is defined!

    TODO: The Anthropic message handling needs testing and possibly better handling. 
    We spent a long time experimenting with the OpenAI `ChatCompletionMessages` returned
    to find a (reasonably) good way of displaying the results!
    """

    def __init__(self, 
        title: str,
        yaml_header_template: Optional[Path] = None):
        """Construct a MarkdownObserver object.

        Args:
            title (str): The H1 title at the top of the document.
            yaml_header_template (Path): An optional template for a YAML block that will be printed first. Useful for GitHub Pages display.
        
        Returns:
            MarkdownObserver: An observer of DeepResearch state for rendering Markdown.
        
        Discussion:
            When printing the final report, the following call, the `yaml_header_template`
            file will be read into a `string` and `replace_variables(string, ..., **self.system.variables)`
            will be called to substitute any variables indicated with `{{key}}` entries. The ...
            are for other attributes not in `variables` that will be passed, too.
            See `__repr__()`. This YAML block will be printed first, if the template isn't None
            or the resolved block isn't empty, followed by the hierarchical Markdown sections 
            held in `self.layout`.
            To keep the logic as simple and bug free as possible, we only allow the DeepResearch instance
            to be set once, during lazy initialization, where it is changed from `None` to the 
            real instance.
        """
        super().__init__(disallow_system_change=True)
        self.title = title
        self.yaml_header_template = yaml_header_template

        # Lazy initialize these in `_after_set_system()`.
        # self.monitor: MarkdownDeepOrchestratorMonitor
        # self.research_report_path: Path

    def _after_set_system(self):
        """
        Once the system is set, we finish initializing this object.
        """ 
        if self.system and self.system.logger:
            self.system.logger.info("MarkdownObserver._after_set_system() (self.system not None)")
        if self.system and self.system.orchestrator:
            self.monitor = MarkdownDeepOrchestratorMonitor(self.system.orchestrator)
        else:
            raise ValueError("self.system.orchestrator can't be None!")
            
        output_dir_path = self.__get_var_value('output_dir_path', Path('./output'))
        self.research_report_path = self.__get_var_value('research_report_path',
            output_dir_path / 'research_report.md')

        self.layout = self.__make_layout(self.title)
        
        super()._after_set_system()

    def _do_update(self, 
        other: dict[str,Any] = {},
        is_final: bool = False) -> Any:
        """
        Update the display with the current state. Because the final Markdown report 
        is all we care about, we don't do anything unless `is_final == True`! 
        """
        # self.system.logger.info(f"MarkdownObserver._do_update(is_final={is_final})") 
        
        if not is_final:
            return self.layout

        self.monitor.update_execution_time()
        
        messages  = other.get('messages', '')
        error_msg = other.get('error_msg', '')
        self.__report_results(messages=messages, error_msg=error_msg)

        statistics = self.layout["statistics_section"]
        statistics["queue"].set_intro_content([self.monitor.get_queue_tree()])
        statistics["plan"].set_intro_content([self.monitor.get_plan_table()])
        statistics["memory"].set_intro_content([
            self.monitor.get_memory_table(),
            self.monitor.get_knowledge_table()])
        statistics["budget"].set_intro_content([self.monitor.get_budget_table()])
        statistics["policy"].set_intro_content(
            [self.monitor.get_policy_table(), self.monitor.get_agents_table()])
        statistics["status"].set_intro_content([self.monitor.get_status_summary_table()])

        objective = self.layout["objective_section"]
        objective.set_subsections([self.monitor.get_objective_section()])
        
        self.__update_final_statistics(),
        self.__update_budget_summary(),
        self.__update_knowledge_summary(),
        self.__update_workspace_artifacts(),

        # Save to the report file.
        all_sections = str(self)
        with self.research_report_path.open('w') as file:
            file.write(all_sections)

        return self.layout

    async def _do_async_update(self,
        other: dict[str,Any] = {},
        is_final: bool = False) -> Any:
        if not is_final:
            return None
        return await self.__update_token_usage()

    def __get_var_value(self, key: str, default: Any = None) -> Any:
        if not self.system:
            raise ValueError("Logic error: self.system not yet initialized!")
        variable = self.system.variables.get(key)
        return variable.value if variable else default

    def __parse_json(self, s: str, context: str = '', log_failure: bool = False) -> tuple[str, list[str]]:
        try:
            # Handle an observed problem with returned results; '\\' that will cause json
            # parsing to fail.
            s2 = clean_json_string(s, '')
            obj = json.loads(s2)
            # format as nested bullets:
            mu = MarkdownUtil()
            md_str = mu.to_markdown(obj, bullet='*', indent='\t', key_format='**%s:**')
            return ('', md_str)
        except (JSONDecodeError, TypeError) as err:
            err_msg = f"{err} raised while parsing attempting to parse {context} results."
            if log_failure and self.system and self.system.logger:
                self.system.logger.warning(f"{err_msg}: input = {s}")
            return (err_msg, [])
        except Exception as err:
            err_msg = f"{err} of type {type(err)} raised while parsing attempting to parse {context} results."
            if log_failure and self.system and self.system.logger:
                self.system.logger.warning(f"{err_msg}: input = {s}")
            return (err_msg, [])

    def __make_layout(self, title: str) -> MarkdownSection:
        layout = MarkdownSection(title=title)
        
        # Make a Markdown table of the runtime properties. First wrap the keys in `...`
        # to render as fixed-width/code font.
        top_table = MarkdownTable("This Run's Properties", ['Property', 'Value'])
        vars = list(self.system.variables.values()) if self.system and self.system.variables else []
        formatted = Variable.make_formatted(
                vars,
                variable_format = VariableFormat.MARKDOWN)
        for key, label, value in formatted:
            top_table.add_row([label, value])
        
        layout.add_intro_content([
            "This report begins with some information about this invocation of deep research.",
            "To skip to the results, go to the [**📊 📈 Results**](#results_section) section.",
            top_table
        ])

        # Main structure
        layout.add_subsections_as_dict({
            "results_section": MarkdownSection(title="📊 📈 Results", 
                content=["This section provides the research results.", "In progress..."]),
            "statistics_section": MarkdownSection(title="💰 Runtime Statistics",
                content=["This section provides general information about the runtime statistics."]),
            "objective_section": MarkdownSection(title="⚙️ Research Objective",
                content=["This section provides detailed information about the research _objective_, such as the prompt."]),
        })

        # Top section - queue, plan, memory, budget, and other status
        layout["statistics_section"].add_subsections_as_dict({
            "queue":  MarkdownSection(title="Task Queue"),
            "plan":   MarkdownSection(title="Current Plan"),
            "memory": MarkdownSection(title="Memory"),
            'budget': MarkdownSection(title="Runtime Budget Statistics"),
            'policy': MarkdownSection(title="Policy Engine"),
            'status': MarkdownSection(title="Status Summary"),
        })

        return layout 

    def add_section(self, title: str, 
        content: Sequence[MarkdownElement | str] = [], 
        subsections: Sequence[MarkdownSection] = []) -> MarkdownSection:
        section = MarkdownSection(title=title, content=content, subsections=subsections)
        self.layout.add_subsections([section])
        return section

    def __message_to_rows(self, table: MarkdownTable, fields: dict[str,Any]):
        for key, value in fields.items():
            v = str(value)
            if key == 'content':
                v2 = v if len(v) <= 100 else f"{v[:50]} ... {v[-50:]}"
                lines = v2.split("\n")
                lines2, is_markdown = self.__handle_content(lines)
            table.add_row([key, f"`{'\n'.join(lines2)}`"])

    def __parse_openai_message(self, message_index: int, obj: Any) -> list[Any]:
        # For inference with OpenAI, the results will be a ChatCompletionMessage:

        def make_metadata_table_from_dict(
            ccm: ChatCompletionMessage) -> MarkdownTable:
            table = MarkdownTable(title=f"✉️ OpenAI/Ollama Reply Message #{message_index}: Metadata",
                columns = ['Item', 'Value'])
            self.__message_to_rows(table, ccm.to_dict())
            return table

        sobj = str(obj)
        content: list[Any] = []
        metadata_table: Optional[MarkdownTable] = None

        if isinstance(obj, ChatCompletionMessage):
            ccm: ChatCompletionMessage = cast(ChatCompletionMessage, obj)
            content = []
            if ccm.content:
                content, is_markdown = self.__handle_content(ccm.content.split('\n'))
                if not is_markdown:
                    content = [f"> {line}" for line in content]
            metadata_table = make_metadata_table_from_dict(ccm)

        elif sobj.startswith("ChatCompletion"):
            # Is it a "str(ChatCompletion...)"? Try parsing it with the following
            #  _ugly_ hack to extract just the `content` from the string:
            try:
                s2 = re.sub(r"""ChatCompletion[^=]+\s*=\s*['"]?""", '', sobj)
                s3 = re.sub(r"""['"]?,\s*refusal\s*=.*$""", '', s2)
                content = [f"> {line}" for line in s3.split('\n')]
            except:  # bail out...
                content = [f"> {line}" for line in sobj.split('\n')]
          
        all_content: list[Any] = []
        if content:
            all_content = ['\n', f"✉️ Reply Message #{message_index} Content:", '\n']
            all_content.extend(content)
            all_content.extend(['\n', "(end content)"])
        if metadata_table:
            all_content.append('\n')
            all_content.append(metadata_table)

        return all_content

    def __parse_anthropic_message(self, message_index: int, obj: Any) -> list[Any]:
        sobj = str(obj)
        content: list[Any] = []
        metadata_table: Optional[MarkdownTable] = None

        if isinstance(obj, Message):
            rm: Message = cast(Message, obj)
            metadata_table = MarkdownTable(title=f"✉️ Anthropic Reply Message #{message_index}: Metadata",
                columns_with_justifications = [('Item', 'left'), ('Value', 'right')])
            self.__message_to_rows(metadata_table, rm.to_dict())
        elif sobj.startswith("Message") or sobj.startswith("ResultMessage"):
            # Try parsing it with the following _ugly_ hack to extract just the
            # `content` from the string:
            try:
                s2 = re.sub(r"""(Result)?Message\([^=]+)\s*=\s*['"]""", '', sobj)
                s3 = re.sub(r"""^.*\s*result=(.*)""", 'result:\n', s2)
                s4 = re.sub('structured_output=', '\nstructured_output:\n', s3)
                content = s4.split('\n')
            except:  # bail out...
                content = str(sobj).split('\n')

        all_content: list[Any] = []
        if content:
            all_content = ['\n', f"**Reply Message #{message_index} Result:**", '\n']
            all_content.extend(content)
            all_content.extend(['\n', "(end content)"])
        if metadata_table:
            all_content.append('\n')
            all_content.append(metadata_table)

        return all_content

    def __handle_content(self, content: list[Any]) -> tuple[list[str], bool]:
        """
        What we hope is that the content returned by messages is Markdown, 
        e.g., "[```markdown", "...", "```"]. If so, we remove the leading and
        trailing "delimiter" lines and return a new list with the `bool` flag `True`,
        meaning Markdown was found. Otherwise, the list is return unchanged along 
        with the `bool` flag `False`.
        """
        result = []
        is_md = False
        try:
            for line in content:
                if re.match(r'^\s*```(markdown|md)\s*$', line):
                    is_md = True
                elif not re.match(r'^\s*```\s*$', '', line):
                    result.append(line)
        except:
            if self.system and self.system.logger:
                self.system.logger.error("Parsing out markdown failed! {content}") 
            result = content
            is_md = False
        return result, is_md


    def __make_task_results_section(self, task_number: int, task: BaseTask) -> MarkdownSection:
        task_table = MarkdownTable(
            title=f'Task {task.title} (`{task.name}`) Properties',
            columns=['Property', 'Value'])
        # We don't pass any exclusions...
        for key, value in task.attributes_as_strs(variable_format = VariableFormat.MARKDOWN).items():
            if value:
                task_table.add_row([key, value])

        result_section = MarkdownSection(title=f"Task #{task_number}: {task.title} (`{task.name}`)", 
            content=[f"Information for task: {task.name}", task_table])
        
        if not task.result:
            error_str = f"> **NOTE:** No {task.name} results! See the log file for details."
            result_section.add_intro_content([error_str])
            return result_section

        subsections: list[MarkdownSection] = []
        for i in range(len(task.result)):
            result = task.result[i]
            content = self.__parse_openai_message(i+1, result)
            if not content:
                content = self.__parse_anthropic_message(i+1, result)
                if not content:
                    # Try parsing as JSON, although it probably isn't JSON...
                    (err_msg, content) = self.__parse_json(str(result))
                    if not content: # not JSON, so just split the text.
                        content = str(result).split('\n')

            ss = MarkdownSection(title=f"✉️ Reply Message #{i+1}", content=content)
            subsections.append(ss)

        result_section.add_subsections(subsections)
        return result_section

    # TODO: Figure out how to fix the warnings on self.system.orchestrator
    @no_type_check
    def __report_results(self, messages: list[str] = [], error_msg: str = ''):
        output_dir_path_msg = ''
        odp = self.__get_var_value('output_dir_path', None)
        if odp:
            output_dir_path_msg = f"output files under `{odp}` and "

        content = [
            "> **NOTE:**", 
            "> \n",
            f"> Finished! See {output_dir_path_msg}log files under `./logs`.",
        ]
        if messages:
            content.append("> \n")
            content.extend([f"> {line}" for line in messages])
        content.append("\n")
        if error_msg:
            content.extend(["> **ERROR:**", "\n"])
            content.append(f"> {error_msg}")
        content.append("\n")
        
        results_section = self.layout["results_section"]
        results_section.set_intro_content(content=content)
        
        results_subsections = []
        for i in range(len(self.system.tasks)):
            task = self.system.tasks[i]
            s = self.__make_task_results_section(i+1, task)
            results_subsections.append(s)

        results_section.add_subsections(results_subsections)

    # TODO: Figure out how to fix the warnings on self.system.orchestrator
    @no_type_check
    def __update_final_statistics(self) -> MarkdownSection:
        """Update the final statistics for display"""

        # Create summary table
        summary_table = MarkdownTable(title="Execution Summary", 
            columns = [("Metric", "left"), ("Value", "right")])
        
        summary_table.add_row(["Total Time", f"{self.monitor.update_execution_time()}"])
        summary_table.add_row(["Iterations", str(self.system.orchestrator.iteration)])
        summary_table.add_row(["Replans", str(self.system.orchestrator.replan_count)])
        summary_table.add_row(
            ["Tasks Completed", str(len(self.system.orchestrator.queue.completed_task_names))]
        )
        summary_table.add_row(
            ["Tasks Failed", str(len(self.system.orchestrator.queue.failed_task_names))]
        )
        summary_table.add_row(
            ["Knowledge Items", str(len(self.system.orchestrator.memory.knowledge))]
        )
        summary_table.add_row(
            ["Artifacts Created", str(len(self.system.orchestrator.memory.artifacts))]
        )
        summary_table.add_row(
            ["Agents Cached", str(len(self.system.orchestrator.agent_cache.cache))]
        )
        summary_table.add_row(
            ["Cache Hit Rate",
            f"{self.system.orchestrator.agent_cache.hits / max(1, self.system.orchestrator.agent_cache.hits + self.system.orchestrator.agent_cache.misses):.1%}"]
        )
        return self.add_section("📊 Final Statistics", [summary_table])

    # TODO: Figure out how to fix the warnings on self.system.orchestrator
    @no_type_check
    def __update_budget_summary(self) -> MarkdownSection:
        """Update the budget summary (where applicable)."""
        budget_summary = self.system.orchestrator.budget.get_status_summary()
        return self.add_section("💶 Budget Summary", [budget_summary])

    # TODO: Figure out how to fix the warnings on self.system.orchestrator
    @no_type_check
    def __update_knowledge_summary(self) -> MarkdownSection:
        """Update knowledge learned."""
        knowledge_table = 'None available...'
        if self.system.orchestrator.memory.knowledge:
            knowledge_table = MarkdownTable(title='', columns = [
                "Category",
                "Key",
                "Value",
                "Confidence",
            ])
            for item in self.system.orchestrator.memory.knowledge[:10]:  # Show first 10
                key = item.key[:30] + "..." if len(item.key) > 30 else item.key
                valstr = str(item.value)
                value = valstr[:50] + "..." if len(valstr) > 50 else valstr
                knowledge_table.add_row([
                    item.category,
                    key,
                    value,
                    f"{item.confidence:.2f}",
                ])
            if len(self.system.orchestrator.memory.knowledge) > 10:
                knowledge_table.add_row(['...', '...', '...', '...'])


        return self.add_section("🧠 Knowledge Extracted", [knowledge_table])

    async def __update_token_usage(self) -> MarkdownSection:
        """Update the token usage, if available."""
        summary_info = ["Token usage not available"]
        if self.system and self.system.token_counter:
            summary = await self.system.token_counter.get_summary()
            if summary and hasattr(summary, "usage"):
                summary_info = [f"* Total Tokens: {summary.usage.total_tokens}"]
                if hasattr(summary, "cost"):
                    summary_info.append(f"* Total Cost: ${summary.cost:.4f}")
        return self.add_section("🪙 Total Tokens", summary_info)

    # TODO: Figure out how to fix the warnings on self.system.orchestrator
    @no_type_check
    def __update_workspace_artifacts(self) -> MarkdownSection:
        """Update workspace artifacts if any were created."""
        artifacts_info = ["Workspace artifacts usage not available"]
        if self.system.orchestrator.memory.artifacts:
            artifacts_info = []
            keys = list(self.system.orchestrator.memory.artifacts.keys())
            for name in keys[:5]:
                artifacts_info.append(f"* {name}")
            if len(keys) > 5:
                artifacts_info.append(f"* ...")

        return self.add_section("📁 Artifacts Created", artifacts_info)

    def __repr__(self) -> str:
        yaml_header_str = ''
        if self.yaml_header_template:
            with self.yaml_header_template.open('r') as file: 
                template_str = file.read()
            if template_str:
                vars = self.system.variables if self.system and self.system.variables else {}
                yaml_header_str = replace_variables(template_str, 
                    vars,
                    title=self.title)
        return f"{yaml_header_str}\n{self.layout}"
