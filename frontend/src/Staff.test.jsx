// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {afterEach,describe,expect,it,vi} from "vitest";
import {cleanup,render,screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Staff from "./Staff.jsx";
import * as api from "./api.js";

vi.mock("./api.js",()=>({
  getStaffSetupStatus:vi.fn(),loginStaff:vi.fn(),bootstrapStaffAdmin:vi.fn(),
  getStaffIssues:vi.fn(),getStaffUsers:vi.fn(),createStaffUser:vi.fn(),
  assignIssue:vi.fn(),getIssueHistory:vi.fn(),
  changeStaffPassword:vi.fn(),setStaffActive:vi.fn(),resetStaffPassword:vi.fn(),
  getResponseTimes:vi.fn(()=>Promise.resolve(null)),
  reviewDuplicate:vi.fn(),
}));
afterEach(()=>{cleanup();vi.clearAllMocks();});

const issue={id:42,title:"Broken classroom light",description:"The light is not working.",category:"Electrical",priority:"High",status:"Submitted",location:"Engineering Building, Room 101",department:"Electrical Maintenance",assigned_staff_id:null,risk_level:"Low",risk_score:0,risk_reasons:[],created_at:"2026-01-01T00:00:00Z"};
const staffUser={id:7,email:"tech@campus.test",full_name:"Campus Technician",department:"Electrical Maintenance",role:"staff",is_active:true};
const adminUser={id:1,email:"admin@campus.test",full_name:"Campus Admin",department:"Campus Administration",role:"admin"};
const session=user=>({access_token:"test-session-token",user});

describe("individual staff task centre",()=>{
  it("signs in an individual staff member before enabling task actions",async()=>{
    const user=userEvent.setup();
    api.getStaffSetupStatus.mockResolvedValue({setup_available:false});
    api.loginStaff.mockResolvedValue(session(staffUser));
    api.getStaffIssues.mockResolvedValue([issue]);
    const onUpdate=vi.fn().mockResolvedValue({...issue,status:"In Progress"});
    render(<Staff issues={[issue]} live onUpdate={onUpdate}/>);
    await user.type(await screen.findByLabelText("Email"),"tech@campus.test");
    await user.type(screen.getByLabelText("Password"),"secure-staff-password");
    await user.click(screen.getByRole("button",{name:"Sign in"}));
    expect(await screen.findByText("Campus Technician")).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"Start work"})).toBeEnabled();
    await user.click(screen.getByRole("button",{name:"Start work"}));
    // The 4th argument is the optional resolution note; starting work sends none.
    expect(onUpdate).toHaveBeenCalledWith(42,"In Progress","test-session-token",undefined);
  });

  it("allows administrators to create staff and assign a department task",async()=>{
    const user=userEvent.setup();
    api.getStaffSetupStatus.mockResolvedValue({setup_available:false});
    api.loginStaff.mockResolvedValue(session(adminUser));
    api.getStaffIssues.mockResolvedValue([issue]);
    api.getStaffUsers.mockResolvedValue([staffUser]);
    api.assignIssue.mockResolvedValue({...issue,assigned_staff_id:7});
    render(<Staff issues={[issue]} live onUpdate={vi.fn()}/>);
    await user.type(await screen.findByLabelText("Email"),"admin@campus.test");
    await user.type(screen.getByLabelText("Password"),"secure-admin-password");
    await user.click(screen.getByRole("button",{name:"Sign in"}));
    await user.click(await screen.findByRole("tab",{name:"Team"}));
    expect(screen.getByText("Create staff account")).toBeInTheDocument();
    await user.click(screen.getByRole("tab",{name:"Tasks"}));
    const assignment=screen.getByLabelText("Assign to");
    await user.selectOptions(assignment,"7");
    expect(api.assignIssue).toHaveBeenCalledWith(42,7,"test-session-token");
  });

  it("offers one-time first administrator setup when no accounts exist",async()=>{
    const user=userEvent.setup();
    api.getStaffSetupStatus.mockResolvedValue({setup_available:true});
    api.bootstrapStaffAdmin.mockResolvedValue(session(adminUser));
    api.getStaffIssues.mockResolvedValue([]);
    api.getStaffUsers.mockResolvedValue([]);
    render(<Staff issues={[]} live onUpdate={vi.fn()}/>);
    expect(await screen.findByText("Create the first administrator")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Administrator name"),"Campus Admin");
    await user.type(screen.getByLabelText("One-time setup key"),"bootstrap-key");
    await user.type(screen.getByLabelText("Email"),"admin@campus.test");
    await user.type(screen.getByLabelText("Password"),"secure-admin-password");
    await user.click(screen.getByRole("button",{name:"Create administrator"}));
    expect(api.bootstrapStaffAdmin).toHaveBeenCalledWith(expect.objectContaining({bootstrap_key:"bootstrap-key",email:"admin@campus.test"}));
  });

  it("signs the user out after changing their own password",async()=>{
    const user=userEvent.setup();
    api.getStaffSetupStatus.mockResolvedValue({setup_available:false});
    api.loginStaff.mockResolvedValue(session(staffUser));
    api.getStaffIssues.mockResolvedValue([issue]);
    api.changeStaffPassword.mockResolvedValue({message:"ok"});
    render(<Staff issues={[issue]} live onUpdate={vi.fn()}/>);
    await user.type(await screen.findByLabelText("Email"),"tech@campus.test");
    await user.type(screen.getByLabelText("Password"),"secure-staff-password");
    await user.click(screen.getByRole("button",{name:"Sign in"}));
    await screen.findByText("Campus Technician");
    await user.click(screen.getByRole("tab",{name:"Account"}));
    await user.type(screen.getByLabelText("Current password"),"secure-staff-password");
    await user.type(screen.getByLabelText("New password (minimum 12 characters)"),"another-secure-password");
    await user.click(screen.getByRole("button",{name:"Update password"}));
    expect(api.changeStaffPassword).toHaveBeenCalledWith("secure-staff-password","another-secure-password","test-session-token");
    expect(await screen.findByText("Your password was changed. Please sign in again.")).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"Sign in"})).toBeInTheDocument();
  });
});
