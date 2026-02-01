import React, { useEffect, useState } from "react";

export default function VetSelector({ onSelect, onBack }) {
  const [vets, setVets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/vets")
      .then(res => res.json())
      .then(data => {
        setVets(data);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="vet-selector">
        <div className="loading-screen" role="status" aria-live="polite">
          <div className="spinner" aria-hidden="true" />
          <div>Loading vets...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="vet-selector">
      <button onClick={onBack} className="btn-back" title="Back">←</button>
      <h2>Select Vet</h2>
      <select
        onChange={e => {
          const vet = vets.find(v => v.vet_id === parseInt(e.target.value));
          if (vet) onSelect(vet);
        }}
        defaultValue=""
      >
        <option value="">-- Select Vet --</option>
        {vets.map(v => (
          <option key={v.vet_id} value={v.vet_id}>
            {v.first_name} {v.last_name} ({v.email})
          </option>
        ))}
      </select>
    </div>
  );
}
