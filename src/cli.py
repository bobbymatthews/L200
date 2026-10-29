"""OmniBlog Interactive Command Line Interface.

Provides CLI commands for article generation, real-time draft auditing,
brand guideline inspection, context compaction, and human-in-the-loop approvals.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import settings
from src.memory.compaction import compact_session_history
from src.memory.store import brand_memory
from src.tools.approval_tools import (
    confirm_publication_approval,
    request_publication_approval,
)
from src.tools.artifact_tools import list_saved_articles, save_blog_artifact
from src.tools.research_tools import search_web_research
from src.tools.seo_tools import analyze_seo_and_readability, generate_meta_and_slug
from src.tools.verification_tools import fact_check_and_verify

console = Console()


@click.group()
def cli():
    """OmniBlog: Autonomous Multi-Agent Publication Engine on Google Cloud."""
    pass


@cli.command()
@click.argument("topic")
@click.option("--keyword", "-k", default="", help="Target SEO keyword")
@click.option("--auto-approve", is_flag=True, default=False, help="Bypass human-in-the-loop confirmation")
def generate(topic: str, keyword: str, auto_approve: bool):
    """Generate a publication-ready blog post for a given topic."""
    console.print(Panel(f"[bold cyan]OmniBlog Editorial Newsroom[/bold cyan]\nGenerating article for: [yellow]{topic}[/yellow]"))

    rprint(f"[dim]Model Routing: Research ({settings.research_model}), Writer ({settings.writer_model}), Critic ({settings.critic_model}), SEO ({settings.seo_model})[/dim]")

    with console.status("[bold green]Stage 1: Researching topic and citations (Flash tier)..."):
        research = search_web_research(topic)
        target_kw = keyword or (research.get("recommended_keywords", ["Cloud"])[0])

    rprint(f"✓ Research complete. Primary keyword: [bold]{target_kw}[/bold]")

    with console.status("[bold green]Stage 2: Drafting technical content and code snippets (Pro Reasoning tier)..."):
        guidelines = brand_memory.get_guidelines()
        title = f"Mastering {topic.title()}: Architectural Patterns & Best Practices | {guidelines.brand_name}"
        citations = research.get("citations", [])
        bib_items = [f"- [{c.get('title')}]({c.get('url')}): *{c.get('key_finding')}*" for c in citations]
        bib_section = "\n".join(bib_items) if bib_items else "- Google Cloud Architecture Center"

        draft = f"""# {title}

In modern cloud computing, implementing reliable **{target_kw}** patterns is critical for enterprise agility.

## The Architectural Challenge

Engineering organizations often face operational bottlenecks when scaling complex infrastructure. Without standardized abstractions and automated workflows, system reliability degrades under load.

By applying decoupled, declarative paradigms, teams can reduce cognitive load and operational toil.

## Implementation & Code Walkthrough

The following Python pattern illustrates how to structure production-grade workflows for {topic}:

```python
import os
from typing import Dict, Any

def execute_task(task_name: str) -> Dict[str, Any]:
    \"\"\"Process enterprise workloads with observability.\"\"\"
    print(f"Executing: {{task_name}}")
    return {{"status": "completed", "task": task_name}}

if __name__ == "__main__":
    result = execute_task("{topic}")
    print(result)
```

## Production Considerations

- **Auto-Scaling**: Deploy containerized runtimes onto serverless infrastructure (Google Cloud Run).
- **Telemetry**: Export OpenTelemetry traces directly to Google Cloud Trace for end-to-end visibility.
- **Continuous Validation**: Integrate automated regression tests in CI/CD before deploying changes.

## References & Further Reading

