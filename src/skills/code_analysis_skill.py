"""
Code analysis skill for detecting programming languages and analyzing code.

This skill provides functionality to identify programming languages in code blocks
and perform basic code analysis.
"""

import re
from typing import Optional, Dict, List


class CodeAnalysisSkill:
    """
    Skill for analyzing code blocks and detecting programming languages.

    Uses keyword and pattern matching to identify programming languages.

    Example:
        >>> skill = CodeAnalysisSkill()
        >>> language = skill.detect_language("def main():\\n    print('hello')")
        >>> print(language)
        'python'
    """

    def __init__(self):
        """Initialize the code analysis skill."""
        # Language detection patterns
        self.language_patterns = {
            'python': {
                'keywords': ['def ', 'import ', 'from ', 'class ', '__init__', 'self.', 'elif ', 'None', 'True', 'False'],
                'patterns': [r'def \w+\(', r'^\s*import ', r':\s*$', r'__\w+__'],
                'weight': 1.0
            },
            'java': {
                'keywords': ['public class', 'private ', 'public ', 'protected ', 'void ', 'static ', 'extends ', 'implements '],
                'patterns': [r'public\s+class', r'System\.out\.println', r'\w+\s+\w+\s*\(.*\)\s*{'],
                'weight': 1.0
            },
            'javascript': {
                'keywords': ['function ', 'const ', 'let ', 'var ', '=>', 'console.log', 'async ', 'await '],
                'patterns': [r'function\s+\w+\s*\(', r'=>', r'console\.log', r'async\s+function'],
                'weight': 1.0
            },
            'typescript': {
                'keywords': ['interface ', 'type ', ': string', ': number', ': boolean', 'export ', 'import '],
                'patterns': [r':\s*\w+(\[\])?(\s*\||&)?', r'interface\s+\w+', r'type\s+\w+\s*='],
                'weight': 1.0
            },
            'cpp': {
                'keywords': ['#include', 'std::', 'cout', 'cin', 'namespace ', 'template<', 'virtual '],
                'patterns': [r'#include\s*<', r'std::', r'cout\s*<<', r'template\s*<'],
                'weight': 1.0
            },
            'c': {
                'keywords': ['#include', 'printf', 'scanf', 'malloc', 'free', 'sizeof'],
                'patterns': [r'#include\s*<\w+\.h>', r'printf\s*\(', r'int\s+main\s*\('],
                'weight': 1.0
            },
            'go': {
                'keywords': ['func ', 'package ', 'import ', 'defer ', 'go ', 'chan ', ':='],
                'patterns': [r'func\s+\w+\(', r'package\s+\w+', r':='],
                'weight': 1.0
            },
            'rust': {
                'keywords': ['fn ', 'let mut', 'pub ', 'impl ', 'trait ', '::'],
                'patterns': [r'fn\s+\w+\(', r'let\s+mut\s+\w+', r'impl\s+\w+'],
                'weight': 1.0
            },
            'ruby': {
                'keywords': ['def ', 'end', 'puts ', 'require ', 'class ', 'module '],
                'patterns': [r'def\s+\w+', r'^\s*end\s*$', r'puts\s+'],
                'weight': 1.0
            },
            'php': {
                'keywords': ['<?php', '$', 'function ', 'echo ', 'require '],
                'patterns': [r'<\?php', r'\$\w+', r'function\s+\w+\s*\('],
                'weight': 1.0
            },
            'sql': {
                'keywords': ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'UPDATE ', 'DELETE ', 'CREATE TABLE'],
                'patterns': [r'SELECT\s+.*\s+FROM', r'INSERT\s+INTO', r'CREATE\s+TABLE'],
                'weight': 1.0
            },
            'html': {
                'keywords': ['<html', '<div', '<body', '<head', '</'],
                'patterns': [r'<\w+[^>]*>', r'<\/\w+>'],
                'weight': 1.0
            },
            'css': {
                'keywords': ['{', '}', ':', ';', 'px', 'color:', 'background:'],
                'patterns': [r'\w+\s*:\s*[^;]+;', r'#[\da-fA-F]{3,6}', r'\.\w+\s*\{'],
                'weight': 0.8
            },
            'json': {
                'keywords': ['{', '}', '[', ']', ':', '"'],
                'patterns': [r'"\w+"\s*:\s*', r'^\s*{', r'^\s*\['],
                'weight': 0.7
            },
            'yaml': {
                'keywords': [':', '-', 'name:', 'version:'],
                'patterns': [r'^\w+:\s*\w+', r'^\s*-\s+\w+'],
                'weight': 0.6
            },
            'bash': {
                'keywords': ['#!/bin/bash', 'echo ', 'if [', 'then', 'fi', 'export '],
                'patterns': [r'#!/bin/bash', r'if\s+\[', r'echo\s+'],
                'weight': 1.0
            }
        }

    def detect_language(self, code: str) -> Optional[str]:
        """
        Detect the programming language of a code snippet.

        Uses keyword and pattern matching with weighted scoring.

        Args:
            code: Code snippet to analyze

        Returns:
            Detected language name (lowercase) or None if uncertain
        """
        if not code or len(code.strip()) < 10:
            return None

        scores: Dict[str, float] = {}

        for language, rules in self.language_patterns.items():
            score = 0.0

            # Check keywords
            for keyword in rules['keywords']:
                if keyword in code:
                    score += 1.0

            # Check patterns
            for pattern in rules['patterns']:
                if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                    score += 1.5

            # Apply language weight
            scores[language] = score * rules['weight']

        # Return language with highest score (if above threshold)
        if scores:
            max_language = max(scores, key=scores.get)
            max_score = scores[max_language]

            # Require minimum score to be confident
            if max_score >= 2.0:
                return max_language

        return None

    def detect_language_from_shebang(self, code: str) -> Optional[str]:
        """
        Detect language from shebang line (#!/usr/bin/...).

        Args:
            code: Code snippet

        Returns:
            Language name or None
        """
        first_line = code.split('\n')[0].strip()

        shebang_map = {
            'python': ['#!/usr/bin/python', '#!/usr/bin/env python'],
            'bash': ['#!/bin/bash', '#!/bin/sh'],
            'ruby': ['#!/usr/bin/ruby', '#!/usr/bin/env ruby'],
            'perl': ['#!/usr/bin/perl', '#!/usr/bin/env perl'],
            'php': ['#!/usr/bin/php'],
        }

        for language, shebangs in shebang_map.items():
            if any(shebang in first_line for shebang in shebangs):
                return language

        return None

    def estimate_complexity(self, code: str) -> Dict[str, int]:
        """
        Estimate code complexity metrics.

        Args:
            code: Code snippet

        Returns:
            Dictionary with complexity metrics
        """
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        # Count various complexity indicators
        metrics = {
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'indent_levels': self._max_indent_level(code),
            'functions': len(re.findall(r'def\s+\w+|function\s+\w+|func\s+\w+', code)),
            'classes': len(re.findall(r'class\s+\w+', code)),
            'conditionals': len(re.findall(r'\b(if|else|elif|switch|case)\b', code)),
            'loops': len(re.findall(r'\b(for|while|do)\b', code)),
        }

        return metrics

    def _max_indent_level(self, code: str) -> int:
        """
        Calculate maximum indentation level in code.

        Args:
            code: Code snippet

        Returns:
            Maximum indent level
        """
        max_level = 0
        for line in code.split('\n'):
            if line.strip():
                # Count leading spaces/tabs
                leading_spaces = len(line) - len(line.lstrip())
                indent_level = leading_spaces // 4  # Assume 4-space indents
                max_level = max(max_level, indent_level)

        return max_level

    def extract_imports(self, code: str, language: Optional[str] = None) -> List[str]:
        """
        Extract import statements from code.

        Args:
            code: Code snippet
            language: Programming language (auto-detected if None)

        Returns:
            List of imported modules/packages
        """
        if language is None:
            language = self.detect_language(code)

        imports = []

        if language == 'python':
            # Python imports
            import_lines = re.findall(r'^(?:from\s+(\S+)|import\s+(\S+))', code, re.MULTILINE)
            for from_module, import_module in import_lines:
                imports.append(from_module or import_module)

        elif language in ['java', 'javascript', 'typescript']:
            # Java/JS/TS imports
            import_lines = re.findall(r'import\s+[^;]+', code)
            imports.extend(import_lines)

        elif language == 'go':
            # Go imports
            import_lines = re.findall(r'import\s+"([^"]+)"', code)
            imports.extend(import_lines)

        return imports

    def has_documentation(self, code: str, language: Optional[str] = None) -> bool:
        """
        Check if code contains documentation (docstrings, comments).

        Args:
            code: Code snippet
            language: Programming language

        Returns:
            True if documentation found, False otherwise
        """
        if language is None:
            language = self.detect_language(code)

        # Check for docstrings (Python)
        if '"""' in code or "'''" in code:
            return True

        # Check for multi-line comments
        if '/*' in code and '*/' in code:
            return True

        # Check for single-line comments
        comment_patterns = ['#', '//', '--', '%']
        for pattern in comment_patterns:
            if pattern in code:
                return True

        return False
