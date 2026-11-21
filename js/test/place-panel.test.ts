import { describe, expect, it } from "vitest";

import { PANEL_GAP, PANEL_MARGIN, PANEL_MAX_HEIGHT, placePanel } from "../src/toolbar/place-panel";

const VIEWPORT = { width: 1000, height: 800 };

function trigger(left: number, top: number, width = 40, height = 30) {
  return { left, top, right: left + width, bottom: top + height };
}

describe("placePanel", () => {
  it("opens below the trigger, aligned to its start", () => {
    const placed = placePanel(trigger(100, 50), { width: 150, height: 200 }, VIEWPORT);
    expect(placed).toEqual({
      left: 100,
      top: 80 + PANEL_GAP,
      maxHeight: PANEL_MAX_HEIGHT,
      side: "below",
    });
  });

  it("aligns to the trigger's end when the start would cross the right edge", () => {
    const placed = placePanel(trigger(900, 50), { width: 150, height: 200 }, VIEWPORT);
    expect(placed.left).toBe(940 - 150);
    expect(placed.left + 150).toBeLessThanOrEqual(VIEWPORT.width);
  });

  it("clamps to the margin when even end alignment does not fit", () => {
    const placed = placePanel(trigger(10, 50, 20), { width: 150, height: 200 }, { width: 160, height: 800 });
    expect(placed.left).toBe(PANEL_MARGIN);
    const wide = placePanel(trigger(990, 50, 20), { width: 150, height: 200 }, VIEWPORT);
    expect(wide.left).toBe(1000 - PANEL_MARGIN - 150);
  });

  it("opens above when the space below is short and the space above is larger", () => {
    const placed = placePanel(trigger(100, 700), { width: 150, height: 200 }, VIEWPORT);
    expect(placed.side).toBe("above");
    expect(placed.top).toBe(700 - PANEL_GAP - 200);
    expect(placed.maxHeight).toBe(PANEL_MAX_HEIGHT);
  });

  it("stays below when below is short but above is shorter", () => {
    const placed = placePanel(trigger(100, 100), { width: 150, height: 260 }, { width: 1000, height: 300 });
    expect(placed.side).toBe("below");
    expect(placed.maxHeight).toBe(300 - 130 - PANEL_GAP - PANEL_MARGIN);
  });

  it("stays below when the panel fits below even though there is more room above", () => {
    const placed = placePanel(trigger(100, 500), { width: 150, height: 200 }, VIEWPORT);
    expect(placed).toMatchObject({ side: "below", top: 530 + PANEL_GAP });
  });

  it("caps maxHeight to the larger side when neither fits", () => {
    const placed = placePanel(trigger(100, 200), { width: 150, height: 280 }, { width: 1000, height: 300 });
    const above = 200 - PANEL_GAP - PANEL_MARGIN;
    expect(placed).toMatchObject({ side: "above", maxHeight: above, top: 200 - PANEL_GAP - above });
  });

  it("never reports a negative maxHeight", () => {
    const placed = placePanel(trigger(100, 0, 40, 300), { width: 150, height: 200 }, { width: 1000, height: 300 });
    expect(placed.maxHeight).toBe(0);
  });
});
