#!/usr/bin/env python3
"""
Resume parser for resume-alchemist.
Supports multiple formats: pdf, doc, docx, md, html, txt

Usage:
    python resume_parser.py <resume_path> [--output <output_path>]

Requirements:
    - pdfplumber (for PDF)
    - python-docx (for DOCX)
    - antiword (for DOC, system dependency)
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class ResumeParser:
    """Parse resume from various formats."""

    def __init__(self):
        self.content = ""
        self.metadata = {}

    def parse(self, file_path: str) -> Dict:
        """Parse resume file and return structured data."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        # Read content based on format
        if suffix == '.md':
            self.content = self._read_markdown(file_path)
        elif suffix == '.html' or suffix == '.htm':
            self.content = self._read_html(file_path)
        elif suffix == '.txt':
            self.content = self._read_text(file_path)
        elif suffix == '.pdf':
            self.content = self._read_pdf(file_path)
        elif suffix == '.docx':
            self.content = self._read_docx(file_path)
        elif suffix == '.doc':
            self.content = self._read_doc(file_path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")

        # Parse content
        return self._parse_content()

    def _read_markdown(self, file_path: str) -> str:
        """Read markdown file."""
        return Path(file_path).read_text(encoding='utf-8')

    def _read_html(self, file_path: str) -> str:
        """Read HTML file and extract text."""
        try:
            from bs4 import BeautifulSoup
            html = Path(file_path).read_text(encoding='utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        except ImportError:
            # Fallback: read raw HTML
            return Path(file_path).read_text(encoding='utf-8')

    def _read_text(self, file_path: str) -> str:
        """Read plain text file."""
        return Path(file_path).read_text(encoding='utf-8')

    def _read_pdf(self, file_path: str) -> str:
        """Read PDF file."""
        try:
            import pdfplumber
            text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return '\n'.join(text)
        except ImportError:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

    def _read_docx(self, file_path: str) -> str:
        """Read DOCX file."""
        try:
            from docx import Document
            doc = Document(file_path)
            text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)
            return '\n'.join(text)
        except ImportError:
            raise ImportError("python-docx not installed. Run: pip install python-docx")

    def _read_doc(self, file_path: str) -> str:
        """Read DOC file using antiword."""
        try:
            import subprocess
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if result.returncode == 0:
                return result.stdout
            else:
                raise RuntimeError(f"antiword failed: {result.stderr}")
        except FileNotFoundError:
            raise ImportError("antiword not installed. Install it first.")

    def _parse_content(self) -> Dict:
        """Parse content and extract structured data."""
        result = {
            'raw_text': self.content,
            'basic_info': self._extract_basic_info(),
            'work_experience': self._extract_work_experience(),
            'project_experience': self._extract_project_experience(),
            'skills': self._extract_skills(),
            'education': self._extract_education(),
            'certificates': self._extract_certificates()
        }
        return result

    def _extract_basic_info(self) -> Dict:
        """Extract basic information."""
        info = {
            'name': '',
            'target_role': '',
            'phone': '',
            'email': '',
            'location': ''
        }

        # Extract name from markdown heading (e.g. "# 张三 - 高级后端工程师")
        lines = self.content.split('\n')
        for line in lines[:10]:
            line = line.strip()
            # Match markdown heading: # Name - Title
            heading_match = re.match(r'^#+\s*(.+?)(?:\s*[-–—]\s*.+)?$', line)
            if heading_match:
                info['name'] = heading_match.group(1).strip()
                break
            # Fallback: short line without special chars
            if line and len(line) < 20 and not any(char in line for char in ['@', '📱', '📧', '📍', '#']):
                info['name'] = line
                break

        # Extract phone
        phone_pattern = r'[\d\+\-\(\)\s]{10,20}'
        phone_match = re.search(phone_pattern, self.content)
        if phone_match:
            info['phone'] = phone_match.group().strip()

        # Extract email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, self.content)
        if email_match:
            info['email'] = email_match.group()

        # Extract location
        location_match = re.search(r'📍\s*(.+)', self.content)
        if location_match:
            info['location'] = location_match.group(1).strip()

        # Extract target role
        role_keywords = ['后端工程师', '前端工程师', '全栈工程师', '产品经理', '设计师', '算法工程师']
        for keyword in role_keywords:
            if keyword in self.content:
                info['target_role'] = keyword
                break

        return info

    def _extract_work_experience(self) -> List[Dict]:
        """Extract work experience from structured markdown."""
        experience = []

        # Company keywords for matching
        company_keywords = r'(?:公司|科技|集团|企业|团队|Siemens|Google|Meta|Amazon|Microsoft|Apple|ByteDance|Alibaba|Tencent)'

        # Pattern 1: "### XX科技有限公司 - 高级后端工程师 (2022-2024)"
        pattern1 = rf'#+\s*(.+?{company_keywords}.*?)\s*[-–—]\s*(.+?)(?:\s*\((\d{{4}}[-.]\d{{4}})\))?\s*$'

        # Pattern 2: "### **西门子 (Siemens)** | 智能制造软件工程师"
        pattern2 = rf'#+\s*\*{{0,2}}(.+?{company_keywords}.*?)\*{{0,2}}\s*[\|｜]\s*\*{{0,2}}(.+?)\*{{0,2}}\s*$'

        # Pattern 3: "### XX科技有限公司 后端工程师"
        position_keywords = r'(?:工程师|经理|总监|架构师|开发|DevOps|SRE|产品经理|设计师)'
        pattern3 = rf'#+\s*(.+?{company_keywords}.*?)\s+({position_keywords}.+?)\s*$'

        for pattern in [pattern1, pattern2, pattern3]:
            for match in re.finditer(pattern, self.content, re.MULTILINE):
                company = match.group(1).strip().strip('*').strip()
                position = match.group(2).strip().strip('*').strip()
                date = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else ''

                # Try to extract date from next line if not found in header
                if not date:
                    next_line_pos = match.end()
                    remaining = self.content[next_line_pos:next_line_pos + 100]
                    date_match = re.match(r'\s*\*{0,2}(\d{4}[-.]\d{2}\s*[-–—]\s*(?:\d{4}[-.]\d{2}|至今|present|now))\*{0,2}', remaining, re.IGNORECASE)
                    if date_match:
                        date = date_match.group(1).strip().strip('*').strip()

                # Avoid duplicates
                if any(e['company'] == company and e['position'] == position for e in experience):
                    continue

                exp = {
                    'company': company,
                    'position': position,
                    'date': date,
                    'responsibilities': self._extract_responsibilities(company)
                }
                experience.append(exp)

        # Fallback: simple keyword matching
        if not experience:
            company_pattern = rf'([\w一-鿿\s]+?{company_keywords}[\w一-鿿\s]*?)'
            companies = re.findall(company_pattern, self.content)
            for company in companies:
                company = company.strip()
                if company and len(company) < 30:
                    exp = {
                        'company': company,
                        'position': '',
                        'date': '',
                        'responsibilities': []
                    }
                    experience.append(exp)

        return experience

    def _extract_responsibilities(self, company: str) -> List[str]:
        """Extract responsibilities for a given company from the content."""
        responsibilities = []

        # Find the section for this company
        company_escaped = re.escape(company)
        section_pattern = rf'#+\s*\*{{0,2}}{company_escaped}.*?\n(.*?)(?=^#+|\Z)'
        match = re.search(section_pattern, self.content, re.MULTILINE | re.DOTALL)

        if match:
            section = match.group(1)

            # Skip patterns: section headers, project sub-sections
            skip_patterns = [
                r'^\*\*[^*]+\*\*',     # **anything** (bold text)
                r'^\*[^*]+\*',         # *anything* (italic text)
                r'^#+',                # Sub-headings
            ]

            for line in section.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Skip section headers
                should_skip = False
                for pattern in skip_patterns:
                    if re.match(pattern, line):
                        should_skip = True
                        break
                if should_skip:
                    continue

                # Match bullet points
                resp_match = re.match(r'^[-*]\s+(.+)', line)
                if resp_match:
                    resp = resp_match.group(1).strip()
                    if resp and len(resp) > 5:
                        responsibilities.append(resp)

        return responsibilities

    def _extract_project_experience(self) -> List[Dict]:
        """Extract project experience from structured markdown."""
        projects = []

        # Match patterns like: "### 项目名 (2024.01-2024.06)"
        project_pattern = r'###\s*(.+?)(?:\s*\(([\d.]+-[\d.]+)\))?\s*$'
        matches = re.findall(project_pattern, self.content, re.MULTILINE)

        for name, date in matches:
            # Skip non-project headers (skill categories, sections, etc.)
            skip_keywords = [
                '技能', '教育', '证书', '荣誉', '自我评价', '工作经历',
                '编程语言', '框架', '数据库', '工具', '其他',
                '项目经历', '项目背景', '项目描述', '项目成果'
            ]
            if any(skip in name for skip in skip_keywords):
                continue
            # Skip if it looks like a work entry (contains company pattern)
            company_pattern = r'公司|科技|集团|企业|Siemens|Google|Meta|Amazon|Microsoft|Apple|ByteDance|Alibaba|Tencent'
            if re.search(company_pattern, name, re.IGNORECASE):
                continue
            # Skip if it contains a pipe (work format: "公司 | 职位")
            if '|' in name or '｜' in name:
                continue
            project = {
                'name': name.strip().strip('*').strip(),
                'role': '',
                'date': date.strip() if date else '',
                'tech_stack': [],
                'description': '',
                'result': ''
            }
            projects.append(project)

        # Fallback 1: match "项目：xxx" or "项目:xxx"
        if not projects:
            project_pattern = r'项目[：:]\s*([^\n]+)'
            project_matches = re.findall(project_pattern, self.content)
            for match in project_matches:
                project = {
                    'name': match.strip().strip('*').strip(),
                    'role': '',
                    'date': '',
                    'tech_stack': [],
                    'description': '',
                    'result': ''
                }
                projects.append(project)

        # Fallback 2: match "**项目 N：xxx**" or "*项目 N：xxx*"
        if not projects:
            project_pattern2 = r'\*{1,2}\s*项目\s*\d+[：:]\s*(.+?)\*{1,2}'
            project_matches2 = re.findall(project_pattern2, self.content)
            for match in project_matches2:
                name = match.strip()
                if name and len(name) > 3:
                    project = {
                        'name': name,
                        'role': '',
                        'date': '',
                        'tech_stack': [],
                        'description': '',
                        'result': ''
                    }
                    projects.append(project)

        return projects

    def _extract_skills(self) -> List[Dict]:
        """Extract skills with proficiency levels."""
        skills = []

        # Skill level mapping
        level_map = {
            '精通': '精通',
            '熟练': '熟练',
            '了解': '了解',
            '熟悉': '熟练'
        }

        # Common skills to search for
        common_skills = [
            'Python', 'Java', 'Go', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Rust',
            'Django', 'Flask', 'FastAPI', 'Spring', 'Spring Boot', 'React', 'Vue', 'Angular',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
            'Docker', 'Kubernetes', 'Git', 'Jenkins', 'AWS', 'Azure',
            '分布式', '微服务', '高并发', '性能优化'
        ]

        for skill in common_skills:
            # Try to find skill with level: "Python (精通)" or "Python：精通"
            skill_escaped = re.escape(skill)
            level_match = re.search(
                rf'{skill_escaped}\s*[\(（]([一-鿿]+)[\)）]|{skill_escaped}[：:]\s*([一-鿿]+)',
                self.content
            )
            if level_match:
                raw_level = level_match.group(1) or level_match.group(2)
                level = level_map.get(raw_level, '熟练')
                skills.append({
                    'name': skill,
                    'level': level,
                    'evidence': '简历声明'
                })
            elif skill.lower() in self.content.lower():
                skills.append({
                    'name': skill,
                    'level': '熟练',  # Default
                    'evidence': '简历声明'
                })

        return skills

    def _extract_education(self) -> List[Dict]:
        """Extract education background with major, degree, date."""
        education = []

        # Match pattern: "**XX 大学** - 计算机科学与技术 - 本科 (2016-2020)"
        # or: "XX 大学 - 计算机科学 - 本科"
        edu_pattern = r'[\*]*([\w一-鿿]+(?:\s*(?:大学|学院|学校)))[\*]*\s*[-–—]\s*(.+?)(?:\s*[-–—]\s*(.+?))?(?:\s*\(([\d.]+-[\d.]+|[\d]{4})\))?\s*$'
        matches = re.findall(edu_pattern, self.content, re.MULTILINE)

        seen = set()
        for school, major, degree, date in matches:
            school = school.strip()
            if school in seen:
                continue
            seen.add(school)
            edu = {
                'school': school,
                'major': major.strip() if major else '',
                'degree': degree.strip() if degree else '',
                'date': date.strip() if date else ''
            }
            education.append(edu)

        # Fallback: simple university name matching
        if not education:
            university_pattern = r'([\w一-鿿]+(?:\s*(?:大学|学院|学校)))'
            university_matches = re.findall(university_pattern, self.content)
            seen = set()
            for match in university_matches:
                if match not in seen:
                    seen.add(match)
                    education.append({
                        'school': match,
                        'major': '',
                        'degree': '',
                        'date': ''
                    })

        return education

    def _extract_certificates(self) -> List[str]:
        """Extract certificates from list items or inline patterns."""
        certificates = []

        # Pattern 1: Match list items under certificate/荣誉 sections
        cert_section = re.search(
            r'(?:证书|荣誉|奖项)[/／]?(?:荣誉|奖项)?[：:]*\s*\n((?:\s*[-*]\s*.+\n?)+)',
            self.content
        )
        if cert_section:
            items = re.findall(r'[-*]\s*(.+)', cert_section.group(1))
            certificates.extend([item.strip() for item in items])

        # Pattern 2: Inline "证书：xxx"
        if not certificates:
            cert_patterns = [
                r'证书[：:]\s*([^\n]+)',
                r'荣誉[：:]\s*([^\n]+)',
                r'奖项[：:]\s*([^\n]+)'
            ]
            for pattern in cert_patterns:
                matches = re.findall(pattern, self.content)
                certificates.extend(matches)

        return certificates


def main():
    # Ensure UTF-8 output on Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <resume_path> [--output <output_path>]")
        sys.exit(1)

    resume_path = sys.argv[1]
    output_path = None

    # Parse arguments
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    try:
        parser = ResumeParser()
        result = parser.parse(resume_path)

        # Output result
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Parsed resume saved to: {output_path}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"Error parsing resume: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
