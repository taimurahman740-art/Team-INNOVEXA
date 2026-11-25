// Helpers for the student report form (kept out of components so Vite fast refresh stays clean).
import {MATCH_STRENGTH, categoryName} from "./ui.js";

// Building, floor and room are joined into the readable location text. Building and
// the optional equipment are also sent as their own fields (building analytics, staff detail).
export const composeLocation = ({building, floor, room}) => [
  building?.trim(),
  floor?.trim() && `Floor ${floor.trim()}`,
  room?.trim() && `Room ${room.trim()}`,
].filter(Boolean).join(", ").slice(0, 180);

export const reportPayload = f => ({
  title: f.title, description: f.description, category: f.category || null,
  building: f.building.trim(), floor: f.floor.trim() || null, room: f.room.trim() || null,
  equipment: f.equipment?.trim() || null,
  location: composeLocation(f), image_data: f.image_data, image_analysis: f.image_data ? f.image_analysis : null,
});

export function describeAnalysis(r) {
  if (r.needs_more_info) return {status: "unavailable", message: r.message || "The photo is not clear enough. Please add a short title and description."};
  const strength = (MATCH_STRENGTH[r.match_strength] || MATCH_STRENGTH.moderate).label.toLowerCase();
  const hazard = r.hazard ? ` Possible hazard: ${r.hazard.label}. Staff will confirm it on site.` : "";
  return {status: "success", message: `AI suggests ${categoryName(r.category)} (${strength}).${hazard} Empty fields were filled from the photo. Review them before submitting.`};
}
