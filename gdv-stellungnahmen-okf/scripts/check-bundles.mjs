#!/usr/bin/env node
// check-bundles.mjs - validate every OKF bundle in this repo.
//
// Treats each directory under `bundles/` as a bundle, confirms it has a root
// index.md, runs the OKF v0.1 conformance check on it, and warns if it is not
// linked from README.md. Exits non-zero if any bundle fails the hard requirement.
//
// Usage:  node scripts/check-bundles.mjs

import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const validator = join(repoRoot, "scripts", "okf-validate.mjs");
const bundlesDir = join(repoRoot, "bundles");

const bundles = existsSync(bundlesDir)
  ? readdirSync(bundlesDir, { withFileTypes: true })
      .filter((e) => e.isDirectory() && !e.name.startsWith("."))
      .map((e) => e.name)
      .sort()
  : [];

const readme = existsSync(join(repoRoot, "README.md")) ? readFileSync(join(repoRoot, "README.md"), "utf8") : "";

let failed = 0;

if (bundles.length === 0) console.warn("warn  no bundles found under bundles/");

for (const name of bundles) {
  const dir = join(bundlesDir, name);
  console.log(`\n=== ${name} ===`);

  if (!existsSync(join(dir, "index.md"))) {
    console.error(`error ${name}/: not an OKF bundle (no root index.md)`);
    failed++;
    continue;
  }

  try {
    process.stdout.write(execFileSync("node", [validator, dir], { encoding: "utf8" }));
  } catch (e) {
    if (e.stdout) process.stdout.write(e.stdout);
    if (e.stderr) process.stderr.write(e.stderr);
    failed++;
  }

  if (readme && !readme.includes(`${name}/`)) console.warn(`warn  ${name}/ is not linked from README.md`);
}

console.log(`\nChecked ${bundles.length} bundle(s): ${failed} failed.`);
process.exit(failed ? 1 : 0);
