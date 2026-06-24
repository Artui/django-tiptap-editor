// Re-injecting the bundle's asset tag (e.g. inside swapped-in content) re-runs
// its classic-script IIFE. A second execution must be a no-op: it must NOT build
// a fresh, empty glue module and clobber window.DjangoTipTap, which would orphan
// every mounted editor. Re-evaluating the module via resetModules + dynamic
// import reproduces the second IIFE run against the same window.
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.resetModules();
  // window persists across module resets; clear the install so the next test
  // (and re-runs) start from a pristine global.
  delete (window as { DjangoTipTap?: unknown }).DjangoTipTap;
  document.body.innerHTML = "";
});

describe("double bundle-execution guard", () => {
  it("a re-injected bundle keeps the first glue module and does not clobber it", async () => {
    const first = (await import("../src/index")).default;
    expect(window.DjangoTipTap).toBe(first);

    // Second execution of the bundle body against the same window.
    vi.resetModules();
    const second = (await import("../src/index")).default;

    // The guard kept the first module installed and live...
    expect(window.DjangoTipTap).toBe(first);
    // ...and the second execution produced a distinct object that was NOT installed.
    expect(second).not.toBe(first);
  });

  it("the surviving module still mounts editors after a re-execution", async () => {
    const first = (await import("../src/index")).default;
    vi.resetModules();
    await import("../src/index"); // re-exec — should bail

    const form = document.createElement("form");
    form.innerHTML = '<textarea id="id_after" data-tiptap-config="{}"></textarea>';
    document.body.appendChild(form);

    // The first module's listeners are the live ones; its autoMount still works.
    first.autoMount();
    expect(first.get("id_after")).not.toBeNull();
    expect(window.DjangoTipTap.get("id_after")).not.toBeNull();

    first.destroy("id_after");
  });
});
