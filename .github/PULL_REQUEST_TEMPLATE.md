## Summary

<!-- What does this PR do? Link related issues with "Closes #123". -->

## Type of Change

- [ ] Bug fix
- [ ] New skill / agent / hook
- [ ] Refactor (no behavior change)
- [ ] Test improvement
- [ ] Other: ___

## Behavior and evidence

<!-- Give a command, fixture or user action, the previous result and the result on the tested revision. Identify reported or unavailable baselines. For docs-only changes, describe what you verified. -->

## Impact and recovery

<!-- Who or what is affected? What does reverting the commit restore? Mention any files, data or external actions that need separate recovery. -->

## Test plan

- [ ] <!-- Command or manual check, tested revision and observed result. Leave pending checks unchecked. -->

## Checklist

- [ ] I have read the [Contributing Guide](CONTRIBUTING.md)
- [ ] Branch follows naming convention (`feat/`, `fix/`, `refactor/`, etc.)
- [ ] Commits use [Conventional Commits](https://www.conventionalcommits.org/) format
- [ ] `python3 scripts/validate.py` passes
- [ ] `python3 scripts/audit_skills.py --ci` passes (0 HIGH)
- [ ] `bats tests/` passes
- [ ] New code has no external dependencies (stdlib only)
- [ ] No secrets, tokens, or API keys in the code
- [ ] Tracked generated files are current for these changes.
- [ ] I did **not** bump `version` in package.json, manifest.json, or plugin.json (maintainer handles releases)
- [ ] I did **not** update README counts/badges or ARCHITECTURE.md counts (maintainer handles these)

## Notes for Maintainer

<!-- Anything the maintainer should know during review? -->
