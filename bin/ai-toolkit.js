#!/usr/bin/env node
'use strict';

const { execFileSync, spawnSync, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const TOOLKIT_DIR = path.dirname(__dirname);
const CWD = process.cwd();

// ---------------------------------------------------------------------------
// Generator map: command name -> { script, dest, mkdir? }
// Used by individual generator commands, `generate-all`, and the default case.
// ---------------------------------------------------------------------------

/** @type {Record<string, { script: string, dest: string, mkdir?: string }>} */
const GENERATORS = {
  'cursor-rules':         { script: 'generate_cursor_rules.py',  dest: '.cursorrules' },
  'windsurf-rules':       { script: 'generate_windsurf.py',      dest: '.windsurfrules' },
  'copilot-instructions': { script: 'generate_copilot.py',       dest: path.join('.github', 'copilot-instructions.md'), mkdir: '.github' },
  'gemini-md':            { script: 'generate_gemini.py',        dest: 'GEMINI.md' },
  'cline-rules':          { script: 'generate_cline.py',         dest: '.clinerules' },
  'roo-modes':            { script: 'generate_roo_modes.py',     dest: '.roomodes' },
  'aider-conf':           { script: 'generate_aider_conf.py',    dest: '.aider.conf.yml' },
  'agents-md':            { script: 'generate_agents_md.py',     dest: 'AGENTS.md' },
};

// ---------------------------------------------------------------------------
// Simple script dispatch table: command -> { script, toolkitCwd? }
// Commands listed here are dispatched generically via `runScript()`.
// ---------------------------------------------------------------------------

/**
 * @type {Record<string, { script: string, toolkitCwd?: boolean }>}
 */
const SCRIPT_COMMANDS = {
  'install':              { script: 'install.py' },
  'update':               { script: 'install.py' },
  'uninstall':            { script: 'uninstall.py' },
  'validate':             { script: 'validate.py',           toolkitCwd: true },
  'doctor':               { script: 'doctor.py',             toolkitCwd: true },
  'eject':                { script: 'eject.py' },
  'benchmark-ecosystem':  { script: 'benchmark_ecosystem.py', toolkitCwd: true },
  'evaluate':             { script: 'evaluate_skills.py',    toolkitCwd: true },
  'stats':                { script: 'stats.py' },
};

// ---------------------------------------------------------------------------
// Help text: every available command with a short description.
// ---------------------------------------------------------------------------

/** @type {Record<string, string>} */
const COMMANDS = {
  install: 'First-time global install into ~/.claude/ (use --local to also set up project configs)',
  update: 'Re-apply toolkit after npm update (use --local to also refresh project configs)',
  reset: 'Wipe and recreate project-local configs from scratch (requires --local)',
  uninstall: 'Remove ai-toolkit from ~/.claude/',
  'add-rule': 'Register a rule file in ~/.ai-toolkit/rules/ (applied on every install/update)',
  'remove-rule': 'Unregister a rule from ~/.ai-toolkit/rules/ and remove its block from CLAUDE.md',
  validate: 'Verify toolkit integrity',
  doctor: 'Check install health, hooks, and artifact drift',
  eject: 'Export standalone config (no symlinks, no toolkit dependency)',
  benchmark: 'Benchmark toolkit (--my-config to compare your setup vs defaults vs ecosystem)',
  'benchmark-ecosystem': 'Generate ecosystem benchmark snapshot (GitHub metadata + offline fallback)',
  evaluate: 'Run skill evaluation suite',
  stats: 'Show skill usage statistics (--reset to clear, --json for raw output)',
  create: 'Scaffold new skill from template (e.g. create skill my-lint --template=linter)',
  plugin: 'Manage plugin packs (install, remove, update, clean, list, status)',
  sync: 'Sync config to/from GitHub Gist (--export, --push, --pull, --import)',
  'cursor-rules': 'Generate .cursorrules for Cursor IDE',
  'windsurf-rules': 'Generate .windsurfrules for Windsurf',
  'copilot-instructions': 'Generate .github/copilot-instructions.md',
  'gemini-md': 'Generate GEMINI.md for Gemini CLI',
  'cline-rules': 'Generate .clinerules for Cline',
  'roo-modes': 'Generate .roomodes for Roo Code',
  'aider-conf': 'Generate .aider.conf.yml for Aider',
  'agents-md': 'Regenerate AGENTS.md from agent definitions',
  'llms-txt': 'Generate llms.txt and llms-full.txt',
  'generate-all': 'Generate all platform configs at once (agents, cursor, windsurf, copilot, gemini, cline, roo, aider, llms)',
  help: 'Show this help message',
};

// ---------------------------------------------------------------------------
// Core execution helpers
// ---------------------------------------------------------------------------

/**
 * Resolve the absolute path to a script inside the toolkit's scripts/ dir.
 * @param {string} scriptName - Filename within scripts/ (e.g. "install.sh")
 * @returns {string} Absolute path
 */
function scriptPath(scriptName) {
  return path.join(TOOLKIT_DIR, 'scripts', scriptName);
}

/**
 * Execute a generator script synchronously via python3, returning its stdout.
 * Exits the process on failure.
 * @param {string} scriptName - Generator script filename in scripts/
 * @param {string[]} [extraArgs=[]] - Additional CLI arguments
 * @returns {Buffer} stdout output
 */
function runGenerator(scriptName, extraArgs = []) {
  try {
    return execFileSync('python3', [scriptPath(scriptName), ...extraArgs], { cwd: TOOLKIT_DIR });
  } catch (err) {
    console.error(`Error running ${scriptName}: ${err.stderr ? err.stderr.toString().trim() : err.message}`);
    process.exit(1);
  }
}

/**
 * Spawn a script with inherited stdio (interactive). Exits on non-zero status.
 * @param {string} script - Absolute path to the script
 * @param {string[]} [args=[]] - CLI arguments
 * @param {{ cwd?: string }} [opts={}] - Options (cwd override)
 */
function run(script, args = [], opts = {}) {
  const result = spawnSync('python3', [script, ...args], {
    stdio: 'inherit',
    cwd: opts.cwd || CWD,
    env: { ...process.env },
  });
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

/**
 * Generic dispatcher for SCRIPT_COMMANDS entries.
 * Resolves the script path and selects the correct cwd.
 * @param {string} command - Command name (key in SCRIPT_COMMANDS)
 * @param {string[]} args - CLI arguments to forward
 */
function runScript(command, args) {
  const entry = SCRIPT_COMMANDS[command];
  const opts = entry.toolkitCwd ? { cwd: TOOLKIT_DIR } : {};
  run(scriptPath(entry.script), args, opts);
}

/**
 * Write generator output to a destination file, creating parent dirs if needed.
 * @param {{ script: string, dest: string, mkdir?: string }} gen - Generator entry
 */
function writeGeneratorOutput(gen) {
  if (gen.mkdir) {
    const dir = path.join(CWD, gen.mkdir);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }
  const output = runGenerator(gen.script);
  fs.writeFileSync(path.join(CWD, gen.dest), output);
  console.log(`Generated: ${gen.dest}`);
}

/**
 * Generate llms.txt and llms-full.txt in the current working directory.
 */
function generateLlmsTxt() {
  fs.writeFileSync(path.join(CWD, 'llms.txt'), runGenerator('generate_llms_txt.py'));
  fs.writeFileSync(path.join(CWD, 'llms-full.txt'), runGenerator('generate_llms_txt.py', ['--full']));
  console.log('Generated: llms.txt, llms-full.txt');
}

// ---------------------------------------------------------------------------
// Help
// ---------------------------------------------------------------------------

/**
 * Print CLI usage information to stdout.
 */
function showHelp() {
  console.log('\nai-toolkit v' + require('../package.json').version);
  console.log('\nUsage: ai-toolkit <command> [options]\n');
  console.log('Commands:');
  for (const [cmd, desc] of Object.entries(COMMANDS)) {
    console.log(`  ${cmd.padEnd(16)} ${desc}`);
  }
  console.log('\nOptions for install / update:');
  console.log('  --only <list>   Apply only listed components (e.g. agents,hooks,cursor,windsurf,gemini)');
  console.log('  --skip <list>   Skip listed components');
  console.log('  --local         Also set up project-local configs (CLAUDE.md, settings, constitution, copilot, cline, roo, aider, git hooks)');
  console.log('  --profile <p>   Install profile: minimal (agents+skills), standard (default), strict (all+git hooks)');
  console.log('  --list, --dry-run  Dry-run: show what would be applied');
  console.log('\nOptions for create:');
  console.log('  skill <name> --template=<type>  Scaffold skill (types: linter, reviewer, generator, workflow, knowledge)');
  console.log('  --description "..."             Override default description');
  console.log('\nOptions for sync:');
  console.log('  --export              Export config snapshot as JSON to stdout');
  console.log('  --push                Push config to GitHub Gist (requires gh CLI)');
  console.log('  --pull [gist-id]      Pull config from Gist and apply');
  console.log('  --import <file|url>   Import config from local file or URL');
  console.log('\nOptions for reset:');
  console.log('  --local         Required. Wipe and recreate all project-local configs from scratch');
  console.log('\nOptions for remove-rule:');
  console.log('  <rule-name>     Name of rule to unregister (filename without .md)');
  console.log('  [target-dir]    Target dir containing .claude/CLAUDE.md (default: $HOME)');
  console.log('\nOptions for add-rule:');
  console.log('  <rule-file>     Path to .md rule file to register globally');
  console.log('  [rule-name]     Override rule name (default: filename without .md)');
  console.log('\nOptions for plugin:');
  console.log('  install <name>  Install a plugin pack (copies hooks, links skills/agents)');
  console.log('  install --all   Install all available plugin packs');
  console.log('  update <name>   Update a plugin pack (remove + reinstall)');
  console.log('  update --all    Update all installed plugin packs');
  console.log('  clean <name>    Prune old data (e.g. memory-pack --days 30)');
  console.log('  remove <name>   Remove a plugin pack');
  console.log('  remove --all    Remove all installed plugins');
  console.log('  list            Show available plugin packs with install status');
  console.log('  status          Show currently installed plugins with data stats');
  console.log('\nOptions for doctor:');
  console.log('  --fix           Auto-repair detected issues');
  console.log('\nOptions for eject:');
  console.log('  [target-dir]    Target directory (default: current directory)');
  console.log('');
}

// ---------------------------------------------------------------------------
// Special-case command handlers
// Each receives the CLI args array and contains command-specific logic that
// cannot be expressed through the generic SCRIPT_COMMANDS dispatch table.
// ---------------------------------------------------------------------------

/**
 * Handle `ai-toolkit reset` -- requires --local, transforms args for install.sh.
 * @param {string[]} args
 */
function handleReset(args) {
  if (!args.includes('--local')) {
    console.error('Error: ai-toolkit reset requires --local flag');
    console.error('Usage: ai-toolkit reset --local');
    process.exit(1);
  }
  run(scriptPath('install.py'), ['--local', '--reset', ...args.filter(a => a !== '--local')]);
}

/**
 * Handle `ai-toolkit benchmark` -- branches on --my-config flag.
 * @param {string[]} args
 */
function handleBenchmark(args) {
  if (args.includes('--my-config')) {
    run(scriptPath('benchmark_config.py'), [TOOLKIT_DIR]);
  } else {
    run(scriptPath('benchmark_ecosystem.py'), args, { cwd: TOOLKIT_DIR });
  }
}

/**
 * Handle `ai-toolkit create` -- validates subcommand before dispatch.
 * @param {string[]} args
 */
function handleCreate(args) {
  if (args[0] === 'skill') {
    run(scriptPath('create_skill.py'), args.slice(1), { cwd: TOOLKIT_DIR });
  } else {
    console.error('Usage: ai-toolkit create skill <name> --template=<type>');
    console.error('Templates: linter, reviewer, generator, workflow, knowledge');
    process.exit(1);
  }
}

/**
 * Handle `ai-toolkit sync` -- validates that at least one flag is provided.
 * @param {string[]} args
 */
function handleSync(args) {
  if (args.length === 0) {
    console.error('Usage: ai-toolkit sync [--export|--push|--pull <gist-id>|--import <file>]');
    process.exit(1);
  }
  run(scriptPath('sync.py'), args);
}

/**
 * Handle `ai-toolkit remove-rule` -- validates rule name, resolves target dir.
 * @param {string[]} args
 */
function handleRemoveRule(args) {
  const ruleName = args[0];
  if (!ruleName) {
    console.error('Usage: ai-toolkit remove-rule <rule-name> [target-dir]');
    process.exit(1);
  }
  const targetDir = args[1] || process.env.HOME;
  run(scriptPath('remove_rule.py'), [ruleName, targetDir]);
}

/**
 * Handle `ai-toolkit add-rule` -- validates rule file, resolves absolute path.
 * @param {string[]} args
 */
function handleAddRule(args) {
  const ruleFile = args[0];
  if (!ruleFile) {
    console.error('Usage: ai-toolkit add-rule <rule-file> [rule-name]');
    process.exit(1);
  }
  const absRuleFile = path.resolve(CWD, ruleFile);
  const ruleName = args[1];
  run(scriptPath('add_rule.py'), ruleName ? [absRuleFile, ruleName] : [absRuleFile]);
}

/**
 * Handle `ai-toolkit generate-all` -- runs every generator plus llms-txt.
 * @param {string[]} _args - Unused, kept for signature consistency
 */
function handleGenerateAll(_args) {
  for (const gen of Object.values(GENERATORS)) {
    writeGeneratorOutput(gen);
  }
  generateLlmsTxt();
}

/** @type {Record<string, (args: string[]) => void>} */
const SPECIAL_HANDLERS = {
  'reset':        handleReset,
  'benchmark':    handleBenchmark,
  'create':       handleCreate,
  'sync':         handleSync,
  'plugin':       (args) => run(scriptPath('plugin.py'), args),
  'remove-rule':  handleRemoveRule,
  'add-rule':     handleAddRule,
  'llms-txt':     (_args) => generateLlmsTxt(),
  'generate-all': handleGenerateAll,
};

// ---------------------------------------------------------------------------
// Main dispatch
// ---------------------------------------------------------------------------

const [,, command, ...args] = process.argv;

if (!command || command === 'help' || command === '--help' || command === '-h') {
  showHelp();
} else if (SPECIAL_HANDLERS[command]) {
  SPECIAL_HANDLERS[command](args);
} else if (SCRIPT_COMMANDS[command]) {
  runScript(command, args);
} else if (GENERATORS[command]) {
  writeGeneratorOutput(GENERATORS[command]);
} else {
  console.error(`Unknown command: ${command}`);
  showHelp();
  process.exit(1);
}
