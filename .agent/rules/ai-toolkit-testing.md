# Testing

* Every new feature or bug fix must include tests
* Use Arrange-Act-Assert pattern for unit tests
* Test behavior, not implementation — tests should survive refactoring
* Use descriptive test names: `test_<what>_<when>_<expected>`
* Prefer real dependencies over mocks at integration boundaries
* Target >70% code coverage for new code
* Never skip or disable tests without a linked issue explaining why
* Run the full test suite before marking work as done
