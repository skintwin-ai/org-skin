"""
Feature Synthesizer

Synthesizes best features from all repositories into unified templates and configurations.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
import logging

from org_skin.aggregator.combiner import CombinedAnalysis, CombinedFeature

logger = logging.getLogger(__name__)


@dataclass
class SynthesizedTemplate:
    """A synthesized template from combined features."""
    name: str
    category: str
    description: str
    content: str
    source_features: list[str] = field(default_factory=list)
    file_path: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "content": self.content,
            "source_features": self.source_features,
            "file_path": self.file_path,
        }


@dataclass
class SynthesizedConfig:
    """A synthesized configuration from combined features."""
    name: str
    config_type: str  # 'ci', 'linting', 'testing', 'docker', etc.
    content: dict[str, Any] = field(default_factory=dict)
    file_name: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "config_type": self.config_type,
            "content": self.content,
            "file_name": self.file_name,
        }


class FeatureSynthesizer:
    """
    Synthesizes best features into reusable templates and configurations.
    
    Features:
    - Generates standardized templates
    - Creates unified configurations
    - Produces best-practice documentation
    - Exports to various formats
    """
    
    def __init__(self, combined_analysis: Optional[CombinedAnalysis] = None):
        """
        Initialize the feature synthesizer.
        
        Args:
            combined_analysis: Combined analysis from FeatureCombiner.
        """
        self.analysis = combined_analysis
        self.templates: list[SynthesizedTemplate] = []
        self.configs: list[SynthesizedConfig] = []
    
    def synthesize(self, combined_analysis: Optional[CombinedAnalysis] = None) -> None:
        """
        Synthesize templates and configs from combined analysis.
        
        Args:
            combined_analysis: Combined analysis to synthesize from.
        """
        if combined_analysis:
            self.analysis = combined_analysis
        
        if not self.analysis:
            raise ValueError("No combined analysis provided")
        
        # Generate templates
        self._synthesize_readme_template()
        self._synthesize_contributing_template()
        self._synthesize_issue_templates()
        self._synthesize_pr_template()
        
        # Generate configurations
        self._synthesize_ci_config()
        self._synthesize_linting_config()
        self._synthesize_testing_config()
        self._synthesize_docker_config()
        
        logger.info(f"Synthesized {len(self.templates)} templates and {len(self.configs)} configs")
    
    def _synthesize_readme_template(self) -> None:
        """Synthesize a README template."""
        # Determine primary language
        primary_lang = "Python"
        if self.analysis.tech_stack.languages:
            primary_lang = max(
                self.analysis.tech_stack.languages.items(),
                key=lambda x: x[1]
            )[0]
        
        # Determine installation instructions based on language
        install_instructions = self._get_install_instructions(primary_lang)
        
        content = f"""# Project Name

Brief description of the project.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

{install_instructions}

## Usage

```{primary_lang.lower()}
# Example usage code
```

## Configuration

Describe configuration options here.

## Development

### Prerequisites

- List prerequisites

### Setup

```bash
# Setup commands
```

### Running Tests

```bash
# Test commands
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Acknowledgment 1
- Acknowledgment 2
"""
        
        self.templates.append(SynthesizedTemplate(
            name="README Template",
            category="documentation",
            description="Standard README template based on organization best practices",
            content=content,
            source_features=["README"],
            file_path="README.md",
        ))
    
    def _get_install_instructions(self, language: str) -> str:
        """Get installation instructions for a language."""
        instructions = {
            "Python": """```bash
pip install -r requirements.txt
```

Or using poetry:

```bash
poetry install
```""",
            "JavaScript": """```bash
npm install
```

Or using yarn:

```bash
yarn install
```""",
            "TypeScript": """```bash
npm install
```

Or using pnpm:

```bash
pnpm install
```""",
            "Go": """```bash
go mod download
```""",
            "Rust": """```bash
