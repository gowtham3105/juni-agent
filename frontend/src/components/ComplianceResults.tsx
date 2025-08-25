import { ComplianceResult } from '../App'

interface ComplianceResultsProps {
  results: ComplianceResult
}

export default function ComplianceResults({ results }: ComplianceResultsProps) {
  const getDecisionColor = (decision: string) => {
    switch (decision.toLowerCase()) {
      case 'clear': return '#22c55e'
      case 'escalate': return '#f59e0b'
      case 'decline': return '#ef4444'
      default: return '#6b7280'
    }
  }

  const getLinkageColor = (linkage: string) => {
    switch (linkage) {
      case 'yes': return '#ef4444'
      case 'maybe': return '#f59e0b'
      case 'no': return '#22c55e'
      default: return '#6b7280'
    }
  }

  return (
    <div className="compliance-results">
      <div className="results-header">
        <h2>🔍 Compliance Analysis Results</h2>
        <div className="results-summary">
          <div className="summary-card">
            <h3 style={{ color: getDecisionColor(results.final_decision) }}>
              {results.final_decision.toUpperCase()}
            </h3>
            <p>Final Decision</p>
          </div>
          <div className="summary-card">
            <h3>{results.decision_score}/100</h3>
            <p>Risk Score</p>
          </div>
          <div className="summary-card">
            <h3>{results.matched_hits.length}</h3>
            <p>Matched Articles</p>
          </div>
          <div className="summary-card">
            <h3>{results.total_hits}</h3>
            <p>Total Articles</p>
          </div>
        </div>
      </div>

      <div className="subject-info">
        <h3>👤 Subject Information</h3>
        <div className="info-grid">
          <div><strong>Name:</strong> {results.user_profile.full_name}</div>
          <div><strong>DOB:</strong> {results.user_profile.date_of_birth || 'Not provided'}</div>
          <div><strong>City:</strong> {results.user_profile.city || 'Not provided'}</div>
          <div><strong>Employer:</strong> {results.user_profile.employer || 'Not provided'}</div>
        </div>
      </div>

      <div className="rationale">
        <h3>📝 Overall Assessment</h3>
        <p className="rationale-text">{results.overall_rationale}</p>
        {results.targeted_ask && (
          <div className="targeted-ask">
            <h4>🎯 Recommended Action</h4>
            <p>{results.targeted_ask}</p>
          </div>
        )}
      </div>

      <div className="articles-analysis">
        <h3>📰 Article Analysis</h3>
        {results.analyzed_articles.map((article, index) => (
          <div key={index} className="article-card">
            <div className="article-header">
              <div className="article-title">
                <h4>{article.hit.title}</h4>
                <div className="article-meta">
                  <span>{article.hit.source}</span>
                  <span>•</span>
                  <span>{article.hit.date}</span>
                </div>
              </div>
              <div 
                className="linkage-badge"
                style={{ backgroundColor: getLinkageColor(article.linkage_decision) }}
              >
                {article.linkage_decision.toUpperCase()}
              </div>
            </div>

            <div className="article-content">
              <div className="brief-summary">
                <h5>Summary</h5>
                <p>{article.brief_summary}</p>
              </div>

              {article.anchors.length > 0 && (
                <div className="anchors-section">
                  <h5>Identity Anchors Found ({article.anchors.length})</h5>
                  <div className="anchors-grid">
                    {article.anchors.map((anchor: any, anchorIndex: number) => (
                      <div key={anchorIndex} className="anchor-item">
                        <span className="anchor-type">{anchor.anchor_type}:</span>
                        <span className="anchor-value">{anchor.value}</span>
                        <span className="anchor-confidence">({(anchor.confidence * 100).toFixed(0)}%)</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {article.anchor_verifications && article.anchor_verifications.length > 0 && (
                <div className="verifications-section">
                  <h5>Anchor Verification</h5>
                  <div className="verifications-list">
                    {article.anchor_verifications.map((verification: any, verIndex: number) => (
                      <div key={verIndex} className={`verification-item ${verification.matches ? 'match' : verification.conflict ? 'conflict' : 'no-match'}`}>
                        <span className="verification-icon">
                          {verification.matches ? '✅' : verification.conflict ? '❌' : '➖'}
                        </span>
                        <span className="verification-text">{verification.rationale}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {article.contradictions && article.contradictions.length > 0 && (
                <div className="contradictions-section">
                  <h5>⚠️ Contradictions Found</h5>
                  <ul className="contradictions-list">
                    {article.contradictions.map((contradiction: string, contIndex: number) => (
                      <li key={contIndex}>{contradiction}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="article-footer">
                <div className="credibility">{article.credibility_note}</div>
                <div className="recency">{article.recency_note}</div>
                {article.hit.url && (
                  <a href={article.hit.url} target="_blank" rel="noopener noreferrer" className="source-link">
                    View Source →
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="final-memo">
        <h3>📋 Compliance Memo</h3>
        <pre className="memo-content">{results.final_memo}</pre>
      </div>
    </div>
  )
}