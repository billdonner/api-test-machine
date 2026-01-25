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
	import type { RunStatus, RunSummary } from '$lib/types';
	import { StatusDistribution, PassFailGauge, SummaryStats } from '$lib/components/charts';
	import { api } from '$lib/api';

	const statuses: (RunStatus | null)[] = [null, 'pending', 'running', 'completed', 'cancelled', 'failed'];

	// Track which test groups are expanded
	let expandedGroups: Set<string> = new Set();

	// Track re-running state
	let rerunningId: string | null = null;

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

	// Group runs by test name
	interface TestGroup {
		name: string;
		runs: RunSummary[];
		passCount: number;
		failCount: number;
		pendingCount: number;
		latestRun: RunSummary;
	}

	$: groupedRuns = (() => {
		const groups = new Map<string, TestGroup>();

		for (const run of $runs) {
			if (!groups.has(run.name)) {
				groups.set(run.name, {
					name: run.name,
					runs: [],
					passCount: 0,
					failCount: 0,
					pendingCount: 0,
					latestRun: run
				});
			}
			const group = groups.get(run.name)!;
			group.runs.push(run);

			if (run.passed === true) group.passCount++;
			else if (run.passed === false) group.failCount++;
			else group.pendingCount++;

			// Track latest run by start time
			if (run.started_at && (!group.latestRun.started_at || run.started_at > group.latestRun.started_at)) {
				group.latestRun = run;
			}
		}

		// Sort groups by latest run time
		return Array.from(groups.values()).sort((a, b) => {
			const aTime = a.latestRun.started_at || '';
			const bTime = b.latestRun.started_at || '';
			return bTime.localeCompare(aTime);
		});
	})();

	function toggleGroup(name: string) {
		if (expandedGroups.has(name)) {
			expandedGroups.delete(name);
		} else {
			expandedGroups.add(name);
		}
		expandedGroups = expandedGroups; // trigger reactivity
	}

	function getGroupTint(group: TestGroup): string {
		const total = group.passCount + group.failCount;
		if (total === 0) return 'border-slate-700 bg-slate-800/50';
		const passRate = group.passCount / total;
		if (passRate >= 0.8) return 'border-green-800/50 bg-green-900/20';
		if (passRate >= 0.5) return 'border-yellow-800/50 bg-yellow-900/20';
		return 'border-red-800/50 bg-red-900/20';
	}

	function getGroupIcon(group: TestGroup): { color: string; icon: string } {
		const total = group.passCount + group.failCount;
		if (total === 0) return { color: 'text-slate-400', icon: '○' };
		const passRate = group.passCount / total;
		if (passRate >= 0.8) return { color: 'text-green-400', icon: '✓' };
		if (passRate >= 0.5) return { color: 'text-yellow-400', icon: '◐' };
		return { color: 'text-red-400', icon: '✗' };
	}

	async function rerunTest(run: RunSummary) {
		rerunningId = run.id;
		try {
			// Fetch full run details to get the spec
			const detail = await api.getRun(run.id);
			const response = await api.createRun({ spec: detail.spec });
			window.location.href = `/runs/${response.id}`;
		} catch (e) {
			console.error('Failed to re-run test:', e);
			rerunningId = null;
		}
	}

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

	function formatRelativeTime(dateStr: string | undefined): string {
		if (!dateStr) return '-';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMins / 60);
		const diffDays = Math.floor(diffHours / 24);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		return `${diffDays}d ago`;
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
				<h3 class="text-sm font-medium text-slate-400 mb-4">Test Runs by Status</h3>
				<StatusDistribution {statusCounts} />
			</div>
			<div class="card flex flex-col items-center py-6">
				<h3 class="text-sm font-medium text-slate-400 mb-4">Test Run Pass/Fail Rate</h3>
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

	<!-- Grouped Test Runs -->
	<div class="space-y-3">
		{#if $runsLoading && $runs.length === 0}
			<div class="card text-center py-8 text-slate-400">Loading...</div>
		{:else if $runs.length === 0}
			<div class="card text-center py-8 text-slate-400">
				No test runs found.
				<a href="/new" class="text-blue-400 hover:underline">Create one?</a>
			</div>
		{:else}
			{#each groupedRuns as group}
				{@const isExpanded = expandedGroups.has(group.name)}
				{@const tint = getGroupTint(group)}
				{@const icon = getGroupIcon(group)}

				<div class="rounded-lg border {tint} overflow-hidden transition-colors">
					<!-- Group Header (Collapsed View) -->
					<button
						on:click={() => toggleGroup(group.name)}
						class="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
					>
						<div class="flex items-center gap-3">
							<!-- Expand/Collapse Icon -->
							<svg
								class="w-4 h-4 text-slate-400 transition-transform {isExpanded ? 'rotate-90' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
							</svg>

							<!-- Status Icon -->
							<span class="{icon.color} text-lg">{icon.icon}</span>

							<!-- Test Name -->
							<span class="font-medium text-white">{group.name}</span>

							<!-- Run Count Badge -->
							<span class="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
								{group.runs.length} run{group.runs.length !== 1 ? 's' : ''}
							</span>
						</div>

						<div class="flex items-center gap-4 text-sm">
							<!-- Pass/Fail Summary -->
							{#if group.passCount > 0 || group.failCount > 0}
								<div class="flex items-center gap-2">
									{#if group.passCount > 0}
										<span class="text-green-400">{group.passCount} ✓</span>
									{/if}
									{#if group.failCount > 0}
										<span class="text-red-400">{group.failCount} ✗</span>
									{/if}
									{#if group.pendingCount > 0}
										<span class="text-slate-400">{group.pendingCount} ○</span>
									{/if}
								</div>
							{/if}

							<!-- Latest Run Time -->
							<span class="text-slate-500 text-xs">
								{formatRelativeTime(group.latestRun.started_at)}
							</span>

							<!-- Quick Re-run Button (on collapsed) -->
							{#if !isExpanded}
								<button
									on:click|stopPropagation={() => rerunTest(group.latestRun)}
									disabled={rerunningId === group.latestRun.id}
									class="text-blue-400 hover:text-blue-300 p-1 rounded hover:bg-slate-700/50"
									title="Re-run latest"
								>
									{#if rerunningId === group.latestRun.id}
										<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
									{:else}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
										</svg>
									{/if}
								</button>
							{/if}
						</div>
					</button>

					<!-- Expanded Content -->
					{#if isExpanded}
						<div class="border-t border-slate-700/50">
							<table class="w-full">
								<thead>
									<tr class="text-left text-slate-400 text-xs border-b border-slate-700/50 bg-slate-800/30">
										<th class="px-4 py-2 font-medium">Run ID</th>
										<th class="px-4 py-2 font-medium">Status</th>
										<th class="px-4 py-2 font-medium">HTTP Requests</th>
										<th class="px-4 py-2 font-medium">Result</th>
										<th class="px-4 py-2 font-medium">Started</th>
										<th class="px-4 py-2 font-medium">Actions</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-slate-700/50">
									{#each group.runs as run}
										<tr class="hover:bg-slate-700/30">
											<td class="px-4 py-2">
												<a href="/runs/{run.id}" class="text-blue-400 hover:underline font-mono text-sm">
													{run.id.slice(0, 8)}...
												</a>
											</td>
											<td class="px-4 py-2">
												<span class="{getStatusClass(run.status)} font-medium capitalize text-sm">
													{run.status}
												</span>
											</td>
											<td class="px-4 py-2">
												<div class="flex items-center gap-2">
													<div class="w-16 bg-slate-700 rounded-full h-1.5">
														<div
															class="bg-blue-500 rounded-full h-1.5 transition-all"
															style="width: {(run.requests_completed / run.total_requests) * 100}%"
														></div>
													</div>
													<span class="text-xs text-slate-400">
														{run.requests_completed}/{run.total_requests}
													</span>
												</div>
											</td>
											<td class="px-4 py-2">
												{#if run.passed === true}
													<span class="text-green-400 font-medium text-sm">PASS</span>
												{:else if run.passed === false}
													<span class="text-red-400 font-medium text-sm">FAIL</span>
												{:else}
													<span class="text-slate-500 text-sm">-</span>
												{/if}
											</td>
											<td class="px-4 py-2 text-xs text-slate-400">
												{formatDate(run.started_at)}
											</td>
											<td class="px-4 py-2">
												<div class="flex items-center gap-2">
													<a
														href="/runs/{run.id}"
														class="text-slate-400 hover:text-white text-xs"
													>
														View
													</a>
													<button
														on:click={() => rerunTest(run)}
														disabled={rerunningId === run.id || run.status === 'running'}
														class="text-blue-400 hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 text-xs"
													>
														{#if rerunningId === run.id}
															<svg class="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
																<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
																<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
															</svg>
														{:else}
															<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
															</svg>
														{/if}
														Re-run
													</button>
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			{/each}

			<div class="text-sm text-slate-400 text-center pt-2">
				{groupedRuns.length} test type{groupedRuns.length !== 1 ? 's' : ''} · {$runs.length} of {$runsTotal} total runs
			</div>
		{/if}
	</div>
</div>
