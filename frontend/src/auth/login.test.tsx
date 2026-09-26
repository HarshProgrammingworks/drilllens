import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "../pages/LoginPage";
import { AuthProvider } from "../context/AuthContext";

describe("login page", () => {
  it("renders DrillLens branding and the login form", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getAllByText("DrillLens").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Powered by eRTMAC-NWIS").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Login" })).toBeTruthy();
  });
});
