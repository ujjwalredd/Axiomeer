/**
 * Type definitions for Axiomeer SDK
 */

export interface AxiomeerConfig {
  apiKey?: string;
  baseUrl?: string;
  timeout?: number;
}

// Matches AppOut from the API
export interface AppListing {
  id: string;
  name: string;
  description: string;
  category: string;
  subcategory?: string;
  tags: string[];
  capabilities: string[];
  freshness: 'static' | 'daily' | 'realtime';
  citations_supported: boolean;
  product_type: string;
  latency_est_ms: number;
  cost_est_usd: number;
  executor_type: string;
  executor_url: string;
  metadata: Record<string, any>;
}

export interface Constraints {
  citations_required?: boolean;
  freshness?: 'static' | 'daily' | 'realtime';
  max_latency_ms?: number;
  max_cost_usd?: number;
}

export interface ShopRequest {
  task: string;
  required_capabilities?: string[];
  constraints?: Constraints;
  client_id?: string;
}

// Matches Recommendation from the API
export interface Recommendation {
  app_id: string;
  name: string;
  score: number;
  why: string[];
  rationale?: string;
  tradeoff?: string;
  trust_score?: number;
}

// Matches ShopResponse from the API
export interface ShopResponse {
  status: 'OK' | 'NO_MATCH';
  recommendations: Recommendation[];
  explanation: string[];
  sales_agent?: {
    summary: string;
    final_choice: string;
    recommendations: Array<{ app_id: string; rationale: string; tradeoff: string }>;
  };
  metrics: Record<string, any>;
}

export interface ExecuteRequest {
  app_id: string;
  task: string;
  inputs?: Record<string, any>;
  fallback_app_ids?: string[];
  require_citations?: boolean;
  client_id?: string;
}

export interface Provenance {
  sources: string[];
  retrieved_at: string;
  notes: string[];
}

// Matches ExecuteResponse from the API
export interface ExecuteResponse {
  app_id: string;
  ok: boolean;
  output?: Record<string, any>;
  provenance?: Provenance;
  validation_errors: string[];
  run_id?: number;
}

export interface WorkflowStep {
  app_id: string;
  task: string;
  inputs?: Record<string, any>;
  output_key?: string;
}

export interface WorkflowRequest {
  steps: WorkflowStep[];
  client_id?: string;
}

export interface WorkflowStepResult {
  step: number;
  app_id: string;
  ok: boolean;
  output?: Record<string, any>;
  error?: string;
}

export interface WorkflowResponse {
  ok: boolean;
  steps: WorkflowStepResult[];
  final_output?: Record<string, any>;
}

export interface CapabilitiesResponse {
  capabilities: string[];
  count: number;
}

export interface ListAppsParams {
  category?: string;
  limit?: number;
}

export interface HealthResponse {
  status: string;
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
