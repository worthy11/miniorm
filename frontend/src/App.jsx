import React, { useState, useEffect } from "react";
import AdminView from "./admin_view";
import DesktopView from "./desktop_view";

import VetDashboard from "./components/VetDashboard";
import OwnerSelector from "./components/OwnerSelector";
import VetSelector from "./components/VetSelector";

function App() {
  const [role, setRole] = useState(null); // 'admin', 'vet', 'owner'
  const [admin, setAdmin] = useState(false);
  const [vet, setVet] = useState(null);
  const [owner, setOwner] = useState(null);

  // Main landing page
  if (!role) {
    return (
      <div className="landing-page">
        <h1>Vet Clinic System</h1>
        <div>
          <button onClick={() => setRole('admin')}>Admin</button>
          <button onClick={() => setRole('vet')}>Vet</button>
          <button onClick={() => setRole('owner')}>Owner</button>
        </div>
      </div>
    );
  }

  // Admin dashboard
  if (role === 'admin') {
    return <div><button onClick={() => setRole(null)} className="btn-back" title="Back">←</button><AdminView /></div>;
  }

  // Vet dashboard with vet selection
  if (role === 'vet') {
    if (!vet) {
      return <VetSelector onSelect={setVet} onBack={() => setRole(null)} />;
    }
    return <VetDashboard vet={vet} onBack={() => setVet(null)} />;
  }

  // Owner dashboard with owner selection
  if (role === 'owner') {
    if (!owner) {
      return <OwnerSelector onSelect={setOwner} onBack={() => setRole(null)} />;
    }
    return <div><button onClick={() => setOwner(null)} className="btn-back" title="Back">←</button><DesktopView user={owner} /></div>;
  }
}

export default App;

