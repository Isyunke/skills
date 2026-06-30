#!/usr/bin/env python3
"""
测试简历解析器

Usage:
    python -m pytest tests/test_resume_parser.py -v
"""

import sys
import os
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.resume_parser import ResumeParser


class TestResumeParser(unittest.TestCase):
    """测试简历解析器"""

    def setUp(self):
        """测试前准备"""
        self.parser = ResumeParser()
        self.examples_dir = Path(__file__).parent.parent / "examples"

    def test_parse_markdown(self):
        """测试解析 Markdown 文件"""
        resume_path = self.examples_dir / "sample-resume.md"

        if not resume_path.exists():
            self.skipTest(f"示例文件不存在: {resume_path}")

        result = self.parser.parse(str(resume_path))

        # 检查基本结构
        self.assertIn('raw_text', result)
        self.assertIn('basic_info', result)
        self.assertIn('skills', result)
        self.assertIn('work_experience', result)
        self.assertIn('project_experience', result)
        self.assertIn('education', result)

        # 检查基本内容
        self.assertTrue(len(result['raw_text']) > 0)
        self.assertTrue(len(result['skills']) > 0)

    def test_extract_basic_info(self):
        """测试提取基本信息"""
        # 模拟简历内容
        self.parser.content = """
张三 - 高级后端工程师

📱 138-0000-0000
📧 zhangsan@example.com
📍 北京
"""

        info = self.parser._extract_basic_info()

        self.assertEqual(info['name'], '张三 - 高级后端工程师')
        self.assertEqual(info['email'], 'zhangsan@example.com')

    def test_extract_skills(self):
        """测试提取技能"""
        # 模拟简历内容
        self.parser.content = """
技能清单：
- Python (精通)
- Django (熟练)
- MySQL (精通)
- Redis (熟练)
"""

        skills = self.parser._extract_skills()

        # 检查是否提取到技能
        skill_names = [s['name'] for s in skills]
        self.assertIn('Python', skill_names)
        self.assertIn('Django', skill_names)
        self.assertIn('MySQL', skill_names)
        self.assertIn('Redis', skill_names)

    def test_extract_education(self):
        """测试提取教育背景"""
        # 模拟简历内容
        self.parser.content = """
教育背景：
XX 大学 - 计算机科学 - 本科
"""

        education = self.parser._extract_education()

        # 检查是否提取到教育背景
        self.assertTrue(len(education) > 0)
        self.assertIn('XX 大学', education[0]['school'])

    def test_invalid_file(self):
        """测试无效文件"""
        with self.assertRaises(FileNotFoundError):
            self.parser.parse("nonexistent.md")

    def test_unsupported_format(self):
        """测试不支持的格式"""
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            with self.assertRaises(ValueError):
                self.parser.parse(temp_path)
        finally:
            os.unlink(temp_path)


class TestResumeParserIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_parse_flow(self):
        """测试完整解析流程"""
        parser = ResumeParser()
        examples_dir = Path(__file__).parent.parent / "examples"
        resume_path = examples_dir / "sample-resume.md"

        if not resume_path.exists():
            self.skipTest(f"示例文件不存在: {resume_path}")

        # 解析简历
        result = parser.parse(str(resume_path))

        # 检查结果
        self.assertIsInstance(result, dict)
        self.assertIn('raw_text', result)
        self.assertIn('basic_info', result)
        self.assertIn('skills', result)
        self.assertIn('work_experience', result)
        self.assertIn('project_experience', result)
        self.assertIn('education', result)
        self.assertIn('certificates', result)

        # 检查内容不为空
        self.assertTrue(len(result['raw_text']) > 0)

        # 输出结果（用于调试）
        import json
        print("\n解析结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    unittest.main()
