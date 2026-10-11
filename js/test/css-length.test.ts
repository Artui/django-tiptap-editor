// The unit list is the half of the length rule a truth table cannot pin by
// example: a unit the two sides disagree on passes both suites until someone
// writes a case for it. So the table carries the list, the Python suite checks
// it against constants.CSS_LENGTH_UNITS, and this checks it against the glue's.
import { expect, it } from "vitest";

import { CSS_LENGTH_UNITS, isCssLength } from "../src/css-length";
import lengths from "./fixtures/css-lengths.json";

it("accepts exactly the units the Python validator accepts", () => {
  expect([...CSS_LENGTH_UNITS].sort()).toEqual(lengths.units);
});

it.each(lengths.units)("accepts a length in %s", (unit) => {
  expect(isCssLength(`10${unit}`)).toBe(true);
  expect(isCssLength(`calc(100vh - 10${unit})`)).toBe(true);
});
