#!/usr/bin/env node
"use strict";

// Synchronous transport for large solc standard-JSON inputs/outputs.  The
// solcjs CLI may truncate stdout under some Node versions; this wrapper does
// not change compiler settings or results.
const fs = require("fs");
const path = require("path");

if (process.argv.length !== 5) {
  throw new Error("usage: compile_standard_json.js SOLC_PACKAGE INPUT OUTPUT");
}

const solcPackage = path.resolve(process.argv[2]);
const inputPath = path.resolve(process.argv[3]);
const outputPath = path.resolve(process.argv[4]);
const solc = require(solcPackage);
const output = solc.compile(fs.readFileSync(inputPath, "utf8"));
fs.writeFileSync(outputPath, output);

