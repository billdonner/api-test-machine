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

	$: runId = $page.params.id;

	let cancelling = false;

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

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	function getStatusClass(status: string): string {
		return `status-${status}`;
	}

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

			<!-- Status codes -->
			{#if Object.keys(run.metrics.status_code_counts).length > 0}
				<div class="card">
					<h3 class="text-lg font-bold mb-4">Status Codes</h3>
					<div class="flex flex-wrap gap-3">
						{#each Object.entries(run.metrics.status_code_counts) as [code, count]}
							<div class="bg-slate-700 rounded-lg px-3 py-2">
								<span class="{parseInt(code) < 400 ? 'text-green-400' : 'text-red-400'} font-mono">
									{code}
								</span>
								<span class="text-slate-400 ml-2">{count}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/if}

		<!-- Test Configuration -->
		<div class="card">
			<h3 class="text-lg font-bold mb-4">Test Configuration</h3>
			<div class="grid md:grid-cols-2 gap-4 text-sm">
				<div>
					<span class="text-slate-400">URL:</span>
					<span class="ml-2 font-mono">{run.spec.url}</span>
				</div>
				<div>
					<span class="text-slate-400">Method:</span>
					<span class="ml-2">{run.spec.method}</span>
				</div>
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
