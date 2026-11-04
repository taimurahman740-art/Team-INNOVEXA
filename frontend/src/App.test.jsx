// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {afterEach, describe, expect, it, vi} from "vitest";
import {cleanup, render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import * as api from "./api.js";
vi.mock("./api.js", () => ({getIssues: vi.fn(), postIssue: vi.fn(), patchStatus: vi.fn(), verifyStaffKey: vi.fn(), getIssueHistory: vi.fn()}));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const records = [
 {id:1,title:"Broken classroom light",description:"Light is not working",category:"Electrical",priority:"Medium",status:"Submitted",location:"Room 101",department:"Electrical Maintenance",created_at:"2026-01-01T00:00:00Z"},
 {id:2,title:"Leaking tap",description:"Water under sink",category:"Plumbing",priority:"Low",status:"Resolved",location:"Room 202",department:"Plumbing Maintenance",created_at:"2026-01-02T00:00:00Z"}
];
describe("student issue interface", () => {
 it("loads reports and filters them by search text", async () => {
  api.getIssues.mockResolvedValue(records);
  const user=userEvent.setup(); render(<App/>);
  expect(await screen.findByText("Broken classroom light")).toBeInTheDocument();
  expect(screen.getByText("Leaking tap")).toBeInTheDocument();
  await user.type(screen.getByRole("textbox",{name:"Search reports"}),"plumbing");
  expect(screen.queryByText("Broken classroom light")).not.toBeInTheDocument();
  expect(screen.getByText("Leaking tap")).toBeInTheDocument();
 });
 it("submits a valid report and displays the saved record", async () => {
  api.getIssues.mockResolvedValue([]);
  api.postIssue.mockResolvedValue({...records[0],id:3,title:"Broken projector"});
  const user=userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button",{name:/report issue/i}));
  await user.type(screen.getByLabelText("Issue title"),"Broken projector");
  await user.type(screen.getByLabelText("Description"),"The projector does not turn on.");
  await user.type(screen.getByLabelText("Location"),"Lecture Hall 3");
  await user.click(screen.getByRole("button",{name:"Submit report"}));
  expect(await screen.findByText("Broken projector")).toBeInTheDocument();
  expect(api.postIssue).toHaveBeenCalledWith(expect.objectContaining({title:"Broken projector",description:"The projector does not turn on.",location:"Lecture Hall 3"}));
 });
 it("shows an error when report submission fails", async () => {
  api.getIssues.mockResolvedValue([]); api.postIssue.mockRejectedValue(new Error("offline"));
  const user=userEvent.setup(); render(<App/>);
  await user.click(await screen.findByRole("button",{name:/report issue/i}));
  await user.type(screen.getByLabelText("Issue title"),"Broken projector");
  await user.type(screen.getByLabelText("Description"),"The projector does not turn on.");
  await user.type(screen.getByLabelText("Location"),"Lecture Hall 3");
  await user.click(screen.getByRole("button",{name:"Submit report"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not save");
 });
});
