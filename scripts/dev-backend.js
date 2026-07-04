#!/usr/bin/env node
/**
 * Cross-platform backend dev launcher used by `npm run dev:backend`.
 *
 * Mirrors the venv-detection in start.sh so `npm run dev` works on Windows
 * and Unix WITHOUT manually activating the venv: it locates the project
 * virtualenv (backend/.venv, then backend/venv) and runs uvicorn from it,
 * falling back to system `python` on PATH (with a warning) if none exists.
 */
"use strict";

const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const backendDir = path.join(root, "backend");

const isWin = process.platform === "win32";
const venvDirs = [".venv", "venv"];
const binDir = isWin ? "Scripts" : "bin";
const exe = isWin ? "python.exe" : "python";

let pythonBin = null;
for (const v of venvDirs) {
  const candidate = path.join(backendDir, v, binDir, exe);
  if (fs.existsSync(candidate)) {
    pythonBin = candidate;
    break;
  }
}

if (!pythonBin) {
  pythonBin = isWin ? "python" : "python3";
  console.warn(
    `\u26a0\ufe0f  No project virtualenv found in backend/.venv (or backend/venv).\n` +
    `   Falling back to system \`${pythonBin}\`. For a clean setup run:\n` +
    `     cd backend && python -m venv .venv && ` +
    (isWin ? ".venv\\Scripts\\activate" : "source .venv/bin/activate") +
    ` && pip install -r requirements.txt\n`
  );
} else {
  console.log(`Using venv python: ${pythonBin}`);
}

const args = [
  "-m", "uvicorn", "main:app",
  "--reload", "--port", "8000", "--host", "0.0.0.0",
];

// Strip stale OS env vars so backend/.env is the single source of truth for
// provider config. Without this, OPENAI_* / GMI_* inherited from the parent
// shell (e.g. a previous hackathon or GMI endpoint) override .env values via
// pydantic-settings, silently routing the agent to the wrong LLM provider.
const ENV_VARS_TO_STRIP = [
  "OPENAI_API_KEY",
  "OPENAI_BASE_URL",
  "OPENAI_MODEL",
  "GMI_API_KEY",
];
const cleanEnv = { ...process.env };
for (const key of ENV_VARS_TO_STRIP) {
  delete cleanEnv[key];
}

const child = spawn(pythonBin, args, {
  cwd: backendDir,
  stdio: "inherit",
  shell: false,
  env: cleanEnv,
});

child.on("error", (err) => {
  console.error(`\n\u274c Failed to launch backend: ${err.message}`);
  if (pythonBin === "python" || pythonBin === "python3") {
    console.error("   `python` was not found on PATH. Activate the venv or install Python.");
  } else {
    console.error("   Is the venv intact? Try recreating it (see the warning above).");
  }
  process.exit(1);
});

child.on("exit", (code, signal) => {
  process.exit(code ?? (signal ? 128 + 1 : 0));
});

// Forward Ctrl+C / terminate to uvicorn for a clean shutdown.
for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    if (!child.killed) child.kill(sig);
  });
}
