
import { useState, useEffect } from "react";
import { Send, Plus, MessageSquare, Bot, User, Loader2 } from "lucide-react";

function App() {
  const [sessionId, setSessionId] = useState(
    () => crypto.randomUUID()
  );

  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState([]);
  useEffect(() => {
  const fetchSessions = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/sessions");

      if (!response.ok) {
        throw new Error("Failed to fetch chat history");
      }

      const data = await response.json();
      setSessions(data.sessions);

    } catch (error) {
      console.error("Error loading sessions:", error);
    }
  };

  fetchSessions();
}, []);

  const sendMessage = async () => {
    if (!message.trim() || loading) return;

    const userMessage = message.trim();

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage }
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          metadata: data.metadata
        }
      ]);

    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error: " + error.message
        }
      ]);
      // Refresh recent conversations
const sessionsResponse = await fetch(
  "http://127.0.0.1:8000/sessions"
);

if (sessionsResponse.ok) {
  const sessionsData = await sessionsResponse.json();
  setSessions(sessionsData.sessions);
}
    } finally {
      setLoading(false);
    }
  };
const loadSession = async (id) => {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/sessions/${id}/messages`
    );

    if (!response.ok) {
      throw new Error("Failed to load conversation");
    }

    const data = await response.json();

    setSessionId(id);
    setMessages(data.messages);
    setMessage("");

  } catch (error) {
    console.error("Error loading conversation:", error);
  }
};
  const newChat = () => {
    setSessionId(crypto.randomUUID());
    setMessages([]);
    setMessage("");
  };

  return (
    <div className="min-h-screen bg-[#0b0d12] text-white flex">

      <aside className="w-72 bg-[#11141c] border-r border-gray-800 p-5">
        <h1 className="text-2xl font-bold text-purple-400">
          LYFTR AI
        </h1>

        <button
          onClick={newChat}
          className="w-full mt-8 p-3 rounded-xl bg-purple-600 hover:bg-purple-700 flex items-center justify-center gap-2"
        >
          <Plus size={18} /> New Chat
        </button>

        <div className="mt-10 text-gray-400 text-sm">
  Recent Chats
</div>

<div className="mt-5 space-y-3">
  {sessions.map((session) => (
    <button
      key={session.session_id}
      className="w-full text-left text-sm text-gray-400 hover:text-white hover:bg-[#191d27] p-3 rounded-lg truncate"
      onClick={() => loadSession(session.session_id)}
    >
      <MessageSquare size={16} className="inline mr-2" />
      {session.title}
    </button>
  ))}
</div>
      </aside>

      <main className="flex-1 flex flex-col h-screen">

        <div className="flex-1 overflow-y-auto p-8">

          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Bot size={55} className="text-purple-400 mb-5" />

              <h2 className="text-4xl font-bold">
                Welcome to Lyftr AI
              </h2>

              <p className="text-gray-400 mt-4">
                Your intelligent AI assistant. What can I help you with today?
              </p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.role === "assistant" && (
                    <Bot className="text-purple-400 shrink-0 mt-1" />
                  )}

                  <div
                    className={`max-w-[80%] p-4 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-purple-600"
                        : "bg-[#191d27]"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>

{msg.role === "assistant" && msg.metadata && (
  <div className="mt-3 rounded-lg bg-[#191d27] border border-gray-700 p-3 text-xs text-gray-400 space-y-2">
    <div className="font-semibold text-purple-400">
      Response Metadata
    </div>

    <div>Model: {msg.metadata.model}</div>
    <div>Source: {msg.metadata.resolution_source}</div>
    <div>Latency: {msg.metadata.latency_ms} ms</div>
    <div>Tokens: {msg.metadata.input_tokens} input / {msg.metadata.output_tokens} output</div>
    <div>API Key: {msg.metadata.key_id || "Cache hit"}</div>
    <div>Fallback Attempts: {msg.metadata.fallback_attempts}</div>
  </div>
)}
                    {msg.metadata && (
                      <p className="text-xs text-gray-400 mt-3">
                        {msg.metadata.model} · {msg.metadata.latency_ms} ms
                        · {msg.metadata.resolution_source}
                      </p>
                    )}
                  </div>

                  {msg.role === "user" && (
                    <User className="text-gray-400 shrink-0 mt-1" />
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-3 text-gray-400">
                  <Loader2 className="animate-spin text-purple-400" size={20} />
                  Lyftr AI is thinking...
                </div>
              )}
            </div>
          )}

        </div>

        <div className="p-6">
          <div className="max-w-3xl mx-auto flex gap-3 bg-[#191d27] border border-gray-700 rounded-2xl p-3">

            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Message Lyftr AI..."
              className="flex-1 bg-transparent outline-none text-white p-2"
              disabled={loading}
            />

            <button
              onClick={sendMessage}
              disabled={loading || !message.trim()}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-40 px-5 rounded-xl"
            >
              <Send size={20} />
            </button>

          </div>

          <p className="text-center text-gray-500 text-xs mt-3">
            Lyftr AI can make mistakes. Verify important information.
          </p>
        </div>

      </main>
    </div>
  );
}

export default App;
