/**
 * TypeScript interfaces matching Python Pydantic models
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

export type RunStatus = 'pending' | 'running' | 'completed' | 'cancelled' | 'failed';

export interface Thresholds {
	max_latency_p50_ms?: number;
	max_latency_p95_ms?: number;
	max_latency_p99_ms?: number;
	max_error_rate?: number;
	min_throughput_rps?: number;
}

export interface TestSpec {
	name: string;
	description?: string;
	url: string;
	method: HttpMethod;
	headers: Record<string, string>;
	body?: string | Record<string, unknown>;
	total_requests: number;
	concurrency: number;
	requests_per_second?: number;
	timeout_seconds: number;
	thresholds: Thresholds;
	expected_status_codes: number[];
	variables: Record<string, string>;
}

export interface Metrics {
	total_requests: number;
	successful_requests: number;
	failed_requests: number;
	latency_min_ms?: number;
	latency_max_ms?: number;
	latency_mean_ms?: number;
	latency_p50_ms?: number;
	latency_p90_ms?: number;
	latency_p95_ms?: number;
	latency_p99_ms?: number;
	requests_per_second?: number;
	duration_seconds?: number;
	error_rate?: number;
	errors_by_type: Record<string, number>;
	status_code_counts: Record<number, number>;
	total_bytes_received: number;
}

export interface RunSummary {
	id: string;
	name: string;
	status: RunStatus;
	started_at?: string;
	completed_at?: string;
	total_requests: number;
	requests_completed: number;
	passed?: boolean;
}

export interface RunDetail {
	id: string;
	spec: TestSpec;
	status: RunStatus;
	started_at?: string;
	completed_at?: string;
	metrics: Metrics;
	passed?: boolean;
	failure_reasons: string[];
	requests_completed: number;
	error_message?: string;
}

export interface RunListResponse {
	runs: RunSummary[];
	total: number;
}

export interface CreateRunRequest {
	spec: Partial<TestSpec> & { name: string; url: string };
}

export interface CreateRunResponse {
	id: string;
	status: RunStatus;
	message: string;
}

export interface HealthResponse {
	status: string;
	version: string;
	timestamp: string;
}
