"""
AI Prediction Module using Groq
Generates productivity predictions and personalized suggestions
"""

import requests
from typing import Dict, List, Optional
from config import Config, APIConfig


class GroqPredictor:
    """
    Integrates with Groq API to generate AI-powered predictions and suggestions
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.api_config = config.api
        self.api_key = self.api_config.groq_api_key
        
        if not self.api_key:
            print("⚠️ Groq API key not configured. Using fallback suggestions.")
        else:
            print("✓ Groq predictor initialized")
    
    def get_suggestions(self, weekly_summary: Dict, 
                       trends: Optional[Dict] = None,
                       insights: Optional[Dict] = None) -> str:
        """
        Get AI-powered suggestions based on weekly summary
        
        Args:
            weekly_summary: Weekly activity summary
            trends: Optional trend comparison
            insights: Optional activity insights
        
        Returns:
            String with suggestions and predictions
        """
        if not self.api_key:
            return self._fallback_suggestions(weekly_summary)
        
        try:
            prompt = self._build_prompt(weekly_summary, trends, insights)
            response = self._call_groq_api(prompt)
            return response
        except Exception as e:
            print(f"Groq API error: {e}")
            return self._fallback_suggestions(weekly_summary)
    
    def _build_prompt(self, weekly_summary: Dict,
                     trends: Optional[Dict],
                     insights: Optional[Dict]) -> str:
        """Build comprehensive prompt for Groq"""
        breakdown = weekly_summary.get('time_breakdown_hours', {})
        productive_pct = weekly_summary.get('productive_percentage', 0)
        total_hours = weekly_summary.get('total_present_hours', 0)
        
        prompt = f"""You are a productivity coach analyzing someone's weekly activity data.

WEEKLY SUMMARY:
- Week: {weekly_summary['week_start']} to {weekly_summary['week_end']}
- Total Active Time: {total_hours:.1f} hours
- Productivity: {productive_pct:.1f}%

ACTIVITY BREAKDOWN:
"""
        
        for activity, hours in breakdown.items():
            percentage = (hours / total_hours * 100) if total_hours > 0 else 0
            prompt += f"- {activity.replace('_', ' ').title()}: {hours:.1f} hours ({percentage:.1f}%)\n"
        
        if trends:
            prompt += f"\nTRENDS (vs Previous Week):\n"
            if 'summary' in trends:
                for trend_point in trends['summary']:
                    prompt += f"- {trend_point}\n"
        
        if insights:
            prompt += f"\nINSIGHTS:\n"
            if insights.get('warnings'):
                prompt += "Warnings:\n"
                for warning in insights['warnings']:
                    prompt += f"- {warning}\n"
            if insights.get('insights'):
                prompt += "Positive Patterns:\n"
                for insight in insights['insights']:
                    prompt += f"- {insight}\n"
        
        prompt += """
Based on this data, provide:
1. A brief risk assessment (Low/Medium/High) for long-term productivity and well-being
2. 3-5 specific, actionable suggestions to improve productivity and reduce unproductive time
3. One motivational insight or encouragement

Keep your response concise, practical, and encouraging. Format with clear sections."""
        
        return prompt
    
    def _call_groq_api(self, prompt: str) -> str:
        """Call Groq API with the prompt"""
        url = self.api_config.groq_endpoint
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.api_config.groq_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a supportive productivity coach. "
                        "Give practical, actionable advice with empathy. "
                        "Be encouraging but honest about areas needing improvement."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 600,
            "temperature": 0.7
        }
        
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=self.api_config.groq_timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            return content.strip()
        else:
            error_msg = f"API returned status {response.status_code}"
            print(error_msg)
            raise Exception(error_msg)
    
    def _fallback_suggestions(self, weekly_summary: Dict) -> str:
        """
        Generate rule-based suggestions when AI is unavailable
        """
        breakdown = weekly_summary.get('time_breakdown_hours', {})
        productive_pct = weekly_summary.get('productive_percentage', 0)
        total_hours = weekly_summary.get('total_present_hours', 0)
        
        phone_hours = breakdown.get('watching_reels', 0)
        tv_hours = breakdown.get('watching_tv', 0)
        work_hours = breakdown.get('working', 0)
        
        # Risk assessment
        if productive_pct < 20:
            risk = "🔴 HIGH RISK"
            risk_msg = "Your productivity is significantly below healthy levels."
        elif productive_pct < 40:
            risk = "🟡 MEDIUM RISK"
            risk_msg = "There's room for improvement in productivity habits."
        else:
            risk = "🟢 LOW RISK"
            risk_msg = "You're maintaining good productivity levels!"
        
        suggestions = []
        
        # Phone usage suggestions
        if phone_hours > 15:
            suggestions.append(
                "📱 Phone Time: Reduce by 2 hours daily using app blockers "
                "(try Freedom, Forest, or built-in Screen Time)"
            )
        elif phone_hours > 10:
            suggestions.append(
                "📱 Phone Time: Set specific 'no phone' hours, especially during work time"
            )
        
        # TV suggestions
        if tv_hours > 15:
            suggestions.append(
                "📺 TV Time: Replace 1-2 hours with reading or a productive hobby"
            )
        
        # Work suggestions
        if work_hours < 15 and total_hours > 30:
            suggestions.append(
                "💼 Work Focus: Try Pomodoro Technique (25min focused work + 5min break). "
                "Start with 2-3 sessions per day."
            )
        
        # Time blocking
        if productive_pct < 40:
            suggestions.append(
                "⏰ Time Blocking: Schedule your day in advance. "
                "Protect morning hours (9am-12pm) for deep work."
            )
        
        # Environment
        if work_hours > 0:
            suggestions.append(
                "🌿 Environment: Keep phone in another room during work blocks. "
                "Physical distance is the best blocker!"
            )
        
        # Positive reinforcement
        if work_hours > 20:
            encouragement = "💪 Great work ethic this week! Keep the momentum going."
        elif productive_pct > 50:
            encouragement = "✅ You're making good progress. Small consistent improvements compound!"
        else:
            encouragement = "🌱 Every journey starts with a single step. This week, focus on just one habit."
        
        # Build response
        response = f"""
{risk}
{risk_msg}

