# 简历 Schema (Resume Schema)

被这些子 skill 引用：`resume-build`、`resume-optimize`、`resume-localize`、`resume-export`。

---

## 文件位置

```
<user-resume-project>/resumes/jd-<NNN>-<short>/resume.html
<user-resume-project>/resumes/jd-<NNN>-<short>/resume-v<N>.html
<user-resume-project>/resumes/jd-<NNN>-<short>/resume.pdf
```

---

## HTML 结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>简历 - [姓名] - [目标职位]</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="resume">
    <!-- 头部：基本信息 -->
    <header class="resume-header">
      <h1>[姓名]</h1>
      <p class="target-role">[目标职位]</p>
      <div class="contact-info">
        <span>📱 [电话]</span>
        <span>📧 [邮箱]</span>
        <span>📍 [地点]</span>
      </div>
    </header>

    <!-- 自我评价 -->
    <section class="summary">
      <h2>自我评价</h2>
      <p>[个人总结，3-5 句]</p>
    </section>

    <!-- 技能清单 -->
    <section class="skills">
      <h2>技能清单</h2>
      <div class="skill-category">
        <h3>编程语言</h3>
        <ul>
          <li>Python (精通)</li>
          <li>Java (熟练)</li>
        </ul>
      </div>
      <!-- 更多技能分类 -->
    </section>

    <!-- 工作经历 -->
    <section class="experience">
      <h2>工作经历</h2>
      <div class="job">
        <div class="job-header">
          <h3>[公司名称] - [职位]</h3>
          <span class="date">[时间]</span>
        </div>
        <ul class="responsibilities">
          <li>[工作内容 1]</li>
          <li>[工作内容 2]</li>
        </ul>
      </div>
      <!-- 更多工作经历 -->
    </section>

    <!-- 项目经历 -->
    <section class="projects">
      <h2>项目经历</h2>
      <div class="project">
        <div class="project-header">
          <h3>[项目名称]</h3>
          <span class="role">[角色]</span>
          <span class="date">[时间]</span>
        </div>
        <p class="project-desc">[项目描述]</p>
        <ul class="project-details">
          <li>[具体工作 1]</li>
          <li>[具体工作 2]</li>
        </ul>
        <p class="project-result">[项目成果，量化！]</p>
      </div>
      <!-- 更多项目经历 -->
    </section>

    <!-- 教育背景 -->
    <section class="education">
      <h2>教育背景</h2>
      <div class="school">
        <h3>[学校名称]</h3>
        <p>[专业] - [学历] (2016-2020)</p>
      </div>
    </section>

    <!-- 证书/荣誉（可选） -->
    <section class="certificates">
      <h2>证书/荣誉</h2>
      <ul>
        <li>[证书 1]</li>
        <li>[荣誉 1]</li>
      </ul>
    </section>
  </div>
</body>
</html>
```

---

## 数据来源

| 简历部分 | 数据来源 |
|---|---|
| 头部 | self-profile.md |
| 自我评价 | self-profile.md |
| 技能清单 | self-profile.md (针对 JD 优化) |
| 工作经历 | self-profile.md + work-history/*.md |
| 项目经历 | profile/projects/*.md (针对 JD 优化) |
| 教育背景 | self-profile.md |
| 证书/荣誉 | self-profile.md |

---

## 版本管理

- **当前版本**：resume.html
- **历史版本**：resume-v1.html, resume-v2.html, ...
- **PDF 版本**：resume.pdf
- **本地化版本**：resume-en.html, resume-zh.html, ...

**版本命名规则**：
- 每次重大修改创建新版本（resume-v<N>.html）
- 当前版本始终是 resume.html
- PDF 始终从当前版本生成

**本地化版本命名**（由 `/resume-localize` 生成）：
- 通用英文版：`resume-en.html`
- 通用中文版：`resume-zh.html`
- 特定企业英文版：`resume-en-google.html`
- 特定企业中文版：`resume-zh-bytedance.html`
- 历史版本：`resume-en-v1.html`
- 本地化 PDF：`resume-en.pdf`

---

## 原子写

```python
def atomic_write_resume(file_path: str, content: str):
    """Atomic write using .tmp -> rename."""
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, file_path)
```

---

## 模板选择

| 职位类型 | 模板 |
|---|---|
| 技术岗 | tech-standard.html / tech-modern.html |
| 产品岗 | product-standard.html |
| 设计岗 | design-creative.html |
| 用户自定义 | user/*.html |

---

## 校验规则

### 真实性校验

- 每项技能必须有 project.md 支撑
- 量化数据必须有来源
- 不能虚构经历

### 针对性校验

- JD 必须满足的要求 → 简历必须覆盖
- JD 关键词必须在简历中出现
- 简历重点必须与 JD 匹配

### 证据链校验

- 每项技能 → 对应项目 → 具体成果
- 缺少证据链的技能自动降级
- 不能空谈
