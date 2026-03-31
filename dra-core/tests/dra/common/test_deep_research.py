# Unit tests for the "deep research" module using Hypothesis for property-based testing.
# https://hypothesis.readthedocs.io/en/latest/

import os, re, shutil, sys, unittest
from hypothesis import given, strategies as st
from pathlib import Path
from typing import Any, Awaitable, Optional, Sequence

from dra.core.common.deep_research import DeepResearch
from dra.core.common.observer import Observer, Observers
from dra.core.common.tasks import BaseTask, GenerateTask
from dra.core.common.variables import Variable
from dra.core.ux.display import Display
from mcp_agent.workflows.deep_orchestrator.config import DeepOrchestratorConfig

output_dir = './tests/output/META'
output_dir_path = Path(output_dir)

class TestDisplay(Display):
    def __init__(self, title: str = "TestDisplay", disallow_system_change: bool=False):
        super().__init__(title = title, disallow_system_change=disallow_system_change)
    async def run_live(self, function: Awaitable[None]) -> None:
        await function

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
            'other':    other,
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
            'other':    other,
            })
        return self.updates

    def __repl__(self) -> str:
        return f"TestObserver(updates={self.updates})"

def_app_name: str = 'DeepResearchTest'
def_provider: str = 'ollama'
def_model_name: str = 'gpt-oss:20b'
def_prompt_template_path: Path = Path('tests/templates/research_agent.md')
def_output_dir_path: Path = Path('tests/output')
def_observers: Observers = Observers(dict({'test-observer':TestObserver()}))

def make_test_variables() -> dict[str, Variable]:
    vars = {
        'research_model':        def_model_name,
        'output_dir_path':       def_output_dir_path,
        'max_iterations':        25,
        'max_replans':           2,
        'max_task_retries':      5,
        'enable_parallel':       True,
        'enable_filesystem':     True,
        'max_tokens':            100000,
        'max_cost_dollars':      1.00,
        'max_time_minutes':      10,
        'verbose':               True,
        'research_prompt_path':  def_prompt_template_path,
        'mcp_agent_config_path': Path('tests/config'),
        'update_iteration_frequency_secs': 0.5,
        }
    return dict({(key, Variable(key,value)) for key, value in vars.items()})

def_variables: dict[str,Variable] = make_test_variables()
def_config: DeepOrchestratorConfig = DeepResearch.make_default_config(
    short_run = True,
    name = "TestDeepResearchConfig",
    available_servers = [],
    variables = def_variables)

def_tasks: Sequence[BaseTask] = [
    GenerateTask(
        name = "smart_research",
        title = "Smart Research",
        model_name = def_model_name,
        prompt_template_path = def_prompt_template_path,
        output_dir_path = def_output_dir_path,
        properties = def_variables),
]


class TestDeepResearch(unittest.TestCase):
    """
    Test DeepResearch. TODO!!
    """

    @classmethod
    def setUpClass(cls):
        os.makedirs(output_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(output_dir)
    @classmethod
    def make(cls,
        app_name: str = def_app_name,
        provider: str = def_provider,
        config: DeepOrchestratorConfig = def_config,
        tasks: Sequence[BaseTask] = def_tasks,
        display: Display = TestDisplay(),
        observers: Observers = def_observers,
        variables: dict[str, Variable] = def_variables):
        return DeepResearch(
            app_name = app_name,
            provider = provider,
            config = config,
            tasks = tasks,
            display = display,
            observers = observers,
            variables = variables)

    def test_DeepResearch_init(self):
        dr = TestDeepResearch.make()
        self.assertEqual(def_config,    dr.config)
        self.assertEqual(def_tasks,     dr.tasks)
        self.assertEqual(def_observers, dr.observers)
        self.assertEqual(def_variables, dr.variables)

if __name__ == "__main__":
    unittest.main()