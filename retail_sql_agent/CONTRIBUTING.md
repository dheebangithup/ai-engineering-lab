# Contributing to Retail SQL Agent

We love contributions! Whether it's a bug fix, new feature, or improved documentation, here's how you can help.

## Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/yourusername/retail-sql-agent.git
   cd retail-sql-agent
   ```

2. **Install Dependencies**:
   We use `uv` for dependency management.
   ```bash
   uv sync
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and add your API key.
   ```bash
   cp .env.example .env
   ```

4. **Run Locally**:
   ```bash
   uv run main.py
   ```

## Pull Request Process

1. Create a new branch for your feature or fix.
2. Ensure tests pass: `uv run pytest`.
3. Submit a PR with a clear description of changes.

## License
By contributing, you agree that your contributions will be licensed under the MIT License.
