/**
 * Axiomeer JavaScript/TypeScript SDK
 * Main client for interacting with the Axiomeer API
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  AxiomeerConfig,
  AppListing,
  ShopRequest,
  ShopResult,
  ExecuteRequest,
  ExecutionResult,
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

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        return Promise.reject(this.handleError(error));
      }
    );
  }

  /**
   * Handle API errors and convert to appropriate exception types
   */
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
      case 429:
        const retryAfter = error.response.headers['retry-after'];
        return new RateLimitError(
          'Rate limit exceeded',
          retryAfter ? parseInt(retryAfter) : undefined
        );
      case 404:
        return new NotFoundError(detail);
      case 422:
        return new ValidationError(detail);
      default:
        return new AxiomeerError(`API error (${status}): ${detail}`);
    }
  }

  /**
   * Shop for a tool/API/dataset using natural language
   *
   * @param task Description of what you need
   * @param options Additional shopping options
   * @returns ShopResult with selected tool and alternatives
   *
   * @example
   * ```typescript
   * const result = await marketplace.shop('I need to send SMS messages');
   * console.log(result.selected_app.name);
   * ```
   */
  async shop(
    task: string,
    options: Omit<ShopRequest, 'task'> = {}
  ): Promise<ShopResult> {
    const request: ShopRequest = {
      task,
      required_capabilities: options.required_capabilities || [],
      excluded_providers: options.excluded_providers || [],
      max_cost_usd: options.max_cost_usd,
    };

    const response = await this.client.post<ShopResult>('/shop', request);
    return response.data;
  }

  /**
   * Execute a tool with given parameters
   *
   * @param appId Application/tool ID to execute
   * @param params Tool-specific parameters
   * @returns ExecutionResult with outcome
   *
   * @example
   * ```typescript
   * const result = await marketplace.execute('weather-api', {
   *   location: 'New York'
   * });
   * console.log(result.result);
   * ```
   */
  async execute(
    appId: string,
    params: Record<string, any> = {}
  ): Promise<ExecutionResult> {
    const request: ExecuteRequest = {
      app_id: appId,
      params,
    };

    const response = await this.client.post<ExecutionResult>(
      '/execute',
      request
    );

    const data = response.data;

    if (!data.success && data.error) {
      throw new ExecutionError(`Tool execution failed: ${data.error}`, data);
    }

    return data;
  }

  /**
   * Shop and execute in one call
   *
   * @param task Description of what you need
   * @param params Parameters to pass to the selected tool
   * @returns ExecutionResult
   *
   * @example
   * ```typescript
   * const result = await marketplace.shopAndExecute(
   *   'I need weather information',
   *   { location: 'Tokyo' }
   * );
   * ```
   */
  async shopAndExecute(
    task: string,
    params: Record<string, any> = {}
  ): Promise<ExecutionResult> {
    const shopResult = await this.shop(task);
    return this.execute(shopResult.selected_app.app_id, params);
  }

  /**
   * List available applications in the marketplace
   *
   * @param params Filtering parameters
   * @returns Array of AppListing objects
   *
   * @example
   * ```typescript
   * const apps = await marketplace.listApps({ category: 'weather', limit: 10 });
   * apps.forEach(app => console.log(app.name));
   * ```
   */
  async listApps(params: ListAppsParams = {}): Promise<AppListing[]> {
    const response = await this.client.get<{ apps: AppListing[] }>('/apps', {
      params: {
        category: params.category,
        search: params.search,
        limit: params.limit || 50,
      },
    });

    return response.data.apps;
  }

  /**
   * Check API health status
   *
   * @returns Health check response
   */
  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }
}
