import React, { useState, useEffect } from "react";

function App() {
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => setHealthStatus(data))
      .catch(() => setHealthStatus({ status: "unreachable" }));
  }, []);

  return (
    <div
      style={{
        fontFamily: "sans-serif",
        padding: "2rem",
        maxWidth: "600px",
        margin: "0 auto",
      }}
    >
      <h1>IUT Cafeteria Crisis System</h1>
      <p>Microservices-based ordering platform.</p>
      <h2>Gateway Health</h2>
      <pre
        style={{ background: "#f4f4f4", padding: "1rem", borderRadius: "8px" }}
      >
        {healthStatus ? JSON.stringify(healthStatus, null, 2) : "Loading..."}
      </pre>
    </div>
  );
}

export default App;
