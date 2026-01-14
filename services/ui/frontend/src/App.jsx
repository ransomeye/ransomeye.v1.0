// RansomEye v1.0 SOC UI (Phase 8 - Read-Only)
// AUTHORITATIVE: Minimal read-only frontend for SOC UI
// React - aligns with Phase 8 requirements

import { useState, useEffect } from 'react';

// Phase 8 requirement: UI is read-only (no edits, no actions, no buttons that execute)

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

function App() {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [incidentDetail, setIncidentDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  // Phase 8 requirement: Read-only data fetching (no writes, no actions)
  useEffect(() => {
    fetchIncidents();
  }, []);

  useEffect(() => {
    if (selectedIncident) {
      fetchIncidentDetail(selectedIncident);
    }
  }, [selectedIncident]);

  const fetchIncidents = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents`);
      const data = await response.json();
      setIncidents(data.incidents || []);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching incidents:', error);
      setLoading(false);
    }
  };

  const fetchIncidentDetail = async (incidentId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents/${incidentId}`);
      const data = await response.json();
      setIncidentDetail(data);
    } catch (error) {
      console.error('Error fetching incident detail:', error);
    }
  };

  // Phase 8 requirement: Read-only display (no edits, no actions)
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>RansomEye SOC UI (Read-Only)</h1>
      <p style={{ color: '#666' }}>Phase 8 - Observational Only. No edits, no actions.</p>
      
      {loading ? (
        <p>Loading incidents...</p>
      ) : (
        <div style={{ display: 'flex', gap: '20px' }}>
          {/* Incident List */}
          <div style={{ flex: '1', border: '1px solid #ccc', padding: '10px', borderRadius: '4px' }}>
            <h2>Active Incidents</h2>
            {incidents.length === 0 ? (
              <p>No active incidents</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {incidents.map((incident) => (
                  <li
                    key={incident.incident_id}
                    onClick={() => setSelectedIncident(incident.incident_id)}
                    style={{
                      padding: '10px',
                      margin: '5px 0',
                      backgroundColor: selectedIncident === incident.incident_id ? '#e0e0e0' : '#f5f5f5',
                      cursor: 'pointer',
                      borderRadius: '4px',
                      borderLeft: incident.has_contradiction ? '4px solid #ff6b6b' : '4px solid transparent'
                    }}
                  >
                    <strong>{incident.incident_id.substring(0, 8)}...</strong>
                    <br />
                    Machine: {incident.machine_id}
                    <br />
                    {/* PHASE 5: Separate confidence from certainty */}
                    <span>Stage: <strong>{incident.stage}</strong></span>
                    <br />
                    <span>Confidence: {incident.confidence}%</span>
                    {incident.certainty_state && (
                      <span style={{ marginLeft: '10px', color: incident.certainty_state === 'CONFIRMED' ? '#28a745' : '#ffc107' }}>
                        ({incident.certainty_state})
                      </span>
                    )}
                    <br />
                    Evidence: {incident.total_evidence_count}
                    {incident.has_contradiction && (
                      <span style={{ color: '#ff6b6b', marginLeft: '10px' }}>⚠️ Contradiction</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Incident Detail */}
          <div style={{ flex: '2', border: '1px solid #ccc', padding: '10px', borderRadius: '4px' }}>
            {selectedIncident ? (
              incidentDetail ? (
                <div>
                  <h2>Incident Detail</h2>
                  <p><strong>Incident ID:</strong> {incidentDetail.incident?.incident_id}</p>
                  <p><strong>Machine ID:</strong> {incidentDetail.incident?.machine_id}</p>
                  <p><strong>Stage:</strong> {incidentDetail.incident?.stage}</p>
                  <p><strong>Confidence:</strong> {incidentDetail.incident?.confidence}</p>
                  <p><strong>Created:</strong> {incidentDetail.incident?.created_at}</p>
                  
                  <h3>Timeline</h3>
                  {incidentDetail.timeline && incidentDetail.timeline.length > 0 ? (
                    <ul>
                      {incidentDetail.timeline.map((transition, idx) => (
                        <li key={idx}>
                          {transition.transitioned_at}: {transition.from_stage || 'INITIAL'} → {transition.to_stage}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No timeline data</p>
                  )}

                  <h3>Evidence Summary</h3>
                  {incidentDetail.evidence_summary ? (
                    <p>Evidence Count: {incidentDetail.evidence_summary.evidence_count}</p>
                  ) : (
                    <p>No evidence data</p>
                  )}

                  <h3>AI Insights</h3>
                  {incidentDetail.ai_insights ? (
                    <div>
                      <p>Cluster ID: {incidentDetail.ai_insights.cluster_id || 'N/A'}</p>
                      <p>Novelty Score: {incidentDetail.ai_insights.novelty_score || 'N/A'}</p>
                      {incidentDetail.ai_insights.shap_summary && (
                        <div>
                          <p>SHAP Summary:</p>
                          <pre style={{ backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
                            {JSON.stringify(incidentDetail.ai_insights.shap_summary, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p>No AI insights</p>
                  )}

                  <h3>Policy Recommendations</h3>
                  {incidentDetail.policy_recommendations && incidentDetail.policy_recommendations.length > 0 ? (
                    <div>
                      {incidentDetail.policy_recommendations.map((rec, idx) => (
                        <div key={idx} style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                          <p><strong>Recommended Action:</strong> {rec.recommended_action}</p>
                          <p><strong>Simulation Mode:</strong> {rec.simulation_mode ? 'Yes' : 'No'}</p>
                          <p><strong>Enforcement Disabled:</strong> {rec.enforcement_disabled ? 'Yes' : 'No'}</p>
                          <p><strong>Reason:</strong> {rec.reason}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p>No policy recommendations</p>
                  )}

                  {/* Phase 8 requirement: NO buttons that execute actions */}
                  {/* NO "acknowledge", "resolve", or "close" buttons */}
                  {/* NO edit forms */}
                  {/* NO action triggers */}
                </div>
              ) : (
                <p>Loading incident detail...</p>
              )
            ) : (
              <p>Select an incident to view details</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
