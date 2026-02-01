import React from "react";

export default function VetDashboard({ vet, onBack }) {
  return (
    <div className="vet-dashboard">
      <div>
        <button onClick={onBack} className="btn-back" title="Back">←</button>
        <span>
          Logged in as: <b>{vet.first_name} {vet.last_name}</b>
        </span>
      </div>
      <h2>Vet Dashboard</h2>
      <p>Welcome, Dr. {vet.first_name} {vet.last_name}! (Functionality coming soon)</p>
    </div>
  );
}
