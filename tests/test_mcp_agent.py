import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import hepara.subagents.mcp_agent.subagents as mcp_subagents_module
import hepara.subagents.mcp_agent.tools as mcp_tools_module


class McpConfigurationTest(unittest.IsolatedAsyncioTestCase):
    def _write_config(self, tmpdir: str, content: str | None) -> Path:
        config_path = Path(tmpdir) / "mcp_config.json"
        if content is not None:
            config_path.write_text(content, encoding="utf-8")
        return config_path

    def _reload_tools_with_path(self, config_path: Path):
        previous_mcp_path = os.environ.get("MCP_PATH")
        os.environ["MCP_PATH"] = str(config_path)
        if previous_mcp_path is None:
            self.addCleanup(os.environ.pop, "MCP_PATH", None)
        else:
            self.addCleanup(os.environ.__setitem__, "MCP_PATH", previous_mcp_path)
        importlib.reload(mcp_subagents_module)
        return importlib.reload(mcp_tools_module)

    def test_empty_mcp_configuration_disables_mcp(self):
        contents = [None, "", "   \n", "{}", '{"mcpServers": {}}']
        for content in contents:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmpdir:
                config_path = self._write_config(tmpdir, content)
                tools_module = self._reload_tools_with_path(config_path)

                self.assertIsNone(tools_module.subagent_records)
                self.assertEqual(
                    tools_module.list_mcp_servers(), "No available MCP servers."
                )

    def test_invalid_mcp_configuration_warns_and_disables_mcp(self):
        contents = ["{not-json", "[]", '{"servers": {}}', '{"mcpServers": []}']
        for content in contents:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmpdir:
                config_path = self._write_config(tmpdir, content)
                tools_module = self._reload_tools_with_path(config_path)

                with self.assertLogs(
                    "utils.mcp_helpers", level="WARNING"
                ) as logs:
                    subagents = mcp_subagents_module.create_subagent_records()

                self.assertIsNone(subagents)
                self.assertIn(str(config_path), "\n".join(logs.output))

    def test_valid_stdio_servers_support_optional_args_and_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps(
                    {
                        "mcpServers": {
                            "command_only": {"command": "command-only"},
                            "with_args": {
                                "command": "runner",
                                "args": ["one", "two"],
                            },
                            "with_env": {
                                "command": "runner",
                                "env": {"TOKEN": "value"},
                            },
                        }
                    }
                ),
            )
            tools_module = self._reload_tools_with_path(config_path)

            records = mcp_subagents_module.create_subagent_records()

        self.assertIsNotNone(records)
        self.assertEqual(len(records), 3)
        parameters = [
            record.agent.tools[0]._connection_params.server_params
            for record in records
        ]
        self.assertEqual(parameters[0].args, [])
        self.assertIsNone(parameters[0].env)
        self.assertEqual(parameters[1].args, ["one", "two"])
        self.assertEqual(parameters[2].env, {"TOKEN": "value"})

    def test_mcp_server_names_are_converted_to_valid_agent_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps({"mcpServers": {"memory-server": {"command": "runner"}}}),
            )
            tools_module = self._reload_tools_with_path(config_path)

            subagents = tools_module.subagents

        self.assertIsNotNone(subagents)
        self.assertEqual(subagents[0].name, "memory_server")
        self.assertEqual(tools_module.list_mcp_servers(), "memory-server\n")

    def test_agent_name_conversion_handles_invalid_identifiers(self):
        self.assertEqual(
            mcp_subagents_module._to_agent_name("123-server"),
            "mcp_123_server",
        )
        self.assertEqual(
            mcp_subagents_module._to_agent_name("class"),
            "mcp_class",
        )

    def test_invalid_server_does_not_block_valid_servers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps(
                    {
                        "mcpServers": {
                            "valid": {"command": "runner"},
                            "missing-command": {"args": ["one"]},
                            "invalid-args": {"command": "runner", "args": "one"},
                            "invalid-env": {
                                "command": "runner",
                                "env": {"TOKEN": 1},
                            },
                        }
                    }
                ),
            )
            tools_module = self._reload_tools_with_path(config_path)

            with self.assertLogs(
                "utils.mcp_helpers", level="WARNING"
            ) as logs:
                records = mcp_subagents_module.create_subagent_records()

        self.assertIsNotNone(records)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].agent.name, "valid")
        log_text = "\n".join(logs.output)
        self.assertIn("missing-command", log_text)
        self.assertIn("invalid-args", log_text)
        self.assertIn("invalid-env", log_text)

    def test_list_mcp_servers_only_reports_valid_servers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps(
                    {
                        "mcpServers": {
                            "valid": {"command": "runner"},
                            "missing-command": {"args": ["one"]},
                            "invalid-env": {
                                "command": "runner",
                                "env": {"TOKEN": 1},
                            },
                        }
                    }
                ),
            )
            with self.assertLogs(
                "utils.mcp_helpers", level="WARNING"
            ):
                tools_module = self._reload_tools_with_path(config_path)
                servers = tools_module.list_mcp_servers()

        self.assertEqual(servers, "valid\n")

    def test_mcp_path_uses_override_and_expands_home(self):
        with patch.dict(os.environ, {"MCP_PATH": "~/configs/mcp.json"}):
            subagents_module = importlib.reload(mcp_subagents_module)
            self.assertEqual(
                subagents_module.get_mcp_path(),
                Path("~/configs/mcp.json").expanduser(),
            )

        with patch.dict(os.environ, {"MCP_PATH": "configs/mcp.json"}):
            subagents_module = importlib.reload(mcp_subagents_module)
            self.assertEqual(
                subagents_module.get_mcp_path(),
                Path.cwd() / "configs/mcp.json",
            )

    def test_coordinator_registers_mcp_agent_only_with_valid_config(self):
        import hepara.agent as root_agent_module
        import hepara.subagents.mcp_agent.agent as mcp_agent_module

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.json"
            valid_path = self._write_config(
                tmpdir,
                json.dumps({"mcpServers": {"example": {"command": "runner"}}}),
            )

            with patch.dict(os.environ, {"MCP_PATH": str(missing_path)}, clear=False):
                importlib.reload(mcp_subagents_module)
                importlib.reload(mcp_tools_module)
                importlib.reload(mcp_agent_module)
                importlib.reload(root_agent_module)
                names = [tool.name for tool in root_agent_module.hep_coordinator.tools]
                self.assertNotIn("mcp_agent", names)

            with patch.dict(os.environ, {"MCP_PATH": str(valid_path)}, clear=False):
                importlib.reload(mcp_subagents_module)
                importlib.reload(mcp_tools_module)
                importlib.reload(mcp_agent_module)
                importlib.reload(root_agent_module)
                names = [tool.name for tool in root_agent_module.hep_coordinator.tools]
                self.assertIn("mcp_agent", names)

            with patch.dict(os.environ, {"MCP_PATH": str(missing_path)}, clear=False):
                importlib.reload(mcp_subagents_module)
                importlib.reload(mcp_tools_module)
                importlib.reload(mcp_agent_module)
                importlib.reload(root_agent_module)

    async def test_list_mcp_tools_reports_tools_from_mcp_toolsets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps({"mcpServers": {"example": {"command": "runner"}}}),
            )
            tools_module = self._reload_tools_with_path(config_path)
            mcp_toolset = tools_module.subagents[0].tools[0]
            mcp_toolset.get_tools = AsyncMock(
                return_value=[
                    SimpleNamespace(name="read_file"),
                    SimpleNamespace(name="write_file"),
                ]
            )

            tools = await tools_module.list_mcp_tools("example")

        self.assertEqual(tools, "read_file\nwrite_file\n")

    async def test_list_mcp_tools_uses_server_names_not_agent_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps({"mcpServers": {"memory-server": {"command": "runner"}}}),
            )
            tools_module = self._reload_tools_with_path(config_path)
            mcp_toolset = tools_module.subagents[0].tools[0]
            mcp_toolset.get_tools = AsyncMock(
                return_value=[
                    SimpleNamespace(name="remember"),
                ]
            )

            tools = await tools_module.list_mcp_tools("memory-server")
            invalid = await tools_module.list_mcp_tools("memory_server")

        self.assertEqual(tools, "remember\n")
        self.assertEqual(invalid, "memory_server is not a valid MCP server.")

    async def test_list_mcp_tools_rejects_unknown_server(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self._write_config(
                tmpdir,
                json.dumps({"mcpServers": {"example": {"command": "runner"}}}),
            )
            tools_module = self._reload_tools_with_path(config_path)

            tools = await tools_module.list_mcp_tools("missing")

        self.assertEqual(tools, "missing is not a valid MCP server.")

    def test_list_mcp_servers_tool_uses_configured_path_without_model_argument(self):
        import hepara.subagents.mcp_agent.agent as mcp_agent_module

        declaration = mcp_agent_module.list_mcp_servers_tool._get_declaration()

        self.assertIsNone(declaration.parameters_json_schema)


if __name__ == "__main__":
    unittest.main()
