import {afterEach,describe,expect,it,vi} from "vitest";
import {getIssues,postIssue,getStaffIssues,patchStatus,getIssueHistory,changeStaffPassword} from "./api.js";
afterEach(()=>vi.unstubAllGlobals());
function mockResponse(body,ok=true,status=200){return{ok,status,json:async()=>body,text:async()=>typeof body==="string"?body:JSON.stringify(body)};}
describe("API client",()=>{
  it("loads issues from the backend",async()=>{
    const fetchMock=vi.fn().mockResolvedValue(mockResponse([{id:1}]));
    vi.stubGlobal("fetch",fetchMock);
    await expect(getIssues()).resolves.toEqual([{id:1}]);
    expect(fetchMock.mock.calls[0][0]).toContain("/issues");
  });
  it("submits a report as JSON",async()=>{
    const fetchMock=vi.fn().mockResolvedValue(mockResponse({id:2}));
    vi.stubGlobal("fetch",fetchMock);
    const payload={title:"Broken light",description:"Not working",category:"Electrical",location:"Room 2"};
    await expect(postIssue(payload)).resolves.toEqual({id:2});
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(payload);
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
  });
  it("sends a bearer token for individual staff actions",async()=>{
    const fetchMock=vi.fn().mockResolvedValue(mockResponse([{id:1}]));
    vi.stubGlobal("fetch",fetchMock);
    await getStaffIssues("secret-session-token");
    await patchStatus(4,"Resolved","secret-session-token");
    await getIssueHistory(4,"secret-session-token");
    for(const [,options] of fetchMock.mock.calls) expect(options.headers.Authorization).toBe("Bearer secret-session-token");
    expect(fetchMock.mock.calls[1][0]).toContain("/issues/4/status");
    expect(fetchMock.mock.calls[2][0]).toContain("/issues/4/history");
  });
  it("surfaces API validation details",async()=>{
    vi.stubGlobal("fetch",vi.fn().mockResolvedValue(mockResponse({detail:"Unsupported image"},false,422)));
    await expect(postIssue({})).rejects.toThrow("Unsupported image");
  });
  it("turns FastAPI validation error lists into readable text",async()=>{
    const detail=[{loc:["body","password"],msg:"String should have at least 12 characters"},{loc:["body","email"],msg:"Field required"}];
    vi.stubGlobal("fetch",vi.fn().mockResolvedValue(mockResponse({detail},false,422)));
    await expect(changeStaffPassword("a","b","tok")).rejects.toThrow("String should have at least 12 characters; Field required");
  });
  it("falls back to the raw text for non-JSON errors",async()=>{
    vi.stubGlobal("fetch",vi.fn().mockResolvedValue(mockResponse("Bad gateway",false,502)));
    await expect(getIssues()).rejects.toThrow("Bad gateway");
  });
  it("only sends Content-Type when there is a request body",async()=>{
    const fetchMock=vi.fn().mockResolvedValue(mockResponse([]));
    vi.stubGlobal("fetch",fetchMock);
    await getIssues();
    expect(fetchMock.mock.calls[0][1].headers["Content-Type"]).toBeUndefined();
    await postIssue({title:"x"});
    expect(fetchMock.mock.calls[1][1].headers["Content-Type"]).toBe("application/json");
  });
});
