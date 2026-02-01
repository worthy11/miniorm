import { useEffect, useState } from "react";
import "./styles/desktop.css";

function DesktopView({ user }) {
  const [visits, setVisits] = useState([]);
  const [visitForm, setVisitForm] = useState({ pet_id: "", vet_id: "", date: "", reason: "", paid: 0 });
  const [pets, setPets] = useState([]);
  const [vets, setVets] = useState([]);
  const [petForm, setPetForm] = useState({ name: "", species: "", breed: "", birth_date: "" });
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchVisits();
    fetchPets();
    fetchVets();
  }, []);

  async function fetchVets() {
    const res = await fetch("/api/vets");
    const data = await res.json();
    setVets(data);
  }

  async function fetchVisits() {
    const res = await fetch(`/api/visits?owner_id=${user.owner_id}`);
    const data = await res.json();
    setVisits(data);
  }

  async function fetchPets() {
    const res = await fetch(`/api/pets?owner_id=${user.owner_id}`);
    const data = await res.json();
    console.log("Fetched pets:", data);
    setPets(data);
  }

  async function handleAddVisit(e) {
    e.preventDefault();
    try {
      // Convert pet_id and vet_id to integers for backend
      const visitToSend = {
        ...visitForm,
        pet_id: parseInt(visitForm.pet_id, 10),
        vet_id: parseInt(visitForm.vet_id, 10),
      };
      const res = await fetch("/api/visits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(visitToSend),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage("Visit added!");
        setVisitForm({ pet_id: "", vet_id: "", date: "", reason: "", paid: 0 });
        fetchVisits();
      } else {
        setMessage(data.message || "Error adding visit");
      }
    } catch (err) {
      setMessage("Error: " + err.message);
    }
  }

  async function handleAddPet(e) {
    e.preventDefault();
    try {
      const res = await fetch("/api/pets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...petForm, owner_id: user.owner_id }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage("Pet added!");
        setPetForm({ name: "", species: "", breed: "", birth_date: "" });
        fetchPets();
      } else {
        setMessage(data.message || "Error adding pet");
      }
    } catch (err) {
      setMessage("Error: " + err.message);
    }
  }

  function handleVisitChange(e) {
    const { name, value } = e.target;
    setVisitForm(f => ({ ...f, [name]: value }));
  }

  function handlePetChange(e) {
    const { name, value } = e.target;
    setPetForm(f => ({ ...f, [name]: value }));
  }

  return (
    <div className="desktop-container">
      <div className="desktop-card">
        <h2>Welcome, {user.first_name} {user.last_name}!</h2>
        <p>This is your vet clinic dashboard.</p>
        <p>Email: {user.email}</p>
        <p>Phone: {user.phone}</p>
        <div className="dashboard-section">
          <h3>Add Pet</h3>
          <form onSubmit={handleAddPet} className="pet-form">
            <input name="name" value={petForm.name} onChange={handlePetChange} placeholder="Name" required />
            <input name="species" value={petForm.species} onChange={handlePetChange} placeholder="Species" required />
            <input name="breed" value={petForm.breed} onChange={handlePetChange} placeholder="Breed" required />
            <input name="birth_date" value={petForm.birth_date} onChange={handlePetChange} placeholder="Birth Date (YYYY-MM-DD)" required />
            <button type="submit">Add Pet</button>
          </form>
          <h3>Your Pets</h3>
          <ul>
            {pets.map(p => (
              <li key={p.pet_id}>
                {p.name} ({p.species}, {p.breed}, {p.birth_date})
              </li>
            ))}
          </ul>
        </div>
        <div className="dashboard-section">
          <h3>Add Visit</h3>
          <form onSubmit={handleAddVisit} className="visit-form">
            <select name="pet_id" value={visitForm.pet_id} onChange={handleVisitChange} required>
              <option value="">Select Pet</option>
              {pets.map(p => (
                <option key={p.pet_id} value={p.pet_id}>
                  {p.name} ({p.species})
                </option>
              ))}
            </select>
            <select name="vet_id" value={visitForm.vet_id} onChange={handleVisitChange} required>
              <option value="">Select Vet</option>
              {vets.map(v => (
                <option key={v.vet_id} value={v.vet_id}>
                  {v.first_name} {v.last_name}
                </option>
              ))}
            </select>
            <input name="date" value={visitForm.date} onChange={handleVisitChange} placeholder="Date (YYYY-MM-DD)" required />
            <input name="reason" value={visitForm.reason} onChange={handleVisitChange} placeholder="Reason" required />
            {/* Hide or lock the paid field so user cannot set it manually */}
            <input name="paid" type="hidden" value={visitForm.paid} readOnly />
            <button type="submit">Add Visit</button>
          </form>
          {message && <p>{message}</p>}
          <h3>Visits</h3>
          <ul>
            {visits.map(v => (
              <li key={v.visit_id}>
                Pet: {v.pet_id}, Vet: {v.vet_id}, Date: {v.date}, Reason: {v.reason}, Paid: {v.paid}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );

}

export default DesktopView;

