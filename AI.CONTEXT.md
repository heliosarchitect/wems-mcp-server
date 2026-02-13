# AI Navigation System

This project uses the **LBF AI Navigation Standard** — a set of machine-readable files that help AI agents understand, navigate, and use this codebase efficiently.

## Files

| File | Purpose | Read When |
|------|---------|-----------|
| `AI.TOC` | Project map — what this is, directory layout, entry points | First. Always start here. |
| `AI.INDEX` | Concept/function/class index with file locations | Looking for something specific |
| `AI.REGISTER` | External interfaces — APIs, env vars, configs, data sources | Integrating or deploying |

## How to Use (for AI agents)

1. **Start with `AI.TOC`** — understand what the project does and how it's organized
2. **Search `AI.INDEX`** for specific functions, classes, or concepts
3. **Check `AI.REGISTER`** when you need to call APIs, set env vars, or understand external dependencies

## Why This Exists

Most AI agents waste significant context tokens reading entire files to understand a project. These navigation files provide structured, token-efficient orientation — like a database index for code.

## Convention

- Files are plain text/markdown, no special tooling required
- `AI.TOC` fits in ~500 tokens — high-level map only
- `AI.INDEX` scales with project size, uses one-line entries
- `AI.REGISTER` is the external contract — what you need to USE the project
- Regenerate after significant refactors
- Standard created by Little Big Fish (LBF)
