"""Unit tests for OmniBlog Click CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli


def test_cli_guidelines_command():
    """Verify `omniblog guidelines` prints active brand guidelines."""
    runner = CliRunner()
    result = runner.invoke(cli, ["guidelines"])
    assert result.exit_code == 0
    assert "CloudNative Insights" in result.output
    assert "Style Rules:" in result.output


def test_cli_generate_command():
    """Verify `omniblog generate` creates article and displays summary."""
    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "Modern Cloud Observability", "-k", "OpenTelemetry", "--auto-approve"])
    assert result.exit_code == 0
    assert "OmniBlog Editorial Newsroom" in result.output
    assert "Modern Cloud Observability" in result.output
    assert "OmniBlog Publication Summary" in result.output
    assert "Social Teaser" in result.output


def test_cli_generate_with_hitl_confirm():
    """Verify `omniblog generate` supports interactive human confirmation."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["generate", "Serverless Architecture with Cloud Run", "-k", "Cloud Run"],
        input="y\n",
    )
    assert result.exit_code == 0
    assert "Human-in-the-Loop Confirmation Required" in result.output
    assert "Human approval confirmed" in result.output


def test_cli_compact_command():
    """Verify `omniblog compact` prunes context bloat."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compact", "--tokens", "3000"])
    assert result.exit_code == 0
    assert "Context compaction complete" in result.output


def test_cli_audit_command(tmp_path):
    """Verify `omniblog audit` reviews markdown file."""
    draft_path = tmp_path / "test_draft.md"
    draft_path.write_text(
        "# Observability Guide\n\nContinuous telemetry is key.\n\n## Section\n\nContent here.\n\n## Code\n\n```python\nprint('trace')\n```",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["audit", str(draft_path), "-k", "Observability"])
    assert result.exit_code == 0
    assert "Editorial Audit" in result.output
    assert "SEO Score" in result.output


def test_cli_list_command():
    """Verify `omniblog list` lists published articles."""
    runner = CliRunner()
    # First invoke generate with auto-approve
    runner.invoke(cli, ["generate", "FinOps Architecture", "--auto-approve"])
    # Then list
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Published Articles Catalog" in result.output
    assert "FinOps Architecture" in result.output or "Finops" in result.output
