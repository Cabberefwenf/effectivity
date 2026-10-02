import "server-only";
import { readFileSync } from "node:fs";
import path from "node:path";
import { TABLES, type Tables } from "./api";

/** The bundled synthetic sample is examples/*.csv, read at build time. There is no second copy. */
export function loadSample(root: string = process.cwd()): Tables {
  const out = {} as Tables;
  for (const name of TABLES) {
    out[name] = readFileSync(path.join(root, "examples", `${name}.csv`), "utf8");
  }
  return out;
}
