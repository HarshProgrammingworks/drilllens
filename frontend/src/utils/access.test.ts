import { canAdmin, canWrite } from "./access";

describe("role access", () => {
  it("lets engineers write and blocks viewers", () => {
    expect(canWrite("DRILLING_ENGINEER")).toBe(true);
    expect(canWrite("VIEWER")).toBe(false);
    expect(canAdmin("ADMIN")).toBe(true);
    expect(canAdmin("DRILLING_ENGINEER")).toBe(false);
  });
});
