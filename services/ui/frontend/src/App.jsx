import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

function App() {
  const [accessToken, setAccessToken] = useState(null);
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState('');
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });

  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [incidentDetail, setIncidentDetail] = useState(null);
  const [loading, setLoading] = useState(false);

  const hasPermission = useCallback(
    (permission) => permissions.includes(permission),
    [permissions]
  );

  const refreshSession = useCallback(async () => {
    setAuthLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include'
      });
      if (!response.ok) {
        setAccessToken(null);
        setUser(null);
        setPermissions([]);
        return false;
      }
      const data = await response.json();
      setAccessToken(data.access_token);

      const meResponse = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` }
      });
      if (meResponse.ok) {
        const meData = await meResponse.json();
        setUser(meData.user || null);
      }

      const permResponse = await fetch(`${API_BASE_URL}/auth/permissions`, {
        headers: { Authorization: `Bearer ${data.access_token}` }
      });
      if (permResponse.ok) {
        const permData = await permResponse.json();
        setPermissions(permData.permissions || []);
      }

      return true;
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const apiFetch = useCallback(
    async (path, options = {}, retry = true) => {
      if (!accessToken) {
        throw new Error('Missing access token');
      }
      const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: 'include',
        headers: {
          ...(options.headers || {}),
          Authorization: `Bearer ${accessToken}`
        }
      });
      if (response.status === 401 && retry) {
        const refreshed = await refreshSession();
        if (refreshed) {
          return apiFetch(path, options, false);
        }
      }
      return response;
    },
    [accessToken, refreshSession]
  );

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthError('');
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(loginForm)
      });
      if (!response.ok) {
        setAuthError('Invalid credentials');
        return;
      }
      const data = await response.json();
      setAccessToken(data.access_token);
      setUser(data.user || null);

      const permResponse = await fetch(`${API_BASE_URL}/auth/permissions`, {
        headers: { Authorization: `Bearer ${data.access_token}` }
      });
      if (permResponse.ok) {
        const permData = await permResponse.json();
        setPermissions(permData.permissions || []);
      }
    } catch (error) {
      setAuthError('Login failed');
    }
  };

  const handleLogout = async () => {
    if (accessToken) {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        credentials: 'include'
      });
    }
    setAccessToken(null);
    setUser(null);
    setPermissions([]);
    setIncidents([]);
    setSelectedIncident(null);
    setIncidentDetail(null);
  };

  const fetchIncidents = useCallback(async () => {
    if (!hasPermission('incident:view_all')) {
      return;
    }
    setLoading(true);
    try {
      const response = await apiFetch('/api/incidents');
      if (!response.ok) {
        setLoading(false);
        return;
      }
      const data = await response.json();
      setIncidents(data.incidents || []);
    } catch (error) {
      console.error('Error fetching incidents:', error);
    } finally {
      setLoading(false);
    }
  }, [apiFetch, hasPermission]);

  const fetchIncidentDetail = useCallback(
    async (incidentId) => {
      if (!hasPermission('incident:view')) {
        return;
      }
      try {
        const response = await apiFetch(`/api/incidents/${incidentId}`);
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        setIncidentDetail(data);
      } catch (error) {
        console.error('Error fetching incident detail:', error);
      }
    },
    [apiFetch, hasPermission]
  );

  useEffect(() => {
    if (accessToken && hasPermission('incident:view_all')) {
      fetchIncidents();
    }
  }, [accessToken, fetchIncidents, hasPermission]);

  useEffect(() => {
    if (selectedIncident) {
      fetchIncidentDetail(selectedIncident);
    }
  }, [selectedIncident, fetchIncidentDetail]);

  if (authLoading) {
    return (
      <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
        <p>Loading session...</p>
      </div>
    );
  }

  if (!accessToken) {
    return (
      <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '360px' }}>
        <h1>RansomEye SOC UI</h1>
        <p style={{ color: '#666' }}>Authenticated access required.</p>
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '10px' }}>
            <label>
              Username
              <input
                type="text"
                value={loginForm.username}
                onChange={(event) => setLoginForm({ ...loginForm, username: event.target.value })}
                style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                required
              />
            </label>
          </div>
          <div style={{ marginBottom: '10px' }}>
            <label>
              Password
              <input
                type="password"
                value={loginForm.password}
                onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
                style={{ width: '100%', padding: '8px', marginTop: '4px' }}
                required
              />
            </label>
          </div>
          {authError && <p style={{ color: '#c0392b' }}>{authError}</p>}
          <button type="submit" style={{ padding: '8px 12px' }}>Login</button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>RansomEye SOC UI</h1>
          <p style={{ color: '#666' }}>Authenticated, RBAC-enforced visibility.</p>
        </div>
        <div>
          <p style={{ margin: 0 }}>User: {user?.username || 'unknown'}</p>
          <p style={{ margin: 0 }}>Role: {user?.role || 'unknown'}</p>
          <button onClick={handleLogout} style={{ marginTop: '8px' }}>Logout</button>
        </div>
      </div>

      {!hasPermission('incident:view_all') ? (
        <p>You do not have permission to view incidents.</p>
      ) : loading ? (
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
            {!hasPermission('incident:view') ? (
              <p>You do not have permission to view incident details.</p>
            ) : selectedIncident ? (
              incidentDetail ? (
                <div>
                  <h2>Incident Detail</h2>
                  
                  {incidentDetail.evidence_quality && (
                    <div style={{
                      padding: '15px',
                      marginBottom: '20px',
                      borderRadius: '4px',
                      backgroundColor: (
                        incidentDetail.evidence_quality.has_contradiction ||
                        incidentDetail.evidence_quality.evidence_completeness === 'INCOMPLETE' ||
                        incidentDetail.evidence_quality.evidence_completeness === 'NO_EVIDENCE'
                      ) ? '#fff3cd' : '#d4edda',
                      border: '1px solid ' + (
                        incidentDetail.evidence_quality.has_contradiction ||
                        incidentDetail.evidence_quality.evidence_completeness === 'INCOMPLETE' ||
                        incidentDetail.evidence_quality.evidence_completeness === 'NO_EVIDENCE'
                      ) ? '#ffc107' : '#28a745'
                    }}>
                      <h3 style={{ marginTop: 0, color: '#856404' }}>⚠️ Evidence Quality Warning</h3>
                      {incidentDetail.evidence_quality.has_contradiction && (
                        <p style={{ color: '#856404', fontWeight: 'bold' }}>
                          ⚠️ CONTRADICTION DETECTED: Evidence contains contradictions. Confidence may be unreliable.
                        </p>
                      )}
                      {incidentDetail.evidence_quality.evidence_completeness === 'INCOMPLETE' && (
                        <p style={{ color: '#856404', fontWeight: 'bold' }}>
                          ⚠️ INCOMPLETE EVIDENCE: Evidence count ({incidentDetail.evidence_quality.evidence_count}) is below expected minimum for stage {incidentDetail.incident?.stage}.
                        </p>
                      )}
                      {incidentDetail.evidence_quality.evidence_completeness === 'NO_EVIDENCE' && (
                        <p style={{ color: '#856404', fontWeight: 'bold' }}>
                          ⚠️ NO EVIDENCE: No evidence available for this incident.
                        </p>
                      )}
                      {incidentDetail.ai_insights && !incidentDetail.evidence_quality.has_ai_provenance && (
                        <p style={{ color: '#856404' }}>
                          ⚠️ AI OUTPUT ADVISORY: AI insights are available but AI provenance (model version, training data hash) is missing. AI output is advisory only.
                        </p>
                      )}
                    </div>
                  )}
                  
                  <p><strong>Incident ID:</strong> {incidentDetail.incident?.incident_id}</p>
                  <p><strong>Machine ID:</strong> {incidentDetail.incident?.machine_id}</p>
                  
                  <div style={{ marginBottom: '10px' }}>
                    <p><strong>Stage:</strong> {incidentDetail.incident?.stage}</p>
                    <p><strong>Confidence Score:</strong> {incidentDetail.incident?.confidence}%</p>
                    {incidentDetail.incident?.certainty_state && (
                      <p>
                        <strong>Certainty State:</strong> 
                        <span style={{
                          color: incidentDetail.incident.certainty_state === 'CONFIRMED' ? '#28a745' : 
                                 incidentDetail.incident.certainty_state === 'PROBABLE' ? '#ffc107' : '#ff6b6b',
                          fontWeight: 'bold',
                          marginLeft: '10px'
                        }}>
                          {incidentDetail.incident.certainty_state}
                        </span>
                        {incidentDetail.incident.is_probabilistic && (
                          <span style={{ color: '#ffc107', marginLeft: '10px' }}>
                            (Probabilistic - Not Confirmed)
                          </span>
                        )}
                      </p>
                    )}
                  </div>
                  
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

                  <h3>Evidence Quality Indicators</h3>
                  {incidentDetail.evidence_quality ? (
                    <div style={{ padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px', marginBottom: '10px' }}>
                      <p><strong>Evidence Count:</strong> {incidentDetail.evidence_quality.evidence_count}</p>
                      <p>
                        <strong>Evidence Completeness:</strong> 
                        <span style={{
                          color: incidentDetail.evidence_quality.evidence_completeness === 'COMPLETE' ? '#28a745' : '#ffc107',
                          fontWeight: 'bold',
                          marginLeft: '10px'
                        }}>
                          {incidentDetail.evidence_quality.evidence_completeness}
                        </span>
                        {incidentDetail.evidence_quality.evidence_completeness !== 'COMPLETE' && (
                          <span style={{ color: '#ff6b6b', marginLeft: '10px' }}>⚠️</span>
                        )}
                      </p>
                      <p>
                        <strong>Determinism Status:</strong> 
                        <span style={{
                          color: incidentDetail.evidence_quality.determinism_status === 'DETERMINISTIC' ? '#28a745' : '#ffc107',
                          marginLeft: '10px'
                        }}>
                          {incidentDetail.evidence_quality.determinism_status}
                        </span>
                      </p>
                      <p>
                        <strong>Contradiction Presence:</strong> 
                        <span style={{
                          color: incidentDetail.evidence_quality.has_contradiction ? '#ff6b6b' : '#28a745',
                          fontWeight: 'bold',
                          marginLeft: '10px'
                        }}>
                          {incidentDetail.evidence_quality.has_contradiction ? 'YES' : 'NO'}
                        </span>
                        {incidentDetail.evidence_quality.has_contradiction && (
                          <span style={{ color: '#ff6b6b', marginLeft: '10px' }}>
                            ({incidentDetail.evidence_quality.contradiction_count} contradiction(s) detected)
                          </span>
                        )}
                      </p>
                      <p>
                        <strong>AI Provenance Available:</strong> 
                        <span style={{
                          color: incidentDetail.evidence_quality.has_ai_provenance ? '#28a745' : '#ffc107',
                          marginLeft: '10px'
                        }}>
                          {incidentDetail.evidence_quality.has_ai_provenance ? 'YES' : 'NO'}
                        </span>
                        {!incidentDetail.evidence_quality.has_ai_provenance && (
                          <span style={{ color: '#ffc107', marginLeft: '10px' }}>
                            (AI output is advisory only)
                          </span>
                        )}
                      </p>
                      <p>
                        <strong>SHAP Explanation Available:</strong> 
                        <span style={{
                          color: incidentDetail.evidence_quality.has_shap_explanation ? '#28a745' : '#ffc107',
                          marginLeft: '10px'
                        }}>
                          {incidentDetail.evidence_quality.has_shap_explanation ? 'YES' : 'NO'}
                        </span>
                      </p>
                    </div>
                  ) : (
                    <p>No evidence quality data</p>
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
                      {incidentDetail.evidence_quality && !incidentDetail.evidence_quality.has_ai_provenance && (
                        <div style={{
                          padding: '10px',
                          marginBottom: '10px',
                          backgroundColor: '#fff3cd',
                          border: '1px solid #ffc107',
                          borderRadius: '4px'
                        }}>
                          <p style={{ color: '#856404', fontWeight: 'bold', margin: 0 }}>
                            ⚠️ ADVISORY ONLY: AI output is available but AI provenance (model version, training data hash) is missing. 
                            This output cannot be verified or replayed. Use with caution.
                          </p>
                        </div>
                      )}
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
                  
                  {incidentDetail.ai_provenance && incidentDetail.ai_provenance.length > 0 && (
                    <div style={{ marginTop: '20px' }}>
                      <h3>AI Provenance</h3>
                      {incidentDetail.ai_provenance.map((prov, idx) => (
                        <div key={idx} style={{ padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px', marginBottom: '10px' }}>
                          <p><strong>Model Type:</strong> {prov.model_type || 'N/A'}</p>
                          <p><strong>Model Version:</strong> {prov.model_version_string || 'N/A'}</p>
                          <p><strong>Model Hash:</strong> {prov.model_hash_sha256 ? prov.model_hash_sha256.substring(0, 16) + '...' : 'N/A'}</p>
                          <p><strong>Training Data Hash:</strong> {prov.training_data_hash_sha256 ? prov.training_data_hash_sha256.substring(0, 16) + '...' : 'N/A'}</p>
                          <p><strong>Model Storage Path:</strong> {prov.model_storage_path || 'N/A'}</p>
                          <p><strong>SHAP Explanation Available:</strong> {prov.has_shap_explanation ? 'YES' : 'NO'}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <h3>Policy Recommendations</h3>
                  {incidentDetail.policy_recommendations && incidentDetail.policy_recommendations.length > 0 ? (
                    <div>
                      {incidentDetail.policy_recommendations.map((rec, idx) => (
                        <div key={idx} style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                          {(incidentDetail.evidence_quality?.has_contradiction || 
                            incidentDetail.evidence_quality?.evidence_completeness === 'INCOMPLETE' ||
                            incidentDetail.evidence_quality?.evidence_completeness === 'NO_EVIDENCE' ||
                            (incidentDetail.evidence_quality && !incidentDetail.evidence_quality.has_ai_provenance && incidentDetail.ai_insights)) && (
                            <div style={{
                              padding: '10px',
                              marginBottom: '10px',
                              backgroundColor: '#fff3cd',
                              border: '1px solid #ffc107',
                              borderRadius: '4px'
                            }}>
                              <p style={{ color: '#856404', fontWeight: 'bold', margin: 0 }}>
                                ⚠️ WARNING: Action recommended on ambiguous intelligence. 
                                {incidentDetail.evidence_quality?.has_contradiction && ' Contradictions detected. '}
                                {incidentDetail.evidence_quality?.evidence_completeness === 'INCOMPLETE' && ' Evidence is incomplete. '}
                                {incidentDetail.evidence_quality?.evidence_completeness === 'NO_EVIDENCE' && ' No evidence available. '}
                                {incidentDetail.evidence_quality && !incidentDetail.evidence_quality.has_ai_provenance && incidentDetail.ai_insights && ' AI output is advisory only. '}
                                Explicit acknowledgment required before action.
                              </p>
                            </div>
                          )}
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
