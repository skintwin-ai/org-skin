"""
AIML Parser

Parses AIML templates and extracts GraphQL queries and workflow definitions.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from xml.etree import ElementTree as ET
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""
    name: str
    operation_type: str  # 'graphql', 'mutation', 'condition', 'transform'
    operation: str
    variables: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    """Represents a complete workflow."""
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedTemplate:
    """Result of parsing an AIML template."""
    think: Optional[str] = None
    graphql: Optional[str] = None
    mutation: Optional[str] = None
    variables: dict[str, Any] = field(default_factory=dict)
    workflow: Optional[Workflow] = None
    analysis: Optional[dict[str, Any]] = None
    text: Optional[str] = None


class AIMLParser:
    """
    Parser for AIML templates with GraphQL extensions.
    
    Supports:
    - Standard AIML elements (think, get, set, star)
    - GraphQL query blocks
    - Mutation blocks
    - Workflow definitions
    - Analysis specifications
    """
    
    def __init__(self):
        """Initialize the parser."""
        self.context: dict[str, Any] = {}
    
    def parse_template(self, template: str, wildcards: dict[str, str] = None) -> ParsedTemplate:
        """
        Parse an AIML template string.
        
        Args:
            template: AIML template string.
            wildcards: Extracted wildcard values from pattern matching.
            
        Returns:
            ParsedTemplate with extracted components.
        """
        wildcards = wildcards or {}
        result = ParsedTemplate()
        
        # Substitute wildcards
        template = self._substitute_wildcards(template, wildcards)
        
        # Extract think block
        think_match = re.search(r'<think>(.*?)</think>', template, re.DOTALL)
        if think_match:
            result.think = think_match.group(1).strip()
        
        # Extract GraphQL query
        graphql_match = re.search(r'<graphql>(.*?)</graphql>', template, re.DOTALL)
        if graphql_match:
            result.graphql = graphql_match.group(1).strip()
        
        # Extract mutation
        mutation_match = re.search(r'<mutation>(.*?)</mutation>', template, re.DOTALL)
        if mutation_match:
            result.mutation = mutation_match.group(1).strip()
        
        # Extract variables
        vars_match = re.search(r'<vars>(.*?)</vars>', template, re.DOTALL)
        if vars_match:
            try:
                result.variables = json.loads(vars_match.group(1).strip())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse variables: {vars_match.group(1)}")
        
        # Extract workflow
        workflow_match = re.search(r'<workflow[^>]*>(.*?)</workflow>', template, re.DOTALL)
        if workflow_match:
            result.workflow = self._parse_workflow(workflow_match.group(0))
        
        # Extract analysis
        analysis_match = re.search(r'<analysis[^>]*>(.*?)</analysis>', template, re.DOTALL)
        if analysis_match:
            result.analysis = self._parse_analysis(analysis_match.group(0))
        
        # Extract plain text (everything not in special tags)
        text = template
        for tag in ['think', 'graphql', 'mutation', 'vars', 'workflow', 'analysis']:
            text = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.DOTALL)
        text = text.strip()
        if text:
            result.text = text
        
        return result
    
    def _substitute_wildcards(self, template: str, wildcards: dict[str, str]) -> str:
        """Substitute wildcard references in template."""
        # Handle <star/> and <star index="N"/>
        def replace_star(match):
            index = match.group(1)
            if index:
                key = f"star{index}"
            else:
                key = "star1"
            return wildcards.get(key, match.group(0))
        
        template = re.sub(r'<star(?:\s+index="(\d+)")?/>', replace_star, template)
        
        # Handle <get name="..."/>
        def replace_get(match):
            name = match.group(1)
            return str(self.context.get(name, f"<{name}>"))
        
        template = re.sub(r'<get\s+name="([^"]+)"/>', replace_get, template)
        
        return template
    
    def _parse_workflow(self, workflow_xml: str) -> Workflow:
        """Parse a workflow definition."""
        # Extract workflow name
        name_match = re.search(r'<workflow\s+name="([^"]+)"', workflow_xml)
        workflow_name = name_match.group(1) if name_match else "unnamed"
        
        workflow = Workflow(name=workflow_name)
        
        # Extract steps
        step_pattern = r'<step\s+name="([^"]+)">(.*?)</step>'
        for step_match in re.finditer(step_pattern, workflow_xml, re.DOTALL):
            step_name = step_match.group(1)
            step_content = step_match.group(2)
            
            # Determine operation type
            if '<graphql>' in step_content:
                op_type = 'graphql'
                op_match = re.search(r'<graphql>(.*?)</graphql>', step_content, re.DOTALL)
                operation = op_match.group(1).strip() if op_match else ""
            elif '<mutation>' in step_content:
                op_type = 'mutation'
                op_match = re.search(r'<mutation>(.*?)</mutation>', step_content, re.DOTALL)
                operation = op_match.group(1).strip() if op_match else ""
            elif '<condition>' in step_content:
                op_type = 'condition'
                op_match = re.search(r'<condition>(.*?)</condition>', step_content, re.DOTALL)
                operation = op_match.group(1).strip() if op_match else ""
            else:
                op_type = 'transform'
                operation = step_content.strip()
            
            # Extract variables
            vars_match = re.search(r'<vars>(.*?)</vars>', step_content, re.DOTALL)
            variables = {}
            if vars_match:
                try:
                    variables = json.loads(vars_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
            
            # Extract dependencies
            depends_match = re.search(r'<depends>(.*?)</depends>', step_content, re.DOTALL)
            depends_on = []
            if depends_match:
                depends_on = [d.strip() for d in depends_match.group(1).split(',')]
            
            workflow.steps.append(WorkflowStep(
                name=step_name,
                operation_type=op_type,
                operation=operation,
                variables=variables,
                depends_on=depends_on,
            ))
        
        return workflow
    
    def _parse_analysis(self, analysis_xml: str) -> dict[str, Any]:
        """Parse an analysis specification."""
        result = {}
        
        # Extract analysis type
        type_match = re.search(r'<analysis\s+type="([^"]+)"', analysis_xml)
        if type_match:
            result['type'] = type_match.group(1)
        
        # Extract target(s)
        target_match = re.search(r'<target>(.*?)</target>', analysis_xml, re.DOTALL)
        if target_match:
            result['target'] = target_match.group(1).strip()
        
        targets_match = re.search(r'<targets>(.*?)</targets>', analysis_xml, re.DOTALL)
        if targets_match:
            result['targets'] = re.findall(r'<target>(.*?)</target>', targets_match.group(1))
        
        # Extract metrics
        metrics = []
        for metric_match in re.finditer(r'<metric\s+name="([^"]+)"', analysis_xml):
            metrics.append(metric_match.group(1))
        if metrics:
            result['metrics'] = metrics
        
        # Extract dimensions
        dimensions = []
        for dim_match in re.finditer(r'<dimension\s+name="([^"]+)"', analysis_xml):
            dimensions.append(dim_match.group(1))
        if dimensions:
            result['dimensions'] = dimensions
        
        return result
    
    def set_context(self, name: str, value: Any) -> None:
        """Set a context variable."""
        self.context[name] = value
    
    def get_context(self, name: str) -> Any:
        """Get a context variable."""
        return self.context.get(name)
    
    def clear_context(self) -> None:
        """Clear all context variables."""
        self.context.clear()


class AIMLFileParser:
    """Parser for AIML files."""
    
    def __init__(self):
        """Initialize the file parser."""
        self.categories: list[dict[str, str]] = []
    
    def parse_file(self, filepath: str) -> list[dict[str, str]]:
        """
        Parse an AIML file.
        
        Args:
            filepath: Path to AIML file.
            
        Returns:
            List of category dictionaries with pattern and template.
        """
        self.categories = []
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            for category in root.findall('.//category'):
                pattern_elem = category.find('pattern')
                template_elem = category.find('template')
                that_elem = category.find('that')
                
                if pattern_elem is not None and template_elem is not None:
                    cat_dict = {
                        'pattern': self._get_element_text(pattern_elem),
                        'template': self._get_element_content(template_elem),
                    }
                    if that_elem is not None:
                        cat_dict['that'] = self._get_element_text(that_elem)
                    
                    self.categories.append(cat_dict)
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse AIML file {filepath}: {e}")
        
        return self.categories
    
    def _get_element_text(self, elem: ET.Element) -> str:
        """Get text content of an element."""
        return ''.join(elem.itertext()).strip()
    
    def _get_element_content(self, elem: ET.Element) -> str:
        """Get full content of an element including child tags."""
        return ET.tostring(elem, encoding='unicode', method='xml')