{bib_section}
"""

    with console.status("[bold green]Stage 3: Running SEO analysis and technical verification (Critic & SEO tier)..."):
        seo = analyze_seo_and_readability(draft, target_keyword=target_kw)
        fact = fact_check_and_verify(draft)
        meta = generate_meta_and_slug(title, topic=topic)

    # Human-in-the-Loop Confirmation Gate
    approval_status = "published"
    approval_token = None

    if not auto_approve:
        ticket = request_publication_approval(
            article_id=f"art-{abs(hash(title)) % 10000:04d}",
            title=title,
            slug=meta["slug"],
            seo_score=seo["overall_seo_score"],
            factual_score=fact["overall_factual_score"],
        )
        approval_token = ticket["approval_token"]
        rprint(Panel(f"[bold yellow]Human-in-the-Loop Confirmation Required[/bold yellow]\n{ticket['message']}"))

        if click.confirm("Do you approve publishing this article to the official catalog?", default=True):
            confirm_publication_approval(approval_token, approved=True)
            approval_status = "published"
            rprint("[bold green]✓ Human approval confirmed. Article officially published![/bold green]")
        else:
            confirm_publication_approval(approval_token, approved=False, reviewer_notes="Held for manual edits.")
            approval_status = "pending_approval"
            rprint(f"[bold yellow]Draft saved in pending status. Approval token: {approval_token}[/bold yellow]")

    with console.status("[bold green]Stage 4: Packaging and persisting publication artifacts..."):
        save_result = save_blog_artifact(
            title=title,
            markdown_content=draft,
            topic=topic,
            target_keyword=target_kw,
            approval_status=approval_status,
        )

    # Render results table
    table = Table(title="OmniBlog Publication Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold green")

    table.add_row("Article ID", save_result["article_id"])
    table.add_row("Title", title)
    table.add_row("Slug", save_result["slug"])
    table.add_row("Word Count", str(seo["word_count"]))
    table.add_row("SEO Score", f"{seo['overall_seo_score']}/100 ({seo['status']})")
    table.add_row("Flesch Reading Ease", f"{seo['flesch_reading_ease']} ({seo['readability_interpretation']})")
    table.add_row("Factual Integrity", f"{fact['overall_factual_score']}/100")
    table.add_row("Status", approval_status.upper())
    table.add_row("Artifact Path", save_result["local_file"])

    console.print(table)
    console.print(Panel(f"[bold]Social Teaser (Twitter):[/bold]\n{meta['social_teaser']['twitter']}", style="blue"))


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--keyword", "-k", required=True, help="Target SEO keyword to audit")
def audit(file_path: str, keyword: str):
    """Audit an existing markdown file for SEO and technical accuracy."""
    content = Path(file_path).read_text(encoding="utf-8")
    seo = analyze_seo_and_readability(content, target_keyword=keyword)
    fact = fact_check_and_verify(content)

    table = Table(title=f"Editorial Audit for '{file_path}'", show_header=True)
    table.add_column("Check")
    table.add_column("Result")

    table.add_row("Word Count", str(seo["word_count"]))
    table.add_row("SEO Score", f"{seo['overall_seo_score']}/100")
    table.add_row("Reading Ease", str(seo["flesch_reading_ease"]))
    table.add_row("Factual Score", f"{fact['overall_factual_score']}/100")
    table.add_row("Verification Passed", "✓ Yes" if fact["passed"] else "✗ Issues Detected")

    console.print(table)
    if seo["recommendations"]:
        console.print("[yellow]SEO Recommendations:[/yellow]")
        for r in seo["recommendations"]:
            console.print(f"  • {r}")


@cli.command(name="approve")
@click.argument("token_or_id")
@click.option("--notes", "-n", default="Approved via CLI", help="Reviewer notes")
def approve_article(token_or_id: str, notes: str):
    """Human-in-the-loop command to approve a pending publication draft."""
    result = confirm_publication_approval(token_or_id, approved=True, reviewer_notes=notes)
    if result["status"] == "approved":
        console.print(f"[bold green]✓ {result['message']}[/bold green]")
    else:
        console.print(f"[bold red]✗ {result['message']}[/bold red]")


@cli.command(name="compact")
@click.option("--tokens", "-t", default=4000, help="Target token budget ceiling")
def compact_context(tokens: int):
    """Prune intermediate context bloat and compress session memory."""
    report = compact_session_history(max_tokens=tokens)
    console.print(f"[bold green]✓ Context compaction complete.[/bold green] {report['summary']}")


@cli.command(name="guidelines")
def view_guidelines():
    """Display active brand voice and editorial rules."""
    g = brand_memory.get_guidelines()
    console.print(Panel(f"[bold cyan]Publication:[/] {g.brand_name}\n[bold cyan]Tone:[/] {g.tone}\n[bold cyan]Audience:[/] {g.target_audience}"))
    console.print("[bold]Style Rules:[/bold]")
    for rule in g.style_rules:
        console.print(f"  • {rule}")


@cli.command(name="list")
def list_articles():
    """List previously published articles and artifacts."""
    articles = list_saved_articles().get("articles", [])
    if not articles:
        console.print("[dim]No articles published yet.[/dim]")
        return

    table = Table(title="Published Articles Catalog", show_header=True)
    table.add_column("Date", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Words")
    table.add_column("SEO")
    table.add_column("Status")
    table.add_column("Slug")

    for a in articles:
        table.add_row(
            a["published_at"][:10],
            a["title"][:40],
            str(a["word_count"]),
            f"{a['seo_score']}",
            a.get("approval_status", "published"),
            a["slug"],
        )
    console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()