cargo build
```""",
        }
        
        return instructions.get(language, "```bash\n# Install dependencies\n```")
    
    def _synthesize_contributing_template(self) -> None:
        """Synthesize a CONTRIBUTING template."""
        content = """# Contributing to This Project

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

### Suggesting Features

1. Check existing issues and discussions
2. Create a new issue with the "enhancement" label
3. Describe the feature and its use case

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/REPO_NAME.git

# Install dependencies
# (language-specific commands)

# Run tests
# (test commands)
```

## Style Guidelines

### Code Style

- Follow the existing code style
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and small

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs in the body

### Documentation

- Update README if needed
- Add docstrings/comments for new code
- Update CHANGELOG for significant changes

## Review Process

1. All PRs require at least one review
2. Address review comments
3. Ensure CI passes
4. Squash commits if requested

## Questions?

Feel free to open an issue for any questions about contributing.
"""
        
        self.templates.append(SynthesizedTemplate(
            name="CONTRIBUTING Template",
            category="documentation",
            description="Standard contribution guidelines",
            content=content,
            source_features=["Contributing Guide"],
            file_path="CONTRIBUTING.md",
        ))
    
    def _synthesize_issue_templates(self) -> None:
        """Synthesize issue templates."""
        bug_template = """---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of what the bug is.

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

## Expected Behavior
A clear and concise description of what you expected to happen.

## Actual Behavior
What actually happened.

## Screenshots
If applicable, add screenshots to help explain your problem.

## Environment
- OS: [e.g., Ubuntu 22.04]
- Version: [e.g., 1.0.0]
- Browser (if applicable): [e.g., Chrome 120]

## Additional Context
Add any other context about the problem here.
"""
        
        self.templates.append(SynthesizedTemplate(
            name="Bug Report Template",
            category="issue_template",
            description="Template for bug reports",
            content=bug_template,
            source_features=["GitHub Issues"],
            file_path=".github/ISSUE_TEMPLATE/bug_report.md",
        ))
        
        feature_template = """---
name: Feature Request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Problem Statement
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

## Proposed Solution
A clear and concise description of what you want to happen.

## Alternatives Considered
A clear and concise description of any alternative solutions or features you've considered.

## Use Case
Describe the use case for this feature.

## Additional Context
Add any other context or screenshots about the feature request here.
"""
        
        self.templates.append(SynthesizedTemplate(
            name="Feature Request Template",
            category="issue_template",
            description="Template for feature requests",
            content=feature_template,
            source_features=["GitHub Issues"],
            file_path=".github/ISSUE_TEMPLATE/feature_request.md",
        ))
    
    def _synthesize_pr_template(self) -> None:
        """Synthesize pull request template."""
        content = """## Description
Brief description of the changes in this PR.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues
Fixes #(issue number)

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe the tests you ran to verify your changes.

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Screenshots (if applicable)
Add screenshots to show the changes.

## Additional Notes
Any additional information that reviewers should know.
"""
        
        self.templates.append(SynthesizedTemplate(
            name="Pull Request Template",
            category="pr_template",
            description="Template for pull requests",
            content=content,
            source_features=["GitHub PRs"],
            file_path=".github/PULL_REQUEST_TEMPLATE.md",
        ))
    
    def _synthesize_ci_config(self) -> None:
        """Synthesize CI configuration."""
        # Determine primary CI platform
        ci_platform = "GitHub Actions"
        if self.analysis.tech_stack.ci_platforms:
            ci_platform = max(
                self.analysis.tech_stack.ci_platforms.items(),
                key=lambda x: x[1]
            )[0]
        
        # Determine primary language
        primary_lang = "python"
        if self.analysis.tech_stack.languages:
            primary_lang = max(
                self.analysis.tech_stack.languages.items(),
                key=lambda x: x[1]
            )[0].lower()
        
        if ci_platform == "GitHub Actions":
            config = self._generate_github_actions_config(primary_lang)
            self.configs.append(SynthesizedConfig(
                name="GitHub Actions CI",
                config_type="ci",
                content=config,
                file_name=".github/workflows/ci.yml",
            ))
    
    def _generate_github_actions_config(self, language: str) -> dict[str, Any]:
        """Generate GitHub Actions configuration."""
        base_config = {
            "name": "CI",
            "on": {
                "push": {"branches": ["main", "develop"]},
                "pull_request": {"branches": ["main"]},
            },
            "jobs": {},
        }
        
        if language == "python":
            base_config["jobs"]["test"] = {
                "runs-on": "ubuntu-latest",
                "strategy": {
                    "matrix": {"python-version": ["3.10", "3.11", "3.12"]},
                },
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Set up Python ${{ matrix.python-version }}",
                        "uses": "actions/setup-python@v5",
                        "with": {"python-version": "${{ matrix.python-version }}"},
                    },
                    {
                        "name": "Install dependencies",
                        "run": "pip install -e .[dev]",
                    },
                    {
                        "name": "Run linting",
                        "run": "ruff check .",
                    },
                    {
                        "name": "Run tests",
                        "run": "pytest --cov",
                    },
                ],
            }
        elif language in ("javascript", "typescript"):
            base_config["jobs"]["test"] = {
                "runs-on": "ubuntu-latest",
                "strategy": {
                    "matrix": {"node-version": ["18.x", "20.x"]},
                },
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Use Node.js ${{ matrix.node-version }}",
                        "uses": "actions/setup-node@v4",
                        "with": {"node-version": "${{ matrix.node-version }}"},
                    },
                    {"name": "Install dependencies", "run": "npm ci"},
                    {"name": "Run linting", "run": "npm run lint"},
                    {"name": "Run tests", "run": "npm test"},
                ],
            }
        
        return base_config
    
    def _synthesize_linting_config(self) -> None:
        """Synthesize linting configuration."""
        primary_lang = "python"
        if self.analysis.tech_stack.languages:
            primary_lang = max(
                self.analysis.tech_stack.languages.items(),
                key=lambda x: x[1]
            )[0].lower()
        
        if primary_lang == "python":
            # Ruff configuration
            ruff_config = {
                "line-length": 100,
                "target-version": "py311",
                "select": ["E", "F", "I", "N", "W", "UP"],
                "ignore": ["E501"],
                "per-file-ignores": {"__init__.py": ["F401"]},
            }
            
            self.configs.append(SynthesizedConfig(
                name="Ruff Configuration",
                config_type="linting",
                content={"tool": {"ruff": ruff_config}},
                file_name="pyproject.toml",
            ))
        
        elif primary_lang in ("javascript", "typescript"):
            # ESLint configuration
            eslint_config = {
                "env": {"browser": True, "es2021": True, "node": True},
                "extends": ["eslint:recommended"],
                "parserOptions": {"ecmaVersion": "latest", "sourceType": "module"},
                "rules": {
                    "indent": ["error", 2],
                    "linebreak-style": ["error", "unix"],
                    "quotes": ["error", "single"],
                    "semi": ["error", "always"],
                },
            }
            
            self.configs.append(SynthesizedConfig(
                name="ESLint Configuration",
                config_type="linting",
                content=eslint_config,
                file_name=".eslintrc.json",
            ))
    
    def _synthesize_testing_config(self) -> None:
        """Synthesize testing configuration."""
        primary_lang = "python"
        if self.analysis.tech_stack.languages:
            primary_lang = max(
                self.analysis.tech_stack.languages.items(),
                key=lambda x: x[1]
            )[0].lower()
        
        if primary_lang == "python":
            pytest_config = {
                "tool": {
                    "pytest": {
                        "ini_options": {
                            "testpaths": ["tests"],
                            "python_files": ["test_*.py"],
                            "python_functions": ["test_*"],
                            "addopts": "-v --tb=short",
                        }
                    },
                    "coverage": {
                        "run": {"source": ["src"]},
                        "report": {"exclude_lines": ["pragma: no cover", "if TYPE_CHECKING:"]},
                    },
                }
            }
            
            self.configs.append(SynthesizedConfig(
                name="Pytest Configuration",
                config_type="testing",
                content=pytest_config,
                file_name="pyproject.toml",
            ))
    
    def _synthesize_docker_config(self) -> None:
        """Synthesize Docker configuration."""
        primary_lang = "python"
        if self.analysis.tech_stack.languages:
            primary_lang = max(
                self.analysis.tech_stack.languages.items(),
                key=lambda x: x[1]
            )[0].lower()
        
        if primary_lang == "python":
            dockerfile = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
