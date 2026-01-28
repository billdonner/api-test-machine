/**
 * API client for the Control API
 */

import type {
	BatchStartResponse,
	CreateRunRequest,
	CreateRunResponse,
	CreateScheduleRequest,
	HealthResponse,
	RequestDetail,
	RunDetail,
	RunListResponse,
	Schedule,
	ScheduleActionResponse,
	ScheduleListResponse,
	StorageStatus,
	TestConfigList
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

	async listTestConfigs(enabledOnly = false): Promise<TestConfigList> {
		const path = enabledOnly
			? '/api/v1/tests?enabled_only=true'
			: '/api/v1/tests';
		return this.request<TestConfigList>('GET', path);
	}

	async setTestEnabled(name: string, enabled: boolean): Promise<{ name: string; enabled: boolean; message: string }> {
		return this.request('POST', `/api/v1/tests/${encodeURIComponent(name)}/enabled`, { enabled });
	}

	async syncTestConfigs(): Promise<{ message: string; synced: number }> {
		return this.request('POST', '/api/v1/tests/sync');
	}

	async runAllEnabledTests(repetitions: number = 1, maxConcurrency: number = 0): Promise<BatchStartResponse> {
		return this.request<BatchStartResponse>('POST', '/api/v1/tests/run-all', {
			repetitions,
			max_concurrency: maxConcurrency
		});
	}

	// Schedule endpoints
	async listSchedules(): Promise<ScheduleListResponse> {
		return this.request<ScheduleListResponse>('GET', '/api/v1/schedules');
	}

	async getSchedule(id: string): Promise<Schedule> {
		return this.request<Schedule>('GET', `/api/v1/schedules/${id}`);
	}

	async createSchedule(request: CreateScheduleRequest): Promise<Schedule> {
		return this.request<Schedule>('POST', '/api/v1/schedules', request);
	}

	async deleteSchedule(id: string): Promise<ScheduleActionResponse> {
		return this.request<ScheduleActionResponse>('DELETE', `/api/v1/schedules/${id}`);
	}

	async pauseSchedule(id: string): Promise<ScheduleActionResponse> {
		return this.request<ScheduleActionResponse>('POST', `/api/v1/schedules/${id}/pause`);
	}

	async resumeSchedule(id: string): Promise<ScheduleActionResponse> {
		return this.request<ScheduleActionResponse>('POST', `/api/v1/schedules/${id}/resume`);
	}
}

export const api = new ApiClient();
