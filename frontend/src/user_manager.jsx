import { useState } from "react";
import "./styles/user-manager.css";

export default function UserManager() {
  const [formData, setFormData] = useState({ first_name: "", last_name: "", email: "", phone: "" });
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const createPerson = async (e) => {
    e.preventDefault();
    if (!formData.first_name || !formData.last_name || !formData.email || !formData.phone) {
      setMessage("Please fill in all fields");
      return;
    }
    try {
      const res = await fetch("/api/persons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      let data;
      const text = await res.text();
      try {
        data = JSON.parse(text);
      } catch (jsonErr) {
        setMessage("Server error: " + text);
        return;
      }
      if (res.ok) {
        setMessage(`✓ Person "${data.first_name} ${data.last_name}" created successfully!`);
        setUsers([...users, data]);
        setFormData({ first_name: "", last_name: "", email: "", phone: "" });
        setTimeout(() => setMessage(""), 3000);
      } else {
        setMessage(data?.message || "Unknown error");
      }
    } catch (error) {
      setMessage("Error creating person: " + error.message);
    }
  };

  return (
    <div className="user-manager-container">
      <h1>Create Person</h1>
      <div className="form-card">
        <form onSubmit={createPerson}>
          <div className="form-group">
            <label htmlFor="first_name" className="form-label">First Name:</label>
            <input
              type="text"
              id="first_name"
              name="first_name"
              value={formData.first_name}
              onChange={handleInputChange}
              placeholder="Enter first name"
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="last_name" className="form-label">Last Name:</label>
            <input
              type="text"
              id="last_name"
              name="last_name"
              value={formData.last_name}
              onChange={handleInputChange}
              placeholder="Enter last name"
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="email" className="form-label">Email:</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="Enter email"
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="phone" className="form-label">Phone:</label>
            <input
              type="text"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleInputChange}
              placeholder="Enter phone"
              className="form-input"
            />
          </div>
          <button
            type="submit"
            className="submit-btn"
          >
            Create Person
          </button>
        </form>
        {message && (
          <p
            className={
              message.includes("✓") ? "msg-success" : "msg-error"
            }
          >
            {message}
          </p>
        )}
      </div>
      {users.length > 0 && (
        <div className="users-list">
          <h3>Created Persons</h3>
          <ul>
            {users.map((user, index) => (
              <li key={index}>
                <strong>{user.first_name} {user.last_name}</strong> - {user.email} - {user.phone}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
