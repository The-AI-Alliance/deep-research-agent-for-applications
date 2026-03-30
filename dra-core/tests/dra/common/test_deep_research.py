# Unit tests for the "deep research" module using Hypothesis for property-based testing.
# https://hypothesis.readthedocs.io/en/latest/

import os, re, shutil, sys, unittest
from hypothesis import given, strategies as st
from pathlib import Path
from typing import Awaitable

from dra.core.common.deep_research import DeepResearch
from dra.core.common.observer import Observers
from dra.core.common.tasks import BaseTask
from dra.core.common.variables import Variable
from dra.core.ux.display import Display
from mcp_agent.workflows.deep_orchestrator.config import DeepOrchestratorConfig

output_dir = './tests/output/META'
output_dir_path = Path(output_dir)

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
    def default_config():
        return DeepResearch.make_default_config(
            short_run = True,
            name = "TestDeepResearchConfig",
            available_servers = [],
            variables = {})

    def make(self,
        app_name: str = 'DeepResearchTest',
        provider: str = 'ollama',
        config: DeepOrchestratorConfig = default_config(),
        tasks: list[BaseTask] = [],
        display: Display = TestDisplay(),
        observers: Observers = Observers(),
        variables: dict[str, Variable] = {}):
        return DeepResearch(
            app_name = app_name,
            provider = provider,
            config = config,
            tasks = tasks,
            display = display,
            observers = observers,
            variables = variables)

    def test_DeepResearch_init(self):
        dr = self.make()
        self.assertEqual([], dr.tasks)
        self.assertEqual(Observers(), dr.observers)
        self.assertEqual({}, dr.variables)

if __name__ == "__main__":
    unittest.main()