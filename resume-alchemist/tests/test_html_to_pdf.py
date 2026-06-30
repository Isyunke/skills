#!/usr/bin/env python3
"""
Tests for HTML to PDF converter.

Usage:
    python -m pytest tests/test_html_to_pdf.py -v
"""

import sys
import os
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.html_to_pdf import atomic_write


class TestAtomicWrite(unittest.TestCase):
    """Test atomic write utility."""

    def test_atomic_write_creates_file(self):
        """Should create file with correct content."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            tmp_path = f.name

        try:
            atomic_write(tmp_path, b"hello world")
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, 'rb') as f:
                self.assertEqual(f.read(), b"hello world")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_atomic_write_overwrites(self):
        """Should overwrite existing file atomically."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='wb') as f:
            f.write(b"old content")
            tmp_path = f.name

        try:
            atomic_write(tmp_path, b"new content")
            with open(tmp_path, 'rb') as f:
                self.assertEqual(f.read(), b"new content")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_atomic_write_empty_content(self):
        """Should handle empty content."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            tmp_path = f.name

        try:
            atomic_write(tmp_path, b"")
            with open(tmp_path, 'rb') as f:
                self.assertEqual(f.read(), b"")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_atomic_write_binary_content(self):
        """Should handle binary content."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            tmp_path = f.name

        try:
            data = bytes(range(256))
            atomic_write(tmp_path, data)
            with open(tmp_path, 'rb') as f:
                self.assertEqual(f.read(), data)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_tmp_file_cleaned_up(self):
        """Should not leave .tmp file behind."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            tmp_path = f.name

        try:
            atomic_write(tmp_path, b"test")
            self.assertFalse(os.path.exists(tmp_path + ".tmp"))
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
