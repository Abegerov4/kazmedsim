const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchScenarios(lang: string, difficulty?: string, specialty?: string) {
  const params = new URLSearchParams({ lang });
  if (difficulty) params.append("difficulty", difficulty);
  if (specialty) params.append("specialty", specialty);
  const res = await fetch(`${API_URL}/api/scenarios?${params}`);
  if (!res.ok) throw new Error("Failed to fetch scenarios");
  return res.json();
}

export async function startSession(scenario_id: number, student_name: string, language: string) {
  const res = await fetch(`${API_URL}/api/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id, student_name, language }),
  });
  if (!res.ok) throw new Error("Failed to start session");
  return res.json();
}

/**
 * Stream the patient reply via SSE, invoking `onDelta` for each text chunk
 * as it arrives. Resolves with the full accumulated text once `done`.
 */
export async function sendMessageStream(
  session_id: number,
  message: string,
  onDelta: (delta: string) => void,
): Promise<{ full: string }> {
  const res = await fetch(`${API_URL}/api/session/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, message }),
  });
  if (!res.ok || !res.body) throw new Error("Failed to send message");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  // Parse the SSE stream by splitting on "\n\n" boundaries.
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const eventStr = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const m = eventStr.match(/^data: (.+)$/m);
      if (!m) continue;
      try {
        const data = JSON.parse(m[1]);
        if (typeof data.delta === "string") {
          full += data.delta;
          onDelta(data.delta);
        } else if (data.done) {
          return { full };
        } else if (data.error) {
          throw new Error(data.error);
        }
      } catch { /* malformed chunk — ignore */ }
    }
  }
  return { full };
}

export async function getLabs(session_id: number) {
  const res = await fetch(`${API_URL}/api/session/${session_id}/labs`);
  if (!res.ok) throw new Error("Failed to fetch labs");
  return res.json();
}

export interface ToolChip { icon: string; label: string }
export interface AssistantMsg { role: "user" | "assistant"; content: string; tools_used?: ToolChip[] }

export async function askAssistant(messages: AssistantMsg[], language: string) {
  const res = await fetch(`${API_URL}/api/assistant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, language }),
  });
  if (!res.ok) throw new Error("Failed to reach assistant");
  return res.json() as Promise<{ reply: string; tools_used?: ToolChip[] }>;
}

export interface RealtimeSession {
  client_secret: string;
  expires_at?: number;
  instructions: string;
  voice: string;
  model: string;
}

export async function getRealtimeSession(session_id: number): Promise<RealtimeSession> {
  const res = await fetch(`${API_URL}/api/realtime/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id }),
  });
  if (!res.ok) throw new Error("Failed to mint realtime session");
  return res.json();
}

export async function logTurn(session_id: number, role: "student" | "patient", text: string) {
  if (!text.trim()) return;
  try {
    await fetch(`${API_URL}/api/session/log_turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, role, text }),
    });
  } catch { /* fire-and-forget — voice still works if logging fails */ }
}

export async function endSession(
  session_id: number,
  student_diagnosis: string,
  student_treatment: string,
  ordered_tests: string[] = [],
  examined = false,
  elapsed_seconds = 0,
) {
  const res = await fetch(`${API_URL}/api/session/end`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, student_diagnosis, student_treatment, ordered_tests, examined, elapsed_seconds }),
  });
  if (!res.ok) throw new Error("Failed to end session");
  return res.json();
}
