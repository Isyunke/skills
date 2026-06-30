#!/usr/bin/env python3
"""
Keyword matcher for resume-alchemist.
Matches JD keywords against resume content.

Usage:
    python keyword_matcher.py <resume_path> <jd_path>
"""

import sys
import re
from pathlib import Path


# Keywords organized by domain
DOMAIN_KEYWORDS = {
    "programming_languages": [
        'Python', 'Java', 'Go', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Rust',
        'Ruby', 'PHP', 'Kotlin', 'Swift', 'Scala', 'R', 'MATLAB'
    ],
    "frameworks": [
        'Django', 'Flask', 'FastAPI', 'Spring', 'Spring Boot', 'React', 'Vue',
        'Angular', 'Express', 'Node.js', 'Gin', 'Gorm', 'TensorFlow', 'PyTorch'
    ],
    "databases": [
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Oracle',
        'SQL Server', 'SQLite', 'Cassandra', 'Neo4j', 'Vector Database'
    ],
    "devops": [
        'Docker', 'Kubernetes', 'K8s', 'Git', 'Jenkins', 'CI/CD', 'GitLab CI',
        'GitHub Actions', 'Terraform', 'Ansible', 'Prometheus', 'Grafana',
        'Nginx', 'Linux', 'Ubuntu', 'Shell', 'Bash', 'Helm', 'ArgoCD'
    ],
    "cloud": [
        'AWS', 'Azure', 'GCP', 'S3', 'EC2', 'Lambda', 'Cloud Functions',
        'Serverless', 'Microservices', 'API Gateway', 'Load Balancer'
    ],
    "observability": [
        'Observability', 'Logging', 'Metrics', 'Tracing', 'ELK', 'Loki',
        'Jaeger', 'Zipkin', 'Monitoring', 'Diagnostics', 'Alerting',
        'Prometheus', 'Grafana', 'Kibana', 'Datadog'
    ],
    "ai_ml": [
        'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision', 'LLM',
        'RAG', 'LangChain', 'LlamaIndex', 'Agent', 'Agentic', 'Embedding',
        'Vector', 'Fine-tuning', 'Transformer', 'BERT', 'GPT', 'VLA',
        'Vision-Language', 'YOLO', 'Object Detection', 'Image Recognition'
    ],
    "robotics": [
        'Robotics', 'Robot', 'AGV', 'AMR', 'Manipulator', 'Robotic Arm',
        'Motion Planning', 'Path Planning', 'Obstacle Avoidance', 'SLAM',
        'ROS', 'Simulation', 'Digital Twin', 'Cobot', 'Collaborative Robot'
    ],
    "industrial": [
        'PLC', 'SCADA', 'Modbus', 'OPC UA', 'MQTT', 'Edge Computing',
        'Industrial IoT', 'IIoT', 'Industry 4.0', 'Smart Manufacturing',
        'Factory Automation', 'MES', 'ERP', 'DAQ', 'Data Acquisition',
        'Embedded', 'RTOS', 'Firmware'
    ],
    "concepts": [
        'Distributed Systems', 'Microservices', 'High Concurrency', 'High Availability',
        'Performance Optimization', 'Caching', 'Message Queue', 'Load Balancing',
        'API', 'REST', 'GraphQL', 'gRPC', 'WebSocket', 'Security', 'Authentication',
        'Authorization', 'DevOps', 'Platform Engineering', 'SRE', 'Infrastructure',
        'Automation', 'Testing', 'Test Automation', 'Deployment', 'Release'
    ],
}


def extract_keywords(text: str) -> set:
    """Extract keywords from text using domain-organized keyword library."""
    keywords = set()

    for domain, domain_kw in DOMAIN_KEYWORDS.items():
        for kw in domain_kw:
            # Case-insensitive matching for English keywords
            if kw.lower() in text.lower():
                keywords.add(kw)
            # Chinese keywords need exact matching
            elif any('一' <= c <= '鿿' for c in kw) and kw in text:
                keywords.add(kw)

    return keywords


def match_keywords(jd_keywords: set, resume_keywords: set) -> dict:
    """Match JD keywords against resume keywords."""
    matched = jd_keywords & resume_keywords
    missing = jd_keywords - resume_keywords
    extra = resume_keywords - jd_keywords

    return {
        'matched': matched,
        'missing': missing,
        'extra': extra,
        'coverage': len(matched) / len(jd_keywords) if jd_keywords else 0
    }


def main():
    # Ensure UTF-8 output on Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 3:
        print("Usage: python keyword_matcher.py <resume_path> <jd_path>")
        sys.exit(1)

    resume_path = sys.argv[1]
    jd_path = sys.argv[2]

    # Read files
    resume_text = Path(resume_path).read_text(encoding='utf-8')
    jd_text = Path(jd_path).read_text(encoding='utf-8')

    # Extract keywords
    resume_keywords = extract_keywords(resume_text)
    jd_keywords = extract_keywords(jd_text)

    # Match keywords
    result = match_keywords(jd_keywords, resume_keywords)

    # Output results
    print("Keyword Match Report")
    print("=" * 50)
    print(f"\nJD Keywords ({len(jd_keywords)}):")
    print(f"  {', '.join(sorted(jd_keywords))}")

    print(f"\nResume Keywords ({len(resume_keywords)}):")
    print(f"  {', '.join(sorted(resume_keywords))}")

    print(f"\nMatched ({len(result['matched'])}):")
    print(f"  {', '.join(sorted(result['matched']))}")

    print(f"\nMissing ({len(result['missing'])}):")
    print(f"  {', '.join(sorted(result['missing']))}")

    print(f"\nExtra ({len(result['extra'])}):")
    print(f"  {', '.join(sorted(result['extra']))}")

    print(f"\nCoverage: {result['coverage']:.1%}")

    # Suggestions
    if result['missing']:
        print("\nSuggestions:")
        for keyword in sorted(result['missing']):
            print(f"  - Add '{keyword}' to your resume")


if __name__ == "__main__":
    main()
