const API_URL = "http://127.0.0.1:8000";

export async function sendMessage(message) {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: "user1",
      message: message,
    }),
  });

  return await response.json();
}