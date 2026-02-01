import React, { useEffect, useState } from "react";

export default function OwnerSelector({ onSelect, onBack }) {
  const [owners, setOwners] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/owners")
      .then(res => res.json())
      .then(data => {
        setOwners(data);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="owner-selector">
        <div className="loading-screen" role="status" aria-live="polite">
          <div className="spinner" aria-hidden="true" />
          <div>Loading owners...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="owner-selector">
      <button onClick={onBack} className="btn-back" title="Back">←</button>
      <h2>Select Owner</h2>
      <select
        onChange={e => {
          const owner = owners.find(o => o.owner_id === parseInt(e.target.value));
          if (owner) onSelect(owner);
        }}
        defaultValue=""
      >
        <option value="">-- Select Owner --</option>
        {owners.map(o => (
          <option key={o.owner_id} value={o.owner_id}>
            {o.first_name} {o.last_name} ({o.email})
          </option>
        ))}
      </select>
    </div>
  );
}