ACTIONABLE SUGGESTIONS:
"""
        for i, suggestion in enumerate(suggestions[:5], 1):
            response += f"\n{i}. {suggestion}"
        
        response += f"\n\n{encouragement}"
        
        return response.strip()
    
    def predict_risk_level(self, weekly_summary: Dict) -> Dict:
        """
        Predict risk level based on activity patterns
        
        Returns:
            Dictionary with risk score and category
        """
        breakdown = weekly_summary.get('time_breakdown_hours', {})
        productive_pct = weekly_summary.get('productive_percentage', 0)
        total_hours = weekly_summary.get('total_present_hours', 0)
        
        phone_hours = breakdown.get('watching_reels', 0)
        tv_hours = breakdown.get('watching_tv', 0)
        work_hours = breakdown.get('working', 0)
        
        # Calculate risk score (0-100, higher = more risk)
        risk_score = 0
        
        # Factor 1: Low productivity (40 points max)
        if productive_pct < 20:
            risk_score += 40
        elif productive_pct < 40:
            risk_score += 25
        elif productive_pct < 60:
            risk_score += 10
        
        # Factor 2: Excessive phone usage (30 points max)
        phone_pct = (phone_hours / total_hours * 100) if total_hours > 0 else 0
        if phone_pct > 40:
            risk_score += 30
        elif phone_pct > 25:
            risk_score += 20
        elif phone_pct > 15:
            risk_score += 10
        
        # Factor 3: Excessive TV (20 points max)
        tv_pct = (tv_hours / total_hours * 100) if total_hours > 0 else 0
        if tv_pct > 30:
            risk_score += 20
        elif tv_pct > 20:
            risk_score += 10
        
        # Factor 4: Low work hours (10 points max)
        if work_hours < 10 and total_hours > 20:
            risk_score += 10
        elif work_hours < 15 and total_hours > 30:
            risk_score += 5
        
        # Determine category
        if risk_score >= 60:
            category = "HIGH"
            color = "🔴"
        elif risk_score >= 30:
            category = "MEDIUM"
            color = "🟡"
        else:
            category = "LOW"
            color = "🟢"
        
        return {
            "risk_score": risk_score,
            "risk_category": category,
            "risk_emoji": color,
            "factors": {
                "productivity_score": 100 - productive_pct,
                "phone_usage_pct": round(phone_pct, 1),
                "tv_usage_pct": round(tv_pct, 1),
                "work_hours": work_hours
            },
            "interpretation": self._interpret_risk(category, risk_score)
        }
    
    def _interpret_risk(self, category: str, score: int) -> str:
        """Interpret risk score"""
        interpretations = {
            "LOW": "Your activity patterns support healthy productivity and well-being.",
            "MEDIUM": "Some habits could be improved to boost productivity and reduce digital distractions.",
            "HIGH": "Current patterns may lead to reduced productivity and well-being. Immediate changes recommended."
        }
        return interpretations.get(category, "")
    
    def generate_feature_vector(self, weekly_summary: Dict, 
                               trends: Optional[Dict] = None) -> Dict:
        """
        Generate feature vector for ML prediction
        (Useful if you want to train your own model later)
        
        Returns:
            Dictionary of numerical features
        """
        breakdown = weekly_summary.get('time_breakdown_hours', {})
        total_hours = weekly_summary.get('total_present_hours', 0)
        
        features = {
            # Time features
            "total_hours": total_hours,
            "productive_percentage": weekly_summary.get('productive_percentage', 0),
            "productive_hours": weekly_summary.get('productive_hours', 0),
            "unproductive_hours": weekly_summary.get('unproductive_hours', 0),
            
            # Activity percentages
            "phone_pct": (breakdown.get('watching_reels', 0) / total_hours * 100) if total_hours > 0 else 0,
            "tv_pct": (breakdown.get('watching_tv', 0) / total_hours * 100) if total_hours > 0 else 0,
            "work_pct": (breakdown.get('working', 0) / total_hours * 100) if total_hours > 0 else 0,
            "idle_pct": (breakdown.get('idle', 0) / total_hours * 100) if total_hours > 0 else 0,
            
            # Trend features (if available)
            "productivity_trend": 0,
            "total_time_trend_pct": 0
        }
        
        if trends:
            overall_trends = trends.get('overall_trends', {})
            
            # Parse trend strings
            time_change_str = overall_trends.get('total_time_change', '0%')
            try:
                time_trend_val = float(time_change_str.replace('%', '').replace('+', ''))
                features["total_time_trend_pct"] = time_trend_val
            except ValueError:
                pass
            
            prod_change = overall_trends.get('productivity_change', 0)
            features["productivity_trend"] = prod_change
        
        return features
