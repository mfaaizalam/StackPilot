import { useState } from "react";
import { sendMessage } from "./services/api";

function App() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");

  const handleSend = async () => {
    const data = await sendMessage(message);
    setResponse(data.response);
  };

  return (
    <div className="p-10">
      <h1 className="text-3xl font-bold mb-4">
        StackPilot
      </h1>

      <input
        className="border p-2 mr-2"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
      />

      <button
        className="border px-4 py-2"
        onClick={handleSend}
      >
        Send
      </button>

      <div className="mt-6">
        <h2 className="font-bold">AI Response:</h2>
        <p>{response}</p>
      </div>
    </div>
  );
}

export default App;