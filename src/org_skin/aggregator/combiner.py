"""
Feature Combiner

Combines features from multiple repositories into a unified view.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from collections import defaultdict
import logging

from org_skin.aggregator.analyzer import FeatureAnalysis, CodePattern, DependencyInfo

logger = logging.getLogger(__name__)


@dataclass
class CombinedFeature:
    """A feature combined from multiple repositories."""
    name: str
    category: str
    description: str
    sources: list[str] = field(default_factory=list)  # Repository names
    prevalence: float = 0.0  # Percentage of repos with this feature
    importance_score: float = 0.0
    examples: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "sources": self.sources,
            "prevalence": self.prevalence,
            "importance_score": self.importance_score,
            "examples": self.examples,
        }


@dataclass
class TechnologyStack:
    """Combined technology stack from all repositories."""
    languages: dict[str, int] = field(default_factory=dict)  # language -> repo count
    frameworks: dict[str, int] = field(default_factory=dict)
    tools: dict[str, int] = field(default_factory=dict)
    ci_platforms: dict[str, int] = field(default_factory=dict)
    test_frameworks: dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "languages": self.languages,
            "frameworks": self.frameworks,
            "tools": self.tools,
            "ci_platforms": self.ci_platforms,
            "test_frameworks": self.test_frameworks,
        }


@dataclass
class CombinedAnalysis:
    """Combined analysis from all repositories."""
    organization: str
    analyzed_at: datetime = field(default_factory=datetime.now)
    repository_count: int = 0
    
    # Combined features
    features: list[CombinedFeature] = field(default_factory=list)
    
    # Technology stack
    tech_stack: TechnologyStack = field(default_factory=TechnologyStack)
    
    # Best practices across org
    common_best_practices: list[str] = field(default_factory=list)
    recommended_practices: list[str] = field(default_factory=list)
    
    # Quality metrics
    avg_quality_score: float = 0.0
    avg_maintainability_score: float = 0.0
    
    # Documentation coverage
    readme_coverage: float = 0.0
    license_coverage: float = 0.0
    ci_coverage: float = 0.0
    test_coverage: float = 0.0
    
    # Architecture patterns
    architecture_patterns: dict[str, int] = field(default_factory=dict)
    
    # Dependencies
    common_dependencies: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "organization": self.organization,
            "analyzed_at": self.analyzed_at.isoformat(),
            "repository_count": self.repository_count,
            "features": [f.to_dict() for f in self.features],
            "tech_stack": self.tech_stack.to_dict(),
            "common_best_practices": self.common_best_practices,
            "recommended_practices": self.recommended_practices,
            "avg_quality_score": self.avg_quality_score,
            "avg_maintainability_score": self.avg_maintainability_score,
            "readme_coverage": self.readme_coverage,
            "license_coverage": self.license_coverage,
            "ci_coverage": self.ci_coverage,
            "test_coverage": self.test_coverage,
            "architecture_patterns": self.architecture_patterns,
            "common_dependencies": self.common_dependencies,
        }


class FeatureCombiner:
    """
    Combines features from multiple repository analyses.
    
    Features:
    - Aggregates patterns across repositories
    - Identifies common technologies and practices
    - Calculates organization-wide metrics
    - Generates recommendations
    """
    
    def __init__(self, organization: str = "skintwin-ai"):
        """
        Initialize the feature combiner.
        
        Args:
            organization: Organization name.
        """
        self.organization = organization
        self.analyses: list[FeatureAnalysis] = []
    
    def add_analysis(self, analysis: FeatureAnalysis) -> None:
        """Add a repository analysis."""
        self.analyses.append(analysis)
    
    def combine(self) -> CombinedAnalysis:
        """
        Combine all analyses into a unified view.
        
        Returns:
            CombinedAnalysis with aggregated features.
        """
        if not self.analyses:
            return CombinedAnalysis(organization=self.organization)
        
        combined = CombinedAnalysis(
            organization=self.organization,
            repository_count=len(self.analyses),
        )
        
        # Combine technology stack
        combined.tech_stack = self._combine_tech_stack()
        
        # Combine features
        combined.features = self._combine_features()
        
        # Calculate coverage metrics
        self._calculate_coverage(combined)
        
        # Calculate quality metrics
        self._calculate_quality_metrics(combined)
        
        # Combine architecture patterns
        combined.architecture_patterns = self._combine_architecture_patterns()
        
        # Combine dependencies
        combined.common_dependencies = self._combine_dependencies()
        
        # Generate best practices and recommendations
        self._generate_recommendations(combined)
        
        return combined
    
    def _combine_tech_stack(self) -> TechnologyStack:
        """Combine technology stacks from all repositories."""
        stack = TechnologyStack()
        
        for analysis in self.analyses:
            # Languages
            for lang in analysis.languages:
                stack.languages[lang] = stack.languages.get(lang, 0) + 1
            
            # CI platforms
            for platform in analysis.ci_platforms:
                stack.ci_platforms[platform] = stack.ci_platforms.get(platform, 0) + 1
            
            # Test frameworks
            for framework in analysis.test_frameworks:
                stack.test_frameworks[framework] = stack.test_frameworks.get(framework, 0) + 1
            
            # Extract frameworks from dependencies
            for dep in analysis.dependencies:
                dep_name = dep.name.lower()
                
                # Common frameworks
                framework_indicators = {
                    "react": "React",
                    "vue": "Vue.js",
                    "angular": "Angular",
                    "express": "Express.js",
                    "fastapi": "FastAPI",
                    "flask": "Flask",
                    "django": "Django",
                    "next": "Next.js",
                    "nuxt": "Nuxt.js",
                    "svelte": "Svelte",
                }
                
                for indicator, framework in framework_indicators.items():
                    if indicator in dep_name:
                        stack.frameworks[framework] = stack.frameworks.get(framework, 0) + 1
                        break
                
                # Common tools
                tool_indicators = {
                    "eslint": "ESLint",
                    "prettier": "Prettier",
                    "typescript": "TypeScript",
                    "webpack": "Webpack",
                    "vite": "Vite",
                    "docker": "Docker",
                    "kubernetes": "Kubernetes",
                }
                
                for indicator, tool in tool_indicators.items():
                    if indicator in dep_name:
                        stack.tools[tool] = stack.tools.get(tool, 0) + 1
                        break
        
        return stack
    
    def _combine_features(self) -> list[CombinedFeature]:
        """Combine features from all repositories."""
        feature_map: dict[str, CombinedFeature] = {}
        
        for analysis in self.analyses:
            repo_name = analysis.repository
            
            # Add documentation features
            if analysis.has_readme:
                self._add_feature(feature_map, "README", "documentation", 
                                 "Project documentation", repo_name)
            if analysis.has_contributing:
                self._add_feature(feature_map, "Contributing Guide", "documentation",
                                 "Contribution guidelines", repo_name)
            if analysis.has_license:
                self._add_feature(feature_map, "License", "documentation",
                                 "License file", repo_name)
            if analysis.has_changelog:
                self._add_feature(feature_map, "Changelog", "documentation",
                                 "Version history", repo_name)
            
            # Add CI/CD features
            if analysis.has_ci:
                for platform in analysis.ci_platforms:
                    self._add_feature(feature_map, f"CI: {platform}", "ci_cd",
                                     f"CI/CD using {platform}", repo_name)
            
            # Add testing features
            if analysis.has_tests:
                for framework in analysis.test_frameworks:
                    self._add_feature(feature_map, f"Tests: {framework}", "testing",
                                     f"Testing with {framework}", repo_name)
            
            # Add architecture features
            for pattern in analysis.architecture_patterns:
                self._add_feature(feature_map, f"Architecture: {pattern}", "architecture",
                                 f"{pattern} architecture pattern", repo_name)
            
            # Add pattern features
            for pattern in analysis.patterns:
                self._add_feature(feature_map, pattern.name, pattern.pattern_type,
                                 pattern.description, repo_name,
                                 examples=pattern.examples)
        
        # Calculate prevalence and importance
        features = list(feature_map.values())
        for feature in features:
            feature.prevalence = len(feature.sources) / len(self.analyses)
            feature.importance_score = self._calculate_importance(feature)
        
        # Sort by importance
        features.sort(key=lambda f: f.importance_score, reverse=True)
        
        return features
    
    def _add_feature(
        self,
        feature_map: dict[str, CombinedFeature],
        name: str,
        category: str,
        description: str,
        source: str,
        examples: list[str] = None,
    ) -> None:
        """Add or update a feature in the map."""
        if name not in feature_map:
            feature_map[name] = CombinedFeature(
                name=name,
                category=category,
                description=description,
            )
        
        feature = feature_map[name]
        if source not in feature.sources:
            feature.sources.append(source)
        
        if examples:
            feature.examples.append({
                "source": source,
                "files": examples,
            })
    
    def _calculate_importance(self, feature: CombinedFeature) -> float:
        """Calculate feature importance score."""
        # Base score from prevalence
        score = feature.prevalence * 0.5
        
        # Category weights
        category_weights = {
            "documentation": 0.2,
            "ci_cd": 0.25,
            "testing": 0.25,
            "architecture": 0.2,
            "other": 0.1,
        }
        
        weight = category_weights.get(feature.category, 0.1)
        score += weight
        
        # Bonus for high prevalence
        if feature.prevalence >= 0.8:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_coverage(self, combined: CombinedAnalysis) -> None:
        """Calculate coverage metrics."""
        if not self.analyses:
            return
        
        readme_count = sum(1 for a in self.analyses if a.has_readme)
        license_count = sum(1 for a in self.analyses if a.has_license)
        ci_count = sum(1 for a in self.analyses if a.has_ci)
        test_count = sum(1 for a in self.analyses if a.has_tests)
        
        total = len(self.analyses)
        combined.readme_coverage = readme_count / total
        combined.license_coverage = license_count / total
        combined.ci_coverage = ci_count / total
        combined.test_coverage = test_count / total
    
    def _calculate_quality_metrics(self, combined: CombinedAnalysis) -> None:
        """Calculate average quality metrics."""
        if not self.analyses:
            return
        
        quality_sum = sum(a.quality_score for a in self.analyses)
        maintainability_sum = sum(a.maintainability_score for a in self.analyses)
        
        combined.avg_quality_score = quality_sum / len(self.analyses)
        combined.avg_maintainability_score = maintainability_sum / len(self.analyses)
    
    def _combine_architecture_patterns(self) -> dict[str, int]:
        """Combine architecture patterns."""
        patterns: dict[str, int] = {}
        
        for analysis in self.analyses:
            for pattern in analysis.architecture_patterns:
                patterns[pattern] = patterns.get(pattern, 0) + 1
        
        return patterns
    
    def _combine_dependencies(self) -> list[dict[str, Any]]:
        """Combine and rank dependencies."""
        dep_count: dict[str, int] = defaultdict(int)
        dep_info: dict[str, DependencyInfo] = {}
        
        for analysis in self.analyses:
            for dep in analysis.dependencies:
                dep_count[dep.name] += 1
                if dep.name not in dep_info:
                    dep_info[dep.name] = dep
        
        # Sort by usage count
        sorted_deps = sorted(dep_count.items(), key=lambda x: x[1], reverse=True)
        
        # Return top dependencies
        result = []
        for name, count in sorted_deps[:20]:
            info = dep_info[name]
            result.append({
                "name": name,
                "usage_count": count,
                "prevalence": count / len(self.analyses),
                "source": info.source,
                "is_dev": info.is_dev,
            })
        
        return result
    
    def _generate_recommendations(self, combined: CombinedAnalysis) -> None:
        """Generate best practices and recommendations."""
        # Common best practices (features in >50% of repos)
        common = []
        for feature in combined.features:
            if feature.prevalence >= 0.5:
                common.append(f"{feature.name}: {feature.description}")
        
        combined.common_best_practices = common[:10]
        
        # Recommendations (features in <50% but important)
        recommendations = []
        
        if combined.readme_coverage < 1.0:
            recommendations.append(
                f"Add README to {int((1-combined.readme_coverage)*100)}% of repos without one"
            )
        
        if combined.license_coverage < 1.0:
            recommendations.append(
                f"Add LICENSE to {int((1-combined.license_coverage)*100)}% of repos without one"
            )
        
        if combined.ci_coverage < 0.8:
            recommendations.append(
                f"Set up CI/CD for {int((1-combined.ci_coverage)*100)}% of repos"
            )
        
        if combined.test_coverage < 0.8:
            recommendations.append(
                f"Add tests to {int((1-combined.test_coverage)*100)}% of repos"
            )
        
        # Recommend standardization
        if len(combined.tech_stack.ci_platforms) > 1:
            top_ci = max(combined.tech_stack.ci_platforms.items(), key=lambda x: x[1])
            recommendations.append(
                f"Consider standardizing on {top_ci[0]} for CI/CD"
            )
        
        if len(combined.tech_stack.test_frameworks) > 2:
            recommendations.append(
                "Consider standardizing test frameworks across repositories"
            )
        
        combined.recommended_practices = recommendations
    
    def export_to_json(self, filepath: str) -> None:
        """Export combined analysis to JSON."""
        combined = self.combine()
        with open(filepath, 'w') as f:
            json.dump(combined.to_dict(), f, indent=2)
    
    def generate_report(self) -> str:
        """Generate a markdown report."""
        combined = self.combine()
        
        report = f"""# Organization Analysis Report: {combined.organization}

