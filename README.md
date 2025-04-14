# ReasonChip

![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

Open source agentic workflow automation software

## Quick links

- [QuickStart](https://www.reasonchip.io/docs/quickstart/)
- [Documentation](https://www.reasonchip.io/docs/)
- [Website](https://www.reasonchip.io/)

## Installation

Easy peasy, lemon squeezy

```bash
pip install reasonchip
```

## Example workflows

They're right here in the source tree: [Examples](./examples/README.md)


## Additional Links

- [PyPI package](https://pypi.org/project/reasonchip/)


## Developer Setup

### Code formatting

We use [`black`](https://github.com/psf/black) for consistent Python formatting,
enforced with [`pre-commit`](https://pre-commit.com/).

After checkout, run:

```bash
pre-commit install
```

Now Black will automatically format your Python files before every commit.

To manually format the full codebase:

```bash
pre-commit run --all-files
```

Formatting config lives in `pyproject.toml` with a line length of 80 characters.


