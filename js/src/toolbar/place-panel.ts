// Where an open dropdown panel goes, in viewport coordinates: below the trigger
// at its start, end-aligned when that would cross the right edge, above when the
// space below is short and the space above is larger. Pure, so it is tested
// without a layout engine.
export const PANEL_GAP = 4;
export const PANEL_MARGIN = 8;
export const PANEL_MAX_HEIGHT = 280;

export interface TriggerRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface Placement {
  left: number;
  top: number;
  maxHeight: number;
  side: "below" | "above";
}

export function placePanel(
  trigger: TriggerRect,
  panel: { width: number; height: number },
  viewport: { width: number; height: number },
): Placement {
  let left = trigger.left;
  if (left + panel.width > viewport.width - PANEL_MARGIN) {
    left = trigger.right - panel.width;
  }
  left = Math.max(PANEL_MARGIN, Math.min(left, viewport.width - PANEL_MARGIN - panel.width));

  const below = viewport.height - trigger.bottom - PANEL_GAP - PANEL_MARGIN;
  const above = trigger.top - PANEL_GAP - PANEL_MARGIN;
  const height = Math.min(panel.height, PANEL_MAX_HEIGHT);
  const side = below < height && above > below ? "above" : "below";
  const maxHeight = Math.max(0, Math.min(PANEL_MAX_HEIGHT, side === "below" ? below : above));
  const top =
    side === "below"
      ? trigger.bottom + PANEL_GAP
      : trigger.top - PANEL_GAP - Math.min(height, maxHeight);
  return { left, top, maxHeight, side };
}
