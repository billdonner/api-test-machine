<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		currentRun,
		currentRunLoading,
		currentRunError,
		startRunPolling,
		stopRunPolling
	} from '$lib/stores';
	import { api } from '$lib/api';
	import SuccessRateChart from '$lib/components/charts/SuccessRateChart.svelte';
	import LatencyChart from '$lib/components/charts/LatencyChart.svelte';
	import LatencyScatterChart from '$lib/components/charts/LatencyScatterChart.svelte';
	import RequestDetailViewer from '$lib/components/RequestDetailViewer.svelte';

	$: runId = $page.params.id;

	// Restart polling when runId changes (e.g., after rerun navigates to new run)
	$: if (runId) {
		startRunPolling(runId);
	}

	let cancelling = false;
	let rerunning = false;

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
			goto(`/runs/${response.id}`);
		} catch (e) {
			console.error('Failed to rerun:', e);
			alert('Failed to rerun test');
		}
		rerunning = false;
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	function getStatusClass(status: string): string {
		return `status-${status}`;
	}

	// Polling is started by the reactive statement above when runId changes

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
					<span class="{getStatusClass(run.status)} text-lg font-bold capitalize flex items-center gap-2">
						{#if run.status === 'running' || run.status === 'pending'}
							<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
						{/if}
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
								<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								Starting...
							{:else}
								↻ Rerun
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
					<div class="text-slate-400 text-sm">Progress</div>
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

		<!-- Metrics -->
		{#if run.metrics.total_requests > 0}
			<div class="grid md:grid-cols-2 gap-6">
				<!-- Throughput & Errors -->
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Summary</h3>
					<div class="space-y-3">
						<div class="flex justify-between">
							<span class="text-slate-400">Total Requests</span>
							<span>{run.metrics.total_requests}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-slate-400">Successful</span>
							<span class="text-green-400">{run.metrics.successful_requests}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-slate-400">Failed</span>
							<span class="text-red-400">{run.metrics.failed_requests}</span>
						</div>
						{#if run.metrics.error_rate !== null && run.metrics.error_rate !== undefined}
							<div class="flex justify-between">
								<span class="text-slate-400">Error Rate</span>
								<span class="{run.metrics.error_rate > 0.01 ? 'text-red-400' : 'text-green-400'}">
									{(run.metrics.error_rate * 100).toFixed(2)}%
								</span>
							</div>
						{/if}
						{#if run.metrics.requests_per_second}
							<div class="flex justify-between">
								<span class="text-slate-400">Throughput</span>
								<span>{run.metrics.requests_per_second.toFixed(1)} req/s</span>
							</div>
						{/if}
						{#if run.metrics.duration_seconds}
							<div class="flex justify-between">
								<span class="text-slate-400">Duration</span>
								<span>{run.metrics.duration_seconds.toFixed(2)}s</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Latency -->
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Latency</h3>
					<div class="space-y-3">
						{#if run.metrics.latency_min_ms}
							<div class="flex justify-between">
								<span class="text-slate-400">Min</span>
								<span>{run.metrics.latency_min_ms.toFixed(1)}ms</span>
							</div>
						{/if}
						{#if run.metrics.latency_p50_ms}
							<div class="flex justify-between">
								<span class="text-slate-400">P50</span>
								<span>{run.metrics.latency_p50_ms.toFixed(1)}ms</span>
							</div>
						{/if}
						{#if run.metrics.latency_p90_ms}
							<div class="flex justify-between">
								<span class="text-slate-400">P90</span>
								<span>{run.metrics.latency_p90_ms.toFixed(1)}ms</span>
							</div>
						{/if}
						{#if run.metrics.latency_p95_ms}
							<div class="flex justify-between">
								<span class="text-slate-400">P95</span>
								<span>{run.metrics.latency_p95_ms.toFixed(1)}ms</span>
							</div>
						{/if}
						{#if run.metrics.latency_p99_ms}
							<div class="flex justify-between">
								<span class="text-slate-400">P99</span>
								<span>{run.metrics.latency_p99_ms.toFixed(1)}ms</span>
							</div>
						{/if}
						{#if run.metrics.latency_max_ms}
							<div class="flex justify-between">
								<span class="text-slate-400">Max</span>
								<span>{run.metrics.latency_max_ms.toFixed(1)}ms</span>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Performance Charts -->
			<div class="grid md:grid-cols-3 gap-6">
				<!-- Success Rate Donut -->
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Success Rate</h3>
					<SuccessRateChart metrics={run.metrics} />
				</div>

				<!-- Latency Bar Chart -->
				<div class="card md:col-span-2">
					<h3 class="text-lg font-bold mb-4">Latency Distribution</h3>
					<LatencyChart metrics={run.metrics} />
				</div>
			</div>

			<!-- Latency scatter chart -->
			{#if run.sampled_requests && run.sampled_requests.length > 0}
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Request Latencies</h3>
					<LatencyScatterChart requests={run.sampled_requests} />
				</div>
			{/if}

			<!-- Per-endpoint metrics (for multi-endpoint tests) -->
			{#if run.endpoint_metrics && run.endpoint_metrics.length > 0}
				<details class="card" open>
					<summary class="text-lg font-bold cursor-pointer mb-4">
						Per-Endpoint Metrics ({run.endpoint_metrics.length} endpoints)
					</summary>
					<div class="space-y-4 mt-4">
						{#each run.endpoint_metrics as epMetrics}
							<div class="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
								<h4 class="font-medium text-blue-400 mb-3">{epMetrics.endpoint_name}</h4>
								<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
									<div>
										<div class="text-slate-400 text-xs">Requests</div>
										<div>{epMetrics.metrics.total_requests}</div>
									</div>
									<div>
										<div class="text-slate-400 text-xs">Success</div>
										<div class="text-green-400">{epMetrics.metrics.successful_requests}</div>
									</div>
									<div>
										<div class="text-slate-400 text-xs">Failed</div>
										<div class="text-red-400">{epMetrics.metrics.failed_requests}</div>
									</div>
									<div>
										<div class="text-slate-400 text-xs">Error Rate</div>
										<div class="{(epMetrics.metrics.error_rate || 0) > 0.01 ? 'text-red-400' : 'text-green-400'}">
											{((epMetrics.metrics.error_rate || 0) * 100).toFixed(2)}%
										</div>
									</div>
									{#if epMetrics.metrics.latency_p50_ms}
										<div>
											<div class="text-slate-400 text-xs">P50</div>
											<div>{epMetrics.metrics.latency_p50_ms.toFixed(1)}ms</div>
										</div>
									{/if}
									{#if epMetrics.metrics.latency_p95_ms}
										<div>
											<div class="text-slate-400 text-xs">P95</div>
											<div>{epMetrics.metrics.latency_p95_ms.toFixed(1)}ms</div>
										</div>
									{/if}
									{#if epMetrics.metrics.latency_p99_ms}
										<div>
											<div class="text-slate-400 text-xs">P99</div>
											<div>{epMetrics.metrics.latency_p99_ms.toFixed(1)}ms</div>
										</div>
									{/if}
									{#if epMetrics.metrics.requests_per_second}
										<div>
											<div class="text-slate-400 text-xs">Throughput</div>
											<div>{epMetrics.metrics.requests_per_second.toFixed(1)} req/s</div>
										</div>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</details>
			{/if}
		{/if}

		<!-- Request/Response Details -->
		{#if run.sampled_requests && run.sampled_requests.length > 0}
			<div class="card">
				<RequestDetailViewer runId={run.id} requests={run.sampled_requests} />
			</div>
		{/if}

		<!-- Test Configuration -->
		<div class="card">
			<h3 class="text-lg font-bold mb-4">Test Configuration</h3>
			<div class="grid md:grid-cols-2 gap-4 text-sm">
				{#if run.spec.endpoints && run.spec.endpoints.length > 0}
					<!-- Multi-endpoint configuration -->
					<div class="md:col-span-2">
						<span class="text-slate-400">Mode:</span>
						<span class="ml-2 text-blue-400">Multi-endpoint</span>
						<span class="ml-2 text-slate-500">({run.spec.distribution_strategy || 'round_robin'})</span>
					</div>
					<div class="md:col-span-2">
						<span class="text-slate-400 block mb-2">Endpoints:</span>
						<div class="space-y-2 pl-4">
							{#each run.spec.endpoints as ep}
								<div class="font-mono text-xs bg-slate-800/50 rounded p-2">
									<span class="text-blue-400">{ep.name}</span>
									<span class="text-slate-500 mx-2">|</span>
									<span class="text-yellow-400">{ep.method}</span>
									<span class="text-slate-400 ml-2">{ep.url}</span>
									{#if ep.weight > 1}
										<span class="text-slate-500 ml-2">(weight: {ep.weight})</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{:else}
					<!-- Single endpoint configuration -->
					<div>
						<span class="text-slate-400">URL:</span>
						<span class="ml-2 font-mono">{run.spec.url}</span>
					</div>
					<div>
						<span class="text-slate-400">Method:</span>
						<span class="ml-2">{run.spec.method}</span>
					</div>
				{/if}
				<div>
					<span class="text-slate-400">Total Requests:</span>
					<span class="ml-2">{run.spec.total_requests}</span>
				</div>
				<div>
					<span class="text-slate-400">Concurrency:</span>
					<span class="ml-2">{run.spec.concurrency}</span>
				</div>
				{#if run.spec.requests_per_second}
					<div>
						<span class="text-slate-400">Rate Limit:</span>
						<span class="ml-2">{run.spec.requests_per_second} req/s</span>
					</div>
				{/if}
				<div>
					<span class="text-slate-400">Timeout:</span>
					<span class="ml-2">{run.spec.timeout_seconds}s</span>
				</div>
			</div>
		</div>
	{/if}
</div>
