import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

function canonicalizePath(inputPath) {
  const resolved = path.resolve(inputPath);
  const parsed = path.parse(resolved);
  const segments = resolved.slice(parsed.root.length).split(path.sep).filter(Boolean);
  let current = parsed.root;

  for (const segment of segments) {
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      current = path.join(current, segment);
      continue;
    }

    const actual = entries.find((entry) => entry.name.toLowerCase() === segment.toLowerCase())?.name ?? segment;
    current = path.join(current, actual);
  }

  return current;
}

const [command, ...args] = process.argv.slice(2);

if (!command) {
  console.error("Usage: node scripts/with-canonical-cwd.mjs <command> [...args]");
  process.exit(1);
}

const cwd = canonicalizePath(process.cwd());
const localEntrypoints = {
  eslint: path.join(cwd, "node_modules", "eslint", "bin", "eslint.js"),
  next: path.join(cwd, "node_modules", "next", "dist", "bin", "next"),
};
const localEntrypoint = localEntrypoints[command];
const executable = localEntrypoint && fs.existsSync(localEntrypoint) ? process.execPath : command;
const spawnArgs = localEntrypoint && fs.existsSync(localEntrypoint) ? [localEntrypoint, ...args] : args;

const child = spawn(executable, spawnArgs, {
  cwd,
  env: process.env,
  stdio: "inherit",
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  }

  process.exit(code ?? 1);
});
