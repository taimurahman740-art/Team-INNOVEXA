import {afterEach, describe, expect, it, vi} from "vitest";
import {getIssues, postIssue, verifyStaffKey, patchStatus, getIssueHistory} from "./api.js";
afterEach(() => vi.unstubAllGlobals());
function mockResponse(body, ok = true, status = 200) {
  return {ok, status, json: async () => body, text: async () => typeof body === "string" ? body : JSON.stringify(body)};
}
describe("API client", () => {
  it("loads issues from the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse([{id: 1}]));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getIssues()).resolves.toEqual([{id: 1}]);
    expect(fetchMock.mock.calls[0][0]).toContain("/issues");
  });
  it("submits a report as JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({id: 2}));
    vi.stubGlobal("fetch", fetchMock);
    const payload = {title: "Broken light", description: "Not working", category: "Electrical", location: "Room 2"};
    await expect(postIssue(payload)).resolves.toEqual({id: 2});
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(payload);
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
  });
  it("sends staff key for protected actions", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ok: true}));
    vi.stubGlobal("fetch", fetchMock);
    await verifyStaffKey("secret-test-key");
    await patchStatus(4, "Resolved", "secret-test-key");
    await getIssueHistory(4, "secret-test-key");
    for (const [, options] of fetchMock.mock.calls) expect(options.headers["X-Staff-Key"]).toBe("secret-test-key");
    expect(fetchMock.mock.calls[1][0]).toContain("/issues/4/status");
    expect(fetchMock.mock.calls[2][0]).toContain("/issues/4/history");
  });
  it("surfaces API validation details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse({detail: "Unsupported image"}, false, 422)));
    await expect(postIssue({})).rejects.toThrow("Unsupported image");
  });
});
