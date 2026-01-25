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

export interface RequestSummary {
	request_number: number;
	status_code: number | null;
	latency_ms: number;
	error: string | null;
	timestamp: string;
	response_size_bytes: number | null;
}

export interface RequestDetail extends RequestSummary {
	request_url: string | null;
	request_method: string | null;
	request_headers: Record<string, string> | null;
	request_body: string | null;
	response_headers: Record<string, string> | null;
	response_body: string | null;
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
	sampled_requests: RequestSummary[];
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
