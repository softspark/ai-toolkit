#!/usr/bin/env node
'use strict';

const { execFileSync, spawnSync, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const TOOLKIT_DIR = path.dirname(__dirname);
const CWD = process.cwd();

if (!process.env.HOME) {
  console.error('Error: HOME environment variable is not set');
  process.exit(1);
}

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
  'augment-rules':        { script: 'generate_augment.py',       dest: path.join('.augment', 'rules', 'ai-toolkit.md'), mkdir: '.augment/rules' },
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
  update: 'Re-apply toolkit with saved modules from state.json (use --local to also refresh project configs)',
  status: 'Show installed modules, version, and profile from state.json',
  reset: 'Wipe and recreate project-local configs from scratch (requires --local)',
  uninstall: 'Remove ai-toolkit from ~/.claude/',
  'add-rule': 'Register a rule file in ~/.ai-toolkit/rules/ (applied on every install/update)',
  'remove-rule': 'Unregister a rule from ~/.ai-toolkit/rules/ and remove its block from CLAUDE.md',
  'inject-hook': 'Inject external hooks into ~/.claude/settings.json (tagged with _source for idempotent updates)',
  'remove-hook': 'Remove injected hooks by source name from ~/.claude/settings.json',
  validate: 'Verify toolkit integrity',
  doctor: 'Check install health, hooks, and artifact drift',
  eject: 'Export standalone config (no symlinks, no toolkit dependency)',
  benchmark: 'Benchmark toolkit (--my-config to compare your setup vs defaults vs ecosystem)',
  'benchmark-ecosystem': 'Generate ecosystem benchmark snapshot (GitHub metadata + offline fallback)',
  evaluate: 'Run skill evaluation suite',
  stats: 'Show skill usage statistics (--reset to clear, --json for raw output)',
  create: 'Scaffold new skill from template (e.g. create skill my-lint --template=linter)',
  mcp: 'Manage MCP server templates (list, show, add, remove)',
  plugin: 'Manage plugin packs (install, remove, update, clean, list, status)',
  sync: 'Sync config to/from GitHub Gist (--export, --push, --pull, --import)',
  'cursor-rules': 'Generate .cursorrules for Cursor IDE (legacy)',
  'cursor-mdc': 'Generate .cursor/rules/*.mdc for Cursor IDE (recommended)',
  'windsurf-rules': 'Generate .windsurfrules for Windsurf (legacy)',
  'windsurf-dir-rules': 'Generate .windsurf/rules/*.md for Windsurf (recommended)',
  'copilot-instructions': 'Generate .github/copilot-instructions.md',
  'gemini-md': 'Generate GEMINI.md for Gemini CLI',
  'cline-rules': 'Generate .clinerules for Cline (legacy)',
  'cline-dir-rules': 'Generate .cline/rules/*.md for Cline (recommended)',
  'roo-modes': 'Generate .roomodes for Roo Code',
  'roo-dir-rules': 'Generate .roo/rules/*.md shared rules for Roo Code',
  'aider-conf': 'Generate .aider.conf.yml for Aider',
  'conventions-md': 'Generate CONVENTIONS.md for Aider (auto-loaded)',
  'augment-rules': 'Generate .augment/rules/ai-toolkit.md for Augment (legacy)',
  'augment-dir-rules': 'Generate .augment/rules/ai-toolkit-*.md for Augment (recommended)',
  'antigravity-rules': 'Generate .agent/rules/ and .agent/workflows/ for Google Antigravity',
  'agents-md': 'Regenerate AGENTS.md from agent definitions',
  'llms-txt': 'Generate llms.txt and llms-full.txt',
  'generate-all': 'Generate all platform configs at once (agents, cursor, windsurf, copilot, gemini, cline, roo, aider, augment, antigravity, llms)',
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
  console.log('  --modules <list>  Install specific modules (e.g. core,agents,rules-typescript)');
  console.log('  --lang <list>   Explicitly select language rules (e.g. typescript, go,python)');
  console.log('  --editors <list> Install editor configs: cursor,windsurf,cline,roo,aider,augment,copilot,antigravity (or "all")');
  console.log('                  Default with --local: auto-detect from existing project files');
  console.log('  --auto-detect   Detect project languages and install matching rule modules');
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
  console.log('\nOptions for inject-hook:');
  console.log('  <hooks-file>    Path to JSON file with {"hooks": {"EventName": [...]}} format');
  console.log('  [target-dir]    Target dir containing .claude/settings.json (default: $HOME)');
  console.log('\nOptions for remove-hook:');
  console.log('  <source-name>   Source tag to remove (derived from hooks filename stem)');
  console.log('  [target-dir]    Target dir containing .claude/settings.json (default: $HOME)');
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
  console.log('\nOptions for mcp:');
  console.log('  list                          List available MCP templates');
  console.log('  show <name>                   Show template details');
  console.log('  add <name> [names..] [--target <path>]  Add servers to .mcp.json');
  console.log('  remove <name>                 Remove a server from .mcp.json');
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
 * Handle `ai-toolkit inject-hook` -- injects external hooks into settings.json.
 * @param {string[]} args
 */
function handleInjectHook(args) {
  const hooksFile = args[0];
  if (!hooksFile) {
    console.error('Usage: ai-toolkit inject-hook <hooks-file.json> [target-dir]');
    process.exit(1);
  }
  const absHooksFile = path.resolve(CWD, hooksFile);
  const targetDir = args[1] || process.env.HOME;
  run(scriptPath('inject_hook_cli.py'), [absHooksFile, targetDir]);
}

/**
 * Handle `ai-toolkit remove-hook` -- removes injected hooks by source name.
 * @param {string[]} args
 */
function handleRemoveHook(args) {
  const sourceName = args[0];
  if (!sourceName) {
    console.error('Usage: ai-toolkit remove-hook <hook-source-name> [target-dir]');
    process.exit(1);
  }
  const targetDir = args[1] || process.env.HOME;
  run(scriptPath('inject_hook_cli.py'), ['--remove', sourceName, targetDir]);
}

/**
 * Handle `ai-toolkit mcp` -- delegates to mcp_manager.py with subcommand.
 * @param {string[]} args
 */
function handleMcp(args) {
  if (args.length === 0) {
    console.error('Usage: ai-toolkit mcp <list|show|add|remove> [args..]');
    process.exit(1);
  }
  run(scriptPath('mcp_manager.py'), args);
}

/**
 * Handle `ai-toolkit generate-all` -- runs every generator plus llms-txt.
 * @param {string[]} _args - Unused, kept for signature consistency
 */
function handleGenerateAll(_args) {
  for (const gen of Object.values(GENERATORS)) {
    writeGeneratorOutput(gen);
  }
  // Directory-based generators (multi-file output)
  run(scriptPath('generate_antigravity.py'), [CWD]);
  run(scriptPath('generate_cursor_mdc.py'), [CWD]);
  run(scriptPath('generate_windsurf_rules.py'), [CWD]);
  run(scriptPath('generate_cline_rules.py'), [CWD]);
  run(scriptPath('generate_roo_rules.py'), [CWD]);
  run(scriptPath('generate_augment_rules.py'), [CWD]);
  // Single-file generators
  const conventionsOut = runGenerator('generate_conventions.py');
  fs.writeFileSync(path.join(CWD, 'CONVENTIONS.md'), conventionsOut);
  console.log('Generated: CONVENTIONS.md');
  generateLlmsTxt();
}

/**
 * Handle `ai-toolkit status` -- shows installed modules from state.json.
 * @param {string[]} _args
 */
function handleStatus(_args) {
  run(scriptPath('install.py'), ['--status']);
}

/**
 * Handle `ai-toolkit update` -- re-runs install with saved state.
 * Reads state.json to find previously installed modules and profile,
 * then re-runs install.py with those flags to perform an incremental update.
 * @param {string[]} args
 */
function handleUpdate(args) {
  const statePath = path.join(process.env.HOME, '.ai-toolkit', 'state.json');
  let stateArgs = [];

  if (fs.existsSync(statePath)) {
    try {
      const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      const modules = state.installed_modules;
      const profile = state.profile;

      // If we have recorded modules, pass them to install.py
      if (Array.isArray(modules) && modules.length > 0) {
        stateArgs.push('--modules', modules.join(','));
      } else if (profile) {
        stateArgs.push('--profile', profile);
      }
    } catch (_err) {
      // State file is corrupt or unreadable -- fall through to plain install
    }
  }

  // User-provided args override state-derived args
  run(scriptPath('install.py'), [...stateArgs, ...args]);
}

/** @type {Record<string, (args: string[]) => void>} */
const SPECIAL_HANDLERS = {
  'status':       handleStatus,
  'update':       handleUpdate,
  'reset':        handleReset,
  'benchmark':    handleBenchmark,
  'create':       handleCreate,
  'sync':         handleSync,
  'mcp':          handleMcp,
  'plugin':       (args) => run(scriptPath('plugin.py'), args),
  'remove-rule':  handleRemoveRule,
  'add-rule':     handleAddRule,
  'inject-hook':  handleInjectHook,
  'remove-hook':  handleRemoveHook,
  'llms-txt':     (_args) => generateLlmsTxt(),
  'antigravity-rules': (_args) => run(scriptPath('generate_antigravity.py'), [CWD]),
  'cursor-mdc':   (_args) => run(scriptPath('generate_cursor_mdc.py'), [CWD]),
  'windsurf-dir-rules': (_args) => run(scriptPath('generate_windsurf_rules.py'), [CWD]),
  'cline-dir-rules': (_args) => run(scriptPath('generate_cline_rules.py'), [CWD]),
  'roo-dir-rules': (_args) => run(scriptPath('generate_roo_rules.py'), [CWD]),
  'conventions-md': (_args) => { const out = runGenerator('generate_conventions.py'); fs.writeFileSync(path.join(CWD, 'CONVENTIONS.md'), out); console.log('Generated: CONVENTIONS.md'); },
  'augment-dir-rules': (_args) => run(scriptPath('generate_augment_rules.py'), [CWD]),
  'generate-all': handleGenerateAll,
};

// ---------------------------------------------------------------------------
// Main dispatch
// ---------------------------------------------------------------------------

const [,, command, ...args] = process.argv;

if (!command || command === 'help' || command === '--help' || command === '-h') {
  showHelp();
} else if (command === '--version' || command === '-v' || command === 'version') {
  console.log(require('../package.json').version);
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
