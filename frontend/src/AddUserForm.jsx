import { useState } from "react";

export default function AddUserForm() {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    password: ""
  });
  const [message, setMessage] = useState("");

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleAddUser(e) {
    e.preventDefault();
    try {
      const res = await fetch("/api/owners", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage("User added!");
        setForm({ first_name: "", last_name: "", email: "", phone: "", password: "" });
      } else {
        setMessage(data.message || "Error adding user");
      }
    } catch (err) {
      setMessage("Error: " + err.message);
    }
  }

  return (
    <form onSubmit={handleAddUser} className="pet-form">
      <input name="first_name" value={form.first_name} onChange={handleChange} placeholder="First Name" required />
      <input name="last_name" value={form.last_name} onChange={handleChange} placeholder="Last Name" required />
      <input name="email" value={form.email} onChange={handleChange} placeholder="Email" required />
      <input name="phone" value={form.phone} onChange={handleChange} placeholder="Phone" required />
      <input name="password" type="password" value={form.password} onChange={handleChange} placeholder="Password" required />
      <button type="submit">Add User</button>
      {message && <p>{message}</p>}
    </form>
  );
}
