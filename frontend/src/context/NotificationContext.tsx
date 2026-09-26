import { createContext, useContext, useEffect, useState } from "react";
import { getToken } from "../api/client";
import { systemApi } from "../services/api";
import { useAuth } from "./AuthContext";

interface Note {
  id: string;
  type: string;
  title: string;
  body: string;
  link?: string;
  read: boolean;
  created_at?: string;
}

interface NoteState {
  items: Note[];
  unread: number;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
}

const NotificationContext = createContext<NoteState | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [items, setItems] = useState<Note[]>([]);

  async function refresh() {
    const response = await systemApi.notifications();
    setItems(response.data as unknown as Note[]);
  }

  async function markRead(id: string) {
    await systemApi.read(id);
    await refresh();
  }

  useEffect(() => {
    if (!user) return;
    refresh().catch(() => undefined);
    const timer = window.setInterval(() => refresh().catch(() => undefined), 15000);
    const token = getToken();
    let socket: WebSocket | null = null;
    if (token) {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws/notifications?token=${encodeURIComponent(token)}`);
      socket.onmessage = () => refresh().catch(() => undefined);
      const ping = window.setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) socket.send("ping");
      }, 20000);
      return () => {
        window.clearInterval(timer);
        window.clearInterval(ping);
        socket?.close();
      };
    }
    return () => window.clearInterval(timer);
  }, [user]);

  const unread = items.filter((item) => !item.read).length;
  return <NotificationContext.Provider value={{ items, unread, refresh, markRead }}>{children}</NotificationContext.Provider>;
}

export function useNotes() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("NotificationProvider is required");
  return ctx;
}
