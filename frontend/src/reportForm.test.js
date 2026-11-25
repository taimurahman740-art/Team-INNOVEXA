import {describe, expect, it} from "vitest";
import {composeLocation, describeAnalysis, reportPayload} from "./reportForm.js";
describe("report form helpers", () => {
 it("joins building, floor and room", () => {
  expect(composeLocation({building:"Library",floor:"2",room:"204"})).toBe("Library · Floor 2 · Room 204");
  expect(composeLocation({building:"Library",floor:"",room:""})).toBe("Library");
 });
 it("sends auto-detect as null and drops analysis without a photo", () => {
  const p=reportPayload({title:"t",description:"d",category:"",building:"Library",floor:"",room:"",image_data:null,image_analysis:{category:"IT"}});
  expect(p.category).toBeNull();
  expect(p.image_analysis).toBeNull();
 });
 it("describes uncertain and hazard results", () => {
  expect(describeAnalysis({needs_more_info:true}).status).toBe("unavailable");
  expect(describeAnalysis({category:"Electrical",score:0.9,hazard:{label:"Exposed electrical wiring",score:0.8}}).message).toMatch(/Exposed electrical wiring/);
 });
});