CMD ["python", "-m", "app"]
"""
            
            self.templates.append(SynthesizedTemplate(
                name="Dockerfile",
                category="docker",
                description="Standard Dockerfile for Python applications",
                content=dockerfile,
                source_features=["Docker"],
                file_path="Dockerfile",
            ))
    
    def export_templates(self, output_dir: str) -> None:
        """Export all templates to a directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for template in self.templates:
            file_path = output_path / template.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(template.content)
        
        logger.info(f"Exported {len(self.templates)} templates to {output_dir}")
    
    def export_configs(self, output_dir: str) -> None:
        """Export all configurations to a directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for config in self.configs:
            file_path = output_path / config.file_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if config.file_name.endswith('.json'):
                file_path.write_text(json.dumps(config.content, indent=2))
            elif config.file_name.endswith('.yml') or config.file_name.endswith('.yaml'):
                import yaml
                file_path.write_text(yaml.dump(config.content, default_flow_style=False))
            else:
                # For pyproject.toml, we'd need toml library
                file_path.write_text(json.dumps(config.content, indent=2))
        
        logger.info(f"Exported {len(self.configs)} configs to {output_dir}")
    
    def get_summary(self) -> str:
        """Get a summary of synthesized items."""
        return f"""Synthesized Items:
- Templates: {len(self.templates)}
- Configurations: {len(self.configs)}

Templates:
{chr(10).join(f'  - {t.name} ({t.file_path})' for t in self.templates)}

Configurations:
{chr(10).join(f'  - {c.name} ({c.file_name})' for c in self.configs)}
"""
