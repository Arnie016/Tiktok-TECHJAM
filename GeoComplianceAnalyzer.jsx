import React, { useState } from 'react';
import './GeoComplianceAnalyzer.css';

const GeoComplianceAnalyzer = ({ lambdaFunctionUrl }) => {
  const [formData, setFormData] = useState({
    featureName: '',
    featureDescription: '',
    lawContext: ''
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const presets = {
    gdpr: {
      name: "EU Cookie Consent Banner",
      description: "Display cookie consent banner for EU users accessing the website with options to accept or reject non-essential cookies for analytics and marketing purposes.",
      context: '[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}, {"law": "GDPR Article 6", "jurisdiction": "EU", "requirement": "Lawful basis for processing personal data"}]'
    },
    ccpa: {
      name: "California Do Not Sell Button",
      description: "Provides California residents with a prominent button to opt-out of the sale of their personal information as required by state privacy law.",
      context: '[{"law": "CCPA Section 1798.135", "jurisdiction": "US-CA", "requirement": "Right to opt-out of sale of personal information"}]'
    },
    kids: {
      name: "Age Verification System",
      description: "System to verify user age and obtain parental consent for users under 13 (US) or 16 (EU), with different consent mechanisms.",
      context: '[{"law": "COPPA", "jurisdiction": "US", "requirement": "Parental consent for children under 13"}, {"law": "GDPR Article 8", "jurisdiction": "EU", "requirement": "Parental consent for children under 16"}]'
    },
    simple: {
      name: "Dark Mode Theme Toggle",
      description: "Simple UI toggle button that allows users to switch between light and dark color themes for better visual comfort.",
      context: '[]'
    }
  };

  const loadPreset = (type) => {
    const preset = presets[type];
    setFormData({
      featureName: preset.name,
      featureDescription: preset.description,
      lawContext: preset.context
    });
    setError(null);
    setResults(null);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const analyzeCompliance = async (e) => {
    e.preventDefault();
    
    if (!lambdaFunctionUrl) {
      setError('Lambda Function URL is not configured');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const payload = {
        instruction: "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
        input: `Feature Name: ${formData.featureName}\nFeature Description: ${formData.featureDescription}\n\nLaw Context (structured JSON):\n${formData.lawContext}`
      };

      const response = await fetch(lambdaFunctionUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error?.message || 'Analysis failed');
      }

      setResults(result);

    } catch (error) {
      console.error('Error:', error);
      setError(`Analysis failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const ComplianceResults = ({ results }) => {
    const compliance = results.compliance;

    return (
      <div className="results">
        <div className={`compliance-badge ${compliance.need_geo_logic ? 'compliance-yes' : 'compliance-no'}`}>
          {compliance.need_geo_logic ? '⚠️ Geo-Compliance Required' : '✅ No Geo-Compliance Needed'}
        </div>

        {compliance.jurisdictions.length > 0 && (
          <div className="section">
            <h3>🌍 Affected Jurisdictions</h3>
            <div>
              {compliance.jurisdictions.map((jurisdiction, index) => (
                <span key={index} className="jurisdiction-tag">{jurisdiction}</span>
              ))}
            </div>
          </div>
        )}

        {compliance.legal_citations.length > 0 && (
          <div className="section">
            <h3>📚 Legal Citations</h3>
            {compliance.legal_citations.map((citation, index) => (
              <div key={index} className="citation">
                <strong>{citation.law}</strong> {citation.article && `(${citation.article})`} - {citation.jurisdiction}
              </div>
            ))}
          </div>
        )}

        {compliance.data_categories.length > 0 && (
          <div className="section">
            <h3>📊 Data Categories</h3>
            <div>
              {compliance.data_categories.map((category, index) => (
                <span key={index} className="jurisdiction-tag">{category}</span>
              ))}
            </div>
          </div>
        )}

        {compliance.lawful_basis.length > 0 && (
          <div className="section">
            <h3>⚖️ Lawful Basis</h3>
            <div>
              {compliance.lawful_basis.map((basis, index) => (
                <span key={index} className="jurisdiction-tag">{basis}</span>
              ))}
            </div>
          </div>
        )}

        {compliance.notes && (
          <div className="section">
            <h3>📝 Analysis Notes</h3>
            <p>{compliance.notes}</p>
          </div>
        )}

        {compliance.risks.length > 0 && (
          <div className="section">
            <h3>⚠️ Compliance Risks</h3>
            {compliance.risks.map((risk, index) => (
              <div key={index} className={`risk-item risk-${risk.severity}`}>
                <strong>Risk:</strong> {risk.risk}<br/>
                <strong>Severity:</strong> {risk.severity}<br/>
                <strong>Mitigation:</strong> {risk.mitigation}
              </div>
            ))}
          </div>
        )}

        {compliance.implementation.length > 0 && (
          <div className="section">
            <h3>🛠️ Implementation Steps</h3>
            {compliance.implementation.map((step, index) => (
              <div key={index} className="impl-step">
                <div className="priority-badge">{step.priority}</div>
                <div>{step.step}</div>
              </div>
            ))}
          </div>
        )}

        <div className="section">
          <h3>🎯 Confidence Score</h3>
          <div className="confidence-bar">
            <div 
              className="confidence-fill" 
              style={{ width: `${compliance.confidence * 100}%` }}
            ></div>
          </div>
          <p style={{ marginTop: '10px' }}>
            {Math.round(compliance.confidence * 100)}% confidence
          </p>
        </div>

        <div className="metadata">
          <strong>Model:</strong> {results.metadata.model_version} | 
          <strong>Response Time:</strong> {results.metadata.latency_ms}ms |
          <strong>Request ID:</strong> {results.metadata.request_id}
        </div>
      </div>
    );
  };

  return (
    <div className="geo-compliance-analyzer">
      <div className="container">
        <div className="header">
          <h1>🛡️ Geo-Compliance Analyzer</h1>
          <p>Powered by Phi-2 v5 | Real-time privacy law analysis</p>
        </div>

        <div className="main-content">
          <div className="input-section">
            <h2>Feature Analysis</h2>
            
            <div className="preset-buttons">
              <button className="preset-btn" onClick={() => loadPreset('gdpr')}>🇪🇺 GDPR Cookies</button>
              <button className="preset-btn" onClick={() => loadPreset('ccpa')}>🇺🇸 CCPA Button</button>
              <button className="preset-btn" onClick={() => loadPreset('kids')}>👶 Kids Privacy</button>
              <button className="preset-btn" onClick={() => loadPreset('simple')}>⚡ Simple UI</button>
            </div>

            <form onSubmit={analyzeCompliance}>
              <div className="form-group">
                <label htmlFor="featureName">Feature Name</label>
                <input
                  type="text"
                  id="featureName"
                  name="featureName"
                  value={formData.featureName}
                  onChange={handleInputChange}
                  placeholder="e.g., EU Cookie Consent Banner"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="featureDescription">Feature Description</label>
                <textarea
                  id="featureDescription"
                  name="featureDescription"
                  value={formData.featureDescription}
                  onChange={handleInputChange}
                  placeholder="Describe what your feature does, what data it processes, and who it affects..."
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="lawContext">Legal Context (JSON format)</label>
                <textarea
                  id="lawContext"
                  name="lawContext"
                  value={formData.lawContext}
                  onChange={handleInputChange}
                  placeholder='[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent"}]'
                />
              </div>

              <button type="submit" className="analyze-btn" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    Analyzing...
                  </>
                ) : (
                  '🔍 Analyze Compliance'
                )}
              </button>
            </form>
          </div>

          <div className="output-section">
            <h2>Analysis Results</h2>
            
            {loading && (
              <div className="loading">
                <div className="spinner"></div>
                Analyzing with Phi-2 v5...
              </div>
            )}

            {error && (
              <div className="error">
                <strong>Error:</strong> {error}
              </div>
            )}

            {results && <ComplianceResults results={results} />}

            {!loading && !error && !results && (
              <div className="placeholder">
                <div style={{ fontSize: '3em', marginBottom: '20px' }}>⚖️</div>
                <p>Enter your feature details and click "Analyze Compliance" to get started.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GeoComplianceAnalyzer;

