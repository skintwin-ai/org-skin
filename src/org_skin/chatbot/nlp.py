"""
NLP Processor

Natural language processing for understanding user queries.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class NLPResult:
    """Result of NLP processing."""
    action: Optional[str] = None
    entities: dict[str, Any] = None
    confidence: float = 0.0
    raw_text: str = ""
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


class NLPProcessor:
    """
    Natural language processor for understanding user queries.
    
    Uses a combination of:
    - Rule-based pattern matching
    - Entity extraction
    - Optional LLM-based understanding
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the NLP processor.
        
        Args:
            api_key: OpenAI API key for LLM-based processing (optional).
        """
        self.api_key = api_key
        self._setup_patterns()
    
    def _setup_patterns(self) -> None:
        """Set up intent patterns."""
        self.intent_patterns = {
            "list_repos": [
                r"list\s+(?:all\s+)?repos(?:itories)?",
                r"show\s+(?:all\s+)?repos(?:itories)?",
                r"get\s+(?:all\s+)?repos(?:itories)?",
                r"what\s+repos(?:itories)?\s+(?:are\s+there|exist)",
            ],
            "describe_repo": [
                r"describe\s+(?:repo(?:sitory)?\s+)?(\w+[-\w]*)",
                r"(?:tell\s+me\s+)?about\s+(?:repo(?:sitory)?\s+)?(\w+[-\w]*)",
                r"(?:what\s+is|info\s+(?:on|about))\s+(?:repo(?:sitory)?\s+)?(\w+[-\w]*)",
                r"details?\s+(?:for|of|on)\s+(?:repo(?:sitory)?\s+)?(\w+[-\w]*)",
            ],
            "list_issues": [
                r"(?:list|show|get)\s+issues?\s+(?:in|for|of)\s+(\w+[-\w]*)",
                r"what\s+issues?\s+(?:are\s+)?(?:in|for)\s+(\w+[-\w]*)",
                r"(\w+[-\w]*)\s+issues?",
            ],
            "create_issue": [
                r"create\s+(?:an?\s+)?issue\s+(?:in|for)\s+(\w+[-\w]*)",
                r"(?:new|add)\s+issue\s+(?:in|for|to)\s+(\w+[-\w]*)",
                r"open\s+(?:an?\s+)?issue\s+(?:in|for)\s+(\w+[-\w]*)",
            ],
            "org_overview": [
                r"org(?:anization)?\s+(?:overview|summary|info|details?)",
                r"(?:tell\s+me\s+)?about\s+(?:the\s+)?org(?:anization)?",
                r"(?:what\s+is|describe)\s+(?:the\s+)?org(?:anization)?",
            ],
            "scan_org": [
                r"scan\s+(?:the\s+)?org(?:anization)?",
                r"map\s+(?:the\s+)?org(?:anization)?",
                r"(?:full\s+)?org(?:anization)?\s+scan",
            ],
            "help": [
                r"help",
                r"what\s+can\s+you\s+do",
                r"how\s+(?:do\s+I|to)\s+use",
                r"commands?",
                r"capabilities",
            ],
        }
        
        self.entity_patterns = {
            "repository": [
                r"repo(?:sitory)?\s+(\w+[-\w]*)",
                r"in\s+(\w+[-\w]*)",
                r"for\s+(\w+[-\w]*)",
            ],
            "organization": [
                r"org(?:anization)?\s+(\w+[-\w]*)",
                r"(\w+[-\w]*)\s+org(?:anization)?",
            ],
            "issue_number": [
                r"issue\s+#?(\d+)",
                r"#(\d+)",
            ],
            "title": [
                r"titled?\s+['\"]([^'\"]+)['\"]",
                r"titled?\s+(.+?)(?:\s+(?:with|body|in)|$)",
            ],
        }
    
    async def understand(
        self,
        text: str,
        context: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Understand a natural language query.
        
        Args:
            text: User input text.
            context: Conversation context.
            
        Returns:
            Dictionary with action, entities, and confidence.
        """
        text = text.strip().lower()
        context = context or {}
        
        # Try rule-based understanding first
        result = self._rule_based_understand(text)
        
        # If confidence is low and we have an API key, try LLM
        if result.confidence < 0.5 and self.api_key:
            llm_result = await self._llm_understand(text, context)
            if llm_result.confidence > result.confidence:
                result = llm_result
        
        return {
            "action": result.action,
            "entities": result.entities,
            "confidence": result.confidence,
        }
    
    def _rule_based_understand(self, text: str) -> NLPResult:
        """Rule-based intent and entity extraction."""
        result = NLPResult(raw_text=text)
        
        # Match intent
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.action = intent
                    result.confidence = 0.8
                    
                    # Extract entity from match groups if present
                    if match.groups():
                        if intent in ("describe_repo", "list_issues", "create_issue"):
                            result.entities["repository"] = match.group(1)
                    break
            if result.action:
                break
        
        # Extract additional entities
        for entity_type, patterns in self.entity_patterns.items():
            if entity_type not in result.entities:
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        result.entities[entity_type] = match.group(1)
                        break
        
        # Adjust confidence based on entity extraction
        if result.action and result.entities:
            result.confidence = min(0.95, result.confidence + 0.1)
        
        return result
    
    async def _llm_understand(
        self,
        text: str,
        context: dict[str, Any],
    ) -> NLPResult:
        """LLM-based understanding using OpenAI."""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            system_prompt = """You are an NLP parser for a GitHub organization management bot.
Extract the user's intent and entities from their message.

Possible intents:
- list_repos: List repositories
- describe_repo: Get info about a specific repository
- list_issues: List issues in a repository
- create_issue: Create a new issue
- org_overview: Get organization overview
- scan_org: Scan/map the organization
- help: Get help

Possible entities:
- repository: Name of a repository
- organization: Name of an organization
- issue_number: Issue number
- title: Title for new issue

Respond in JSON format:
{"action": "intent_name", "entities": {"entity_name": "value"}, "confidence": 0.0-1.0}
"""
            
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                max_tokens=200,
            )
            
            import json
            result_text = response.choices[0].message.content
            parsed = json.loads(result_text)
            
            return NLPResult(
                action=parsed.get("action"),
                entities=parsed.get("entities", {}),
                confidence=parsed.get("confidence", 0.7),
                raw_text=text,
            )
            
        except Exception as e:
            logger.warning(f"LLM understanding failed: {e}")
            return NLPResult(raw_text=text)
    
    def extract_entities(self, text: str) -> dict[str, str]:
        """Extract entities from text."""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities[entity_type] = match.group(1)
                    break
        
        return entities
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for processing."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation except hyphens in words
        text = re.sub(r'[^\w\s-]', '', text)
        
        return text.strip()
    
    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        return self.normalize_text(text).split()
    
    def get_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - remove common words
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
            'until', 'while', 'what', 'which', 'who', 'whom', 'this',
            'that', 'these', 'those', 'am', 'i', 'me', 'my', 'myself',
            'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
            'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
            'they', 'them', 'their', 'theirs', 'themselves',
        }
        
        tokens = self.tokenize(text)
        return [t for t in tokens if t not in stopwords and len(t) > 2]
