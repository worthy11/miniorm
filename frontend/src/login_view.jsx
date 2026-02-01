import { useState } from "react";
import "./styles/login.css";

export default function LoginView({ onLogin, onAdmin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    password: ""
  });
  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    console.log("Register clicked", form);
    if (!form.first_name || !form.last_name || !form.email || !form.phone || !form.password) {
      setMessage("Please fill in all fields");
      return;
    }
    try {
      const res = await fetch("/api/owners", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { setMessage("Server error: " + text); return; }
      if (res.ok) {
        setMessage("Registration successful! You can now log in.");
        setIsRegister(false);
        setForm({ first_name: "", last_name: "", email: "", phone: "", password: "" });
      } else {
        setMessage(data?.message || "Unknown error");
      }
      console.log("Register response", res.status, data);
    } catch (err) {
      setMessage("Error: " + err.message);
      console.log("Register error", err);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    console.log("Login clicked", form);
    if (!form.email || !form.password) {
      setMessage("Please enter email and password");
      return;
    }
    try {
      const res = await fetch(`/api/owners?email=${encodeURIComponent(form.email)}&password=${encodeURIComponent(form.password)}`);
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { setMessage("Server error: " + text); return; }
      if (res.ok && data.length > 0) {
        setMessage("");
        onLogin(data[0]);
      } else {
        setMessage("Invalid email or password");
      }
      console.log("Login response", res.status, data);
    } catch (err) {
      setMessage("Error: " + err.message);
      console.log("Login error", err);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>{isRegister ? "Register" : "Login"}</h2>
        <form onSubmit={isRegister ? handleRegister : handleLogin}>
          {isRegister && (
            <>
              <div className="form-group">
                <label>First Name:</label>
                <input name="first_name" value={form.first_name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Last Name:</label>
                <input name="last_name" value={form.last_name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Phone:</label>
                <input name="phone" value={form.phone} onChange={handleChange} />
              </div>
            </>
          )}
          <div className="form-group">
            <label>Email:</label>
            <input name="email" value={form.email} onChange={handleChange} type="email" />
          </div>
          <div className="form-group">
            <label>Password:</label>
            <input name="password" value={form.password} onChange={handleChange} type="password" />
          </div>
          <button type="submit" className="submit-btn">{isRegister ? "Register" : "Login"}</button>
        </form>
        <button className="switch-btn" onClick={() => { setIsRegister(!isRegister); setMessage(""); }}>
          {isRegister ? "Already have an account? Login" : "Don't have an account? Register"}
        </button>
        <button className="switch-btn" style={{marginTop: 12}} onClick={() => onAdmin && onAdmin()}>
          Admin Dashboard
        </button>
        {message && <p className={message.includes("success") ? "msg-success" : "msg-error"}>{message}</p>}
      </div>
    </div>
  );
}
