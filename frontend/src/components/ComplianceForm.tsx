import { useState } from 'react'
import { UserProfile, MediaHit } from '../App'

interface ComplianceFormProps {
  onSubmit: (userProfile: UserProfile, mediaHits: MediaHit[]) => void
  onLoadSample: () => Promise<any>
  loading: boolean
  error: string | null
}

export default function ComplianceForm({ onSubmit, onLoadSample, loading, error }: ComplianceFormProps) {
  const [userProfile, setUserProfile] = useState<UserProfile>({
    full_name: '',
    date_of_birth: '',
    city: '',
    employer: '',
    aliases: []
  })
  
  const [mediaHits, setMediaHits] = useState<MediaHit[]>([
    {
      title: '',
      snippet: '',
      date: '',
      source: '',
      url: '',
      hit_type: 'adverse_media'
    }
  ])

  const updateUserProfile = (field: keyof UserProfile, value: any) => {
    setUserProfile(prev => ({ ...prev, [field]: value }))
  }

  const updateMediaHit = (index: number, field: keyof MediaHit, value: any) => {
    setMediaHits(prev => prev.map((hit, i) => 
      i === index ? { ...hit, [field]: value } : hit
    ))
  }

  const addMediaHit = () => {
    setMediaHits(prev => [...prev, {
      title: '',
      snippet: '',
      date: '',
      source: '',
      url: '',
      hit_type: 'adverse_media'
    }])
  }

  const removeMediaHit = (index: number) => {
    if (mediaHits.length > 1) {
      setMediaHits(prev => prev.filter((_, i) => i !== index))
    }
  }

  const handleLoadSample = async () => {
    const sampleData = await onLoadSample()
    if (sampleData) {
      setUserProfile(sampleData.user_profile)
      setMediaHits(sampleData.media_hits)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(userProfile, mediaHits)
  }

  const updateAliases = (value: string) => {
    const aliases = value.split(',').map(alias => alias.trim()).filter(alias => alias)
    updateUserProfile('aliases', aliases)
  }

  return (
    <div className="compliance-form">
      <div className="form-header">
        <h2>Compliance Check</h2>
        <button 
          type="button" 
          className="btn-secondary" 
          onClick={handleLoadSample}
          disabled={loading}
        >
          Load Sample Data
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="section">
          <h3>👤 User Profile</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Full Name *</label>
              <input
                type="text"
                value={userProfile.full_name}
                onChange={(e) => updateUserProfile('full_name', e.target.value)}
                required
              />
            </div>
            
            <div className="form-group">
              <label>Date of Birth</label>
              <input
                type="date"
                value={userProfile.date_of_birth}
                onChange={(e) => updateUserProfile('date_of_birth', e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label>City</label>
              <input
                type="text"
                value={userProfile.city}
                onChange={(e) => updateUserProfile('city', e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label>Employer</label>
              <input
                type="text"
                value={userProfile.employer}
                onChange={(e) => updateUserProfile('employer', e.target.value)}
              />
            </div>
            
            <div className="form-group full-width">
              <label>Aliases (comma-separated)</label>
              <input
                type="text"
                value={userProfile.aliases.join(', ')}
                onChange={(e) => updateAliases(e.target.value)}
                placeholder="John Smith, J. Smith, Johnny"
              />
            </div>
          </div>
        </div>

        <div className="section">
          <div className="section-header">
            <h3>📄 Media Hits</h3>
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={addMediaHit}
            >
              + Add Hit
            </button>
          </div>
          
          {mediaHits.map((hit, index) => (
            <div key={index} className="media-hit">
              <div className="media-hit-header">
                <h4>Article {index + 1}</h4>
                {mediaHits.length > 1 && (
                  <button 
                    type="button" 
                    className="btn-danger" 
                    onClick={() => removeMediaHit(index)}
                  >
                    Remove
                  </button>
                )}
              </div>
              
              <div className="form-grid">
                <div className="form-group">
                  <label>Title *</label>
                  <input
                    type="text"
                    value={hit.title}
                    onChange={(e) => updateMediaHit(index, 'title', e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Source *</label>
                  <input
                    type="text"
                    value={hit.source}
                    onChange={(e) => updateMediaHit(index, 'source', e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Date *</label>
                  <input
                    type="date"
                    value={hit.date}
                    onChange={(e) => updateMediaHit(index, 'date', e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>URL</label>
                  <input
                    type="url"
                    value={hit.url}
                    onChange={(e) => updateMediaHit(index, 'url', e.target.value)}
                  />
                </div>
                
                <div className="form-group full-width">
                  <label>Article Content/Snippet</label>
                  <textarea
                    value={hit.snippet}
                    onChange={(e) => updateMediaHit(index, 'snippet', e.target.value)}
                    rows={4}
                    placeholder="Paste the article content or snippet here..."
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        <button 
          type="submit" 
          className="btn-primary" 
          disabled={loading || !userProfile.full_name}
        >
          {loading ? '🔄 Analyzing...' : '🔍 Run Compliance Check'}
        </button>
      </form>
    </div>
  )
}