import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "../pages/LoginPage";
import { AuthProvider } from "../context/AuthContext";
import { authApi } from "../services/api";
import { vi } from "vitest";

describe("login page", () => {
  it("renders DrillLens branding, fields, and MVP demo accounts", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    // Branding
    expect(screen.getAllByText("DrillLens").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Powered by eRTMAC-NWIS").length).toBeGreaterThan(0);

    // Form fields & buttons
    expect(screen.getByLabelText(/Username or Email/i)).toBeTruthy();
    expect(screen.getByLabelText(/^Password$/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Show" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Login" })).toBeTruthy();

    // MVP Demo Accounts section
    expect(screen.getByText("MVP Demo Accounts")).toBeTruthy();
    expect(screen.getByText("MVP Demo Credentials")).toBeTruthy();

    // Role buttons
    expect(screen.getByRole("button", { name: "Login as Admin" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Login as Drilling Engineer" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Login as Viewer" })).toBeTruthy();

    // Role descriptions
    expect(screen.getByText("Full system access")).toBeTruthy();
    expect(screen.getByText("Engineering intelligence and review access")).toBeTruthy();
    expect(screen.getByText("Read-only access")).toBeTruthy();

    // Credentials displayed
    expect(screen.getAllByText("Admin123!").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Engineer123!").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Viewer123!").length).toBeGreaterThan(0);
  });

  it("fills credentials when an account card is clicked", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    const engineerCard = screen.getByText("Engineering intelligence and review access").closest("div");
    if (engineerCard) fireEvent.click(engineerCard);

    const usernameInput = screen.getByLabelText(/Username or Email/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/^Password$/i) as HTMLInputElement;

    expect(usernameInput.value).toBe("engineer");
    expect(passwordInput.value).toBe("Engineer123!");
  });

  it("toggles password visibility with Show/Hide button", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    const passwordInput = screen.getByLabelText(/^Password$/i) as HTMLInputElement;
    const toggleButton = screen.getByRole("button", { name: "Show" });

    expect(passwordInput.type).toBe("password");
    fireEvent.click(toggleButton);
    expect(passwordInput.type).toBe("text");
    expect(screen.getByRole("button", { name: "Hide" })).toBeTruthy();
  });

  it("shows clean error message when login fails", async () => {
    vi.spyOn(authApi, "login").mockRejectedValueOnce(new Error("Network Error"));

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    const loginButton = screen.getByRole("button", { name: "Login as Admin" });
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(
        screen.getByText("Login failed. Please verify the credentials or check the backend connection."),
      ).toBeTruthy();
    });
  });
});
