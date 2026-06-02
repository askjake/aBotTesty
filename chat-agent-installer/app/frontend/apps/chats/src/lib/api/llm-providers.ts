/**
 * LLM Provider API Client
 * Handles all API calls for LLM provider management
 */

export interface LLMModel {
  model_id: string;
  display_name: string;
  context_length: number;
  supports_streaming: boolean;
  supports_vision: boolean;
}

export interface LLMProvider {
  id: string;
  name: string;
  provider_type: 'openai' | 'anthropic' | 'ollama' | 'gemini' | 'bedrock' | 'custom' | 'dishchat';
  api_key_set: boolean;
  api_base?: string;
  models: LLMModel[];
  is_active: boolean;
  is_default: boolean;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderCreate {
  name: string;
  provider_type: string;
  api_key?: string;
  api_base?: string;
  models?: LLMModel[];
  is_active?: boolean;
  is_default?: boolean;
}

export interface LLMProviderTestResult {
  success: boolean;
  provider_name: string;
  provider_type: string;
  response_text?: string;
  error_message?: string;
  latency_ms?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const API_PREFIX = '/rest/api/v1';

export class LLMProviderAPI {
  private baseUrl: string;

  constructor(baseUrl: string = `${API_BASE}${API_PREFIX}`) {
    this.baseUrl = baseUrl;
  }

  async listProviders(activeOnly: boolean = true): Promise<LLMProvider[]> {
    const params = new URLSearchParams({ active_only: activeOnly.toString() });
    const response = await fetch(`${this.baseUrl}/llm-providers?${params}`);
    if (!response.ok) throw new Error('Failed to fetch providers');
    return response.json();
  }

  async getProvider(providerId: string): Promise<LLMProvider> {
    const response = await fetch(`${this.baseUrl}/llm-providers/${providerId}`);
    if (!response.ok) throw new Error('Failed to fetch provider');
    return response.json();
  }

  async createProvider(data: LLMProviderCreate): Promise<LLMProvider> {
    const response = await fetch(`${this.baseUrl}/llm-providers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create provider');
    return response.json();
  }

  async updateProvider(providerId: string, data: Partial<LLMProviderCreate>): Promise<LLMProvider> {
    const response = await fetch(`${this.baseUrl}/llm-providers/${providerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update provider');
    return response.json();
  }

  async deleteProvider(providerId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/llm-providers/${providerId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete provider');
  }

  async setDefaultProvider(providerId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/llm-providers/${providerId}/set-default`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to set default provider');
  }

  async testProvider(providerId: string): Promise<LLMProviderTestResult> {
    const response = await fetch(`${this.baseUrl}/llm-providers/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: providerId }),
    });
    if (!response.ok) throw new Error('Failed to test provider');
    return response.json();
  }

  async discoverProviders(): Promise<LLMProvider[]> {
    const response = await fetch(`${this.baseUrl}/llm-providers/discover`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to discover providers');
    return response.json();
  }
}

export const llmProviderAPI = new LLMProviderAPI();
