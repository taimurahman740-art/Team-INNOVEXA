// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {afterEach, describe, expect, it, vi} from "vitest";
import {cleanup, render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Staff from "./Staff.jsx";
import * as api from "./api.js";

vi.mock("./api.js", () => ({
  verifyStaffKey: vi.fn(),
  getIssueHistory: vi.fn(),
  getStaffIssues: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const issue = {
  id: 42,
  title: "Broken classroom light",
  description: "The light is not working.",
  category: "Electrical",
  priority: "High",
  status: "Submitted",
  location: "Engineering Building, Room 101",
  department: "Electrical Maintenance",
  risk_level: "Low",
  risk_score: 0,
  risk_reasons: [],
  created_at: "2026-01-01T00:00:00Z",
};

describe("staff task centre", () => {
  it("keeps status actions locked until the staff key is verified", async () => {
    const user = userEvent.setup();
    render(<Staff issues={[issue]} live onUpdate={vi.fn()} />);

    expect(screen.getByRole("button", {name: "Start work"})).toBeDisabled();
    expect(screen.getByRole("button", {name: "Mark resolved"})).toBeDisabled();
    expect(screen.getByRole("button", {name: "View history"})).toBeDisabled();

    api.verifyStaffKey.mockResolvedValue({authorized: true});\n    api.getStaffIssues.mockResolvedValue([issue]);
    await user.type(screen.getByPlaceholderText("Staff access key"), "test-key");
    await user.click(screen.getByRole("button", {name: "Unlock actions"}));

    expect(api.verifyStaffKey).toHaveBeenCalledWith("test-key");
    expect(await screen.findByText(/Staff access verified/)).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Start work"})).toBeEnabled();
    expect(screen.getByRole("button", {name: "Mark resolved"})).toBeEnabled();
    expect(screen.getByRole("button", {name: "View history"})).toBeEnabled();
  });

  it("does not unlock actions when staff-key verification fails", async () => {
    const user = userEvent.setup();
    render(<Staff issues={[issue]} live onUpdate={vi.fn()} />);
    api.verifyStaffKey.mockRejectedValue(new Error("A valid staff access key is required."));

    await user.type(screen.getByPlaceholderText("Staff access key"), "wrong-key");
    await user.click(screen.getByRole("button", {name: "Unlock actions"}));

    expect(await screen.findByText("A valid staff access key is required.")).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Start work"})).toBeDisabled();
    expect(screen.getByRole("button", {name: "Mark resolved"})).toBeDisabled();
  });

  it("updates a report and displays its status history after authorization", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn().mockResolvedValue({...issue, status: "In Progress"});
    api.verifyStaffKey.mockResolvedValue({authorized: true});
    api.getIssueHistory.mockResolvedValue([
      {id: 1, old_status: null, new_status: "Submitted", changed_at: "2026-01-01T00:00:00Z", changed_by: "system"},
      {id: 2, old_status: "Submitted", new_status: "In Progress", changed_at: "2026-01-02T00:00:00Z", changed_by: "staff-key"},
    ]);
    render(<Staff issues={[issue]} live onUpdate={onUpdate} />);

    await user.type(screen.getByPlaceholderText("Staff access key"), "test-key");
    await user.click(screen.getByRole("button", {name: "Unlock actions"}));
    await user.click(await screen.findByRole("button", {name: "Start work"}));
    expect(onUpdate).toHaveBeenCalledWith(42, "In Progress", "test-key");

    await user.click(screen.getByRole("button", {name: "View history"}));
    expect(await screen.findByText("Status history")).toBeInTheDocument();
    expect(screen.getByText(/Submitted → In Progress/)).toBeInTheDocument();
    expect(api.getIssueHistory).toHaveBeenCalledWith(42, "test-key");
  });

  it("filters tasks by open, resolved, all, and department", async () => {
    const user = userEvent.setup();
    const resolved = {...issue, id: 43, title: "Resolved plumbing issue", status: "Resolved", department: "Plumbing Maintenance"};
    render(<Staff issues={[issue, resolved]} live onUpdate={vi.fn()} />);

    expect(screen.getByText("Broken classroom light")).toBeInTheDocument();
    expect(screen.queryByText("Resolved plumbing issue")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: "Resolved"}));
    expect(screen.getByText("Resolved plumbing issue")).toBeInTheDocument();
    expect(screen.queryByText("Broken classroom light")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", {name: "All", exact: true}));
    expect(screen.getByText("Resolved plumbing issue")).toBeInTheDocument();
    expect(screen.getByText("Broken classroom light")).toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", {name: "Filter by department"}), "Electrical Maintenance");
    expect(screen.getByText("Broken classroom light")).toBeInTheDocument();
    expect(screen.queryByText("Resolved plumbing issue")).not.toBeInTheDocument();
  });
});
