"""
Org-Skin CLI

Command-line interface for the Org-Skin SDK.
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
import logging

from org_skin import __version__
from org_skin.graphql.client import GitHubGraphQLClient
from org_skin.mapper.scanner import OrganizationMapper
from org_skin.aggregator.analyzer import RepoAnalyzer
from org_skin.aggregator.combiner import FeatureCombiner
from org_skin.aggregator.synthesizer import FeatureSynthesizer
from org_skin.chatbot.bot import OrgSkinBot
from org_skin.db.store import DataStore
from org_skin.db.sync import DataSyncer, SyncConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="org-skin",
        description="Org-Skin: GitHub Organization Management SDK with AI/ML",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--token",
        help="GitHub Personal Access Token (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--org",
        default="skintwin-ai",
        help="Organization name (default: skintwin-ai)",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan organization")
    scan_parser.add_argument(
        "--output", "-o",
        help="Output file for scan results (JSON)",
    )
    scan_parser.add_argument(
        "--include-issues",
        action="store_true",
        default=True,
        help="Include issues in scan",
    )
    scan_parser.add_argument(
        "--include-prs",
        action="store_true",
        default=True,
        help="Include pull requests in scan",
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze repositories")
    analyze_parser.add_argument(
        "repo",
        nargs="?",
        help="Repository name (or 'all' for all repos)",
    )
    analyze_parser.add_argument(
        "--output", "-o",
        help="Output file for analysis results",
    )
    analyze_parser.add_argument(
        "--deep",
        action="store_true",
        help="Perform deep analysis",
    )
    
    # Combine command
    combine_parser = subparsers.add_parser("combine", help="Combine features from all repos")
    combine_parser.add_argument(
        "--output", "-o",
        help="Output file for combined analysis",
    )
    combine_parser.add_argument(
        "--report",
        action="store_true",
        help="Generate markdown report",
    )
    
    # Synthesize command
    synth_parser = subparsers.add_parser("synthesize", help="Synthesize templates and configs")
    synth_parser.add_argument(
        "--output-dir", "-o",
        default="templates",
        help="Output directory for synthesized files",
    )
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Interactive chat interface")
    chat_parser.add_argument(
        "--message", "-m",
        help="Single message (non-interactive mode)",
    )
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync data with GitHub")
    sync_parser.add_argument(
        "--direction",
        choices=["pull", "push", "both"],
        default="both",
        help="Sync direction",
    )
    sync_parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to repository",
    )
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Execute GraphQL query")
    query_parser.add_argument(
        "query",
        help="GraphQL query string or file path",
    )
    query_parser.add_argument(
        "--variables", "-v",
        help="Query variables (JSON string)",
    )
    
    return parser


async def cmd_scan(args) -> None:
    """Execute scan command."""
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    client = GitHubGraphQLClient(token=token)
    mapper = OrganizationMapper(client)
    
    print(f"Scanning organization: {args.org}")
    result = await mapper.scan(
        args.org,
        include_issues=args.include_issues,
        include_prs=args.include_prs,
    )
    
    print(f"\nScan completed in {result.scan_time:.2f} seconds")
    print(f"Total entities: {result.total_entities}")
    print(f"  - Repositories: {len(result.repositories)}")
    print(f"  - Teams: {len(result.teams)}")
    print(f"  - Members: {len(result.members)}")
    print(f"  - Issues: {len(result.issues)}")
    print(f"  - Pull Requests: {len(result.pull_requests)}")
    
    if args.output:
        mapper.export_to_json(args.output)
        print(f"\nResults saved to: {args.output}")


async def cmd_analyze(args) -> None:
    """Execute analyze command."""
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    client = GitHubGraphQLClient(token=token)
    analyzer = RepoAnalyzer(client)
    
    if args.repo and args.repo != "all":
        # Analyze single repo
        print(f"Analyzing repository: {args.org}/{args.repo}")
        analysis = await analyzer.analyze(args.org, args.repo, deep_analysis=args.deep)
        
        print(f"\nAnalysis for {analysis.repository}:")
        print(f"  Quality Score: {analysis.quality_score:.2%}")
        print(f"  Maintainability: {analysis.maintainability_score:.2%}")
        print(f"  Documentation: {analysis.doc_score:.2%}")
        print(f"  Has CI: {analysis.has_ci}")
        print(f"  Has Tests: {analysis.has_tests}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(analysis.to_dict(), f, indent=2)
            print(f"\nResults saved to: {args.output}")
    else:
        print("Analyzing all repositories...")
        # Would need to scan first to get repo list
        print("Use 'scan' command first, then analyze individual repos")


async def cmd_combine(args) -> None:
    """Execute combine command."""
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    client = GitHubGraphQLClient(token=token)
    mapper = OrganizationMapper(client)
    analyzer = RepoAnalyzer(client)
    combiner = FeatureCombiner(args.org)
    
    print(f"Scanning organization: {args.org}")
    scan_result = await mapper.scan(args.org, include_issues=False, include_prs=False)
    
    print(f"Analyzing {len(scan_result.repositories)} repositories...")
    for repo in scan_result.repositories[:10]:  # Limit for demo
        print(f"  Analyzing: {repo.name}")
        analysis = await analyzer.analyze(args.org, repo.name)
        combiner.add_analysis(analysis)
    
    combined = combiner.combine()
    
    print(f"\nCombined Analysis:")
    print(f"  Repositories: {combined.repository_count}")
    print(f"  Avg Quality: {combined.avg_quality_score:.2%}")
    print(f"  README Coverage: {combined.readme_coverage:.2%}")
    print(f"  CI Coverage: {combined.ci_coverage:.2%}")
    print(f"  Test Coverage: {combined.test_coverage:.2%}")
    
    if args.report:
        report = combiner.generate_report()
        report_file = args.output or "org_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {report_file}")
    elif args.output:
        combiner.export_to_json(args.output)
        print(f"\nResults saved to: {args.output}")


async def cmd_synthesize(args) -> None:
    """Execute synthesize command."""
    # Load combined analysis or create new one
    combiner = FeatureCombiner(args.org)
    combined = combiner.combine()  # Empty for now
    
    synthesizer = FeatureSynthesizer(combined)
    synthesizer.synthesize()
    
    print(synthesizer.get_summary())
    
    synthesizer.export_templates(args.output_dir)
    print(f"\nTemplates exported to: {args.output_dir}")


async def cmd_chat(args) -> None:
    """Execute chat command."""
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    bot = OrgSkinBot(organization=args.org, github_token=token)
    
    if args.message:
        # Single message mode
        response = await bot.chat(args.message)
        print(response.text)
        if response.data:
            print(f"\nData: {json.dumps(response.data, indent=2)}")
    else:
        # Interactive mode
        print("Org-Skin Chat (type 'exit' to quit)")
        print("-" * 40)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ('exit', 'quit', 'q'):
                    break
                
                if not user_input:
                    continue
                
                response = await bot.chat(user_input)
                print(f"\nBot: {response.text}")
                
                if response.suggestions:
                    print(f"\nSuggestions: {', '.join(response.suggestions)}")
                    
            except KeyboardInterrupt:
                break
        
        print("\nGoodbye!")


async def cmd_sync(args) -> None:
    """Execute sync command."""
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    store = DataStore(data_dir=Path(args.repo_path) / "data")
    config = SyncConfig(organization=args.org)
    syncer = DataSyncer(store, config, github_token=token)
    
    if args.direction in ("pull", "both"):
        print("Pulling data from GitHub...")
        record = await syncer.sync_from_github()
        print(f"  Status: {record.status}")
        print(f"  Items: {record.items_created}")
    
    if args.direction in ("push", "both"):
        print("Pushing data to repository...")
        record = await syncer.sync_to_repository(args.repo_path)
        print(f"  Status: {record.status}")
        print(f"  Items: {record.items_processed}")
    
    print("\nSync complete!")


async def cmd_query(args) -> None:
    """Execute query command."""
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    # Check if query is a file path
    query = args.query
    if os.path.isfile(query):
        with open(query, 'r') as f:
            query = f.read()
    
    variables = {}
    if args.variables:
        variables = json.loads(args.variables)
    
    client = GitHubGraphQLClient(token=token)
    async with client:
        result = await client.execute(query, variables)
        
        if result.success:
            print(json.dumps(result.data, indent=2))
        else:
            print(f"Error: {result.errors}")


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Map commands to handlers
    handlers = {
        "scan": cmd_scan,
        "analyze": cmd_analyze,
        "combine": cmd_combine,
        "synthesize": cmd_synthesize,
        "chat": cmd_chat,
        "sync": cmd_sync,
        "query": cmd_query,
    }
    
    handler = handlers.get(args.command)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
