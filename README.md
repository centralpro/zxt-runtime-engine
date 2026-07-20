# zxt-runtime-engine

ZXT / Runtime 静态博客生成器（Python 包名：`zxt-runtime-blog`）。

## 本地开发

```bash
uv sync --extra dev
uv run pytest
```

Content 仓库通过 path 依赖引用本仓库：

```toml
[tool.uv.sources]
zxt-runtime-blog = { path = "../zxt-runtime-engine", editable = true }
```

## CLI

```bash
uv run runtime-blog build
uv run runtime-blog lint
uv run runtime-blog new "文章标题"
uv run runtime-blog dev
```
