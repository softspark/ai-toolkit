"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");

const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const FALLBACK_PORT = 38888;

let currentContent = "<p>Waiting for content...</p>";
let idleTimer = null;

function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    console.log("Idle timeout reached. Shutting down.");
    process.exit(0);
  }, IDLE_TIMEOUT_MS);
}

const templatePath = path.join(__dirname, "frame-template.html");
const templateHtml = fs.readFileSync(templatePath, "utf-8");

const server = http.createServer((req, res) => {
  resetIdleTimer();

  if (req.method === "GET" && (req.url === "/" || req.url === "/index.html")) {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(templateHtml);
    return;
  }

  if (req.method === "GET" && req.url === "/content") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ html: currentContent }));
    return;
  }

  if (req.method === "POST" && req.url === "/update") {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      try {
        const data = JSON.parse(body);
        if (typeof data.html === "string") {
          currentContent = data.html;
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ ok: true }));
        } else {
          res.writeHead(400, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Missing 'html' field" }));
        }
      } catch {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Invalid JSON" }));
      }
    });
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not Found");
});

server.listen(0, () => {
  const port = server.address().port;
  console.log(`Visual companion ready at http://localhost:${port}`);
  resetIdleTimer();
});

server.on("error", () => {
  server.listen(FALLBACK_PORT, () => {
    console.log(`Visual companion ready at http://localhost:${FALLBACK_PORT}`);
    resetIdleTimer();
  });
});

process.on("SIGINT", () => process.exit(0));
process.on("SIGTERM", () => process.exit(0));
