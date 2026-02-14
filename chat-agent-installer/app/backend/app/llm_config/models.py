"""
SQLAlchemy models for LLM provider configuration storage
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON
from sqlalchemy.ext.hybrid import hybrid_property
from cryptography.fernet import Fernet
import os
import base64

from app.db import Base


class LLMProviderModel(Base):
    """Database model for LLM provider configurations"""
    __tablename__ = "llm_providers"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)  # openai, anthropic, ollama, etc.
    
    # Encrypted API key
    _api_key_encrypted = Column("api_key", Text, nullable=True)
    
    # Optional API base URL (for custom endpoints, Ollama, etc.)
    api_base = Column(String, nullable=True)
    
    # Available models (stored as JSON)
    models = Column(JSON, nullable=True)
    
    # Extra provider-specific configuration
    extra_config = Column(JSON, nullable=True)
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Encryption key from environment or default
    _ENCRYPTION_KEY = None
    
    @classmethod
    def get_encryption_key(cls) -> bytes:
        """Get or create encryption key"""
        if cls._ENCRYPTION_KEY is None:
            key_str = os.getenv("LLM_API_KEY_ENCRYPTION_KEY")
            if key_str:
                cls._ENCRYPTION_KEY = base64.urlsafe_b64decode(key_str)
            else:
                # Use master key from settings as fallback
                from app.config import get_settings
                settings = get_settings()
                cls._ENCRYPTION_KEY = base64.urlsafe_b64decode(settings.MASTER_KEY)
        return cls._ENCRYPTION_KEY
    
    @hybrid_property
    def api_key(self) -> str | None:
        """Decrypt and return API key"""
        if not self._api_key_encrypted:
            return None
        
        try:
            fernet = Fernet(self.get_encryption_key())
            decrypted = fernet.decrypt(self._api_key_encrypted.encode())
            return decrypted.decode()
        except Exception:
            return None
    
    @api_key.setter
    def api_key(self, value: str | None):
        """Encrypt and store API key"""
        if value is None:
            self._api_key_encrypted = None
        else:
            fernet = Fernet(self.get_encryption_key())
            encrypted = fernet.encrypt(value.encode())
            self._api_key_encrypted = encrypted.decode()
    
    def to_dict(self, include_api_key: bool = False) -> dict:
        """Convert to dictionary"""
        data = {
            "id": self.id,
            "name": self.name,
            "provider_type": self.provider_type,
            "api_base": self.api_base,
            "models": self.models or [],
            "extra_config": self.extra_config or {},
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_api_key:
            data["api_key"] = self.api_key
        else:
            data["api_key_set"] = bool(self._api_key_encrypted)
        
        return data
