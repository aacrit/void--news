"""
Cluster summarization module for void --news pipeline.

Uses Google Gemini Flash (free tier) to generate polished cluster
headlines, summaries, and consensus/divergence points. Falls back
to existing rule-based generation when the API is unavailable.
"""
