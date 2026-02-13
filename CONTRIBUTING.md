# Contributing to WEMS MCP Server

Thank you for your interest in contributing to the World Event Monitoring System (WEMS) MCP Server!

## 🌟 Ways to Contribute

- **Bug Reports**: Found an issue? Open an issue with details
- **Feature Requests**: Have an idea? We'd love to hear it
- **Code Contributions**: Submit pull requests for improvements
- **Documentation**: Help improve our docs and examples
- **Testing**: Test with different MCP clients and report compatibility

## 🚀 Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/yourusername/wems-mcp-server.git`
3. **Install** dependencies: `pip install -r requirements.txt`
4. **Test** the server: `python3 wems_mcp_server.py`
5. **Create** a feature branch: `git checkout -b feature/your-feature-name`

## 🔧 Development Setup

```bash
# Clone repository
git clone https://github.com/loverbearfarm/wems-mcp-server.git
cd wems-mcp-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure settings
cp config.example.yaml config.yaml
# Edit config.yaml with your preferences

# Run the server
python3 wems_mcp_server.py
```

## 🧪 Testing

- Test all MCP tools manually: `check_earthquakes`, `check_solar`, etc.
- Verify webhook functionality (if configured)
- Test with different MCP clients (Claude Desktop, OpenClaw, etc.)
- Validate API responses from data sources

## 📝 Pull Request Process

1. **Update** documentation if needed
2. **Add** tests for new functionality
3. **Follow** existing code style and patterns
4. **Test** thoroughly across different scenarios
5. **Submit** PR with clear description of changes

## 🏗️ Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings for new functions
- Keep functions focused and single-purpose
- Handle errors gracefully with informative messages

## 🛠️ Adding New Data Sources

When adding new monitoring capabilities:

1. **Research** the API documentation thoroughly
2. **Implement** appropriate error handling
3. **Add** configuration options to `config.example.yaml`
4. **Update** README.md with new features
5. **Test** with various scenarios (no data, API errors, etc.)

## 🔍 Data Source Guidelines

- **Authoritative sources only** (government agencies, research institutions)
- **Free/open APIs preferred** (no API keys when possible)
- **Reliable endpoints** (established data providers)
- **Consistent response format** (standardize across sources)

## 📋 Issue Guidelines

**Bug Reports:**
- Include Python version and OS
- Provide configuration details (sanitized)
- Include error messages and stack traces
- Steps to reproduce the issue

**Feature Requests:**
- Describe the use case
- Suggest implementation approach
- Consider impact on existing functionality

## 🤝 Community

- Be respectful and inclusive
- Help others learn and contribute
- Focus on constructive feedback
- Remember this serves emergency monitoring use cases

## 📞 Contact

- **Email**: heliosarchitectlbf@gmail.com
- **Issues**: GitHub Issues
- **Organization**: Lover Bear Farm

---

Built with ❤️ for the global monitoring community