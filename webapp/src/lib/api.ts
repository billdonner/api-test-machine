/**
 * API client for the Control API
 */

import type {
	CreateRunRequest,
	CreateRunResponse,
	HealthResponse,
	RequestDetail,
	RunDetail,
	RunListResponse,
	StorageStatus
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
	private apiKey: string | null = null;

	setApiKey(key: string | null) {
		this.apiKey = key;
	}

	private async request<T>(
		method: string,
		path: string,
		body?: unknown
	): Promise<T> {
		const headers: Record<string, string> = {
			'Content-Type': 'application/json'
		};

		if (this.apiKey) {
			headers['X-API-Key'] = this.apiKey;
		}

		const response = await fetch(`${API_BASE}${path}`, {
			method,
			headers,
			body: body ? JSON.stringify(body) : undefined
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`API error ${response.status}: ${error}`);
		}

		return response.json();
	}

	async health(): Promise<HealthResponse> {
		return this.request<HealthResponse>('GET', '/api/v1/health');
	}

	async listRuns(limit = 50, offset = 0, status?: string): Promise<RunListResponse> {
		let path = `/api/v1/runs?limit=${limit}&offset=${offset}`;
		if (status) {
			path += `&status=${status}`;
		}
		return this.request<RunListResponse>('GET', path);
	}

	async getRun(id: string): Promise<RunDetail> {
		return this.request<RunDetail>('GET', `/api/v1/runs/${id}`);
	}

	async createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
		return this.request<CreateRunResponse>('POST', '/api/v1/runs', request);
	}

	async cancelRun(id: string): Promise<{ id: string; status: string; message: string }> {
		return this.request('POST', `/api/v1/runs/${id}/cancel`);
	}

	async getRequestDetail(runId: string, requestNumber: number): Promise<RequestDetail> {
		return this.request<RequestDetail>('GET', `/api/v1/runs/${runId}/requests/${requestNumber}`);
	}

	async deleteRun(id: string): Promise<{ id: string; message: string }> {
		return this.request('DELETE', `/api/v1/runs/${id}`);
	}

	async getStorageStatus(): Promise<StorageStatus> {
		return this.request<StorageStatus>('GET', '/api/v1/storage/status');
	}
}

export const api = new ApiClient();
