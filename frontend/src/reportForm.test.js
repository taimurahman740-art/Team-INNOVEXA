import {describe, expect, it} from "vitest";
import {composeLocation, describeAnalysis, reportPayload} from "./reportForm.js";
describe("report form helpers", () => {
 it("joins building, floor and room, and sends equipment separately", () => {
  expect(composeLocation({building:"Library",floor:"2",room:"204",equipment:"Projector"})).toBe("Library, Floor 2, Room 204");
  expect(reportPayload({title:"t",description:"d",category:"",building:"Library",floor:"",room:"",equipment:" Projector ",image_data:null,image_analysis:null}).equipment).toBe("Projector");
  expect(composeLocation({building:"Library",floor:"",room:""})).toBe("Library");
 });
 it("sends auto-detect as null and drops analysis without a photo", () => {
  const p=reportPayload({title:"t",description:"d",category:"",building:"Library",floor:"",room:"",equipment:"",image_data:null,image_analysis:{category:"IT"}});
  expect(p.category).toBeNull();
  expect(p.image_analysis).toBeNull();
 });
 it("describes results in words, not percentages", () => {
  expect(describeAnalysis({needs_more_info:true}).status).toBe("unavailable");
  const m=describeAnalysis({category:"Electrical",score:0.9,match_strength:"strong",hazard:{label:"Exposed electrical wiring",score:0.8}}).message;
  expect(m).toMatch(/Exposed electrical wiring/);
  expect(m).not.toMatch(/%/);
 });
});
