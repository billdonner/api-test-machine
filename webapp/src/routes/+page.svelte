<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { derived, writable } from 'svelte/store';
	import { goto } from '$app/navigation';
	import {
		runs,
		runsTotal,
		runsLoading,
		runsError,
		statusFilter,
		startPolling,
		stopPolling,
		loadRuns,
		testRepetitions
	} from '$lib/stores';
	import { api } from '$lib/api';
	import type { RunStatus, RunSummary, TestConfig } from '$lib/types';
	import RunsPerDayChart from '$lib/components/charts/RunsPerDayChart.svelte';

	const statuses: (RunStatus | null)[] = [null, 'pending', 'running', 'completed', 'cancelled', 'failed'];

	// Track which groups are expanded
	const expandedGroups = writable<Set<string>>(new Set());

	// Test configs for enabled/disabled status
	let testConfigs: Map<string, TestConfig> = new Map();
	let configsLoading = false;
	let runningAll = false;
	let enabledCount = 0;

	// Group runs by name
	interface RunGroup {
		name: string;
		runs: RunSummary[];
		latestRun: RunSummary;
		passCount: number;
		failCount: number;
		enabled: boolean;
	}

	const groupedRuns = derived(runs, ($runs) => {
		const groups = new Map<string, RunSummary[]>();
		for (const run of $runs) {
			const existing = groups.get(run.name) || [];
			existing.push(run);
			groups.set(run.name, existing);
		}

		const result: RunGroup[] = [];
		for (const [name, groupRuns] of groups) {
			// Sort by started_at descending
			groupRuns.sort((a, b) => {
				const aTime = a.started_at ? new Date(a.started_at).getTime() : 0;
				const bTime = b.started_at ? new Date(b.started_at).getTime() : 0;
				return bTime - aTime;
			});
			const config = testConfigs.get(name);
			result.push({
				name,
				runs: groupRuns,
				latestRun: groupRuns[0],
				passCount: groupRuns.filter(r => r.passed === true).length,
				failCount: groupRuns.filter(r => r.passed === false).length,
				enabled: config?.enabled ?? true
			});
		}
		// Sort groups by latest run time
		result.sort((a, b) => {
			const aTime = a.latestRun.started_at ? new Date(a.latestRun.started_at).getTime() : 0;
			const bTime = b.latestRun.started_at ? new Date(b.latestRun.started_at).getTime() : 0;
			return bTime - aTime;
		});
		// Update enabled count
		enabledCount = result.filter(g => g.enabled).length;
		return result;
	});

	// Compute stats from current runs
	const stats = derived(runs, ($runs) => {
		const running = $runs.filter((r) => r.status === 'running').length;
		const passed = $runs.filter((r) => r.passed === true).length;
		const failed = $runs.filter((r) => r.passed === false).length;
		return { running, passed, failed };
	});

	function toggleGroup(name: string) {
		expandedGroups.update(set => {
			const newSet = new Set(set);
			if (newSet.has(name)) {
				newSet.delete(name);
			} else {
				newSet.add(name);
			}
			return newSet;
		});
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

	async function rerunTest(run: RunSummary) {
		try {
			// Fetch full run details to get the spec
			const detail = await api.getRun(run.id);
			// Create new run with same spec
			const response = await api.createRun({ spec: detail.spec });
			// Navigate to the new run
			goto(`/runs/${response.id}`);
		} catch (e) {
			console.error('Failed to rerun:', e);
			alert('Failed to rerun test');
		}
	}

	async function deleteTest(run: RunSummary) {
		if (!confirm(`Delete "${run.name}"?`)) return;
		try {
			await api.deleteRun(run.id);
			loadRuns();
		} catch (e) {
			console.error('Failed to delete:', e);
			alert('Failed to delete test');
		}
	}

	async function deleteAllInGroup(group: RunGroup) {
		if (!confirm(`Delete all ${group.runs.length} runs of "${group.name}"?`)) return;
		try {
			for (const run of group.runs) {
				if (run.status !== 'running') {
					await api.deleteRun(run.id);
				}
			}
			loadRuns();
		} catch (e) {
			console.error('Failed to delete:', e);
			alert('Failed to delete tests');
		}
	}

	async function loadTestConfigs() {
		try {
			configsLoading = true;
			const response = await api.listTestConfigs();
			testConfigs = new Map(response.configs.map(c => [c.name, c]));
			// Trigger reactivity
			testConfigs = testConfigs;
		} catch (e) {
			console.error('Failed to load test configs:', e);
		} finally {
			configsLoading = false;
		}
	}

	async function syncTestConfigs() {
		try {
			configsLoading = true;
			const result = await api.syncTestConfigs();
			await loadTestConfigs();
			if (result.synced > 0) {
				alert(`Synced ${result.synced} test configuration(s) from existing runs.`);
			}
		} catch (e) {
			console.error('Failed to sync configs:', e);
			alert('Failed to sync test configurations');
		} finally {
			configsLoading = false;
		}
	}

	async function toggleTestEnabled(name: string, enabled: boolean) {
		try {
			await api.setTestEnabled(name, enabled);
			const config = testConfigs.get(name);
			if (config) {
				config.enabled = enabled;
				testConfigs = testConfigs; // Trigger reactivity
			}
		} catch (e) {
			console.error('Failed to toggle test:', e);
			alert('Failed to update test status');
		}
	}

	async function runAllEnabledTests() {
		if (enabledCount === 0) {
			alert('No tests are enabled. Enable some tests first.');
			return;
		}
		const reps = $testRepetitions;
		const totalRuns = enabledCount * reps;
		if (!confirm(`Run all ${enabledCount} enabled test(s)${reps > 1 ? ` x ${reps} repetitions = ${totalRuns} runs` : ''}?`)) return;

		try {
			runningAll = true;
			const response = await api.runAllEnabledTests(reps);
			// Store results in session storage for the batch page (can be viewed later)
			sessionStorage.setItem('batchResults', JSON.stringify(response));
			// Reload runs to show progress - dashboard will update via polling
			await loadRuns();
		} catch (e) {
			console.error('Failed to run all tests:', e);
			alert('Failed to run tests: ' + (e instanceof Error ? e.message : 'Unknown error'));
		} finally {
			runningAll = false;
		}
	}

	onMount(() => {
		startPolling(3000);
		loadTestConfigs();
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
		<div class="flex items-center gap-3">
			<button
				on:click={syncTestConfigs}
				disabled={configsLoading}
				class="text-slate-400 hover:text-white transition-colors disabled:opacity-50"
				title="Sync test configs from runs"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
				</svg>
			</button>
			<a href="/storage" class="text-slate-400 hover:text-white transition-colors" title="Storage Status">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
				</svg>
			</a>
			<button
				on:click={runAllEnabledTests}
				disabled={runningAll || enabledCount === 0}
				class="btn bg-green-600 hover:bg-green-500 text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
			>
				{#if runningAll}
					<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Running...
				{:else}
					Run All ({enabledCount})
				{/if}
			</button>
		</div>
	</div>

	<!-- Stats Overview -->
	<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
		<div class="card">
			<div class="text-slate-400 text-sm">Total Runs</div>
			<div class="text-3xl font-bold text-white">{$runsTotal}</div>
		</div>
		<div class="card">
			<div class="text-slate-400 text-sm">Running</div>
			<div class="text-3xl font-bold text-blue-400">{$stats.running}</div>
		</div>
		<div class="card">
			<div class="text-slate-400 text-sm">Passed</div>
			<div class="text-3xl font-bold text-green-400">{$stats.passed}</div>
		</div>
		<div class="card">
			<div class="text-slate-400 text-sm">Failed</div>
			<div class="text-3xl font-bold text-red-400">{$stats.failed}</div>
		</div>
	</div>

	<!-- Runs per Day Chart -->
	<div class="card">
		<h3 class="text-lg font-bold mb-4">Test Runs (Last 30 Days)</h3>
		<RunsPerDayChart runs={$runs} />
	</div>

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

	<!-- Runs table (grouped by name) -->
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
						<th class="pb-3 font-medium w-8"></th>
						<th class="pb-3 font-medium w-12" title="Enable/disable test for batch runs">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</th>
						<th class="pb-3 font-medium">Name</th>
						<th class="pb-3 font-medium">Runs</th>
						<th class="pb-3 font-medium">Latest Status</th>
						<th class="pb-3 font-medium">Pass/Fail</th>
						<th class="pb-3 font-medium">Last Run</th>
						<th class="pb-3 font-medium">Actions</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-700">
					{#each $groupedRuns as group (group.name)}
						<!-- Group header row -->
						<tr
							class="hover:bg-slate-700/50 cursor-pointer"
							role="button"
							tabindex="0"
							on:click={() => group.runs.length > 1 && toggleGroup(group.name)}
							on:keydown={(e) => e.key === 'Enter' && group.runs.length > 1 && toggleGroup(group.name)}
						>
							<td class="py-3 text-center">
								{#if group.runs.length > 1}
									<span class="text-slate-400">
										{$expandedGroups.has(group.name) ? '▼' : '▶'}
									</span>
								{/if}
							</td>
							<td class="py-3 text-center" on:click|stopPropagation on:keydown|stopPropagation>
								<input
									type="checkbox"
									checked={group.enabled}
									on:change={(e) => toggleTestEnabled(group.name, e.currentTarget.checked)}
									class="w-4 h-4 rounded border-slate-500 bg-slate-700 text-green-500 focus:ring-green-500 focus:ring-offset-slate-800 cursor-pointer"
									title={group.enabled ? 'Enabled for batch runs' : 'Disabled for batch runs'}
								/>
							</td>
							<td class="py-3">
								<a
									href="/runs/{group.latestRun.id}"
									class="text-blue-400 hover:underline font-medium"
									on:click|stopPropagation
								>
									{group.name}
								</a>
							</td>
							<td class="py-3">
								<span class="text-slate-300">{group.runs.length}</span>
							</td>
							<td class="py-3">
								<span class="{getStatusClass(group.latestRun.status)} font-medium capitalize">
									{group.latestRun.status}
								</span>
							</td>
							<td class="py-3">
								<span class="text-green-400">{group.passCount}</span>
								<span class="text-slate-500 mx-1">/</span>
								<span class="text-red-400">{group.failCount}</span>
							</td>
							<td class="py-3 text-sm text-slate-400">
								{formatDate(group.latestRun.started_at)}
							</td>
							<td class="py-3">
								<!-- svelte-ignore a11y-no-static-element-interactions -->
								<div class="flex items-center gap-2" on:click|stopPropagation on:keydown|stopPropagation>
									{#if group.latestRun.status !== 'running' && group.latestRun.status !== 'pending'}
										<button
											on:click={() => rerunTest(group.latestRun)}
											class="text-blue-400 hover:text-blue-300 text-sm"
											title="Rerun this test"
										>
											↻
										</button>
										<a
											href="/edit/{group.latestRun.id}"
											class="text-yellow-400 hover:text-yellow-300 text-sm"
											title="Edit test configuration"
										>
											✎
										</a>
										<button
											on:click={() => deleteAllInGroup(group)}
											class="text-red-400 hover:text-red-300 text-sm"
											title="Delete all runs with this name"
										>
											✕
										</button>
									{/if}
								</div>
							</td>
						</tr>
						<!-- Expanded runs -->
						{#if $expandedGroups.has(group.name)}
							{#each group.runs as run, i (run.id)}
								<tr class="bg-slate-800/50 hover:bg-slate-700/50">
									<td class="py-2"></td>
									<td class="py-2"></td>
									<td class="py-2 pl-4">
										<a href="/runs/{run.id}" class="text-blue-400/80 hover:underline text-sm">
											Run #{group.runs.length - i}
										</a>
										<span class="text-xs text-slate-500 font-mono ml-2">{run.id.slice(0, 8)}</span>
									</td>
									<td class="py-2"></td>
									<td class="py-2">
										<span class="{getStatusClass(run.status)} text-sm capitalize">
											{run.status}
										</span>
									</td>
									<td class="py-2">
										{#if run.passed === true}
											<span class="text-green-400 text-sm">PASS</span>
										{:else if run.passed === false}
											<span class="text-red-400 text-sm">FAIL</span>
										{:else}
											<span class="text-slate-500 text-sm">-</span>
										{/if}
									</td>
									<td class="py-2 text-sm text-slate-400">
										{formatDate(run.started_at)}
									</td>
									<td class="py-2">
										<div class="flex items-center gap-2">
											{#if run.status !== 'running' && run.status !== 'pending'}
												<button
													on:click={() => rerunTest(run)}
													class="text-blue-400/80 hover:text-blue-300 text-xs"
													title="Rerun"
												>
													↻
												</button>
											{/if}
											{#if run.status !== 'running'}
												<button
													on:click={() => deleteTest(run)}
													class="text-red-400/80 hover:text-red-300 text-xs"
													title="Delete"
												>
													✕
												</button>
											{/if}
										</div>
									</td>
								</tr>
							{/each}
						{/if}
					{/each}
				</tbody>
			</table>

			<div class="mt-4 pt-4 border-t border-slate-700 text-sm text-slate-400">
				Showing {$groupedRuns.length} test groups ({$runs.length} total runs)
			</div>
		{/if}
	</div>
</div>
