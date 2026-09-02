# 发布到 PyPI 指南

本文档说明如何将 `qq-botpy-v2` 发布到 PyPI。

## 包名说明

| 名称 | 用途 |
| --- | --- |
| `qq-botpy-v2` | **PyPI 发行名**（pip 安装时使用） |
| `botpy` | **代码导入名**（保持与原版 botpy 兼容，不变） |

```bash
pip install qq-botpy-v2            # 安装后仍然:
import botpy                       # import botpy 使用
```

发布前请确认 `pyproject.toml` 中的 `[project.urls]` 已改为自己的仓库地址。

## 方式一：GitHub Actions 自动发布（推荐）

仓库已配置 workflow：[.github/workflows/publish.yml](../.github/workflows/publish.yml)。
使用 PyPI 官方推荐的 **Trusted Publishing（OIDC）**，全程无需保管任何 token。

### 首次配置（一次性）

1. **在 PyPI 登记发布来源**（[pypi.org](https://pypi.org) → 账号设置 → Publishing → Add a new pending publisher）：
   - PyPI project name：`qq-botpy-v2`
   - Owner / Repository：你的 GitHub 用户名 / 本仓库名
   - Workflow name：`publish.yml`
   - Environment name：`pypi`

   > 首次发布后，这个名字就归属于你的账号，后续无需再登记。
   > TestPyPI（[test.pypi.org](https://test.pypi.org)）如需使用，同样登记一条，Environment 填 `testpypi`。

2. **在 GitHub 仓库创建环境**：Settings → Environments → New environment，分别创建 `pypi`（和可选的 `testpypi`）。
   可选：在环境中配置 *Required reviewers*，每次上传需要人工点击批准。

### 发布新版本

```bash
# 1. 更新 pyproject.toml 中的 version（建议遵循语义化版本）
# 2. 提交并打 tag
git add pyproject.toml
git commit -m "release: v1.0.1"
git tag v1.0.1
git push origin master v1.0.1
```

推送 tag 后自动执行：构建 sdist + wheel → twine check → 上传到 PyPI。
在仓库 Actions 页面可查看进度；若配置了 Required reviewers，需人工批准后才会真正上传。

### 手动触发 / TestPyPI 验证

GitHub 仓库 → Actions → **Publish to PyPI** → Run workflow → 选择 target：

- `pypi`：发布正式版
- `testpypi`：发布到测试索引（用于验证打包与发布链路，不影响正式版）

TestPyPI 上的安装验证：

```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple qq-botpy-v2
```

## 方式二：本地手动发布

```bash
# 1. 安装构建与上传工具
pip install --upgrade build twine

# 2. 构建（同时产出 sdist 与 wheel）
python -m build

# 3. 检查元数据
twine check dist/*

# 4. 上传到 TestPyPI 验证（可选）
twine upload -r testpypi dist/*

# 5. 上传到 PyPI
twine upload dist/*
# 用户名填 __token__，密码填 API Token（pypi.org → 账号设置 → API tokens 创建）
```

## 发布检查清单

- [ ] `pyproject.toml` 中 `version` 已更新（同一版本不能重复上传）
- [ ] `[project.urls]` 已改为自己的仓库地址
- [ ] `git status` 干净，全部更改已提交
- [ ] 测试通过：`pip install -e ".[test]" && pytest`
- [ ] 本地构建验证：`python -m build && twine check dist/*`
- [ ] （可选）先发 TestPyPI 验证
- [ ] 发布后在新环境验证：`pip install qq-botpy-v2 && python -c "import botpy; print(botpy.__version__)"`
