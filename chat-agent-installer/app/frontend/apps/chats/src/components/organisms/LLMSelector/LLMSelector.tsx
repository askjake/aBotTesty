/**
 * LLM Selector Component
 * Dropdown to select which LLM provider to use for a chat
 */
'use client';

import React, { useState, useEffect } from 'react';
import { llmProviderAPI, LLMProvider } from '@/lib/api/llm-providers';

interface LLMSelectorProps {
  selectedProviderId?: string;
  onSelect: (providerId: string) => void;
  className?: string;
}

export function LLMSelector({ selectedProviderId, onSelect, className = '' }: LLMSelectorProps) {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const data = await llmProviderAPI.listProviders(true);
      setProviders(data);
      
      // Select default if no selection
      if (!selectedProviderId && data.length > 0) {
        const defaultProvider = data.find(p => p.is_default) || data[0];
        onSelect(defaultProvider.id);
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className={className}>Loading...</div>;
  }

  if (providers.length === 0) {
    return (
      <div className={className}>
        <span className="text-yellow-600">⚠️ No LLM providers configured</span>
      </div>
    );
  }

  return (
    <select
      value={selectedProviderId || ''}
      onChange={(e) => onSelect(e.target.value)}
      className={`rounded border px-2 py-1 ${className}`}
    >
      {providers.map((provider) => (
        <option key={provider.id} value={provider.id}>
          {provider.is_available ? '🟢' : '🔴'} {provider.name}
          {provider.is_default && ' (default)'}
        </option>
      ))}
    </select>
  );
}
