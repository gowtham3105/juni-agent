import { useState } from 'react'
import './App.css'
import ComplianceForm from './components/ComplianceForm'
import ComplianceResults from './components/ComplianceResults'

export interface UserProfile {
  full_name: string
  date_of_birth?: string
  city?: string
  employer?: string
  id_data?: Record<string, string>
  aliases: string[]
}

export interface MediaHit {
  title: string
  snippet?: string
  full_text?: string
  date: string
  source: string
  url?: string
  hit_type: 'adverse_media' | 'pep' | 'watchlist' | 'sanctions'
}

export interface ComplianceResult {
  user_profile: UserProfile
  total_hits: number
  analyzed_articles: any[]
  matched_hits: any[]
  non_matched_hits: any[]
  final_decision: string
  decision_score: number
  overall_rationale: string
  targeted_ask?: string
  final_memo: string
  processing_timestamp: string
}

function App() {
  const [results, setResults] = useState<ComplianceResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleComplianceCheck = async (userProfile: UserProfile, mediaHits: MediaHit[]) => {
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await fetch('/compliance/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_profile: userProfile,
          media_hits: mediaHits
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        setResults(data.result)
      } else {
        setError(data.message || 'Unknown error occurred')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error occurred')
    } finally {
      setLoading(false)
    }
  }

  const loadSampleData = async () => {
    try {
      const response = await fetch('/compliance/sample')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (err) {
      setError('Failed to load sample data')
      return null
    }
  }

  return (
    <div className="app">
      <div className="header">
        <h1>🛡️ AI Compliance Agent</h1>
        <p>AML/KYC Adverse Media Review System</p>
      </div>

      <div className="main-content">
        {!results ? (
          <ComplianceForm 
            onSubmit={handleComplianceCheck}
            onLoadSample={loadSampleData}
            loading={loading}
            error={error}
          />
        ) : (
          <div>
            <ComplianceResults results={results} />
            <button 
              className="btn-secondary" 
              onClick={() => setResults(null)}
              style={{ marginTop: '20px' }}
            >
              ← New Analysis
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default App