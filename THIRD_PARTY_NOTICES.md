# Third-Party Notices

## Ante Foundation (this fork)

The `ante/` package, `scripts/ante`, `foundation/`, `tests/foundation/`,
`tests/characterization/` and `examples/foundation/` are original work of this
fork, `bionic0x/Ante-agency-agents`, which derives from
[msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) under
the MIT License in [LICENSE](LICENSE); the upstream copyright notice is retained
there. The foundation adds no third-party code and no new runtime dependency:
it uses the Python standard library and the hash-pinned PyYAML already declared
in `scripts/requirements-validation.txt`. Eight modules under `ante/nexus/` are
mechanical moves of this repository's own scripts (see `foundation/MIGRATION.md`).

Some internal command and module names (nodal, street, stub, jackpot, ghosts,
deck, constructs, ICE, Turing lock) allude to William Gibson's fiction. They are
naming conventions only: no text from those works is reproduced, and outputs read
by third parties use functional names. Doctrinal references (the General Theory
of Strategy and the works it cites) are cited by section, not reproduced.

## ACT-LABS-IO architectural references

The [external marketplace assessment](strategy/external-marketplaces/README.md)
references ACT-LABS-IO's marketplace MCP server, Eliza plugin and contracts at
the commits recorded in [sources.json](strategy/external-marketplaces/sources.json).
The intake tool, contract, tests and synthetic fixture are original Ante work;
no ACT source code, credentials, SDK or contract artifact is redistributed.
Package license declarations and source-file SPDX markers are recorded as
observations in the source receipt; they are not a resolved licensing opinion
or permission to import additional material.

This repository includes or derives portions of third-party open-source material. The canonical source registry records source paths and commits for imported agents.

## awesome-openclaw-agents

Source: `https://github.com/mergisi/awesome-openclaw-agents`

Imported material is derived from MIT-licensed `SOUL.md` agent templates and is normalized into the Agency Agents canonical format.

### MIT License

Copyright (c) 2025 OpenClaw Community

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
