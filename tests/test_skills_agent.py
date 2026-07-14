import importlib
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import hepara.subagents.skills_agent.subagents as skills_subagents_module
import hepara.subagents.skills_agent.agent as skills_agent_module
import hepara.subagents.skills_agent.prompt as skills_prompt_module
import hepara.subagents.skills_agent.tools as skills_tools_module


class SkillsAgentTest(unittest.TestCase):
    def _set_skill_path(self, skills_path: Path):
        previous_skill_path = os.environ.get("SKILL_PATH")
        os.environ["SKILL_PATH"] = str(skills_path)
        if previous_skill_path is None:
            self.addCleanup(os.environ.pop, "SKILL_PATH", None)
        else:
            self.addCleanup(os.environ.__setitem__, "SKILL_PATH", previous_skill_path)

    def _reload_subagents_with_path(self, skills_path: Path):
        self._set_skill_path(skills_path)
        return importlib.reload(skills_subagents_module)

    def _reload_tools_with_path(self, skills_path: Path):
        self._set_skill_path(skills_path)
        importlib.reload(skills_subagents_module)
        return importlib.reload(skills_tools_module)

    def _reload_agent_with_path(self, skills_path: Path):
        self._set_skill_path(skills_path)
        importlib.reload(skills_subagents_module)
        importlib.reload(skills_tools_module)
        return importlib.reload(skills_agent_module)

    def test_missing_skill_directory_disables_skills_agent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing-skills"
            subagents_module = self._reload_subagents_with_path(missing_path)

            self.assertEqual(subagents_module._get_other_skill_names(), [])
            self.assertIsNone(subagents_module.create_subagent_records())

    def test_skill_names_are_converted_to_valid_agent_names(self):
        self.assertEqual(
            skills_subagents_module._to_agent_name("openai-docs"),
            "openai_docs",
        )
        self.assertEqual(
            skills_subagents_module._to_agent_name("123-search"),
            "skill_123_search",
        )
        self.assertEqual(
            skills_subagents_module._to_agent_name("class"),
            "skill_class",
        )

    def test_list_all_skills_uses_skill_names_and_includes_mcp_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_path = Path(tmpdir)
            (skills_path / "memory-server").mkdir()
            (skills_path / "openai-docs").mkdir()

            with patch(
                "hepara.subagents.mcp_agent.tools.list_mcp_servers",
                return_value="memory-server\n",
            ):
                tools_module = self._reload_tools_with_path(skills_path)

                skills = tools_module.list_all_skills()

        self.assertEqual(skills, "memory-server\nopenai-docs\n")

    def test_skills_agent_exists_when_only_mcp_skills_are_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_path = Path(tmpdir)
            (skills_path / "memory-server").mkdir()

            with patch(
                "hepara.subagents.mcp_agent.tools.list_mcp_servers",
                return_value="memory-server\n",
            ):
                agent_module = self._reload_agent_with_path(skills_path)

        self.assertIsNotNone(agent_module.skills_agent)
        tool_names = [tool.name for tool in agent_module.skills_agent.tools]
        self.assertIn("list_all_skills", tool_names)

    def test_skills_prompt_imports_and_mentions_callable_subagent_names(self):
        prompt_module = importlib.reload(skills_prompt_module)

        self.assertIn("callable skill subagents", prompt_module.SKILL_AGENT_PROMPT)
        self.assertIn("not the raw skill folder name", prompt_module.SKILL_AGENT_PROMPT)

    def test_subagent_records_keep_original_skill_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_path = Path(tmpdir)
            (skills_path / "memory-server").mkdir()
            (skills_path / "openai-docs").mkdir()

            with patch(
                "hepara.subagents.mcp_agent.tools.list_mcp_servers",
                return_value="memory-server\n",
            ):
                subagents_module = self._reload_subagents_with_path(skills_path)
                with patch.object(
                    subagents_module,
                    "_create_subagent",
                    return_value=SimpleNamespace(name="openai_docs"),
                ):
                    records = subagents_module.create_subagent_records()

        self.assertIsNotNone(records)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].skill_name, "openai-docs")
        self.assertEqual(records[0].agent.name, "openai_docs")


if __name__ == "__main__":
    unittest.main()
