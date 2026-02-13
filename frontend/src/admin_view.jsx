import { useEffect, useState } from "react";
import "./styles/desktop.css";
import "./styles/admin.css";

const TABS = ["owners", "vets", "pets", "visits", "procedures"];

export default function AdminView() {
  const [activeTab, setActiveTab] = useState("owners");
  const [owners, setOwners] = useState([]);
  const [vets, setVets] = useState([]);
  const [pets, setPets] = useState([]);
  const [visits, setVisits] = useState([]);
  const [procedures, setProcedures] = useState([]);
  const [filters, setFilters] = useState({});
  const [message, setMessage] = useState("");
  const [editModal, setEditModal] = useState(null);
  const [form, setForm] = useState({});
  const [sort, setSort] = useState({ column: "", direction: "ASC" });

  useEffect(() => {
    fetchData();
  }, [activeTab, filters]);

  async function fetchData() {
    const setParams = (keys) => {
      const q = new URLSearchParams();
      keys.forEach((k) => {
        if (filters[k] != null && filters[k] !== "") q.set(k, filters[k]);
      });
      if (sort.column) {
      q.set("order_by", sort.column);
      q.set("order_dir", sort.direction);
    }
      return q.toString();
    };
    if (activeTab === "owners") {
      const res = await fetch(
        `/api/owners?${setParams(["first_name", "last_name", "email", "phone"])}`,
      );
      setOwners(await res.json());
    } else if (activeTab === "vets") {
      const res = await fetch(
        `/api/vets?${setParams(["first_name", "last_name", "email", "phone", "license"])}`,
      );
      setVets(await res.json());
    } else if (activeTab === "pets") {
      const res = await fetch(
        `/api/pets?${setParams(["owner_id", "name", "species", "breed", "birth_date"])}`,
      );
      setPets(await res.json());
    } else if (activeTab === "visits") {
      const res = await fetch(
        `/api/visits?${setParams(["owner_id", "vet_id", "pet_id", "date", "reason", "paid"])}`,
      );
      setVisits(await res.json());
    } else if (activeTab === "procedures") {
      const res = await fetch(
        `/api/procedures?${setParams(["name", "description", "price_min", "price_max"])}`,
      );
      setProcedures(await res.json());
    }
  }

  // Load owners/vets for dropdowns
  const [ownersList, setOwnersList] = useState([]);
  const [vetsList, setVetsList] = useState([]);
  const [petsList, setPetsList] = useState([]);

  useEffect(() => {
    fetch("/api/owners")
      .then((r) => r.json())
      .then(setOwnersList);
    fetch("/api/vets")
      .then((r) => r.json())
      .then(setVetsList);
    fetch("/api/pets")
      .then((r) => r.json())
      .then(setPetsList);
  }, [activeTab]);

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  function handleFilterChange(e) {
    setFilters((f) => ({ ...f, [e.target.name]: e.target.value || undefined }));
  }

  function showMessage(msg) {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  }

  async function handleAdd(e) {
    e.preventDefault();
    setMessage("");
    try {
      let res;
      if (activeTab === "owners") {
        res = await fetch("/api/owners", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else if (activeTab === "vets") {
        res = await fetch("/api/vets", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else if (activeTab === "pets") {
        res = await fetch("/api/pets", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            owner_id: parseInt(form.owner_id, 10),
          }),
        });
      } else if (activeTab === "visits") {
        res = await fetch("/api/visits", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pet_id: parseInt(form.pet_id, 10),
            vet_id: parseInt(form.vet_id, 10),
            date: form.date,
            reason: form.reason,
            paid: parseInt(form.paid || 0, 10),
          }),
        });
      } else if (activeTab === "procedures") {
        res = await fetch("/api/procedures", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...form, price: parseFloat(form.price || 0) }),
        });
      }
      const data = await res.json();
      if (res.ok) {
        showMessage("Added successfully!");
        setForm({});
        fetchData();
      } else {
        showMessage(data.detail || data.message || "Error");
      }
    } catch (err) {
      showMessage("Error: " + err.message);
    }
  }

  async function handleUpdate(e) {
    e.preventDefault();
    if (!editModal) return;
    setMessage("");
    try {
      const { entity, idKey, id } = editModal;
      let res;
      if (entity === "owners") {
        res = await fetch(`/api/owners/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else if (entity === "vets") {
        res = await fetch(`/api/vets/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
      } else if (entity === "pets") {
        res = await fetch(`/api/pets/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            owner_id: form.owner_id ? parseInt(form.owner_id, 10) : undefined,
          }),
        });
      } else if (entity === "visits") {
        res = await fetch(`/api/visits/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pet_id: form.pet_id ? parseInt(form.pet_id, 10) : undefined,
            vet_id: form.vet_id ? parseInt(form.vet_id, 10) : undefined,
            date: form.date,
            reason: form.reason,
            paid: form.paid !== "" ? parseInt(form.paid, 10) : undefined,
          }),
        });
      } else if (entity === "procedures") {
        res = await fetch(`/api/procedures/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            price: form.price !== "" ? parseFloat(form.price) : undefined,
          }),
        });
      }
      const data = await res.json();
      if (res.ok) {
        showMessage("Updated successfully!");
        setEditModal(null);
        fetchData();
      } else {
        showMessage(data.detail || data.message || "Error");
      }
    } catch (err) {
      showMessage("Error: " + err.message);
    }
  }

  async function handleDelete(entity, id) {
    if (!confirm("Delete this record?")) return;
    setMessage("");
    try {
      const res = await fetch(`/api/${entity}/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) {
        showMessage("Deleted successfully!");
        fetchData();
      } else {
        showMessage(data.detail || data.message || "Error");
      }
    } catch (err) {
      showMessage("Error: " + err.message);
    }
  }

  function openEdit(entity, row) {
    if (entity === "owners") {
      setForm({
        first_name: row.first_name,
        last_name: row.last_name,
        email: row.email,
        phone: row.phone,
        password: "",
      });
      setEditModal({ entity, idKey: "owner_id", id: row.owner_id });
    } else if (entity === "vets") {
      setForm({
        first_name: row.first_name,
        last_name: row.last_name,
        email: row.email,
        phone: row.phone,
        license: row.license,
      });
      setEditModal({ entity, idKey: "vet_id", id: row.vet_id });
    } else if (entity === "pets") {
      setForm({
        owner_id: row.owner_id || "",
        name: row.name,
        species: row.species,
        breed: row.breed,
        birth_date: row.birth_date,
      });
      setEditModal({ entity, idKey: "pet_id", id: row.pet_id });
    } else if (entity === "visits") {
      setForm({
        pet_id: row.pet_id,
        vet_id: row.vet_id,
        date: row.date,
        reason: row.reason,
        paid: row.paid,
      });
      setEditModal({ entity, idKey: "visit_id", id: row.visit_id });
    } else if (entity === "procedures") {
      setForm({
        name: row.name,
        description: row.description,
        price: row.price,
      });
      setEditModal({ entity, idKey: "procedure_id", id: row.procedure_id });
    }
  }

  return (
    <div className="desktop-container">
      <div className="desktop-card">
        <h2>Admin Dashboard</h2>
        <div className="admin-tabs">
          {TABS.map((t) => (
            <button
              key={t}
              className={`admin-tab ${activeTab === t ? "active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {message && (
          <p className="dashboard-section" style={{ marginTop: 0 }}>
            {message}
          </p>
        )}

        {/* Owners */}
        {activeTab === "owners" && (
          <div className="dashboard-section">
            <h3>Owners</h3>
            <div className="admin-filters">
              <input
                name="first_name"
                placeholder="First name"
                value={filters.first_name || ""}
                onChange={handleFilterChange}
              />
              <input
                name="last_name"
                placeholder="Last name"
                value={filters.last_name || ""}
                onChange={handleFilterChange}
              />
              <input
                name="email"
                placeholder="Email"
                value={filters.email || ""}
                onChange={handleFilterChange}
              />
              <input
                name="phone"
                placeholder="Phone"
                value={filters.phone || ""}
                onChange={handleFilterChange}
              />
              <select name="order_by" value={sort.column} onChange={(e) => setSort(s => ({...s, column: e.target.value}))}>
                <option value="">Sort by (None)</option>
                <option value="last_name">Last Name</option>
                <option value="first_name">First Name</option>
                <option value="email">Email</option>
                <option value="person_id">ID</option>
              </select>

              <select 
                name="order_dir" 
                value={sort.direction} 
                onChange={(e) => setSort(s => ({...s, direction: e.target.value}))}
              >
                <option value="ASC">Ascending</option>
                <option value="DESC">Descending</option>
              </select>

              <button onClick={fetchData}>Apply & Sort</button>
            </div>
            <form onSubmit={handleAdd} className="pet-form">
              <input
                name="first_name"
                value={form.first_name || ""}
                onChange={handleChange}
                placeholder="First Name"
                required
              />
              <input
                name="last_name"
                value={form.last_name || ""}
                onChange={handleChange}
                placeholder="Last Name"
                required
              />
              <input
                name="email"
                value={form.email || ""}
                onChange={handleChange}
                placeholder="Email"
                required
              />
              <input
                name="phone"
                value={form.phone || ""}
                onChange={handleChange}
                placeholder="Phone"
                required
              />
              <input
                name="password"
                type="password"
                value={form.password || ""}
                onChange={handleChange}
                placeholder="Password"
                required
              />
              <button type="submit">Add Owner</button>
            </form>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {owners.map((o) => (
                    <tr key={o.owner_id}>
                      <td>{o.owner_id}</td>
                      <td>
                        {o.first_name} {o.last_name}
                      </td>
                      <td>{o.email}</td>
                      <td>{o.phone}</td>
                      <td>
                        <button
                          type="button"
                          className="btn-edit"
                          onClick={() => openEdit("owners", o)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn-delete"
                          onClick={() => handleDelete("owners", o.owner_id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Vets */}
        {activeTab === "vets" && (
          <div className="dashboard-section">
            <h3>Vets</h3>
            <div className="admin-filters">
              <input
                name="first_name"
                placeholder="First name"
                value={filters.first_name || ""}
                onChange={handleFilterChange}
              />
              <input
                name="last_name"
                placeholder="Last name"
                value={filters.last_name || ""}
                onChange={handleFilterChange}
              />
              <input
                name="email"
                placeholder="Email"
                value={filters.email || ""}
                onChange={handleFilterChange}
              />
              <input
                name="phone"
                placeholder="Phone"
                value={filters.phone || ""}
                onChange={handleFilterChange}
              />
              <input
                name="license"
                placeholder="License"
                value={filters.license || ""}
                onChange={handleFilterChange}
              />
              <button onClick={fetchData}>Apply</button>
            </div>
            <form onSubmit={handleAdd} className="pet-form">
              <input
                name="first_name"
                value={form.first_name || ""}
                onChange={handleChange}
                placeholder="First Name"
                required
              />
              <input
                name="last_name"
                value={form.last_name || ""}
                onChange={handleChange}
                placeholder="Last Name"
                required
              />
              <input
                name="email"
                value={form.email || ""}
                onChange={handleChange}
                placeholder="Email"
                required
              />
              <input
                name="phone"
                value={form.phone || ""}
                onChange={handleChange}
                placeholder="Phone"
                required
              />
              <input
                name="license"
                value={form.license || ""}
                onChange={handleChange}
                placeholder="License"
                required
              />
              <button type="submit">Add Vet</button>
            </form>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>License</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {vets.map((v) => (
                    <tr key={v.vet_id}>
                      <td>{v.vet_id}</td>
                      <td>
                        {v.first_name} {v.last_name}
                      </td>
                      <td>{v.email}</td>
                      <td>{v.phone}</td>
                      <td>{v.license}</td>
                      <td>
                        <button
                          type="button"
                          className="btn-edit"
                          onClick={() => openEdit("vets", v)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn-delete"
                          onClick={() => handleDelete("vets", v.vet_id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pets */}
        {activeTab === "pets" && (
          <div className="dashboard-section">
            <h3>Pets</h3>
            <div className="admin-filters">
              <select
                name="owner_id"
                value={filters.owner_id || ""}
                onChange={handleFilterChange}
              >
                <option value="">All owners</option>
                {ownersList.map((o) => (
                  <option key={o.owner_id} value={o.owner_id}>
                    {o.first_name} {o.last_name}
                  </option>
                ))}
              </select>
              <input
                name="name"
                placeholder="Name"
                value={filters.name || ""}
                onChange={handleFilterChange}
              />
              <input
                name="species"
                placeholder="Species"
                value={filters.species || ""}
                onChange={handleFilterChange}
              />
              <input
                name="breed"
                placeholder="Breed"
                value={filters.breed || ""}
                onChange={handleFilterChange}
              />
              <input
                name="birth_date"
                placeholder="Birth date"
                value={filters.birth_date || ""}
                onChange={handleFilterChange}
              />
              <button onClick={fetchData}>Apply</button>
            </div>
            <form onSubmit={handleAdd} className="pet-form">
              <select
                name="owner_id"
                value={form.owner_id || ""}
                onChange={handleChange}
                required
              >
                <option value="">Select owner</option>
                {ownersList.map((o) => (
                  <option key={o.owner_id} value={o.owner_id}>
                    {o.first_name} {o.last_name}
                  </option>
                ))}
              </select>
              <input
                name="name"
                value={form.name || ""}
                onChange={handleChange}
                placeholder="Name"
                required
              />
              <input
                name="species"
                value={form.species || ""}
                onChange={handleChange}
                placeholder="Species"
                required
              />
              <input
                name="breed"
                value={form.breed || ""}
                onChange={handleChange}
                placeholder="Breed"
                required
              />
              <input
                name="birth_date"
                value={form.birth_date || ""}
                onChange={handleChange}
                placeholder="Birth date (YYYY-MM-DD)"
                required
              />
              <button type="submit">Add Pet</button>
            </form>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Owner</th>
                    <th>Name</th>
                    <th>Species</th>
                    <th>Breed</th>
                    <th>Birth</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {pets.map((p) => (
                    <tr key={p.pet_id}>
                      <td>{p.pet_id}</td>
                      <td>
                        {ownersList.find((o) => o.owner_id === p.owner)
                          ?.first_name || "-"}{" "}
                        {ownersList.find((o) => o.owner_id === p.owner)
                          ?.last_name || ""}
                      </td>
                      <td>{p.name}</td>
                      <td>{p.species}</td>
                      <td>{p.breed}</td>
                      <td>{p.birth_date}</td>
                      <td>
                        <button
                          type="button"
                          className="btn-edit"
                          onClick={() =>
                            openEdit("pets", { ...p, owner_id: p.owner })
                          }
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn-delete"
                          onClick={() => handleDelete("pets", p.pet_id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Visits */}
        {activeTab === "visits" && (
          <div className="dashboard-section">
            <h3>Visits</h3>
            <div className="admin-filters">
              <select
                name="owner_id"
                value={filters.owner_id || ""}
                onChange={handleFilterChange}
              >
                <option value="">All owners</option>
                {ownersList.map((o) => (
                  <option key={o.owner_id} value={o.owner_id}>
                    {o.first_name} {o.last_name}
                  </option>
                ))}
              </select>
              <select
                name="vet_id"
                value={filters.vet_id || ""}
                onChange={handleFilterChange}
              >
                <option value="">All vets</option>
                {vetsList.map((v) => (
                  <option key={v.vet_id} value={v.vet_id}>
                    {v.first_name} {v.last_name}
                  </option>
                ))}
              </select>
              <select
                name="pet_id"
                value={filters.pet_id || ""}
                onChange={handleFilterChange}
              >
                <option value="">All pets</option>
                {petsList.map((p) => (
                  <option key={p.pet_id} value={p.pet_id}>
                    {p.name} ({p.species})
                  </option>
                ))}
              </select>
              <input
                name="date"
                placeholder="Date"
                value={filters.date || ""}
                onChange={handleFilterChange}
              />
              <input
                name="reason"
                placeholder="Reason"
                value={filters.reason || ""}
                onChange={handleFilterChange}
              />
              <select
                name="paid"
                value={filters.paid ?? ""}
                onChange={handleFilterChange}
              >
                <option value="">Paid (any)</option>
                <option value="0">No</option>
                <option value="1">Yes</option>
              </select>
              <button onClick={fetchData}>Apply</button>
            </div>
            <form onSubmit={handleAdd} className="pet-form">
              <select
                name="pet_id"
                value={form.pet_id || ""}
                onChange={handleChange}
                required
              >
                <option value="">Select pet</option>
                {petsList.map((p) => (
                  <option key={p.pet_id} value={p.pet_id}>
                    {p.name} ({p.species})
                  </option>
                ))}
              </select>
              <select
                name="vet_id"
                value={form.vet_id || ""}
                onChange={handleChange}
                required
              >
                <option value="">Select vet</option>
                {vetsList.map((v) => (
                  <option key={v.vet_id} value={v.vet_id}>
                    {v.first_name} {v.last_name}
                  </option>
                ))}
              </select>
              <input
                name="date"
                value={form.date || ""}
                onChange={handleChange}
                placeholder="Date (YYYY-MM-DD)"
                required
              />
              <input
                name="reason"
                value={form.reason || ""}
                onChange={handleChange}
                placeholder="Reason"
                required
              />
              <input
                name="paid"
                type="number"
                min="0"
                max="1"
                value={form.paid ?? 0}
                onChange={handleChange}
                placeholder="Paid"
              />
              <button type="submit">Add Visit</button>
            </form>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Pet</th>
                    <th>Vet</th>
                    <th>Date</th>
                    <th>Reason</th>
                    <th>Paid</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {visits.map((v) => (
                    <tr key={v.visit_id}>
                      <td>{v.visit_id}</td>
                      <td>
                        {petsList.find((p) => p.pet_id === v.pet_id)?.name ||
                          v.pet_id}
                      </td>
                      <td>
                        {vetsList.find((x) => x.vet_id === v.vet_id)
                          ?.first_name || ""}{" "}
                        {vetsList.find((x) => x.vet_id === v.vet_id)
                          ?.last_name || v.vet_id}
                      </td>
                      <td>{v.date}</td>
                      <td>{v.reason}</td>
                      <td>{v.paid ? "Yes" : "No"}</td>
                      <td>
                        <button
                          type="button"
                          className="btn-edit"
                          onClick={() => openEdit("visits", v)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn-delete"
                          onClick={() => handleDelete("visits", v.visit_id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Procedures */}
        {activeTab === "procedures" && (
          <div className="dashboard-section">
            <h3>Procedures</h3>
            <div className="admin-filters">
              <input
                name="name"
                placeholder="Name"
                value={filters.name || ""}
                onChange={handleFilterChange}
              />
              <input
                name="description"
                placeholder="Description"
                value={filters.description || ""}
                onChange={handleFilterChange}
              />
              <input
                name="price_min"
                type="number"
                step="0.01"
                placeholder="Price min"
                value={filters.price_min ?? ""}
                onChange={handleFilterChange}
              />
              <input
                name="price_max"
                type="number"
                step="0.01"
                placeholder="Price max"
                value={filters.price_max ?? ""}
                onChange={handleFilterChange}
              />
              <button onClick={fetchData}>Apply</button>
            </div>
            <form onSubmit={handleAdd} className="pet-form">
              <input
                name="name"
                value={form.name || ""}
                onChange={handleChange}
                placeholder="Name"
                required
              />
              <input
                name="description"
                value={form.description || ""}
                onChange={handleChange}
                placeholder="Description"
              />
              <input
                name="price"
                type="number"
                step="0.01"
                value={form.price ?? ""}
                onChange={handleChange}
                placeholder="Price"
              />
              <button type="submit">Add Procedure</button>
            </form>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Price</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {procedures.map((p) => (
                    <tr key={p.procedure_id}>
                      <td>{p.procedure_id}</td>
                      <td>{p.name}</td>
                      <td>{p.description || "-"}</td>
                      <td>{p.price}</td>
                      <td>
                        <button
                          type="button"
                          className="btn-edit"
                          onClick={() => openEdit("procedures", p)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn-delete"
                          onClick={() =>
                            handleDelete("procedures", p.procedure_id)
                          }
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editModal && (
        <div className="admin-modal-overlay" onClick={() => setEditModal(null)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Edit {editModal.entity.slice(0, -1)}</h3>
            <form
              onSubmit={handleUpdate}
              className="pet-form"
              style={{ flexDirection: "column" }}
            >
              {editModal.entity === "owners" && (
                <>
                  <input
                    name="first_name"
                    value={form.first_name || ""}
                    onChange={handleChange}
                    placeholder="First Name"
                    required
                  />
                  <input
                    name="last_name"
                    value={form.last_name || ""}
                    onChange={handleChange}
                    placeholder="Last Name"
                    required
                  />
                  <input
                    name="email"
                    value={form.email || ""}
                    onChange={handleChange}
                    placeholder="Email"
                    required
                  />
                  <input
                    name="phone"
                    value={form.phone || ""}
                    onChange={handleChange}
                    placeholder="Phone"
                    required
                  />
                  <input
                    name="password"
                    type="password"
                    value={form.password || ""}
                    onChange={handleChange}
                    placeholder="Password (leave blank to keep)"
                  />
                </>
              )}
              {editModal.entity === "vets" && (
                <>
                  <input
                    name="first_name"
                    value={form.first_name || ""}
                    onChange={handleChange}
                    placeholder="First Name"
                    required
                  />
                  <input
                    name="last_name"
                    value={form.last_name || ""}
                    onChange={handleChange}
                    placeholder="Last Name"
                    required
                  />
                  <input
                    name="email"
                    value={form.email || ""}
                    onChange={handleChange}
                    placeholder="Email"
                    required
                  />
                  <input
                    name="phone"
                    value={form.phone || ""}
                    onChange={handleChange}
                    placeholder="Phone"
                    required
                  />
                  <input
                    name="license"
                    value={form.license || ""}
                    onChange={handleChange}
                    placeholder="License"
                    required
                  />
                </>
              )}
              {editModal.entity === "pets" && (
                <>
                  <select
                    name="owner_id"
                    value={form.owner_id || ""}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select owner</option>
                    {ownersList.map((o) => (
                      <option key={o.owner_id} value={o.owner_id}>
                        {o.first_name} {o.last_name}
                      </option>
                    ))}
                  </select>
                  <input
                    name="name"
                    value={form.name || ""}
                    onChange={handleChange}
                    placeholder="Name"
                    required
                  />
                  <input
                    name="species"
                    value={form.species || ""}
                    onChange={handleChange}
                    placeholder="Species"
                    required
                  />
                  <input
                    name="breed"
                    value={form.breed || ""}
                    onChange={handleChange}
                    placeholder="Breed"
                    required
                  />
                  <input
                    name="birth_date"
                    value={form.birth_date || ""}
                    onChange={handleChange}
                    placeholder="Birth date"
                    required
                  />
                </>
              )}
              {editModal.entity === "visits" && (
                <>
                  <select
                    name="pet_id"
                    value={form.pet_id || ""}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select pet</option>
                    {petsList.map((p) => (
                      <option key={p.pet_id} value={p.pet_id}>
                        {p.name} ({p.species})
                      </option>
                    ))}
                  </select>
                  <select
                    name="vet_id"
                    value={form.vet_id || ""}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select vet</option>
                    {vetsList.map((v) => (
                      <option key={v.vet_id} value={v.vet_id}>
                        {v.first_name} {v.last_name}
                      </option>
                    ))}
                  </select>
                  <input
                    name="date"
                    value={form.date || ""}
                    onChange={handleChange}
                    placeholder="Date (YYYY-MM-DD)"
                    required
                  />
                  <input
                    name="reason"
                    value={form.reason || ""}
                    onChange={handleChange}
                    placeholder="Reason"
                    required
                  />
                  <input
                    name="paid"
                    type="number"
                    value={form.paid ?? ""}
                    onChange={handleChange}
                    placeholder="Paid (0/1)"
                  />
                </>
              )}
              {editModal.entity === "procedures" && (
                <>
                  <input
                    name="name"
                    value={form.name || ""}
                    onChange={handleChange}
                    placeholder="Name"
                    required
                  />
                  <input
                    name="description"
                    value={form.description || ""}
                    onChange={handleChange}
                    placeholder="Description"
                  />
                  <input
                    name="price"
                    type="number"
                    step="0.01"
                    value={form.price ?? ""}
                    onChange={handleChange}
                    placeholder="Price"
                  />
                </>
              )}
              <div className="admin-modal-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setEditModal(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="primary">
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
