/**
 * LLM Provider Management Component
 * Allows users to add, edit, and delete LLM providers
 */
'use client';

import React, { useState, useEffect } from 'react';
import { llmProviderAPI, LLMProvider, LLMProviderCreate } from '@/lib/api/llm-providers';

export function LLMManagement() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const data = await llmProviderAPI.listProviders(false);
      setProviders(data);
    } catch (error) {
      console.error('Failed to load providers:', error);
      alert('Failed to load providers');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (providerId: string) => {
    setTestingProvider(providerId);
    try {
      const result = await llmProviderAPI.testProvider(providerId);
      if (result.success) {
        alert(`✅ Provider working! Latency: ${result.latency_ms?.toFixed(0)}ms`);
      } else {
        alert(`❌ Test failed: ${result.error_message}`);
      }
    } catch (error) {
      alert(`❌ Test failed: ${error}`);
    } finally {
      setTestingProvider(null);
    }
  };

  const handleDelete = async (providerId: string) => {
    if (!confirm('Are you sure you want to delete this provider?')) return;
    
    try {
      await llmProviderAPI.deleteProvider(providerId);
      await loadProviders();
    } catch (error) {
      alert(`Failed to delete provider: ${error}`);
    }
  };

  const handleSetDefault = async (providerId: string) => {
    try {
      await llmProviderAPI.setDefaultProvider(providerId);
      await loadProviders();
    } catch (error) {
      alert(`Failed to set default: ${error}`);
    }
  };

  const handleDiscover = async () => {
    try {
      setLoading(true);
      await llmProviderAPI.discoverProviders();
      await loadProviders();
      alert('Auto-discovery complete! Check the provider list.');
    } catch (error) {
      alert(`Discovery failed: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading providers...</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">LLM Providers</h2>
        <div className="space-x-2">
          <button
            onClick={handleDiscover}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            🔍 Auto-Discover
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            ➕ Add Provider
          </button>
        </div>
      </div>

      {showAddForm && (
        <AddProviderForm
          onSuccess={() => {
            setShowAddForm(false);
            loadProviders();
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      <div className="grid gap-4">
        {providers.map((provider) => (
          <ProviderCard
            key={provider.id}
            provider={provider}
            onTest={handleTest}
            onDelete={handleDelete}
            onSetDefault={handleSetDefault}
            testing={testingProvider === provider.id}
          />
        ))}
      </div>

      {providers.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No providers configured.</p>
          <p>Click "Auto-Discover" or "Add Provider" to get started.</p>
        </div>
      )}
    </div>
  );
}

interface ProviderCardProps {
  provider: LLMProvider;
  onTest: (id: string) => void;
  onDelete: (id: string) => void;
  onSetDefault: (id: string) => void;
  testing: boolean;
}

function ProviderCard({ provider, onTest, onDelete, onSetDefault, testing }: ProviderCardProps) {
  return (
    <div className="border rounded-lg p-4 shadow">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold">{provider.name}</h3>
            {provider.is_default && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                DEFAULT
              </span>
            )}
            <span className={`px-2 py-1 text-xs rounded ${
              provider.is_available 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {provider.is_available ? '🟢 Available' : '🔴 Offline'}
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            Type: {provider.provider_type} | Models: {provider.models.length}
          </p>
          {provider.api_base && (
            <p className="text-xs text-gray-500 mt-1">
              Endpoint: {provider.api_base}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onTest(provider.id)}
            disabled={testing}
            className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {testing ? '⏳ Testing...' : '🧪 Test'}
          </button>
          {!provider.is_default && (
            <button
              onClick={() => onSetDefault(provider.id)}
              className="px-3 py-1 bg-gray-500 text-white text-sm rounded hover:bg-gray-600"
            >
              Set Default
            </button>
          )}
          <button
            onClick={() => onDelete(provider.id)}
            className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
          >
            🗑️ Delete
          </button>
        </div>
      </div>
    </div>
  );
}

interface AddProviderFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

function AddProviderForm({ onSuccess, onCancel }: AddProviderFormProps) {
  const [formData, setFormData] = useState<LLMProviderCreate>({
    name: '',
    provider_type: 'openai',
    api_key: '',
    api_base: '',
    is_active: true,
    is_default: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await llmProviderAPI.createProvider(formData);
      alert('Provider added successfully!');
      onSuccess();
    } catch (error) {
      alert(`Failed to add provider: ${error}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border rounded-lg p-4 bg-gray-50">
      <h3 className="text-lg font-semibold mb-4">Add New Provider</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full border rounded px-3 py-2"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Provider Type</label>
          <select
            value={formData.provider_type}
            onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
            className="w-full border rounded px-3 py-2"
          >
            <option value="openai">OpenAI (ChatGPT)</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="gemini">Google (Gemini)</option>
            <option value="ollama">Ollama (Local)</option>
            <option value="custom">Custom (OpenAI-compatible)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">API Key</label>
          <input
            type="password"
            value={formData.api_key}
            onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
            className="w-full border rounded px-3 py-2"
            placeholder="sk-..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">API Base URL (optional)</label>
          <input
            type="text"
            value={formData.api_base}
            onChange={(e) => setFormData({ ...formData, api_base: e.target.value })}
            className="w-full border rounded px-3 py-2"
            placeholder="http://localhost:11434"
          />
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Add Provider
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
