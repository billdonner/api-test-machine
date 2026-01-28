/**
 * Svelte stores for state management
 */

import { writable, derived, type Readable } from 'svelte/store';
import { api } from './api';
import type { RunSummary, RunDetail, RunStatus } from './types';

// Browser check helper
const isBrowser = typeof window !== 'undefined';

// API key store
export const apiKey = writable<string | null>(
	isBrowser ? window.localStorage.getItem('atm_api_key') : null
);

// Update API client when key changes
apiKey.subscribe((key) => {
	api.setApiKey(key);
	if (isBrowser) {
		if (key) {
			window.localStorage.setItem('atm_api_key', key);
		} else {
			window.localStorage.removeItem('atm_api_key');
		}
	}
});

// Test repetitions store (number of times to run each test, 0 = run once as specified)
const DEFAULT_REPETITIONS = 0;
export const testRepetitions = writable<number>(
	isBrowser ? parseInt(window.localStorage.getItem('atm_test_repetitions') || String(DEFAULT_REPETITIONS), 10) : DEFAULT_REPETITIONS
);

// Persist repetitions to localStorage
testRepetitions.subscribe((reps) => {
	if (isBrowser) {
		window.localStorage.setItem('atm_test_repetitions', String(reps));
	}
});

// Max concurrency store (0 = use test's specified concurrency)
const DEFAULT_MAX_CONCURRENCY = 0;
export const maxConcurrency = writable<number>(
	isBrowser ? parseInt(window.localStorage.getItem('atm_max_concurrency') || String(DEFAULT_MAX_CONCURRENCY), 10) : DEFAULT_MAX_CONCURRENCY
);

// Persist max concurrency to localStorage
maxConcurrency.subscribe((conc) => {
	if (isBrowser) {
		window.localStorage.setItem('atm_max_concurrency', String(conc));
	}
});

// Runs list store
export const runs = writable<RunSummary[]>([]);
export const runsTotal = writable<number>(0);
export const runsLoading = writable<boolean>(false);
export const runsError = writable<string | null>(null);

// Filter store
export const statusFilter = writable<RunStatus | null>(null);

// Poll interval store
let pollInterval: ReturnType<typeof setInterval> | null = null;

export async function loadRuns(limit = 200, offset = 0): Promise<void> {
	runsLoading.set(true);
	runsError.set(null);

	try {
		let status: string | undefined;
		statusFilter.subscribe((v) => (status = v ?? undefined))();

		const response = await api.listRuns(limit, offset, status);
		runs.set(response.runs);
		runsTotal.set(response.total);
	} catch (e) {
		runsError.set(e instanceof Error ? e.message : 'Failed to load runs');
	} finally {
		runsLoading.set(false);
	}
}

export function startPolling(intervalMs = 2000): void {
	stopPolling();
	loadRuns();
	pollInterval = setInterval(() => loadRuns(), intervalMs);
}

export function stopPolling(): void {
	if (pollInterval) {
		clearInterval(pollInterval);
		pollInterval = null;
	}
}

// Current run detail store
export const currentRun = writable<RunDetail | null>(null);
export const currentRunLoading = writable<boolean>(false);
export const currentRunError = writable<string | null>(null);

let runPollInterval: ReturnType<typeof setInterval> | null = null;

export async function loadRun(id: string): Promise<void> {
	currentRunLoading.set(true);
	currentRunError.set(null);

	try {
		const run = await api.getRun(id);
		currentRun.set(run);
	} catch (e) {
		currentRunError.set(e instanceof Error ? e.message : 'Failed to load run');
	} finally {
		currentRunLoading.set(false);
	}
}

export function startRunPolling(id: string, intervalMs = 1000): void {
	stopRunPolling();
	loadRun(id);
	runPollInterval = setInterval(() => loadRun(id), intervalMs);
}

export function stopRunPolling(): void {
	if (runPollInterval) {
		clearInterval(runPollInterval);
		runPollInterval = null;
	}
}

// Currently running test name (for display)
export const currentlyRunningTest = writable<string | null>(null);

// Health check
export const apiHealthy = writable<boolean | null>(null);

export async function checkHealth(): Promise<void> {
	try {
		await api.health();
		apiHealthy.set(true);
	} catch {
		apiHealthy.set(false);
	}
}
