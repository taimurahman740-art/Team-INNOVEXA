// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {afterEach, describe, expect, it, vi} from "vitest";
import {cleanup, render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import * as api from "./api.js";
vi.mock("./api.js", () => ({getIssues: vi.fn(), postIssue: vi.fn(), patchStatus: vi.fn(), getStaffSetupStatus: vi.fn(), loginStaff: vi.fn(), bootstrapStaffAdmin: vi.fn(), getStaffIssues: vi.fn(), getStaffUsers: vi.fn(), createStaffUser: vi.fn(), assignIssue: vi.fn(), getIssueHistory: vi.fn(), getIssueTracking: vi.fn(), classifyImage: vi.fn(), getResponseTimes: vi.fn(), changeStaffPassword: vi.fn(), setStaffActive: vi.fn(), resetStaffPassword: vi.fn()}));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const records = [
 {id:1,title:"Broken classroom light",description:"Light is not working",category:"Electrical",priority:"Medium",status:"Submitted",location:"Room 101",department:"Electrical Maintenance",created_at:"2026-01-01T00:00:00Z"},
 {id:2,title:"Leaking tap",description:"Water under sink",category:"Plumbing",priority:"Low",status:"Resolved",location:"Room 202",department:"Plumbing Maintenance",created_at:"2026-01-02T00:00:00Z"}
];
describe("student issue interface", () => {
 it("loads reports and filters them by search text", async () => {
  api.getIssues.mockResolvedValue(records);
  const user=userEvent.setup(); render(<App/>);
  const table=await screen.findByRole("table");
  expect(within(table).getByText("Broken classroom light")).toBeInTheDocument();
  expect(within(table).getByText("Leaking tap")).toBeInTheDocument();
  await user.type(screen.getByRole("textbox",{name:"Search reports"}),"plumbing");
  expect(within(screen.getByRole("table")).queryByText("Broken classroom light")).not.toBeInTheDocument();
  expect(within(screen.getByRole("table")).getByText("Leaking tap")).toBeInTheDocument();
 });
 it("submits a valid report and displays the saved record", async () => {
  api.getIssues.mockResolvedValue([]);
  api.postIssue.mockResolvedValue({...records[0],id:3,title:"Broken projector"});
  const user=userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button",{name:/report issue/i}));
  await user.type(screen.getByLabelText("Issue title"),"Broken projector");
  await user.type(screen.getByLabelText("Description"),"The projector does not turn on.");
  await user.type(screen.getByLabelText("Building"),"Lecture Hall 3");
  await user.click(screen.getByRole("button",{name:"Submit report"}));
  expect(await screen.findByRole("heading",{name:"Report submitted"})).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"Done"}));
  expect(within(await screen.findByRole("table")).getByText("Broken projector")).toBeInTheDocument();
  expect(api.postIssue).toHaveBeenCalledWith(expect.objectContaining({title:"Broken projector",description:"The projector does not turn on.",location:"Lecture Hall 3",building:"Lecture Hall 3",category:null}));
 });
 it("supports a photo-only report using the photo suggestion", async () => {
  api.getIssues.mockResolvedValue([]);
  api.classifyImage.mockResolvedValue({category:"HVAC",score:0.82,needs_more_info:false,hazard:null,suggested_title:"Heating or air-conditioning problem",suggested_description:"Photo report. The image appears to show a HVAC issue (82% match).",category_scores:{HVAC:0.82}});
  api.postIssue.mockResolvedValue({...records[0],id:4,title:"Heating or air-conditioning problem",category:"HVAC"});
  const user=userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button",{name:/report issue/i}));
  await user.type(screen.getByLabelText("Building"),"Library");
  await user.upload(screen.getByLabelText(/attach a photo/i), new File([new Uint8Array([137,80,78,71,13,10,26,10])],"ac.png",{type:"image/png"}));
  expect(await screen.findByText(/AI suggests HVAC/)).toBeInTheDocument();
  expect(screen.getByLabelText("Issue title")).toHaveValue("Heating or air-conditioning problem");
  expect(screen.getByLabelText("Issue title")).not.toBeRequired();
  await user.click(screen.getByRole("button",{name:"Submit report"}));
  expect(await screen.findByRole("heading",{name:"Report submitted"})).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"Done"}));
  expect(within(await screen.findByRole("table")).getByText("Heating or air-conditioning problem")).toBeInTheDocument();
  expect(api.postIssue).toHaveBeenCalledWith(expect.objectContaining({building:"Library",location:"Library",image_analysis:expect.objectContaining({category:"HVAC"})}));
 });
 it("asks for a description when the photo is unclear", async () => {
  api.getIssues.mockResolvedValue([]);
  api.classifyImage.mockResolvedValue({category:"Other",score:0.2,needs_more_info:true,message:"The photo is not clear enough to identify the problem. Please add a short title and description."});
  const user=userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button",{name:/report issue/i}));
  await user.upload(screen.getByLabelText(/attach a photo/i), new File([new Uint8Array([137,80,78,71,13,10,26,10])],"blur.png",{type:"image/png"}));
  expect(await screen.findByText(/not clear enough/)).toBeInTheDocument();
  expect(screen.getByLabelText("Issue title")).toBeRequired();
  expect(screen.getByLabelText("Issue title")).toHaveValue("");
 });
 it("shows an error when report submission fails", async () => {
  api.getIssues.mockResolvedValue([]); api.postIssue.mockRejectedValue(new Error("offline"));
  const user=userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button",{name:/report issue/i}));
  await user.type(screen.getByLabelText("Issue title"),"Broken projector");
  await user.type(screen.getByLabelText("Description"),"The projector does not turn on.");
  await user.type(screen.getByLabelText("Building"),"Lecture Hall 3");
  await user.click(screen.getByRole("button",{name:"Submit report"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not save");
 });
});
