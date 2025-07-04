"""
Tests for Expert model.

Tests expert creation, validation, computed properties, and specializations.
"""

import pytest
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.expert import Expert


class TestExpertModel:
    """Test Expert model functionality."""
    
    def test_expert_creation(self):
        """Test basic expert creation."""
        expert = Expert(
            name="John Smith",
            title="Senior Analyst",
            institution="Goldman Sachs",
            bio="Experienced technology analyst",
            email="j.smith@gs.com",
            years_experience=10
        )
        
        assert expert.name == "John Smith"
        assert expert.title == "Senior Analyst"
        assert expert.institution == "Goldman Sachs"
        assert expert.bio == "Experienced technology analyst"
        assert expert.email == "j.smith@gs.com"
        assert expert.years_experience == 10
        
        # Test defaults
        assert expert.total_ratings == 0
        assert expert.follower_count == 0
        assert expert.is_verified is False
        assert expert.is_active is True
    
    def test_required_fields_only(self):
        """Test expert creation with only required fields."""
        expert = Expert(name="Jane Doe")
        
        assert expert.name == "Jane Doe"
        
        # Optional fields should be None or defaults
        assert expert.title is None
        assert expert.institution is None
        assert expert.bio is None
        assert expert.email is None
        assert expert.years_experience is None
        assert expert.total_ratings == 0
        assert expert.accuracy_score is None
        assert expert.follower_count == 0
        assert expert.is_verified is False
        assert expert.is_active is True
    
    def test_display_name_property(self):
        """Test display_name computed property."""
        # Expert with institution
        expert1 = Expert(
            name="Alice Johnson",
            institution="Morgan Stanley"
        )
        assert expert1.display_name == "Alice Johnson (Morgan Stanley)"
        
        # Expert without institution
        expert2 = Expert(name="Bob Wilson")
        assert expert2.display_name == "Bob Wilson"
        
        # Expert with empty institution
        expert3 = Expert(name="Carol Brown", institution="")
        assert expert3.display_name == "Carol Brown"
    
    def test_reputation_level_property(self):
        """Test reputation_level computed property."""
        # New expert (no accuracy score or low ratings)
        expert1 = Expert(name="New Expert")
        assert expert1.reputation_level == "New"
        
        expert2 = Expert(
            name="New Expert 2", 
            total_ratings=5,
            accuracy_score=0.9
        )
        assert expert2.reputation_level == "New"
        
        # Developing expert
        expert3 = Expert(
            name="Developing Expert",
            total_ratings=20,
            accuracy_score=0.5
        )
        assert expert3.reputation_level == "Developing"
        
        # Intermediate expert
        expert4 = Expert(
            name="Intermediate Expert",
            total_ratings=30,
            accuracy_score=0.65
        )
        assert expert4.reputation_level == "Intermediate"
        
        # Experienced expert
        expert5 = Expert(
            name="Experienced Expert",
            total_ratings=60,
            accuracy_score=0.75
        )
        assert expert5.reputation_level == "Experienced"
        
        # Expert level
        expert6 = Expert(
            name="Expert Level",
            total_ratings=150,
            accuracy_score=0.85
        )
        assert expert6.reputation_level == "Expert"
    
    def test_expertise_areas_property(self):
        """Test expertise_areas computed property."""
        # Expert with no specializations
        expert1 = Expert(name="No Spec Expert")
        assert expert1.expertise_areas == []
        
        # Expert with valid JSON specializations
        expert2 = Expert(
            name="Tech Expert",
            specializations='["Technology", "Software", "AI"]'
        )
        assert expert2.expertise_areas == ["Technology", "Software", "AI"]
        
        # Expert with empty JSON array
        expert3 = Expert(
            name="Empty Spec Expert",
            specializations='[]'
        )
        assert expert3.expertise_areas == []
        
        # Expert with invalid JSON (should return empty list)
        expert4 = Expert(
            name="Invalid JSON Expert",
            specializations='invalid json'
        )
        assert expert4.expertise_areas == []
        
        # Expert with None specializations
        expert5 = Expert(
            name="None Spec Expert",
            specializations=None
        )
        assert expert5.expertise_areas == []
    
    def test_add_specialization(self):
        """Test adding specializations."""
        expert = Expert(name="Growing Expert")
        
        # Add first specialization
        expert.add_specialization("Technology")
        assert expert.expertise_areas == ["Technology"]
        
        # Add second specialization
        expert.add_specialization("Software")
        assert expert.expertise_areas == ["Technology", "Software"]
        
        # Try to add duplicate (should not add)
        expert.add_specialization("Technology")
        assert expert.expertise_areas == ["Technology", "Software"]
        
        # Add third specialization
        expert.add_specialization("AI")
        assert expert.expertise_areas == ["Technology", "Software", "AI"]
    
    def test_add_specialization_to_existing(self):
        """Test adding specialization to expert with existing specializations."""
        expert = Expert(
            name="Existing Spec Expert",
            specializations='["Finance", "Banking"]'
        )
        
        # Verify existing specializations
        assert expert.expertise_areas == ["Finance", "Banking"]
        
        # Add new specialization
        expert.add_specialization("Insurance")
        assert expert.expertise_areas == ["Finance", "Banking", "Insurance"]
        
        # Try to add existing (should not duplicate)
        expert.add_specialization("Finance")
        assert expert.expertise_areas == ["Finance", "Banking", "Insurance"]
    
    def test_update_metrics(self):
        """Test updating expert metrics."""
        expert = Expert(name="Metrics Expert")
        
        # Initial state
        assert expert.total_ratings == 0
        assert expert.accuracy_score is None
        assert expert.avg_rating_score is None
        assert expert.follower_count == 0
        
        # Update metrics
        expert.update_metrics(
            total_ratings=50,
            accuracy_score=0.85,
            avg_rating_score=4.2,
            follower_count=1500
        )
        
        assert expert.total_ratings == 50
        assert expert.accuracy_score == 0.85
        assert expert.avg_rating_score == 4.2
        assert expert.follower_count == 1500
    
    def test_update_metrics_partial(self):
        """Test partial metric updates."""
        expert = Expert(
            name="Partial Expert",
            total_ratings=25,
            accuracy_score=0.75,
            follower_count=800
        )
        
        # Update only some metrics
        expert.update_metrics(
            total_ratings=30,
            accuracy_score=0.78
        )
        
        assert expert.total_ratings == 30
        assert expert.accuracy_score == 0.78
        # These should remain unchanged
        assert expert.avg_rating_score is None
        assert expert.follower_count == 800
    
    def test_update_metrics_bounds_checking(self):
        """Test that update_metrics enforces bounds."""
        expert = Expert(name="Bounds Expert")
        
        # Test accuracy score bounds (should be clamped to 0.0-1.0)
        expert.update_metrics(accuracy_score=1.5)
        assert expert.accuracy_score == 1.0
        
        expert.update_metrics(accuracy_score=-0.5)
        assert expert.accuracy_score == 0.0
        
        # Test follower count bounds (should be non-negative)
        expert.update_metrics(follower_count=-100)
        assert expert.follower_count == 0
        
        expert.update_metrics(follower_count=1000)
        assert expert.follower_count == 1000
    
    def test_verify_expert(self):
        """Test expert verification."""
        expert = Expert(name="Unverified Expert")
        
        # Initially not verified
        assert expert.is_verified is False
        assert expert.verification_date is None
        
        # Verify expert
        before_verification = datetime.now(timezone.utc)
        expert.verify()
        after_verification = datetime.now(timezone.utc)
        
        assert expert.is_verified is True
        assert expert.verification_date is not None
        assert before_verification <= expert.verification_date <= after_verification
    
    def test_expert_repr(self):
        """Test string representation of expert."""
        expert = Expert(
            name="Repr Expert",
            institution="Test Institution",
            is_verified=True
        )
        
        repr_str = repr(expert)
        
        assert "Expert" in repr_str
        assert "Repr Expert" in repr_str
        assert "Test Institution" in repr_str
        assert "True" in repr_str
    
    def test_social_media_fields(self):
        """Test social media related fields."""
        expert = Expert(
            name="Social Expert",
            website="https://example.com",
            linkedin_url="https://linkedin.com/in/social-expert",
            twitter_handle="SocialExpert"
        )
        
        assert expert.website == "https://example.com"
        assert expert.linkedin_url == "https://linkedin.com/in/social-expert"
        assert expert.twitter_handle == "SocialExpert"
    
    def test_professional_fields(self):
        """Test professional credential fields."""
        expert = Expert(
            name="Professional Expert",
            certifications="CFA, CPA, FRM",
            years_experience=15
        )
        
        assert expert.certifications == "CFA, CPA, FRM"
        assert expert.years_experience == 15
    
    @pytest.mark.asyncio
    async def test_expert_persistence(self, async_session: AsyncSession):
        """Test saving and retrieving expert from database."""
        expert = Expert(
            name="Persistent Expert",
            title="Chief Investment Officer",
            institution="Investment Firm LLC",
            bio="Long-time investment professional with focus on growth stocks",
            email="expert@investmentfirm.com",
            website="https://investmentfirm.com/experts/persistent",
            linkedin_url="https://linkedin.com/in/persistent-expert",
            twitter_handle="PersistentExpert",
            years_experience=20,
            specializations='["Technology", "Healthcare", "Finance"]',
            certifications="CFA, CPA",
            total_ratings=150,
            accuracy_score=0.87,
            avg_rating_score=4.1,
            follower_count=5200,
            is_verified=True
        )
        
        # Set verification date
        expert.verify()
        
        # Save to database
        async_session.add(expert)
        await async_session.commit()
        
        # Refresh to get updated timestamps
        await async_session.refresh(expert)
        
        # Verify all fields were saved correctly
        assert expert.id is not None
        assert expert.name == "Persistent Expert"
        assert expert.title == "Chief Investment Officer"
        assert expert.institution == "Investment Firm LLC"
        assert expert.bio == "Long-time investment professional with focus on growth stocks"
        assert expert.email == "expert@investmentfirm.com"
        assert expert.website == "https://investmentfirm.com/experts/persistent"
        assert expert.linkedin_url == "https://linkedin.com/in/persistent-expert"
        assert expert.twitter_handle == "PersistentExpert"
        assert expert.years_experience == 20
        assert expert.specializations == '["Technology", "Healthcare", "Finance"]'
        assert expert.certifications == "CFA, CPA"
        assert expert.total_ratings == 150
        assert expert.accuracy_score == 0.87
        assert expert.avg_rating_score == 4.1
        assert expert.follower_count == 5200
        assert expert.is_verified is True
        assert expert.is_active is True
        assert expert.verification_date is not None
        
        # Should have timestamps
        assert expert.created_at is not None
        assert expert.updated_at is not None
        
        # Test computed properties work with persisted data
        assert expert.display_name == "Persistent Expert (Investment Firm LLC)"
        assert expert.expertise_areas == ["Technology", "Healthcare", "Finance"]
        assert expert.reputation_level == "Expert"