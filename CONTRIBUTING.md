# Contributing to Njuskalo Store Scraper

Thank you for your interest in contributing to this project! 

## How to Contribute

### Reporting Issues
- Use the GitHub issue tracker to report bugs
- Include detailed information about your environment
- Provide steps to reproduce the issue
- Include relevant log files or error messages

### Suggesting Features
- Open an issue to discuss new features before implementing
- Explain the use case and benefits
- Consider backward compatibility

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

4. **Test your changes**
   ```bash
   # Run the test suite
   python tests/test_complete_workflow.py
   python tests/test_gz_download.py
   python tests/test_single_store.py
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add: Brief description of your changes"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Include screenshots if UI changes are involved

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Include error handling and logging

## Testing

- Test new features thoroughly
- Include both positive and negative test cases
- Test with different website conditions
- Verify that existing functionality still works

## Legal Considerations

- Ensure your contributions respect website terms of service
- Do not implement features that could harm website performance
- Maintain ethical scraping practices
- Respect rate limits and implement appropriate delays

## Questions?

If you have questions about contributing, please open an issue or contact webmaster@solveit.in.rs.