/**
 * Axiomeer JavaScript/TypeScript SDK
 * Main client for interacting with the Axiomeer API
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  AxiomeerConfig,
  AppListing,
  ShopRequest,
  ShopResponse,
  ExecuteRequest,
  ExecuteResponse,
  WorkflowRequest,
  WorkflowResponse,
  CapabilitiesResponse,
  ListAppsParams,
  HealthResponse,
  AxiomeerError,
  AuthenticationError,
  RateLimitError,
  NotFoundError,
  ExecutionError,
  ValidationError,
} from './types';

export class AgentMarketplace {
  private apiKey: string;
  private client: AxiosInstance;

  /**
   * Create a new Axiomeer client
   *
   * @param config Configuration options
   * @example
   * ```typescript
   * const marketplace = new AgentMarketplace({
   *   apiKey: 'axm_your_key',
   *   baseUrl: 'http://localhost:8000'
   * });
   * ```
   */
  constructor(config: AxiomeerConfig = {}) {
    this.apiKey =
      config.apiKey ||
      process.env.AXIOMEER_API_KEY ||
      '';

    if (!this.apiKey) {
      throw new AxiomeerError(
        'API key required. Pass apiKey in config or set AXIOMEER_API_KEY environment variable.'
      );
    }

    const baseUrl = (
      config.baseUrl ||
      process.env.AXIOMEER_BASE_URL ||
      'http://localhost:8000'
    ).replace(/\/$/, '');

    this.client = axios.create({
      baseURL: baseUrl,
      timeout: config.timeout || 30000,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: AxiosError): Error {
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        return new AxiomeerError('Request timed out');
      }
      return new AxiomeerError(`Network error: ${error.message}`);
    }

    const status = error.response.status;
    const data: any = error.response.data;
    const detail = data?.detail || 'Unknown error';

    switch (status) {
      case 401:
        return new AuthenticationError();
      case 429: {
        const retryAfter = error.response.headers['retry-after'];
        return new RateLimitError(
          'Rate limit exceeded',
          retryAfter ? parseInt(retryAfter) : undefined
        );
      }
      case 404:
        return new NotFoundError(detail);
      case 422:
        return new ValidationError(detail);
      default:
        return new AxiomeerError(`API error (${status}): ${detail}`);
    }
  }

  /**
   * Shop for APIs using natural language
   *
   * @param task Description of what you need
   * @param options Additional shopping options
   * @returns ShopResponse with ranked recommendations
   *
   * @example
   * ```typescript
   * const result = await marketplace.shop('get weather in Tokyo');
   * console.log(result.recommendations[0].name);
   * ```
   */
  async shop(
    task: string,
    options: Omit<ShopRequest, 'task'> = {}
  ): Promise<ShopResponse> {
    const request: ShopRequest = {
      task,
      ...options,
    };
    const response = await this.client.post<ShopResponse>('/shop', request);
    return response.data;
  }

  /**
   * Execute an API with given parameters
   *
   * @param appId Application ID to execute
   * @param task Natural language task description
   * @param options Additional execute options (inputs, fallback_app_ids, etc.)
   * @returns ExecuteResponse with output
   *
   * @example
   * ```typescript
   * const result = await marketplace.execute('realtime_weather_agent', 'weather in NYC', {
   *   inputs: { lat: 40.7, lon: -74.0 }
   * });
   * console.log(result.output);
   * ```
   */
  async execute(
    appId: string,
    task: string,
    options: Omit<ExecuteRequest, 'app_id' | 'task'> = {}
  ): Promise<ExecuteResponse> {
    const request: ExecuteRequest = {
      app_id: appId,
      task,
      ...options,
    };

    const response = await this.client.post<ExecuteResponse>('/execute', request);
    const data = response.data;

    if (!data.ok && data.validation_errors?.length > 0) {
      throw new ExecutionError(
        `Tool execution failed: ${data.validation_errors.join(', ')}`,
        data
      );
    }

    return data;
  }

  /**
   * Shop and execute in one call — finds the best API and runs it
   *
   * @param task Natural language task description
   * @param inputs Parameters to pass to the selected API
   * @returns ExecuteResponse
   *
   * @example
   * ```typescript
   * const result = await marketplace.shopAndExecute(
   *   'get weather in Tokyo',
   *   { lat: 35.67, lon: 139.65 }
   * );
   * console.log(result.output);
   * ```
   */
  async shopAndExecute(
    task: string,
    inputs: Record<string, any> = {}
  ): Promise<ExecuteResponse> {
    const shopResult = await this.shop(task);
    if (shopResult.status === 'NO_MATCH' || shopResult.recommendations.length === 0) {
      throw new AxiomeerError(`No matching API found for task: "${task}"`);
    }
    const appId = shopResult.recommendations[0].app_id;
    return this.execute(appId, task, { inputs });
  }

  /**
   * Execute a multi-step workflow
   *
   * @param request WorkflowRequest with ordered steps
   * @returns WorkflowResponse with per-step results
   *
   * @example
   * ```typescript
   * const result = await marketplace.executeWorkflow({
   *   steps: [
   *     { app_id: 'realtime_weather_agent', task: 'weather in Tokyo', output_key: 'weather' },
   *     { app_id: 'wikipedia_agent', task: 'Tokyo climate', inputs: {} }
   *   ]
   * });
   * ```
   */
  async executeWorkflow(request: WorkflowRequest): Promise<WorkflowResponse> {
    const response = await this.client.post<WorkflowResponse>('/execute/workflow', request);
    return response.data;
  }

  /**
   * List available apps in the marketplace
   *
   * @param params Filtering parameters
   * @returns Array of AppListing objects
   */
  async listApps(params: ListAppsParams = {}): Promise<AppListing[]> {
    const response = await this.client.get<AppListing[]>('/apps', { params });
    return response.data;
  }

  /**
   * Get all unique capabilities available in the marketplace
   */
  async listCapabilities(): Promise<CapabilitiesResponse> {
    const response = await this.client.get<CapabilitiesResponse>('/capabilities');
    return response.data;
  }

  /**
   * Check API health status
   */
  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }
}
