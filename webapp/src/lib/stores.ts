/**
 * Svelte stores for state management
 */

import { writable, derived, type Readable } from 'svelte/store';
import { api } from './api';
import type { RunSummary, RunDetail, RunStatus } from './types';

// API key store
export const apiKey = writable<string | null>(
	typeof localStorage !== 'undefined' ? localStorage.getItem('atm_api_key') : null
);

// Update API client when key changes
apiKey.subscribe((key) => {
	api.setApiKey(key);
	if (typeof localStorage !== 'undefined') {
		if (key) {
			localStorage.setItem('atm_api_key', key);
		} else {
			localStorage.removeItem('atm_api_key');
		}
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

export async function loadRuns(limit = 50, offset = 0): Promise<void> {
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
