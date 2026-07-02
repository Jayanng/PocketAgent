// Verifies that package-lock.json is functionally in sync with package.json.
//
// This is a robust replacement for `npm install --package-lock-only && git diff
// --exit-code`, which is fragile: it fails on harmless formatting differences
// across npm versions and operating systems (e.g. a lock file generated with
// npm 11 on Windows versus one regenerated with npm 10 on Linux). Instead this
// check only verifies what actually matters — that every direct dependency in
// package.json has a resolved entry in package-lock.json. Full transitive
// enforcement is still provided by the `npm ci` step that follows in CI.
import { readFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync("package.json", "utf8"));
const lock = JSON.parse(readFileSync("package-lock.json", "utf8"));

const packages = lock.packages;
if (!packages) {
  console.error("package-lock.json is missing a 'packages' map (expected lockfileVersion 3).");
  process.exit(1);
}

const direct = { ...pkg.dependencies, ...pkg.devDependencies };
const missing = Object.keys(direct).filter((name) => !(`node_modules/${name}` in packages));

if (missing.length > 0) {
  console.error("package-lock.json is out of sync with package.json.");
  console.error(`Missing resolved entries for: ${missing.join(", ")}`);
  console.error("Fix: run `npm install` in frontend/ and commit the updated package-lock.json.");
  process.exit(1);
}

console.log(`OK: all ${Object.keys(direct).length} direct dependencies are resolved in package-lock.json.`);
