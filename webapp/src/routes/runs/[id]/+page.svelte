<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import {
		currentRun,
		currentRunLoading,
		currentRunError,
		startRunPolling,
		stopRunPolling
	} from '$lib/stores';
	import { api } from '$lib/api';
	import type { RequestDetail } from '$lib/types';
	import { LatencyChart, ResponseTimeHistogram } from '$lib/components/charts';

	$: runId = $page.params.id;

	let cancelling = false;
	let rerunning = false;
	let selectedRequest: RequestDetail | null = null;
	let loadingRequest = false;

	async function cancelRun() {
		if (!$currentRun) return;
		cancelling = true;
		try {
			await api.cancelRun($currentRun.id);
		} catch (e) {
			console.error('Failed to cancel:', e);
		}
		cancelling = false;
	}

	async function rerunTest() {
		if (!$currentRun) return;
		rerunning = true;
		try {
			const response = await api.createRun({ spec: $currentRun.spec });
			// Navigate to the new run
			window.location.href = `/runs/${response.id}`;
		} catch (e) {
			console.error('Failed to re-run test:', e);
			rerunning = false;
		}
	}

	async function viewRequestDetail(requestNumber: number) {
		if (!runId) return;
		loadingRequest = true;
		showHtmlPreview = false;
		try {
			selectedRequest = await api.getRequestDetail(runId, requestNumber);
		} catch (e) {
			console.error('Failed to load request:', e);
		}
		loadingRequest = false;
	}

	function closeRequestDetail() {
		selectedRequest = null;
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	function getStatusClass(status: string): string {
		return `status-${status}`;
	}

	function formatBytes(bytes: number | null): string {
		if (bytes === null) return '-';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	}

	function formatJson(str: string | null): string {
		if (!str) return '';
		try {
			return JSON.stringify(JSON.parse(str), null, 2);
		} catch {
			return str;
		}
	}

	function isHtmlContent(body: string | null, headers: Record<string, string> | null): boolean {
		if (!body) return false;
		// Check content-type header
		if (headers) {
			const contentType = Object.entries(headers).find(([k]) => k.toLowerCase() === 'content-type')?.[1] || '';
			if (contentType.includes('text/html')) return true;
		}
		// Check if body starts with HTML doctype or common HTML tags
		const trimmed = body.trim().toLowerCase();
		return trimmed.startsWith('<!doctype html') || trimmed.startsWith('<html') || trimmed.startsWith('<!doctype');
	}

	let showHtmlPreview = false;

	onMount(() => {
		startRunPolling(runId);
	});

	onDestroy(() => {
		stopRunPolling();
	});

	// Stop polling when run is complete
	$: if ($currentRun && ['completed', 'cancelled', 'failed'].includes($currentRun.status)) {
		stopRunPolling();
	}
</script>

<svelte:head>
	<title>{$currentRun?.spec.name || 'Loading...'} | API Test Machine</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center gap-4">
		<a href="/" class="text-slate-400 hover:text-white">&larr; Back</a>
	</div>

	{#if $currentRunError}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300">
			{$currentRunError}
		</div>
	{/if}

	{#if $currentRunLoading && !$currentRun}
		<div class="card text-center py-8 text-slate-400">Loading...</div>
	{:else if $currentRun}
		{@const run = $currentRun}

		<!-- Header -->
		<div class="card">
			<div class="flex items-start justify-between">
				<div>
					<h1 class="text-2xl font-bold">{run.spec.name}</h1>
					<p class="text-sm text-slate-400 font-mono mt-1">{run.id}</p>
				</div>
				<div class="flex items-center gap-4">
					<span class="{getStatusClass(run.status)} text-lg font-bold capitalize">
						{run.status}
					</span>
					{#if run.status === 'running'}
						<button
							on:click={cancelRun}
							disabled={cancelling}
							class="btn btn-danger"
						>
							{cancelling ? 'Cancelling...' : 'Cancel'}
						</button>
					{:else}
						<button
							on:click={rerunTest}
							disabled={rerunning}
							class="btn btn-primary flex items-center gap-2"
						>
							{#if rerunning}
								<svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								Starting...
							{:else}
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
								</svg>
								Re-run Test
							{/if}
						</button>
					{/if}
				</div>
			</div>

			<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
				<div>
					<div class="text-slate-400 text-sm">Started</div>
					<div>{formatDate(run.started_at)}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Completed</div>
					<div>{formatDate(run.completed_at)}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">HTTP Requests</div>
					<div>{run.requests_completed} / {run.spec.total_requests}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Result</div>
					<div>
						{#if run.passed === true}
							<span class="text-green-400 font-bold">PASS</span>
						{:else if run.passed === false}
							<span class="text-red-400 font-bold">FAIL</span>
						{:else}
							<span class="text-slate-500">Pending</span>
						{/if}
					</div>
				</div>
			</div>

			<!-- Progress bar -->
			<div class="mt-4">
				<div class="w-full bg-slate-700 rounded-full h-3">
					<div
						class="bg-blue-500 rounded-full h-3 transition-all"
						style="width: {(run.requests_completed / run.spec.total_requests) * 100}%"
					></div>
				</div>
			</div>
		</div>

		<!-- Failure reasons -->
		{#if run.failure_reasons.length > 0}
			<div class="bg-red-900/30 border border-red-700 rounded-lg p-4">
				<h3 class="font-bold text-red-400 mb-2">Failure Reasons</h3>
				<ul class="list-disc list-inside text-red-300 space-y-1">
					{#each run.failure_reasons as reason}
						<li>{reason}</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Error message -->
		{#if run.error_message}
			<div class="bg-red-900/30 border border-red-700 rounded-lg p-4">
				<h3 class="font-bold text-red-400 mb-2">Error</h3>
				<p class="text-red-300">{run.error_message}</p>
			</div>
		{/if}

		<!-- Test Configuration -->
		<div class="card">
			<details class="group">
				<summary class="text-lg font-bold mb-4 cursor-pointer flex items-center justify-between">
					<span>Test Configuration</span>
					<svg class="w-5 h-5 text-slate-400 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
					</svg>
				</summary>

				<p class="text-sm text-slate-400 mb-4">
					This test run makes <strong class="text-white">{run.spec.total_requests} HTTP requests</strong> to the target URL
					with <strong class="text-white">{run.spec.concurrency} concurrent</strong> connections.
				</p>

				<div class="space-y-4 mt-4">
					<!-- Target Endpoint -->
					<div class="bg-slate-900 rounded-lg p-3">
						<div class="text-slate-400 text-xs mb-1">Target Endpoint</div>
						<div class="font-mono text-sm">
							<span class="text-blue-400 font-bold">{run.spec.method}</span>
							<span class="text-green-400 ml-2 break-all">{run.spec.url}</span>
						</div>
					</div>

					<!-- Load Settings -->
					<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
						<div class="bg-slate-900 rounded-lg p-3">
							<div class="text-slate-400 text-xs">Total Requests</div>
							<div class="font-bold text-lg">{run.spec.total_requests}</div>
						</div>
						<div class="bg-slate-900 rounded-lg p-3">
							<div class="text-slate-400 text-xs">Concurrency</div>
							<div class="font-bold text-lg">{run.spec.concurrency}</div>
						</div>
						<div class="bg-slate-900 rounded-lg p-3">
							<div class="text-slate-400 text-xs">Rate Limit</div>
							<div class="font-bold text-lg">{run.spec.requests_per_second || '∞'} <span class="text-xs font-normal text-slate-400">req/s</span></div>
						</div>
						<div class="bg-slate-900 rounded-lg p-3">
							<div class="text-slate-400 text-xs">Timeout</div>
							<div class="font-bold text-lg">{run.spec.timeout_seconds}<span class="text-xs font-normal text-slate-400">s</span></div>
						</div>
					</div>

					<!-- Headers -->
					{#if Object.keys(run.spec.headers).length > 0}
						<div>
							<h4 class="text-sm font-semibold text-slate-300 mb-2">Headers</h4>
							<div class="bg-slate-900 rounded-lg p-3 font-mono text-sm overflow-x-auto">
								{#each Object.entries(run.spec.headers) as [key, value]}
									<div class="flex">
										<span class="text-purple-400">{key}:</span>
										<span class="text-slate-300 ml-2">{value}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Body -->
					{#if run.spec.body}
						<div>
							<h4 class="text-sm font-semibold text-slate-300 mb-2">Request Body</h4>
							<pre class="bg-slate-900 rounded-lg p-3 font-mono text-sm overflow-x-auto text-green-400">{typeof run.spec.body === 'string' ? run.spec.body : JSON.stringify(run.spec.body, null, 2)}</pre>
						</div>
					{/if}

					<!-- Thresholds -->
					{#if run.spec.thresholds && Object.keys(run.spec.thresholds).length > 0}
						<div>
							<h4 class="text-sm font-semibold text-slate-300 mb-2">Pass/Fail Thresholds</h4>
							<div class="bg-slate-900 rounded-lg p-3 text-sm">
								<div class="grid grid-cols-2 gap-2">
									{#if run.spec.thresholds.max_latency_p50_ms}
										<div><span class="text-slate-400">Max P50 Latency:</span> <span class="text-yellow-400">{run.spec.thresholds.max_latency_p50_ms}ms</span></div>
									{/if}
									{#if run.spec.thresholds.max_latency_p95_ms}
										<div><span class="text-slate-400">Max P95 Latency:</span> <span class="text-yellow-400">{run.spec.thresholds.max_latency_p95_ms}ms</span></div>
									{/if}
									{#if run.spec.thresholds.max_latency_p99_ms}
										<div><span class="text-slate-400">Max P99 Latency:</span> <span class="text-yellow-400">{run.spec.thresholds.max_latency_p99_ms}ms</span></div>
									{/if}
									{#if run.spec.thresholds.max_error_rate !== undefined}
										<div><span class="text-slate-400">Max Error Rate:</span> <span class="text-yellow-400">{(run.spec.thresholds.max_error_rate * 100).toFixed(1)}%</span></div>
									{/if}
									{#if run.spec.thresholds.min_throughput_rps}
										<div><span class="text-slate-400">Min Throughput:</span> <span class="text-yellow-400">{run.spec.thresholds.min_throughput_rps} req/s</span></div>
									{/if}
								</div>
							</div>
						</div>
					{/if}

					<!-- Expected Status Codes -->
					{#if run.spec.expected_status_codes && run.spec.expected_status_codes.length > 0}
						<div>
							<h4 class="text-sm font-semibold text-slate-300 mb-2">Expected Status Codes</h4>
							<div class="flex flex-wrap gap-2">
								{#each run.spec.expected_status_codes as code}
									<span class="bg-slate-700 text-green-400 font-mono px-2 py-1 rounded">{code}</span>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Variables -->
					{#if run.spec.variables && Object.keys(run.spec.variables).length > 0}
						<div>
							<h4 class="text-sm font-semibold text-slate-300 mb-2">Variables</h4>
							<div class="bg-slate-900 rounded-lg p-3 font-mono text-sm">
								{#each Object.entries(run.spec.variables) as [key, value]}
									<div class="flex">
										<span class="text-cyan-400">${`{${key}}`}:</span>
										<span class="text-slate-300 ml-2">{value}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Full JSON -->
					<details class="mt-4">
						<summary class="text-sm text-slate-400 cursor-pointer hover:text-slate-300">View Raw JSON</summary>
						<pre class="bg-slate-900 rounded-lg p-3 font-mono text-xs overflow-x-auto mt-2 text-slate-300">{JSON.stringify(run.spec, null, 2)}</pre>
					</details>
				</div>
			</details>
		</div>

		<!-- Aggregated Results -->
		{#if run.metrics.total_requests > 0}
			<div class="card">
				<details class="group" open>
					<summary class="text-lg font-bold mb-4 cursor-pointer flex items-center justify-between">
						<span>Aggregated Results</span>
						<svg class="w-5 h-5 text-slate-400 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
						</svg>
					</summary>

					<p class="text-sm text-slate-400 mb-4">
						Summary metrics across all <strong class="text-white">{run.metrics.total_requests} HTTP requests</strong> in this test run.
					</p>

					<div class="space-y-4 mt-4">
						<!-- Summary Stats -->
						<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
							<div class="bg-slate-900 rounded-lg p-3 text-center">
								<div class="text-2xl font-bold">{run.metrics.total_requests}</div>
								<div class="text-xs text-slate-400">Total Requests</div>
							</div>
							<div class="bg-slate-900 rounded-lg p-3 text-center">
								<div class="text-2xl font-bold text-green-400">{run.metrics.successful_requests}</div>
								<div class="text-xs text-slate-400">Successful</div>
							</div>
							<div class="bg-slate-900 rounded-lg p-3 text-center">
								<div class="text-2xl font-bold text-red-400">{run.metrics.failed_requests}</div>
								<div class="text-xs text-slate-400">Failed</div>
							</div>
							<div class="bg-slate-900 rounded-lg p-3 text-center">
								<div class="text-2xl font-bold {run.metrics.error_rate && run.metrics.error_rate > 0.01 ? 'text-red-400' : 'text-green-400'}">
									{run.metrics.error_rate !== undefined ? (run.metrics.error_rate * 100).toFixed(2) : '0'}%
								</div>
								<div class="text-xs text-slate-400">Error Rate</div>
							</div>
						</div>

						<!-- Performance -->
						<div class="grid md:grid-cols-2 gap-4">
							<div class="bg-slate-900 rounded-lg p-4">
								<h4 class="text-sm font-semibold text-slate-300 mb-3">Performance</h4>
								<div class="space-y-2 text-sm">
									{#if run.metrics.requests_per_second}
										<div class="flex justify-between">
											<span class="text-slate-400">Throughput</span>
											<span class="font-mono">{run.metrics.requests_per_second.toFixed(2)} req/s</span>
										</div>
									{/if}
									{#if run.metrics.duration_seconds}
										<div class="flex justify-between">
											<span class="text-slate-400">Duration</span>
											<span class="font-mono">{run.metrics.duration_seconds.toFixed(3)}s</span>
										</div>
									{/if}
									{#if run.metrics.total_bytes_received}
										<div class="flex justify-between">
											<span class="text-slate-400">Bytes Received</span>
											<span class="font-mono">{(run.metrics.total_bytes_received / 1024).toFixed(2)} KB</span>
										</div>
									{/if}
								</div>
							</div>

							<div class="bg-slate-900 rounded-lg p-4">
								<h4 class="text-sm font-semibold text-slate-300 mb-3">Latency Percentiles</h4>
								<div class="space-y-2 text-sm">
									{#if run.metrics.latency_min_ms}
										<div class="flex justify-between">
											<span class="text-slate-400">Min</span>
											<span class="font-mono">{run.metrics.latency_min_ms.toFixed(2)}ms</span>
										</div>
									{/if}
									{#if run.metrics.latency_p50_ms}
										<div class="flex justify-between">
											<span class="text-slate-400">P50 (Median)</span>
											<span class="font-mono">{run.metrics.latency_p50_ms.toFixed(2)}ms</span>
										</div>
									{/if}
									{#if run.metrics.latency_p90_ms}
										<div class="flex justify-between">
											<span class="text-slate-400">P90</span>
											<span class="font-mono">{run.metrics.latency_p90_ms.toFixed(2)}ms</span>
										</div>
									{/if}
									{#if run.metrics.latency_p95_ms}
										<div class="flex justify-between">
											<span class="text-slate-400">P95</span>
											<span class="font-mono">{run.metrics.latency_p95_ms.toFixed(2)}ms</span>
										</div>
									{/if}
									{#if run.metrics.latency_p99_ms}
										<div class="flex justify-between">
											<span class="text-slate-400">P99</span>
											<span class="font-mono">{run.metrics.latency_p99_ms.toFixed(2)}ms</span>
										</div>
									{/if}
									{#if run.metrics.latency_max_ms}
										<div class="flex justify-between">
											<span class="text-slate-400">Max</span>
											<span class="font-mono">{run.metrics.latency_max_ms.toFixed(2)}ms</span>
										</div>
									{/if}
								</div>
							</div>
						</div>

						<!-- Status Codes -->
						{#if Object.keys(run.metrics.status_code_counts).length > 0}
							<div class="bg-slate-900 rounded-lg p-4">
								<h4 class="text-sm font-semibold text-slate-300 mb-3">Response Status Codes</h4>
								<div class="flex flex-wrap gap-3">
									{#each Object.entries(run.metrics.status_code_counts) as [code, count]}
										<div class="bg-slate-800 rounded-lg px-3 py-2 flex items-center gap-2">
											<span class="{parseInt(code) < 400 ? 'text-green-400' : 'text-red-400'} font-mono font-bold">
												{code}
											</span>
											<span class="text-slate-300">{count} requests</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Errors by Type -->
						{#if Object.keys(run.metrics.errors_by_type).length > 0}
							<div class="bg-red-900/20 border border-red-800 rounded-lg p-4">
								<h4 class="text-sm font-semibold text-red-400 mb-3">Errors by Type</h4>
								<div class="space-y-2">
									{#each Object.entries(run.metrics.errors_by_type) as [errorType, count]}
										<div class="flex justify-between text-sm">
											<span class="text-red-300 font-mono">{errorType}</span>
											<span class="text-red-400">{count}</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Full JSON -->
						<details class="mt-4">
							<summary class="text-sm text-slate-400 cursor-pointer hover:text-slate-300">View Raw JSON</summary>
							<pre class="bg-slate-900 rounded-lg p-3 font-mono text-xs overflow-x-auto mt-2 text-slate-300">{JSON.stringify(run.metrics, null, 2)}</pre>
						</details>
					</div>
				</details>
			</div>
		{/if}

		<!-- Latency Charts -->
		{#if run.sampled_requests && run.sampled_requests.length > 0}
			<div class="grid md:grid-cols-2 gap-6">
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Latency Over Requests</h3>
					<LatencyChart
						requests={run.sampled_requests}
						p50={run.metrics.latency_p50_ms}
						p95={run.metrics.latency_p95_ms}
						p99={run.metrics.latency_p99_ms}
					/>
				</div>
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Response Time Distribution</h3>
					<ResponseTimeHistogram requests={run.sampled_requests} />
					<div class="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
						<div class="bg-slate-900 rounded p-2">
							<div class="text-slate-400">Min</div>
							<div class="font-mono font-bold text-green-400">{run.metrics.latency_min_ms?.toFixed(0) || '-'}ms</div>
						</div>
						<div class="bg-slate-900 rounded p-2">
							<div class="text-slate-400">Mean</div>
							<div class="font-mono font-bold text-blue-400">{run.metrics.latency_mean_ms?.toFixed(0) || '-'}ms</div>
						</div>
						<div class="bg-slate-900 rounded p-2">
							<div class="text-slate-400">Max</div>
							<div class="font-mono font-bold text-red-400">{run.metrics.latency_max_ms?.toFixed(0) || '-'}ms</div>
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Individual HTTP Requests -->
		{#if run.sampled_requests && run.sampled_requests.length > 0}
			<div class="card">
				<details class="group" open>
					<summary class="text-lg font-bold mb-4 cursor-pointer flex items-center justify-between">
						<span>Individual HTTP Requests ({run.sampled_requests.length} of {run.spec.total_requests})</span>
						<svg class="w-5 h-5 text-slate-400 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
						</svg>
					</summary>

					<p class="text-sm text-slate-400 mb-4">
						Each row below is one HTTP request/response. Click "View Details" to see the full request and response data.
					</p>

					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-slate-400 border-b border-slate-700">
									<th class="pb-2 font-medium">#</th>
									<th class="pb-2 font-medium">Status</th>
									<th class="pb-2 font-medium">Latency</th>
									<th class="pb-2 font-medium">Size</th>
									<th class="pb-2 font-medium">Time</th>
									<th class="pb-2 font-medium">Action</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-700">
								{#each run.sampled_requests as req}
									<tr class="hover:bg-slate-700/50">
										<td class="py-2 font-mono text-slate-300">{req.request_number}</td>
										<td class="py-2">
											{#if req.error}
												<span class="text-red-400 font-medium">{req.error}</span>
											{:else if req.status_code}
												<span class="{req.status_code < 400 ? 'text-green-400' : 'text-red-400'} font-mono font-medium">
													{req.status_code}
												</span>
											{:else}
												<span class="text-slate-500">-</span>
											{/if}
										</td>
										<td class="py-2 font-mono text-slate-300">{req.latency_ms.toFixed(1)}ms</td>
										<td class="py-2 font-mono text-slate-300">{formatBytes(req.response_size_bytes)}</td>
										<td class="py-2 text-slate-400 text-xs">{new Date(req.timestamp).toLocaleTimeString()}</td>
										<td class="py-2">
											<button
												on:click={() => viewRequestDetail(req.request_number)}
												class="text-blue-400 hover:text-blue-300 text-xs font-medium"
											>
												View Details
											</button>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>

					<p class="mt-4 text-xs text-slate-500">
						Showing {run.sampled_requests.length} of {run.spec.total_requests} HTTP requests (first 20 + any failures are captured with full details).
					</p>
				</details>
			</div>
		{/if}
	{/if}
</div>

<!-- Request Detail Modal -->
{#if selectedRequest}
	<div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" on:click={closeRequestDetail} on:keydown={(e) => e.key === 'Escape' && closeRequestDetail()} role="dialog" tabindex="-1">
		<div class="bg-slate-800 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden" on:click|stopPropagation on:keydown|stopPropagation role="document">
			<!-- Modal Header -->
			<div class="flex items-center justify-between p-4 border-b border-slate-700">
				<h2 class="text-lg font-bold">
					Request #{selectedRequest.request_number}
					{#if selectedRequest.status_code}
						<span class="{selectedRequest.status_code < 400 ? 'text-green-400' : 'text-red-400'} ml-2">
							{selectedRequest.status_code}
						</span>
					{/if}
				</h2>
				<button on:click={closeRequestDetail} class="text-slate-400 hover:text-white">
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>

			<!-- Modal Content -->
			<div class="p-4 overflow-y-auto max-h-[calc(90vh-120px)] space-y-4">
				<!-- Summary -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
					<div class="bg-slate-900 rounded-lg p-3">
						<div class="text-slate-400 text-xs">Latency</div>
						<div class="font-mono font-bold">{selectedRequest.latency_ms.toFixed(2)}ms</div>
					</div>
					<div class="bg-slate-900 rounded-lg p-3">
						<div class="text-slate-400 text-xs">Response Size</div>
						<div class="font-mono font-bold">{formatBytes(selectedRequest.response_size_bytes)}</div>
					</div>
					<div class="bg-slate-900 rounded-lg p-3">
						<div class="text-slate-400 text-xs">Method</div>
						<div class="font-mono font-bold text-blue-400">{selectedRequest.request_method || '-'}</div>
					</div>
					<div class="bg-slate-900 rounded-lg p-3">
						<div class="text-slate-400 text-xs">Timestamp</div>
						<div class="font-mono text-xs">{new Date(selectedRequest.timestamp).toLocaleString()}</div>
					</div>
				</div>

				<!-- Error -->
				{#if selectedRequest.error}
					<div class="bg-red-900/30 border border-red-700 rounded-lg p-3">
						<div class="text-red-400 text-sm font-semibold mb-1">Error</div>
						<div class="text-red-300 font-mono text-sm">{selectedRequest.error}</div>
					</div>
				{/if}

				<!-- Request Section -->
				<div class="border border-slate-700 rounded-lg overflow-hidden">
					<div class="bg-slate-700 px-4 py-2 text-sm font-semibold flex items-center gap-2">
						<svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12"></path>
						</svg>
						Request
					</div>
					<div class="p-4 space-y-3">
						<!-- URL -->
						{#if selectedRequest.request_url}
							<div>
								<div class="text-slate-400 text-xs mb-1">URL</div>
								<div class="bg-slate-900 rounded p-2 font-mono text-sm break-all text-green-400">
									{selectedRequest.request_method} {selectedRequest.request_url}
								</div>
							</div>
						{/if}

						<!-- Request Headers -->
						{#if selectedRequest.request_headers && Object.keys(selectedRequest.request_headers).length > 0}
							<div>
								<div class="text-slate-400 text-xs mb-1">Headers</div>
								<div class="bg-slate-900 rounded p-2 font-mono text-xs overflow-x-auto">
									{#each Object.entries(selectedRequest.request_headers) as [key, value]}
										<div><span class="text-purple-400">{key}:</span> <span class="text-slate-300">{value}</span></div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Request Body -->
						{#if selectedRequest.request_body}
							<div>
								<div class="text-slate-400 text-xs mb-1">Body</div>
								<pre class="bg-slate-900 rounded p-2 font-mono text-xs overflow-x-auto text-yellow-400 whitespace-pre-wrap">{formatJson(selectedRequest.request_body)}</pre>
							</div>
						{/if}
					</div>
				</div>

				<!-- Response Section -->
				<div class="border border-slate-700 rounded-lg overflow-hidden">
					<div class="bg-slate-700 px-4 py-2 text-sm font-semibold flex items-center gap-2">
						<svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5m0 0l-5-5m5 5V6"></path>
						</svg>
						Response
						{#if selectedRequest.status_code}
							<span class="{selectedRequest.status_code < 400 ? 'text-green-400' : 'text-red-400'} font-mono">
								{selectedRequest.status_code}
							</span>
						{/if}
					</div>
					<div class="p-4 space-y-3">
						<!-- Response Headers -->
						{#if selectedRequest.response_headers && Object.keys(selectedRequest.response_headers).length > 0}
							<div>
								<div class="text-slate-400 text-xs mb-1">Headers</div>
								<div class="bg-slate-900 rounded p-2 font-mono text-xs overflow-x-auto max-h-40 overflow-y-auto">
									{#each Object.entries(selectedRequest.response_headers) as [key, value]}
										<div><span class="text-purple-400">{key}:</span> <span class="text-slate-300">{value}</span></div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Response Body -->
						{#if selectedRequest.response_body}
							<div>
								<div class="flex items-center justify-between mb-1">
									<span class="text-slate-400 text-xs">Body</span>
									{#if isHtmlContent(selectedRequest.response_body, selectedRequest.response_headers)}
										<button
											on:click={() => showHtmlPreview = !showHtmlPreview}
											class="text-xs text-blue-400 hover:text-blue-300"
										>
											{showHtmlPreview ? 'Show Raw' : 'Show HTML Preview'}
										</button>
									{/if}
								</div>
								{#if isHtmlContent(selectedRequest.response_body, selectedRequest.response_headers) && showHtmlPreview}
									<div class="bg-white rounded overflow-hidden">
										<iframe
											srcdoc={selectedRequest.response_body}
											class="w-full h-80 border-0"
											sandbox="allow-same-origin"
											title="HTML Preview"
										></iframe>
									</div>
								{:else}
									<pre class="bg-slate-900 rounded p-2 font-mono text-xs overflow-x-auto max-h-80 overflow-y-auto text-cyan-400 whitespace-pre-wrap">{formatJson(selectedRequest.response_body)}</pre>
								{/if}
							</div>
						{:else}
							<div class="text-slate-500 text-sm italic">No response body captured</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Modal Footer -->
			<div class="flex justify-end p-4 border-t border-slate-700">
				<button on:click={closeRequestDetail} class="btn bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg">
					Close
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Loading overlay for request detail -->
{#if loadingRequest}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-slate-800 rounded-lg p-6 flex items-center gap-3">
			<svg class="animate-spin h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
			</svg>
			<span>Loading request details...</span>
		</div>
	</div>
{/if}
