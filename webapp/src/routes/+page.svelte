<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		runs,
		runsTotal,
		runsLoading,
		runsError,
		statusFilter,
		startPolling,
		stopPolling,
		loadRuns
	} from '$lib/stores';
	import type { RunStatus } from '$lib/types';
	import { StatusDistribution, PassFailGauge, SummaryStats } from '$lib/components/charts';

	const statuses: (RunStatus | null)[] = [null, 'pending', 'running', 'completed', 'cancelled', 'failed'];

	$: statusCounts = $runs.reduce(
		(acc, run) => {
			acc[run.status] = (acc[run.status] || 0) + 1;
			return acc;
		},
		{ pending: 0, running: 0, completed: 0, cancelled: 0, failed: 0 } as Record<RunStatus, number>
	);

	$: passFailCounts = $runs.reduce(
		(acc, run) => {
			if (run.passed === true) acc.passed++;
			else if (run.passed === false) acc.failed++;
			return acc;
		},
		{ passed: 0, failed: 0 }
	);

	function setFilter(status: RunStatus | null) {
		statusFilter.set(status);
		loadRuns();
	}

	function getStatusClass(status: RunStatus): string {
		return `status-${status}`;
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	onMount(() => {
		startPolling(3000);
	});

	onDestroy(() => {
		stopPolling();
	});
</script>

<svelte:head>
	<title>Dashboard | API Test Machine</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold">Dashboard</h1>
		<a href="/new" class="btn btn-primary">New Test</a>
	</div>

	<!-- Summary Stats -->
	<SummaryStats {statusCounts} passed={passFailCounts.passed} failed={passFailCounts.failed} />

	<!-- Charts Row -->
	{#if $runs.length > 0}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div class="card flex flex-col items-center py-6">
				<h3 class="text-sm font-medium text-slate-400 mb-4">Status Distribution</h3>
				<StatusDistribution {statusCounts} />
			</div>
			<div class="card flex flex-col items-center py-6">
				<h3 class="text-sm font-medium text-slate-400 mb-4">Pass/Fail Rate</h3>
				<PassFailGauge passed={passFailCounts.passed} failed={passFailCounts.failed} />
			</div>
		</div>
	{/if}

	<!-- Filters -->
	<div class="card">
		<div class="flex items-center gap-2 flex-wrap">
			<span class="text-slate-400 text-sm">Filter:</span>
			{#each statuses as status}
				<button
					on:click={() => setFilter(status)}
					class="px-3 py-1 rounded-full text-sm transition-colors {$statusFilter === status
						? 'bg-blue-600 text-white'
						: 'bg-slate-700 text-slate-300 hover:bg-slate-600'}"
				>
					{status || 'All'}
				</button>
			{/each}
		</div>
	</div>

	<!-- Error message -->
	{#if $runsError}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300">
			{$runsError}
		</div>
	{/if}

	<!-- Runs table -->
	<div class="card overflow-x-auto">
		{#if $runsLoading && $runs.length === 0}
			<div class="text-center py-8 text-slate-400">Loading...</div>
		{:else if $runs.length === 0}
			<div class="text-center py-8 text-slate-400">
				No test runs found.
				<a href="/new" class="text-blue-400 hover:underline">Create one?</a>
			</div>
		{:else}
			<table class="w-full">
				<thead>
					<tr class="text-left text-slate-400 text-sm border-b border-slate-700">
						<th class="pb-3 font-medium">Name</th>
						<th class="pb-3 font-medium">Status</th>
						<th class="pb-3 font-medium">Progress</th>
						<th class="pb-3 font-medium">Result</th>
						<th class="pb-3 font-medium">Started</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-700">
					{#each $runs as run}
						<tr class="hover:bg-slate-700/50">
							<td class="py-3">
								<a href="/runs/{run.id}" class="text-blue-400 hover:underline font-medium">
									{run.name}
								</a>
								<div class="text-xs text-slate-500 font-mono">{run.id.slice(0, 8)}...</div>
							</td>
							<td class="py-3">
								<span class="{getStatusClass(run.status)} font-medium capitalize">
									{run.status}
								</span>
							</td>
							<td class="py-3">
								<div class="flex items-center gap-2">
									<div class="w-24 bg-slate-700 rounded-full h-2">
										<div
											class="bg-blue-500 rounded-full h-2 transition-all"
											style="width: {(run.requests_completed / run.total_requests) * 100}%"
										></div>
									</div>
									<span class="text-sm text-slate-400">
										{run.requests_completed}/{run.total_requests}
									</span>
								</div>
							</td>
							<td class="py-3">
								{#if run.passed === true}
									<span class="text-green-400 font-medium">PASS</span>
								{:else if run.passed === false}
									<span class="text-red-400 font-medium">FAIL</span>
								{:else}
									<span class="text-slate-500">-</span>
								{/if}
							</td>
							<td class="py-3 text-sm text-slate-400">
								{formatDate(run.started_at)}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>

			<div class="mt-4 pt-4 border-t border-slate-700 text-sm text-slate-400">
				Showing {$runs.length} of {$runsTotal} runs
			</div>
		{/if}
	</div>
</div>
