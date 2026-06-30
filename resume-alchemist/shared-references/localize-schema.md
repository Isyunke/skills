# 本地化 Schema (Localize Schema)

被这些子 skill 引用：`resume-localize`、`resume-build`、`resume-optimize`、`resume-export`。

---

## 文件位置

```
<user-resume-project>/resumes/jd-<NNN>-<short>/resume-en.html        # 通用英文版
<user-resume-project>/resumes/jd-<NNN>-<short>/resume-zh.html        # 通用中文版
<user-resume-project>/resumes/jd-<NNN>-<short>/resume-en-<company>.html  # 特定企业英文版
<user-resume-project>/resumes/jd-<NNN>-<short>/resume-en-v<N>.html   # 英文历史版本
```

---

## 目标市场枚举

```json
{
  "target_markets": {
    "en-US": { "name": "美国", "language": "English (US)", "date_format": "Mon YYYY" },
    "en-UK": { "name": "英国", "language": "English (UK)", "date_format": "Mon YYYY" },
    "zh-CN": { "name": "中国大陆", "language": "中文 (简体)", "date_format": "YYYY.MM" },
    "zh-TW": { "name": "台湾", "language": "中文 (繁體)", "date_format": "YYYY.MM" },
    "ja-JP": { "name": "日本", "language": "日本語", "date_format": "YYYY年MM月" }
  }
}
```

---

## 文化适配矩阵

### 内容维度

| 维度 | zh-CN | en-US / en-UK |
|---|---|---|
| **自我评价** | 3-5 句，个人品质描述 | 1-2 句 Professional Summary，强调价值主张 |
| **工作描述** | 职责导向："负责 XX 开发" | 成果导向："Led XX, achieving YY%" |
| **项目描述** | 详细背景 + 技术方案 | 简洁：规模 → 问题 → 方案 → 量化成果 |
| **技能标注** | 精通/熟练/了解 | Expert/Proficient/Familiar |
| **关键词** | 中文技术术语 | 英文技术术语 |

### 格式维度

| 维度 | zh-CN | en-US / en-UK |
|---|---|---|
| **照片** | 常见 | 不放（反歧视） |
| **个人信息** | 姓名、电话、邮箱、年龄、性别、政治面貌、地址 | 姓名、邮箱、电话（可选：LinkedIn、GitHub） |
| **日期格式** | 2024.01 - 2024.06 | Jan 2024 - Jun 2024 |
| **排版密度** | 信息密度高 | 留白多，简洁 |
| **字体** | 微软雅黑、苹方 | Georgia、Helvetica、Arial |
| **页数** | 1-2 页 | 1 页（应届）/ 2 页（资深 5 年+） |
| **Section 标题** | 中文（自我评价、技能清单） | 英文大写（PROFESSIONAL SUMMARY、TECHNICAL SKILLS） |

---

## 内容改写规则

### 英文简历强动词表

**Leadership**: Led, Directed, Managed, Oversaw, Coordinated, Mentored
**Achievement**: Achieved, Delivered, Exceeded, Improved, Reduced, Increased
**Creation**: Built, Designed, Architected, Developed, Implemented, Created
**Optimization**: Optimized, Streamlined, Automated, Enhanced, Refactored
**Scale**: Scaled, Expanded, Grew, Increased, Amplified, Migrated

### 禁用短语（英文简历）

- ❌ "Responsible for..." → ✅ "Led..." / "Managed..."
- ❌ "Participated in..." → ✅ "Contributed to..." / "Drove..."
- ❌ "Helped with..." → ✅ "Supported..." / "Facilitated..."
- ❌ "Worked on..." → ✅ "Developed..." / "Built..."

### 自我评价模板

**中文**：
> X 年[职位]经验，专注于[领域]。擅长[技术栈]，熟悉[相关技术]。有丰富的[经验]，曾主导[成果]。

**英文（美式）**：
> [Role] with X years of experience in [domain]. Proven track record in [achievement], with expertise in [skills].