Generated: {combined.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}
Repositories Analyzed: {combined.repository_count}

## Quality Metrics

| Metric | Score |
|--------|-------|
| Average Quality Score | {combined.avg_quality_score:.2%} |
| Average Maintainability | {combined.avg_maintainability_score:.2%} |
| README Coverage | {combined.readme_coverage:.2%} |
| License Coverage | {combined.license_coverage:.2%} |
| CI/CD Coverage | {combined.ci_coverage:.2%} |
| Test Coverage | {combined.test_coverage:.2%} |

## Technology Stack

### Languages
"""
        
        for lang, count in sorted(combined.tech_stack.languages.items(), key=lambda x: x[1], reverse=True):
            report += f"- {lang}: {count} repos\n"
        
        report += "\n### CI/CD Platforms\n"
        for platform, count in sorted(combined.tech_stack.ci_platforms.items(), key=lambda x: x[1], reverse=True):
            report += f"- {platform}: {count} repos\n"
        
        report += "\n### Test Frameworks\n"
        for framework, count in sorted(combined.tech_stack.test_frameworks.items(), key=lambda x: x[1], reverse=True):
            report += f"- {framework}: {count} repos\n"
        
        report += "\n## Common Best Practices\n"
        for practice in combined.common_best_practices:
            report += f"- {practice}\n"
        
        report += "\n## Recommendations\n"
        for rec in combined.recommended_practices:
            report += f"- {rec}\n"
        
        report += "\n## Top Features\n"
        for feature in combined.features[:10]:
            report += f"- **{feature.name}** ({feature.category}): {feature.prevalence:.0%} prevalence\n"
        
        return report
