import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./context/AuthContext";
import { MonitoringProvider } from "./context/MonitoringContext";
import { NotificationProvider } from "./context/NotificationContext";
import { WellProvider } from "./context/WellContext";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <WellProvider>
          <MonitoringProvider>
            <NotificationProvider>
              <App />
            </NotificationProvider>
          </MonitoringProvider>
        </WellProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
