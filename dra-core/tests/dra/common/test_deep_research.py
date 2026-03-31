# Unit tests for the "deep research" module using Hypothesis for property-based testing.
# https://hypothesis.readthedocs.io/en/latest/

import os, re, shutil, sys, unittest
from hypothesis import given, strategies as st
from pathlib import Path
from typing import Any, Awaitable, Optional

from dra.core.common.deep_research import DeepResearch
from dra.core.common.observer import Observer, Observers
from dra.core.common.tasks import BaseTask, GenerateTask
from dra.core.common.variables import Variable
from dra.core.ux.display import Display
from mcp_agent.workflows.deep_orchestrator.config import DeepOrchestratorConfig

output_dir = './tests/output/META'
output_dir_path = Path(output_dir)

class TestObserver(Observer[DeepResearch]):

    def __init__(self, disallow_system_change: bool=False):
        super().__init__(disallow_system_change=disallow_system_change)
        self.updates: list[dict[str,Any]] = []

    def _do_update(self, 
        other: dict[str,Any] = {},
        is_final: bool = False) -> Any:
        self.updates.append({
            'system':   self.system,
            'other':    other,
            'is_final': is_final,
            'is_async': False,
            'response': response,
            })
        return self.updates

    async def _do_async_update(self,
        other: dict[str,Any] = {},
        is_final: bool = False) -> Any:
        self.updates.append({
            'system':   self.system,
            'other':    other,
            'is_final': is_final,
            'is_async': True,
            'response': response,
            })
        return self.updates

    def __repl__(self) -> str:
        return f"TestObserver(updates={self.updates})"

class TestDeepResearch(unittest.TestCase):
    """
    Test DeepResearch. TODO!!
    """

    class TestDisplay(Display):
        def __init__(self, title: str = "TestDisplay", disallow_system_change: bool=False):
            super().__init__(title = title, disallow_system_change=disallow_system_change)
        async def run_live(self, function: Awaitable[None]) -> None:
            await function

    @classmethod
    def setUpClass(cls):
        os.makedirs(output_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(output_dir)

    @classmethod
    def make_test_config(cls) -> DeepOrchestratorConfig:
        return DeepResearch.make_default_config(
            short_run = True,
            name = "TestDeepResearchConfig",
            available_servers = [],
            variables = {})

    @classmethod
    def make_test_variables(cls) -> dict[str, Variable]:
        vars = {
            'research_model':        'gpt-oss:20b',
            'output_dir_path':       Path('tests/output'),
            'max_iterations':        25,
            'max_replans':           2,
            'max_task_retries':      5,
            'enable_parallel':       True,
            'enable_filesystem':     True,
            'max_tokens':            100000,
            'max_cost_dollars':      1.00,
            'max_time_minutes':      10,
            'verbose':               True,
            'research_prompt_path':  Path('tests/templates/research_agent.md'),
            'mcp_agent_config_path': Path('tests/config'),
            'update_iteration_frequency_secs': 0.5,
            }
        return dict({(key, Variable(key,value)) for key, value in vars.items()})


    def make(self,
        app_name: str = 'DeepResearchTest',
        provider: str = 'ollama',
        config: Optional[DeepOrchestratorConfig] = None,
        tasks: list[BaseTask] = [],
        display: Optional[Display] = TestDisplay(),
        observers: Optional[Observers] = None,
        variables: dict[str, Variable] = {}):
        if not config:
            config = TestDeepResearch.make_test_config()
        if not display: 
            display = TestDisplay()
        if not observers:
            observers = Observers(TestObserver())
        if not variables:
            variables = TestDeepResearch.make_test_variables()
        return DeepResearch(
            app_name = app_name,
            provider = provider,
            config = config,
            tasks = tasks,
            display = display,
            observers = observers,
            variables = variables)

    def test_DeepResearch_init(self):
        config = TestDeepResearch.make_test_config()
        variables = TestDeepResearch.make_test_variables()
        observers = Observers(TestObserver())
        tasks = [
            GenerateTask(
                name="smart_research",
                title="Smart Research",
                model_name=variables.get('research_model').value,
                prompt_template_path=variables.get('research_prompt_path').value,
                output_dir_path=variables.get('output_dir_path').value,
                properties=variables),
        ]
        dr = self.make(
            config = config,
            variables = variables,
            observers = observers,
            tasks = tasks)
        self.assertEqual(config,    dr.config)
        self.assertEqual(tasks,     dr.tasks)
        self.assertEqual(observers, dr.observers)
        self.assertEqual(variables, dr.variables)

if __name__ == "__main__":
    unittest.main()