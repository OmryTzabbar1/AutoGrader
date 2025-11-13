You are evaluating the "README Quality" criterion for a Master's level Computer Science software project.

Evaluate the README.md file based on the following aspects:

1. **Project Overview**: Clear description of what the project does and its purpose
2. **Installation Instructions**: Step-by-step setup guide that others can follow
3. **Usage Examples**: Clear examples of how to use the system
4. **Dependencies**: All dependencies and prerequisites listed
5. **Configuration**: How to configure the system (environment variables, config files)
6. **Documentation Links**: Links to additional documentation
7. **Contributing Guidelines**: How others can contribute (if applicable)
8. **License Information**: License type clearly stated
9. **Contact/Support**: How to get help or report issues

Look for:
- Clear project title and description
- Badges (build status, coverage, version)
- Installation steps with commands
- Quick start guide
- API documentation or links
- Configuration examples
- Troubleshooting section
- Credits and acknowledgments
- Professional formatting and organization

Provide your evaluation as a JSON object with the following structure:
{
    "score": <float between 0-100>,
    "evidence": [<list of specific quotes or references from the document>],
    "strengths": [<list of identified strengths>],
    "weaknesses": [<list of identified weaknesses>],
    "suggestions": [<list of actionable improvement suggestions>],
    "severity": "<one of: critical, important, minor, strength>"
}

Be specific and reference concrete examples. A missing README or minimal README is critical; missing sections are important; formatting issues are minor.
