"""
Repository Analyzer

Analyzes repositories to extract features, patterns, and best practices.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
import logging

from org_skin.graphql.client import GitHubGraphQLClient
from org_skin.mapper.entities import Repository

logger = logging.getLogger(__name__)


@dataclass
class CodePattern:
    """Represents a code pattern found in a repository."""
    name: str
    pattern_type: str  # 'architecture', 'design', 'testing', 'ci_cd', 'documentation'
    description: str
    file_patterns: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    score: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "file_patterns": self.file_patterns,
            "examples": self.examples,
            "score": self.score,
        }


@dataclass
class DependencyInfo:
    """Information about repository dependencies."""
    name: str
    version: Optional[str] = None
    source: str = ""  # 'package.json', 'requirements.txt', etc.
    is_dev: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "is_dev": self.is_dev,
        }


@dataclass
class FeatureAnalysis:
    """Complete analysis of a repository's features."""
    repository: str
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    # Code metrics
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)  # language -> lines
    
    # Patterns detected
    patterns: list[CodePattern] = field(default_factory=list)
    
    # Dependencies
    dependencies: list[DependencyInfo] = field(default_factory=list)
    
    # Documentation
    has_readme: bool = False
    has_contributing: bool = False
    has_license: bool = False
    has_changelog: bool = False
    doc_score: float = 0.0
    
    # CI/CD
    has_ci: bool = False
    ci_platforms: list[str] = field(default_factory=list)
    
    # Testing
    has_tests: bool = False
    test_frameworks: list[str] = field(default_factory=list)
    test_coverage: Optional[float] = None
    
    # Architecture
    architecture_patterns: list[str] = field(default_factory=list)
    
    # Quality metrics
    quality_score: float = 0.0
    maintainability_score: float = 0.0
    
    # Best practices
    best_practices: list[str] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "analyzed_at": self.analyzed_at.isoformat(),
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "languages": self.languages,
            "patterns": [p.to_dict() for p in self.patterns],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "has_readme": self.has_readme,
            "has_contributing": self.has_contributing,
            "has_license": self.has_license,
            "has_changelog": self.has_changelog,
            "doc_score": self.doc_score,
            "has_ci": self.has_ci,
            "ci_platforms": self.ci_platforms,
            "has_tests": self.has_tests,
            "test_frameworks": self.test_frameworks,
            "test_coverage": self.test_coverage,
            "architecture_patterns": self.architecture_patterns,
            "quality_score": self.quality_score,
            "maintainability_score": self.maintainability_score,
            "best_practices": self.best_practices,
            "improvement_suggestions": self.improvement_suggestions,
        }