**英文（英式，稍正式）**：
> Experienced [Role] with X years specializing in [domain]. Demonstrated ability in [achievement], with strong proficiency in [skills].

---

## 技能术语对照表

| 中文 | 英文 |
|---|---|
| 精通 | Expert |
| 熟练 | Proficient |
| 了解 | Familiar |
| 分布式系统 | Distributed Systems |
| 高并发 | High Concurrency / High Throughput |
| 高可用 | High Availability |
| 性能优化 | Performance Optimization |
| 微服务架构 | Microservices Architecture |
| 消息队列 | Message Queue |
| 负载均衡 | Load Balancing |
| 缓存 | Caching |
| 数据库 | Database |
| 容器化 | Containerization |
| 持续集成 | Continuous Integration (CI) |
| 持续部署 | Continuous Deployment (CD) |
| 自动化测试 | Automated Testing |
| 代码审查 | Code Review |
| 技术选型 | Technology Selection |
| 架构设计 | Architecture Design |

---

## 企业文化特征库

### 美国科技公司

| 公司 | 文化关键词 | 简历偏好 |
|---|---|---|
| Google | Googleyness, impact, scale | 强调影响力和规模，简洁数据驱动 |
| Meta | Move fast, impact | 强调速度和影响力，偏好创业者心态 |
| Amazon | Leadership Principles | 每条经历对应一个 LP，强调 customer obsession |
| Apple | Secrecy, excellence | 强调产品质量和用户体验 |
| Microsoft | Growth mindset | 强调学习能力和协作 |
| Netflix | Freedom & responsibility | 强调自主性和责任感 |

### 中国科技公司

| 公司 | 文化关键词 | 简历偏好 |
|---|---|---|
| 字节跳动 | Always Day 1, 扁平化 | 强调创新和自驱力 |
| 阿里 | 文化契合, 价值观 | 强调团队协作和业务理解 |
| 腾讯 | 产品思维, 用户体验 | 强调产品感和技术深度 |
| 美团 | 长期主义, 基础设施 | 强调系统性和稳定性 |
| 华为 | 狼性文化, 奋斗者 | 强调执行力和抗压能力 |

---

## 版本命名规则

| 场景 | 文件名 | 说明 |
|---|---|---|
| 中→英（通用） | `resume-en.html` | 通用英文版 |
| 中→英（特定企业） | `resume-en-<company>.html` | 针对特定企业的英文版 |
| 英→中（通用） | `resume-zh.html` | 通用中文版 |
| 英→中（特定企业） | `resume-zh-<company>.html` | 针对特定企业的中文版 |
| 历史版本 | `resume-en-v<N>.html` | 版本号递增 |
| PDF | `resume-en.pdf` | 英文版 PDF |

**命名小写化**：公司名统一小写，如 `resume-en-google.html`

---

## 读写协议

### 读取本地化版本

```python
def get_localized_path(jd_dir: str, target_lang: str, company: str = None) -> str:
    """获取本地化简历路径。"""
    if company:
        path = os.path.join(jd_dir, f"resume-{target_lang}-{company.lower()}.html")
        if os.path.exists(path):
            return path

    path = os.path.join(jd_dir, f"resume-{target_lang}.html")
    return path if os.path.exists(path) else None
```

### 写入本地化版本

```python
def write_localized(jd_dir: str, content: str, target_lang: str, company: str = None):
    """写入本地化简历，使用原子写。"""
    if company:
        filename = f"resume-{target_lang}-{company.lower()}.html"
    else:
        filename = f"resume-{target_lang}.html"

    filepath = os.path.join(jd_dir, filename)
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, filepath)
```

---

## 注意事项

1. **改写不是翻译**——逐句翻译 = 简历灾难。用目标市场的表达习惯重新打磨
2. **文化适配**——不同国家的简历规范差异巨大，必须尊重
3. **真实性不变**——三原则依然适用，改写不能夸大或虚构
4. **双版本维护**——本地化后保留原始版本，两个版本独立管理
5. **原子写**——所有文件使用 .tmp → rename
