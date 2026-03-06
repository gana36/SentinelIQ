export interface User {
  id: string
  email: string
  is_active: boolean
  created_at: string
}

export interface Preferences {
  risk_tolerance: 'low' | 'medium' | 'high'
  alert_sensitivity: number
  sectors: string[]
}

export interface WatchlistItem {
  id: string
  ticker: string
  added_at: string
}

export interface SentimentData {
  label: 'positive' | 'negative' | 'neutral'
  confidence: number
  intensity: number
  scores: Record<string, number>
}

export interface AnomalyData {
  is_anomaly: boolean
  anomaly_score: number
  threshold: number
}

export interface NovaAnalysis {
  event_summary: string
  affected_tickers: string[]
  primary_driver: string
  sector_impact: string
  confidence_level: number
  risk_factors: string[]
  time_horizon: 'intraday' | 'short-term' | 'long-term'
  recommended_actions: string[]
}

export interface SimilarEvent {
  date: string
  ticker: string
  event: string
  outcome: string
  sentiment: string
  similarity_score: number
}

export interface ActionCard {
  alert_id: string
  ticker: string
  event_summary: string
  sentiment: SentimentData
  anomaly: AnomalyData
  nova_analysis: NovaAnalysis
  similar_events: SimilarEvent[]
  credibility_score: number
  source_links: string[]
  target_users: string[]
  timestamp: string
  voice_ready: boolean
}

export interface Alert {
  id: string
  ticker: string
  alert_type: string
  payload: ActionCard
  created_at: string
  delivered_at: string | null
  read_at: string | null
}

export interface QuoteData {
  ticker: string
  price: number
  change_pct: number
  volume: number
  volume_zscore: number
  timestamp: string
}

export interface NewsItem {
  title: string
  source: string
  url: string
  published_at: string
  sentiment_label?: string
}

export interface RawSignal {
  signal_id: string
  source: string
  ticker: string | null
  raw_text: string
  timestamp: string
  metadata: Record<string, unknown>
}
