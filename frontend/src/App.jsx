import { useState } from "react";
import "./App.css";

function App() {
  const [response, setResponse] = useState("");
  const [formData, setFormData] = useState({ name: "", email: "" });
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");

  const sendMessage = async () => {
    const res = await fetch("/api/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Cześć backend!" }),
    });
    const data = await res.json();
    setResponse(data.received);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const createUser = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.email) {
      setMessage("Please fill in all fields");
      return;
    }

    try {
      const res = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      
      if (res.ok) {
        setMessage(`✓ User "${data.name}" created successfully!`);
        setUsers([...users, data]);
        setFormData({ name: "", email: "" });
        
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (error) {
      setMessage("Error creating user: " + error.message);
    }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
      <h1>Test komunikacji React ↔ FastAPI</h1>
      
      <div style={{ marginBottom: "2rem", padding: "1rem", backgroundColor: "#f0f0f0", borderRadius: "8px" }}>
        <h3>Test Endpoint</h3>
        <button onClick={sendMessage}>Wyślij wiadomość</button>
        <p>Odpowiedź backendu: {response}</p>
      </div>

      <div style={{ marginBottom: "2rem", padding: "1rem", backgroundColor: "#f9f9f9", borderRadius: "8px" }}>
        <h3>Create User</h3>
        <form onSubmit={createUser}>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="name" style={{ display: "block", marginBottom: "0.5rem" }}>
              Name:
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="Enter name"
              style={{
                width: "100%",
                padding: "0.5rem",
                border: "1px solid #ddd",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="email" style={{ display: "block", marginBottom: "0.5rem" }}>
              Email:
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="Enter email"
              style={{
                width: "100%",
                padding: "0.5rem",
                border: "1px solid #ddd",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <button
            type="submit"
            style={{
              padding: "0.75rem 1.5rem",
              backgroundColor: "#007bff",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "1rem",
            }}
          >
            Create User
          </button>
        </form>

        {message && (
          <p
            style={{
              marginTop: "1rem",
              padding: "0.75rem",
              backgroundColor: message.includes("✓") ? "#d4edda" : "#f8d7da",
              color: message.includes("✓") ? "#155724" : "#721c24",
              borderRadius: "4px",
            }}
          >
            {message}
          </p>
        )}
      </div>

      {users.length > 0 && (
        <div style={{ padding: "1rem", backgroundColor: "#e8f5e9", borderRadius: "8px" }}>
          <h3>Created Users</h3>
          <ul>
            {users.map((user, index) => (
              <li key={index}>
                <strong>{user.name}</strong> - {user.email}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;