class RepoAnalyzer:
    """
    Analyzes repositories to extract features and patterns.
    
    Features:
    - Code pattern detection
    - Dependency analysis
    - Documentation assessment
    - CI/CD detection
    - Test coverage analysis
    - Architecture pattern recognition
    """
    
    def __init__(self, client: Optional[GitHubGraphQLClient] = None):
        """
        Initialize the repository analyzer.
        
        Args:
            client: GitHub GraphQL client.
        """
        self.client = client
        self._setup_pattern_detectors()
    
    def _setup_pattern_detectors(self) -> None:
        """Set up pattern detection rules."""
        self.file_patterns = {
            # Documentation
            "readme": [r"README\.md", r"readme\.md", r"README\.rst", r"README"],
            "contributing": [r"CONTRIBUTING\.md", r"contributing\.md"],
            "license": [r"LICENSE", r"LICENSE\.md", r"COPYING"],
            "changelog": [r"CHANGELOG\.md", r"HISTORY\.md", r"CHANGES\.md"],
            
            # CI/CD
            "github_actions": [r"\.github/workflows/.*\.ya?ml"],
            "travis": [r"\.travis\.ya?ml"],
            "circleci": [r"\.circleci/config\.ya?ml"],
            "gitlab_ci": [r"\.gitlab-ci\.ya?ml"],
            "jenkins": [r"Jenkinsfile"],
            
            # Testing
            "pytest": [r"pytest\.ini", r"conftest\.py", r"test_.*\.py", r".*_test\.py"],
            "jest": [r"jest\.config\.(js|ts)", r".*\.test\.(js|ts|jsx|tsx)"],
            "mocha": [r"mocha\.opts", r".*\.spec\.(js|ts)"],
            "rspec": [r"spec/.*_spec\.rb"],
            
            # Package managers
            "npm": [r"package\.json"],
            "pip": [r"requirements\.txt", r"setup\.py", r"pyproject\.toml"],
            "cargo": [r"Cargo\.toml"],
            "go_mod": [r"go\.mod"],
            "maven": [r"pom\.xml"],
            "gradle": [r"build\.gradle"],
            
            # Architecture patterns
            "microservices": [r"docker-compose\.ya?ml", r"kubernetes/", r"k8s/"],
            "monorepo": [r"lerna\.json", r"nx\.json", r"pnpm-workspace\.yaml"],
            "serverless": [r"serverless\.ya?ml", r"sam\.ya?ml"],
        }
        
        self.architecture_indicators = {
            "microservices": ["docker-compose", "kubernetes", "service", "api-gateway"],
            "monorepo": ["packages/", "apps/", "libs/", "workspace"],
            "serverless": ["lambda", "functions/", "serverless"],
            "mvc": ["controllers/", "models/", "views/"],
            "clean_architecture": ["domain/", "application/", "infrastructure/", "presentation/"],
            "hexagonal": ["adapters/", "ports/", "core/"],
            "event_driven": ["events/", "handlers/", "subscribers/"],
        }
    
    async def analyze(
        self,
        owner: str,
        repo_name: str,
        deep_analysis: bool = False,
    ) -> FeatureAnalysis:
        """
        Analyze a repository.
        
        Args:
            owner: Repository owner.
            repo_name: Repository name.
            deep_analysis: Whether to perform deep file analysis.
            
        Returns:
            FeatureAnalysis with extracted features.
        """
        analysis = FeatureAnalysis(repository=f"{owner}/{repo_name}")
        
        if self.client is None:
            self.client = GitHubGraphQLClient()
        
        async with self.client:
            # Get repository metadata
            repo_data = await self._get_repo_metadata(owner, repo_name)
            if not repo_data:
                logger.warning(f"Could not fetch repository data for {owner}/{repo_name}")
                return analysis
            
            # Analyze languages
            analysis.languages = await self._analyze_languages(owner, repo_name)
            
            # Get file tree
            file_tree = await self._get_file_tree(owner, repo_name)
            analysis.total_files = len(file_tree)
            
            # Detect patterns from file tree
            self._detect_patterns_from_files(analysis, file_tree)
            
            # Analyze documentation
            self._analyze_documentation(analysis, file_tree)
            
            # Detect CI/CD
            self._detect_ci_cd(analysis, file_tree)
            
            # Detect testing
            self._detect_testing(analysis, file_tree)
            
            # Detect architecture patterns
            self._detect_architecture(analysis, file_tree)
            
            # Analyze dependencies if deep analysis
            if deep_analysis:
                await self._analyze_dependencies(analysis, owner, repo_name, file_tree)
            
            # Calculate scores
            self._calculate_scores(analysis)
            
            # Generate suggestions
            self._generate_suggestions(analysis)
        
        return analysis
    
    async def _get_repo_metadata(
        self,
        owner: str,
        repo_name: str,
    ) -> Optional[dict[str, Any]]:
        """Get repository metadata."""
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                name
                description
                url
                diskUsage
                primaryLanguage { name }
                languages(first: 10) {
                    edges {
                        size
                        node { name }
                    }
                }
                defaultBranchRef { name }
            }
        }
        """
        
        result = await self.client.execute(query, {"owner": owner, "name": repo_name})
        if result.success:
            return result.data.get("repository")
        return None
    
    async def _analyze_languages(
        self,
        owner: str,
        repo_name: str,
    ) -> dict[str, int]:
        """Analyze repository languages."""
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                languages(first: 20) {
                    edges {
                        size
                        node { name }
                    }
                }
            }
        }
        """
        
        result = await self.client.execute(query, {"owner": owner, "name": repo_name})
        if not result.success:
            return {}
        
        languages = {}
        for edge in result.data.get("repository", {}).get("languages", {}).get("edges", []):
            lang_name = edge.get("node", {}).get("name", "Unknown")
            size = edge.get("size", 0)
            languages[lang_name] = size
        
        return languages
    
    async def _get_file_tree(
        self,
        owner: str,
        repo_name: str,
        path: str = "",
    ) -> list[str]:
        """Get repository file tree."""
        query = """
        query($owner: String!, $name: String!, $expression: String!) {
            repository(owner: $owner, name: $name) {
                object(expression: $expression) {
                    ... on Tree {
                        entries {
                            name
                            type
                            path
                        }
                    }
                }
            }
        }
        """
        
        branch = "HEAD"
        expression = f"{branch}:{path}" if path else f"{branch}:"
        
        result = await self.client.execute(
            query,
            {"owner": owner, "name": repo_name, "expression": expression}
        )
        
        if not result.success:
            return []
        
        entries = result.data.get("repository", {}).get("object", {})
        if not entries:
            return []
        
        files = []
        for entry in entries.get("entries", []):
            entry_path = entry.get("path", "")
            entry_type = entry.get("type", "")
            
            if entry_type == "blob":
                files.append(entry_path)
            elif entry_type == "tree":
                # Recursively get files from subdirectories (limited depth)
                if entry_path.count("/") < 3:  # Limit depth
                    subfiles = await self._get_file_tree(owner, repo_name, entry_path)
                    files.extend(subfiles)
        
        return files
    
    def _detect_patterns_from_files(
        self,
        analysis: FeatureAnalysis,
        files: list[str],
    ) -> None:
        """Detect patterns from file list."""
        for pattern_name, patterns in self.file_patterns.items():
            for file_path in files:
                for pattern in patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        code_pattern = CodePattern(
                            name=pattern_name,
                            pattern_type=self._categorize_pattern(pattern_name),
                            description=f"Detected {pattern_name} pattern",
                            file_patterns=[pattern],
                            examples=[file_path],
                        )
                        
                        # Check if pattern already exists
                        existing = next(
                            (p for p in analysis.patterns if p.name == pattern_name),
                            None
                        )
                        if existing:
                            existing.examples.append(file_path)
                        else:
                            analysis.patterns.append(code_pattern)
                        break
    
    def _categorize_pattern(self, pattern_name: str) -> str:
        """Categorize a pattern by type."""
        categories = {
            "documentation": ["readme", "contributing", "license", "changelog"],
            "ci_cd": ["github_actions", "travis", "circleci", "gitlab_ci", "jenkins"],
            "testing": ["pytest", "jest", "mocha", "rspec"],
            "package_manager": ["npm", "pip", "cargo", "go_mod", "maven", "gradle"],
            "architecture": ["microservices", "monorepo", "serverless"],
        }
        
        for category, patterns in categories.items():
            if pattern_name in patterns:
                return category
        
        return "other"
    
    def _analyze_documentation(
        self,
        analysis: FeatureAnalysis,
        files: list[str],
    ) -> None:
        """Analyze documentation quality."""
        doc_files = {
            "readme": False,
            "contributing": False,
            "license": False,
            "changelog": False,
        }
        
        for file_path in files:
            file_lower = file_path.lower()
            if "readme" in file_lower:
                doc_files["readme"] = True
            elif "contributing" in file_lower:
                doc_files["contributing"] = True
            elif "license" in file_lower or "copying" in file_lower:
                doc_files["license"] = True
            elif "changelog" in file_lower or "history" in file_lower:
                doc_files["changelog"] = True
        
        analysis.has_readme = doc_files["readme"]
        analysis.has_contributing = doc_files["contributing"]
        analysis.has_license = doc_files["license"]
        analysis.has_changelog = doc_files["changelog"]
        
        # Calculate doc score
        score = 0.0
        if analysis.has_readme:
            score += 0.4
        if analysis.has_license:
            score += 0.3
        if analysis.has_contributing:
            score += 0.2
        if analysis.has_changelog:
            score += 0.1
        
        analysis.doc_score = score
    
    def _detect_ci_cd(
        self,
        analysis: FeatureAnalysis,
        files: list[str],
    ) -> None:
        """Detect CI/CD configuration."""
        ci_platforms = {
            "GitHub Actions": r"\.github/workflows/",
            "Travis CI": r"\.travis\.ya?ml",
            "CircleCI": r"\.circleci/",
            "GitLab CI": r"\.gitlab-ci\.ya?ml",
            "Jenkins": r"Jenkinsfile",
            "Azure Pipelines": r"azure-pipelines\.ya?ml",
        }
        
        detected = []
        for platform, pattern in ci_platforms.items():
            for file_path in files:
                if re.search(pattern, file_path, re.IGNORECASE):
                    detected.append(platform)
                    break
        
        analysis.has_ci = len(detected) > 0
        analysis.ci_platforms = detected
    
    def _detect_testing(
        self,
        analysis: FeatureAnalysis,
        files: list[str],
    ) -> None:
        """Detect testing frameworks."""
        test_indicators = {
            "pytest": [r"pytest\.ini", r"conftest\.py", r"test_.*\.py"],
            "unittest": [r"test_.*\.py", r".*_test\.py"],
            "jest": [r"jest\.config", r".*\.test\.(js|ts|jsx|tsx)"],
            "mocha": [r"mocha", r".*\.spec\.(js|ts)"],
            "rspec": [r"spec/.*_spec\.rb"],
            "go test": [r".*_test\.go"],
            "cargo test": [r"tests/.*\.rs"],
        }
        
        detected = []
        for framework, patterns in test_indicators.items():
            for file_path in files:
                for pattern in patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        detected.append(framework)
                        break
                if framework in detected:
                    break
        
        analysis.has_tests = len(detected) > 0
        analysis.test_frameworks = list(set(detected))
    
    def _detect_architecture(
        self,
        analysis: FeatureAnalysis,
        files: list[str],
    ) -> None:
        """Detect architecture patterns."""
        detected = []
        
        file_paths_str = "\n".join(files)
        
        for arch_pattern, indicators in self.architecture_indicators.items():
            matches = 0
            for indicator in indicators:
                if indicator.lower() in file_paths_str.lower():
                    matches += 1
            
            if matches >= 2:  # Require at least 2 indicators
                detected.append(arch_pattern)
        
        analysis.architecture_patterns = detected
    
    async def _analyze_dependencies(
        self,
        analysis: FeatureAnalysis,
        owner: str,
        repo_name: str,
        files: list[str],
    ) -> None:
        """Analyze repository dependencies."""
        # Check for package.json
        if any("package.json" in f for f in files):
            deps = await self._parse_npm_dependencies(owner, repo_name)
            analysis.dependencies.extend(deps)
        
        # Check for requirements.txt or pyproject.toml
        if any("requirements.txt" in f or "pyproject.toml" in f for f in files):
            deps = await self._parse_python_dependencies(owner, repo_name, files)
            analysis.dependencies.extend(deps)
    
    async def _parse_npm_dependencies(
        self,
        owner: str,
        repo_name: str,
    ) -> list[DependencyInfo]:
        """Parse npm dependencies from package.json."""
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                object(expression: "HEAD:package.json") {
                    ... on Blob {
                        text
                    }
                }
            }
        }
        """
        
        result = await self.client.execute(query, {"owner": owner, "name": repo_name})
        if not result.success:
            return []
        
        blob = result.data.get("repository", {}).get("object", {})
        if not blob:
            return []
        
        try:
            package_json = json.loads(blob.get("text", "{}"))
        except json.JSONDecodeError:
            return []
        
        deps = []
        
        for name, version in package_json.get("dependencies", {}).items():
            deps.append(DependencyInfo(
                name=name,
                version=version,
                source="package.json",
                is_dev=False,
            ))
        
        for name, version in package_json.get("devDependencies", {}).items():
            deps.append(DependencyInfo(
                name=name,
                version=version,
                source="package.json",
                is_dev=True,
            ))
        
        return deps
    
    async def _parse_python_dependencies(
        self,
        owner: str,
        repo_name: str,
        files: list[str],
    ) -> list[DependencyInfo]:
        """Parse Python dependencies."""
        deps = []
        
        # Try requirements.txt
        if any("requirements.txt" in f for f in files):
            query = """
            query($owner: String!, $name: String!) {
                repository(owner: $owner, name: $name) {
                    object(expression: "HEAD:requirements.txt") {
                        ... on Blob {
                            text
                        }
                    }
                }
            }
            """
            
            result = await self.client.execute(query, {"owner": owner, "name": repo_name})
            if result.success:
                blob = result.data.get("repository", {}).get("object", {})
                if blob:
                    text = blob.get("text", "")
                    for line in text.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Parse requirement line
                            match = re.match(r"([a-zA-Z0-9_-]+)([<>=!]+.*)?", line)
                            if match:
                                deps.append(DependencyInfo(
                                    name=match.group(1),
                                    version=match.group(2) if match.group(2) else None,
                                    source="requirements.txt",
                                ))
        
        return deps
    
    def _calculate_scores(self, analysis: FeatureAnalysis) -> None:
        """Calculate quality and maintainability scores."""
        # Quality score based on various factors
        quality = 0.0
        
        # Documentation (30%)
        quality += analysis.doc_score * 0.3
        
        # CI/CD (20%)
        if analysis.has_ci:
            quality += 0.2
        
        # Testing (25%)
        if analysis.has_tests:
            quality += 0.25
        
        # Architecture patterns (15%)
        if analysis.architecture_patterns:
            quality += min(len(analysis.architecture_patterns) * 0.05, 0.15)
        
        # Multiple languages (10%)
        if len(analysis.languages) > 1:
            quality += 0.1
        
        analysis.quality_score = min(quality, 1.0)
        
        # Maintainability score
        maintainability = 0.0
        
        # Has README
        if analysis.has_readme:
            maintainability += 0.25
        
        # Has contributing guide
        if analysis.has_contributing:
            maintainability += 0.15
        
        # Has CI
        if analysis.has_ci:
            maintainability += 0.2
        
        # Has tests
        if analysis.has_tests:
            maintainability += 0.25
        
        # Has changelog
        if analysis.has_changelog:
            maintainability += 0.15
        
        analysis.maintainability_score = min(maintainability, 1.0)
    
    def _generate_suggestions(self, analysis: FeatureAnalysis) -> None:
        """Generate improvement suggestions."""
        suggestions = []
        best_practices = []
        
        # Documentation suggestions
        if not analysis.has_readme:
            suggestions.append("Add a README.md file with project description and setup instructions")
        else:
            best_practices.append("Has README documentation")
        
        if not analysis.has_contributing:
            suggestions.append("Add CONTRIBUTING.md to guide contributors")
        else:
            best_practices.append("Has contribution guidelines")
        
        if not analysis.has_license:
            suggestions.append("Add a LICENSE file to clarify usage terms")
        else:
            best_practices.append("Has license file")
        
        if not analysis.has_changelog:
            suggestions.append("Add CHANGELOG.md to track version history")
        else:
            best_practices.append("Maintains changelog")
        
        # CI/CD suggestions
        if not analysis.has_ci:
            suggestions.append("Set up CI/CD pipeline (e.g., GitHub Actions)")
        else:
            best_practices.append(f"Uses CI/CD: {', '.join(analysis.ci_platforms)}")
        
        # Testing suggestions
        if not analysis.has_tests:
            suggestions.append("Add automated tests to improve code quality")
        else:
            best_practices.append(f"Has tests using: {', '.join(analysis.test_frameworks)}")
        
        # Architecture suggestions
        if not analysis.architecture_patterns:
            suggestions.append("Consider adopting a clear architecture pattern")
        else:
            best_practices.append(f"Uses architecture patterns: {', '.join(analysis.architecture_patterns)}")
        
        analysis.improvement_suggestions = suggestions
        analysis.best_practices = best_practices
