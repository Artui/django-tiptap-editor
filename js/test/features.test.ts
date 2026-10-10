// The feature model is the server's (FEATURE_CORE / FEATURE_DEPENDENCIES in
// django_tiptap_editor/constants.py) and the server resolves it before writing
// data-tiptap-config. init(config) never sees the server, so features.ts restates
// it; these tests hold that restatement equal to the exported one, so the two
// paths cannot mount different extensions for the same list.
import { describe, expect, it } from "vitest";

import { BUILTIN_NAMES } from "../src/build-extensions";
import { FEATURE_CORE, FEATURE_DEPENDENCIES, resolveFeatures } from "../src/features";
import modelFixture from "./fixtures/feature-model.json";

interface FeatureModel {
  core: string[];
  features: string[];
  dependencies: Record<string, string[]>;
}

const model = modelFixture as FeatureModel;

const sorted = (values: Iterable<string>): string[] => [...values].sort();

describe("the JS feature model matches the server's", () => {
  it("has the same core", () => {
    expect(sorted(FEATURE_CORE)).toEqual(sorted(model.core));
  });

  it("has the same dependencies", () => {
    expect(sorted(Object.keys(FEATURE_DEPENDENCIES))).toEqual(sorted(Object.keys(model.dependencies)));
    for (const [name, deps] of Object.entries(model.dependencies)) {
      expect(sorted(FEATURE_DEPENDENCIES[name]), name).toEqual(sorted(deps));
    }
  });

  it("names exactly the built-in extensions, split into core and features", () => {
    expect(sorted([...model.core, ...model.features])).toEqual(sorted(BUILTIN_NAMES));
    for (const name of [...FEATURE_CORE, ...Object.keys(FEATURE_DEPENDENCIES), ...Object.values(FEATURE_DEPENDENCIES).flat()]) {
      expect(BUILTIN_NAMES.has(name), name).toBe(true);
    }
  });
});

describe("resolveFeatures", () => {
  it("is null, unrestricted, without a features list", () => {
    expect(resolveFeatures({})).toBeNull();
    expect(resolveFeatures({ features: undefined })).toBeNull();
    expect(resolveFeatures({ features: null })).toBeNull();
  });

  it("adds the core to an empty list", () => {
    expect(sorted(resolveFeatures({ features: [] })!)).toEqual(sorted(model.core));
  });

  it("closes over dependencies, transitively", () => {
    const resolved = resolveFeatures({ features: ["highlight", "table", "bulletList"] })!;
    expect(sorted(resolved)).toEqual(
      sorted([
        ...model.core,
        "highlight",
        "backgroundColor",
        "textStyle",
        "table",
        "tableRow",
        "tableCell",
        "tableHeader",
        "bulletList",
        "listItem",
      ]),
    );
  });

  it.each(["tableRow", "tableCell", "tableHeader"])(
    "gives the whole table when only %s is named",
    (part) => {
      expect(sorted(resolveFeatures({ features: [part] })!)).toEqual(
        sorted(resolveFeatures({ features: ["table"] })!),
      );
    },
  );

  it("is idempotent, so a list the server already resolved is a no-op", () => {
    const once = resolveFeatures({ features: ["fontSize", "orderedList", "bold"] })!;
    const twice = resolveFeatures({ features: [...once] })!;
    expect(sorted(twice)).toEqual(sorted(once));
  });
});
