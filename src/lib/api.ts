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

export async function sendMessage(session_id: number, message: string) {
  const res = await fetch(`${API_URL}/api/session/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, message }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function getLabs(session_id: number) {
  const res = await fetch(`${API_URL}/api/session/${session_id}/labs`);
  if (!res.ok) throw new Error("Failed to fetch labs");
  return res.json();
}

export interface AssistantMsg { role: "user" | "assistant"; content: string }

export async function askAssistant(messages: AssistantMsg[], language: string) {
  const res = await fetch(`${API_URL}/api/assistant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, language }),
  });
  if (!res.ok) throw new Error("Failed to reach assistant");
  return res.json() as Promise<{ reply: string }>;
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
