# Org-Skin

**Organization-Wide GitHub Management SDK with AI/ML-Powered GraphQL Workflows**

Org-Skin is a comprehensive SDK for managing GitHub organizations through intelligent GraphQL workflows encoded as AIML (Artificial Intelligence Markup Language) expressions. It serves as the central nervous system for the SkinTwin-AI organization, mapping all repositories, entities, and relationships while combining the best features from across the ecosystem.

## Features

### GraphQL-AIML Integration
- **Intelligent Query Encoding**: Convert natural language queries into GraphQL operations
- **AIML Pattern Matching**: Learn and match patterns for common operations
- **Workflow Automation**: Build complex multi-step workflows with dependency management

### Organization Mapping
- **Complete Entity Discovery**: Scan repositories, teams, members, issues, and PRs
- **Relationship Graph**: Build a hypergraph representation of organizational relationships
- **Real-time Updates**: Incremental sync with GitHub API

### Feature Aggregation
- **Repository Analysis**: Extract patterns, dependencies, and best practices
- **Cross-Repo Comparison**: Identify common technologies and standards
- **Template Synthesis**: Generate standardized templates from best practices

### Intelligent Chatbot
- **Natural Language Interface**: Interact with your organization using plain English
- **Context-Aware Responses**: Multi-turn conversations with session management
- **GraphQL Execution**: Execute queries directly from chat

## Installation

```bash
# Clone the repository
git clone https://github.com/skintwin-ai/org-skin.git
cd org-skin

# Install dependencies
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### Set up authentication

```bash
export GITHUB_TOKEN="your_github_token"
```

### Scan your organization

```bash
org-skin scan --org skintwin-ai --output scan_results.json
```

### Analyze repositories

```bash
org-skin analyze repo-name --deep --output analysis.json
```

### Interactive chat

```bash
org-skin chat
```

## Usage

### Python SDK

```python
import asyncio
from org_skin import GitHubGraphQLClient, OrganizationMapper, OrgSkinBot

async def main():
    # Scan organization
    client = GitHubGraphQLClient()
    mapper = OrganizationMapper(client)
    result = await mapper.scan("skintwin-ai")
    
    print(f"Found {len(result.repositories)} repositories")
    
    # Use the chatbot
    bot = OrgSkinBot(organization="skintwin-ai")
    response = await bot.chat("list all repositories")
    print(response.text)

asyncio.run(main())
```

### GraphQL Queries

```python
from org_skin.graphql import GitHubGraphQLClient

async def query_repos():
    client = GitHubGraphQLClient()
    async with client:
        result = await client.execute("""
            query($org: String!) {
                organization(login: $org) {
                    repositories(first: 10) {
                        nodes { name, description }
                    }
                }
            }
        """, {"org": "skintwin-ai"})
        return result.data
```

### AIML Pattern Encoding

```python
from org_skin.aiml import AIMLEncoder

encoder = AIMLEncoder()

# Add a custom pattern
encoder.add_pattern(
    pattern="LIST * REPOS",
    template="""
    <graphql>
    query { organization(login: "<star/>") { repositories { nodes { name } } } }
    </graphql>
    """
)

# Match and execute
intent = encoder.parse_intent("list skintwin-ai repos")
```

### Feature Aggregation

```python
from org_skin.aggregator import RepoAnalyzer, FeatureCombiner, FeatureSynthesizer

async def analyze_org():
    analyzer = RepoAnalyzer()
    combiner = FeatureCombiner("skintwin-ai")
    
    # Analyze multiple repos
    for repo in ["org-skin", "other-repo"]:
        analysis = await analyzer.analyze("skintwin-ai", repo)
        combiner.add_analysis(analysis)
    
    # Generate combined report
    combined = combiner.combine()
    report = combiner.generate_report()
    
    # Synthesize templates
    synthesizer = FeatureSynthesizer(combined)
    synthesizer.synthesize()
    synthesizer.export_templates("templates/")
```

## Architecture

```
org-skin/
├── src/org_skin/
│   ├── graphql/          # GraphQL client and queries
│   │   ├── client.py     # Async GraphQL client
│   │   ├── queries.py    # Pre-built queries
│   │   └── mutations.py  # Pre-built mutations
│   ├── aiml/             # AIML encoding system
│   │   ├── encoder.py    # Intent parsing and encoding
│   │   ├── parser.py     # AIML template parsing
│   │   └── templates.py  # Template engine
│   ├── mapper/           # Organization mapping
│   │   ├── scanner.py    # Entity discovery
│   │   ├── graph.py      # Relationship graph
│   │   └── entities.py   # Data models
│   ├── chatbot/          # Intelligent chatbot
│   │   ├── bot.py        # Main bot logic
│   │   ├── nlp.py        # NLP processing
│   │   └── session.py    # Session management
│   ├── aggregator/       # Feature aggregation
│   │   ├── analyzer.py   # Repository analysis
│   │   ├── combiner.py   # Feature combination
│   │   └── synthesizer.py # Template synthesis
│   ├── db/               # Data persistence
│   │   ├── store.py      # Data store
│   │   ├── models.py     # Data models
│   │   └── sync.py       # GitHub sync
│   └── cli.py            # Command-line interface
├── data/                 # Synced organization data
├── templates/            # Synthesized templates
└── docs/                 # Documentation
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `org-skin scan` | Scan organization and discover entities |
| `org-skin analyze` | Analyze repository features |
| `org-skin combine` | Combine features from all repos |
| `org-skin synthesize` | Generate templates from best practices |
| `org-skin chat` | Interactive chat interface |
| `org-skin sync` | Sync data with GitHub |
| `org-skin query` | Execute GraphQL queries |

## Configuration

Create a `.env` file or set environment variables:

```bash
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_key  # Optional, for enhanced NLP
ORG_SKIN_DATA_DIR=./data
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Format code
ruff format .
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [SkinTwin-AI](https://github.com/skintwin-ai) - Parent organization
- [cogpy](https://github.com/cogpy) - Cognitive Python frameworks
