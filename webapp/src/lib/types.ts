/**
 * TypeScript interfaces matching Python Pydantic models
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

export type RunStatus = 'pending' | 'running' | 'completed' | 'cancelled' | 'failed';

export type DistributionStrategy = 'round_robin' | 'weighted' | 'sequential';

export interface EndpointSpec {
	name: string;
	url: string;
	method: HttpMethod;
	headers: Record<string, string>;
	body?: string | Record<string, unknown>;
	weight: number;
	expected_status_codes: number[];
}

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
	// Multi-endpoint configuration
	endpoints?: EndpointSpec[];
	distribution_strategy?: DistributionStrategy;
	// Load configuration
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

export interface EndpointMetrics {
	endpoint_name: string;
	metrics: Metrics;
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
	endpoint_name?: string | null;
}

export interface RequestDetail extends RequestSummary {
	endpoint_name?: string | null;
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
	endpoint_metrics?: EndpointMetrics[];
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

// Storage status types
export interface RunsByDay {
	date: string;
	count: number;
	passed: number;
	failed: number;
}

export interface RunsByStatus {
	status: string;
	count: number;
}

export interface TopTest {
	name: string;
	run_count: number;
	passed: number;
	failed: number;
	last_run: string | null;
}

// Test config types
export interface TestConfig {
	name: string;
	enabled: boolean;
	spec: TestSpec;
	created_at: string | null;
	updated_at: string | null;
	run_count: number;
}

export interface TestConfigList {
	configs: TestConfig[];
	total: number;
}

// Batch run types
export interface BatchStartResponse {
	batch_id: string;
	total_tests: number;
	run_ids: string[];
	message: string;
}

export interface StorageStatus {
	storage_type: string;
	database_path: string | null;
	database_size_bytes: number | null;
	database_size_human: string | null;
	sqlite_version: string | null;
	total_runs: number;
	runs_by_status: RunsByStatus[];
	runs_by_day: RunsByDay[];
	total_requests_stored: number;
	avg_requests_per_run: number;
	oldest_run_date: string | null;
	newest_run_date: string | null;
	top_tests: TopTest[];
	avg_run_duration_seconds: number | null;
	total_data_transferred_bytes: number;
}

// Schedule types
export type TriggerType = 'interval' | 'cron' | 'date';

export interface IntervalTrigger {
	type: 'interval';
	seconds?: number;
	minutes?: number;
	hours?: number;
	days?: number;
}

export interface CronTrigger {
	type: 'cron';
	minute: string;
	hour: string;
	day: string;
	month: string;
	day_of_week: string;
	timezone: string;
}

export interface DateTrigger {
	type: 'date';
	run_date: string;
}

export type ScheduleTrigger = IntervalTrigger | CronTrigger | DateTrigger;

export interface Schedule {
	id: string;
	name: string;
	description: string | null;
	test_name: string;
	trigger_type: TriggerType;
	trigger: ScheduleTrigger;
	max_runs: number | null;
	run_count: number;
	enabled: boolean;
	paused: boolean;
	next_run_time: string | null;
	created_at: string;
	updated_at: string;
	tags: string[];
}

export interface ScheduleListResponse {
	schedules: Schedule[];
	total: number;
}

export interface CreateScheduleRequest {
	name: string;
	description?: string;
	test_name: string;
	spec?: Partial<TestSpec> & { name: string; url: string };
	trigger: ScheduleTrigger;
	max_runs?: number | null;
	enabled?: boolean;
	tags?: string[];
}

export interface ScheduleActionResponse {
	id: string;
	action: string;
	success: boolean;
	message: string;
}
