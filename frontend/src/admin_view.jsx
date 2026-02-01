import { useEffect, useState } from "react";
import "./styles/desktop.css";
import AddUserForm from "./AddUserForm";

export default function AdminView() {
  const [vets, setVets] = useState([]);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    license: ""
  });
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchVets();
  }, []);

  async function fetchVets() {
    const res = await fetch("/api/vets");
    const data = await res.json();
    setVets(data);
  }

  async function handleAddVet(e) {
    e.preventDefault();
    try {
      const res = await fetch("/api/vets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage("Vet added!");
        setForm({ first_name: "", last_name: "", email: "", phone: "", license: "" });
        fetchVets();
      } else {
        setMessage(data.message || "Error adding vet");
      }
    } catch (err) {
      setMessage("Error: " + err.message);
    }
  }

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
  }

  return (
    <div className="desktop-container">
      <div className="desktop-card">
        <h2>Admin Dashboard</h2>
        <div className="dashboard-section">
          <h3>Add Vet</h3>
          <form onSubmit={handleAddVet} className="pet-form">
            <input name="first_name" value={form.first_name} onChange={handleChange} placeholder="First Name" required />
            <input name="last_name" value={form.last_name} onChange={handleChange} placeholder="Last Name" required />
            <input name="email" value={form.email} onChange={handleChange} placeholder="Email" required />
            <input name="phone" value={form.phone} onChange={handleChange} placeholder="Phone" required />
            <input name="license" value={form.license} onChange={handleChange} placeholder="License" required />
            <button type="submit">Add Vet</button>
          </form>
          {message && <p>{message}</p>}
        </div>
        <div className="dashboard-section">
          <h3>Add User</h3>
          <AddUserForm />
        </div>
        <div className="dashboard-section">
          <h3>Vet List</h3>
          <ul>
            {vets.map(v => (
              <li key={v.vet_id}>
                {v.first_name} {v.last_name} ({v.email}, {v.phone}) - License: {v.license}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
