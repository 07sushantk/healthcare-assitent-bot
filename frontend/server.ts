import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import cors from "cors";
import "dotenv/config";

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// Forward API request to Python RAG Pipeline
app.post("/api/chat", async (req, res) => {
  const { message, api_key } = req.body;
  if (!message) return res.status(400).json({ error: "Message is required" });
  if (!api_key) return res.status(400).json({ error: "API key is required" });

  try {
    const response = await fetch("http://127.0.0.1:5000/rag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Forward the caller's key in-memory only; do not persist or log it.
      body: JSON.stringify({ message, api_key })
    });

    if (!response.ok) {
      let errorMessage = "Failed to generate response from Python backend";
      try {
        const errorPayload = await response.json();
        if (typeof errorPayload?.detail === "string" && errorPayload.detail) {
          errorMessage = errorPayload.detail;
        }
      } catch {
        // Ignore parse failures and return the generic message.
      }

      console.error("Python API Error:", response.status);
      return res.status(response.status).json({ error: errorMessage });
    }

    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error("Chat API connection error:", error);
    res.status(500).json({ error: "Failed to connect to Python RAG backend. Make sure it is running on port 5000." });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
