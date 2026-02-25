/**
 * Type definitions for Axiomeer SDK
 */

export interface AxiomeerConfig {
  apiKey?: string;
  baseUrl?: string;
  timeout?: number;
}

export interface AppListing {
  app_id: string;
  name: string;
  description: string;
  provider: string;
  capabilities: string[];
  trust_card?: Record<string, any>;
  category?: string;
  uptime?: number;
}

export interface ShopRequest {
  task: string;
  required_capabilities?: string[];
  excluded_providers?: string[];
  max_cost_usd?: number;
}

export interface ShopResult {
  selected_app: AppListing;
  reasoning: string;
  confidence: number;
  alternatives: AppListing[];
}

export interface ExecuteRequest {
  app_id: string;
  params?: Record<string, any>;
}

export interface ExecutionResult {
  success: boolean;
  result: any;
  app_id: string;
  execution_time_ms?: number;
  cost_usd?: number;
  error?: string;
}

export interface ListAppsParams {
  category?: string;
  search?: string;
  limit?: number;
}

export interface HealthResponse {
  status: string;
  version?: string;
  timestamp?: string;
  [key: string]: any;
}

export class AxiomeerError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AxiomeerError';
  }
}

export class AuthenticationError extends AxiomeerError {
  constructor(message = 'Authentication failed. Invalid API key.') {
    super(message);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends AxiomeerError {
  retryAfter?: number;

  constructor(message = 'Rate limit exceeded', retryAfter?: number) {
    super(message);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class NotFoundError extends AxiomeerError {
  constructor(message = 'Resource not found') {
    super(message);
    this.name = 'NotFoundError';
  }
}

export class ExecutionError extends AxiomeerError {
  details?: any;

  constructor(message: string, details?: any) {
    super(message);
    this.name = 'ExecutionError';
    this.details = details;
  }
}

export class ValidationError extends AxiomeerError {
  constructor(message = 'Validation error') {
    super(message);
    this.name = 'ValidationError';
  }
}
