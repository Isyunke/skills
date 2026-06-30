#!/usr/bin/env python3
"""
Tests for keyword matcher.

Usage:
    python -m pytest tests/test_keyword_matcher.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.keyword_matcher import extract_keywords, match_keywords


class TestExtractKeywords(unittest.TestCase):
    """Test keyword extraction."""

    def test_extract_programming_languages(self):
        """Should extract programming languages."""
        text = "I use Python and Java daily, sometimes Go."
        keywords = extract_keywords(text)
        self.assertIn('Python', keywords)
        self.assertIn('Java', keywords)
        self.assertIn('Go', keywords)

    def test_extract_frameworks(self):
        """Should extract frameworks."""
        text = "Built with Django and React, also tried Vue."
        keywords = extract_keywords(text)
        self.assertIn('Django', keywords)
        self.assertIn('React', keywords)
        self.assertIn('Vue', keywords)

    def test_extract_databases(self):
        """Should extract databases."""
        text = "MySQL for primary DB, Redis for cache."
        keywords = extract_keywords(text)
        self.assertIn('MySQL', keywords)
        self.assertIn('Redis', keywords)

    def test_extract_tools(self):
        """Should extract tools."""
        text = "Docker containerized, deployed on AWS."
        keywords = extract_keywords(text)
        self.assertIn('Docker', keywords)
        self.assertIn('AWS', keywords)

    def test_extract_concepts(self):
        """Should extract Chinese concepts."""
        text = "高并发系统，使用微服务架构和分布式缓存。"
        keywords = extract_keywords(text)
        self.assertIn('高并发', keywords)
        self.assertIn('微服务', keywords)
        self.assertIn('分布式', keywords)
        self.assertIn('缓存', keywords)

    def test_case_insensitive(self):
        """Should match case-insensitively."""
        text = "python and PYTHON and Python"
        keywords = extract_keywords(text)
        self.assertIn('Python', keywords)

    def test_empty_text(self):
        """Should return empty set for empty text."""
        self.assertEqual(extract_keywords(""), set())

    def test_no_keywords(self):
        """Should return empty set when no keywords found."""
        text = "This is a plain text with no tech keywords."
        self.assertEqual(extract_keywords(text), set())


class TestMatchKeywords(unittest.TestCase):
    """Test keyword matching."""

    def test_full_match(self):
        """Should show full coverage when all JD keywords are in resume."""
        jd = {'Python', 'Django', 'MySQL'}
        resume = {'Python', 'Django', 'MySQL', 'Redis'}
        result = match_keywords(jd, resume)
        self.assertEqual(result['matched'], {'Python', 'Django', 'MySQL'})
        self.assertEqual(result['missing'], set())
        self.assertEqual(result['extra'], {'Redis'})
        self.assertEqual(result['coverage'], 1.0)

    def test_partial_match(self):
        """Should show partial coverage."""
        jd = {'Python', 'Django', 'Kubernetes'}
        resume = {'Python', 'Django', 'MySQL'}
        result = match_keywords(jd, resume)
        self.assertEqual(result['matched'], {'Python', 'Django'})
        self.assertEqual(result['missing'], {'Kubernetes'})
        self.assertEqual(result['extra'], {'MySQL'})
        self.assertAlmostEqual(result['coverage'], 2 / 3)

    def test_no_match(self):
        """Should show zero coverage."""
        jd = {'Python', 'Django'}
        resume = {'Java', 'Spring'}
        result = match_keywords(jd, resume)
        self.assertEqual(result['matched'], set())
        self.assertEqual(result['missing'], {'Python', 'Django'})
        self.assertEqual(result['extra'], {'Java', 'Spring'})
        self.assertEqual(result['coverage'], 0)

    def test_empty_jd(self):
        """Should handle empty JD keywords."""
        jd = set()
        resume = {'Python'}
        result = match_keywords(jd, resume)
        self.assertEqual(result['matched'], set())
        self.assertEqual(result['missing'], set())
        self.assertEqual(result['coverage'], 0)

    def test_empty_resume(self):
        """Should handle empty resume keywords."""
        jd = {'Python'}
        resume = set()
        result = match_keywords(jd, resume)
        self.assertEqual(result['matched'], set())
        self.assertEqual(result['missing'], {'Python'})
        self.assertEqual(result['coverage'], 0)

    def test_both_empty(self):
        """Should handle both empty."""
        result = match_keywords(set(), set())
        self.assertEqual(result['coverage'], 0)


if __name__ == '__main__':
    unittest.main()
