<script lang="ts">
	import { page } from '$app/stores';
	import type { BatchRunResponse } from '$lib/types';

	// Get batch results from URL state (passed via navigation)
	let batchResults: BatchRunResponse | null = null;

	// Check for results in session storage
	import { onMount } from 'svelte';

	onMount(() => {
		const stored = sessionStorage.getItem('batchResults');
		if (stored) {
			batchResults = JSON.parse(stored);
		}
	});

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	function getStatusClass(status: string): string {
		switch (status) {
			case 'completed':
				return 'text-green-400';
			case 'running':
				return 'text-blue-400';
			case 'failed':
				return 'text-red-400';
			case 'cancelled':
				return 'text-yellow-400';
			default:
				return 'text-slate-400';
		}
	}

	function getPassedClass(passed: boolean | null): string {
		if (passed === true) return 'text-green-400';
		if (passed === false) return 'text-red-400';
		return 'text-slate-400';
	}
</script>

<svelte:head>
	<title>Batch Run Results | API Test Machine</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold">Batch Run Results</h1>
		<a href="/" class="text-blue-400 hover:underline">&larr; Back to Dashboard</a>
	</div>

	{#if !batchResults}
		<div class="card text-center py-8 text-slate-400">
			No batch results available. Run all enabled tests from the dashboard.
		</div>
	{:else}
		<!-- Summary Card -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4">Summary</h2>
			<div class="grid grid-cols-2 md:grid-cols-5 gap-4">
				<div>
					<div class="text-slate-400 text-sm">Total Tests</div>
					<div class="text-3xl font-bold text-white">{batchResults.total_tests}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Passed</div>
					<div class="text-3xl font-bold text-green-400">{batchResults.summary.passed || 0}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Failed</div>
					<div class="text-3xl font-bold text-red-400">{batchResults.summary.failed || 0}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Pass Rate</div>
					<div class="text-3xl font-bold text-blue-400">{batchResults.summary.pass_rate || 'N/A'}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Duration</div>
					<div class="text-3xl font-bold text-purple-400">
						{batchResults.summary.duration_seconds?.toFixed(1) || '-'}s
					</div>
				</div>
			</div>
			<div class="mt-4 text-sm text-slate-400">
				Batch ID: <span class="font-mono">{batchResults.batch_id}</span>
				<br />
				Started: {formatDate(batchResults.started_at)}
				<br />
				Completed: {formatDate(batchResults.completed_at)}
			</div>
		</div>

		<!-- Pass/Fail Visual -->
		{#if batchResults.results.length > 0}
			<div class="card">
				<h2 class="text-lg font-bold mb-4">Results Overview</h2>
				<div class="flex gap-1 flex-wrap">
					{#each batchResults.results as result}
						<a
							href="/runs/{result.run_id}"
							class="w-8 h-8 rounded flex items-center justify-center text-xs font-bold transition-transform hover:scale-110 {result.passed === true
								? 'bg-green-600 hover:bg-green-500'
								: result.passed === false
									? 'bg-red-600 hover:bg-red-500'
									: 'bg-slate-600 hover:bg-slate-500'}"
							title="{result.name}: {result.passed ? 'PASS' : 'FAIL'}"
						>
							{result.passed ? 'P' : 'F'}
						</a>
					{/each}
				</div>
				<div class="flex gap-4 mt-3 text-xs text-slate-400">
					<span class="flex items-center gap-1">
						<span class="w-3 h-3 bg-green-600 rounded"></span> Passed
					</span>
					<span class="flex items-center gap-1">
						<span class="w-3 h-3 bg-red-600 rounded"></span> Failed
					</span>
				</div>
			</div>
		{/if}

		<!-- Results Table -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4">Detailed Results</h2>
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="text-left text-slate-400 text-sm border-b border-slate-700">
							<th class="pb-3 font-medium">Test Name</th>
							<th class="pb-3 font-medium">Status</th>
							<th class="pb-3 font-medium">Result</th>
							<th class="pb-3 font-medium text-right">Requests</th>
							<th class="pb-3 font-medium text-right">P95 Latency</th>
							<th class="pb-3 font-medium">Actions</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-700">
						{#each batchResults.results as result}
							<tr class="hover:bg-slate-700/50">
								<td class="py-3">
									<span class="text-white font-medium">{result.name}</span>
									{#if result.error_message}
										<div class="text-xs text-red-400 mt-1 truncate max-w-xs" title={result.error_message}>
											{result.error_message}
										</div>
									{/if}
								</td>
								<td class="py-3">
									<span class="{getStatusClass(result.status)} capitalize">{result.status}</span>
								</td>
								<td class="py-3">
									<span class="{getPassedClass(result.passed)} font-bold">
										{result.passed === true ? 'PASS' : result.passed === false ? 'FAIL' : '-'}
									</span>
								</td>
								<td class="py-3 text-right text-slate-300">
									{result.requests_completed}/{result.total_requests}
								</td>
								<td class="py-3 text-right text-slate-300">
									{result.latency_p95_ms ? `${result.latency_p95_ms.toFixed(0)}ms` : '-'}
								</td>
								<td class="py-3">
									<a
										href="/runs/{result.run_id}"
										class="text-blue-400 hover:underline text-sm"
									>
										View Details
									</a>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
