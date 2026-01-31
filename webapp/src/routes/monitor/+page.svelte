<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { api } from '$lib/api';
	import type { SystemStatus, RunSummary, ActiveSchedule, ProcessStatus } from '$lib/types';

	let status: SystemStatus | null = null;
	let loading = true;
	let error: string | null = null;
	let polling = true;
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	let lastRefresh: Date | null = null;

	async function refresh() {
		try {
			status = await api.getSystemStatus();
			lastRefresh = new Date();
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load system status';
		} finally {
			loading = false;
		}
	}

	function startPolling() {
		if (pollInterval) clearInterval(pollInterval);
		pollInterval = setInterval(refresh, 3000);
	}

	function stopPolling() {
		if (pollInterval) {
			clearInterval(pollInterval);
			pollInterval = null;
		}
	}

	function togglePolling() {
		polling = !polling;
		if (polling) {
			startPolling();
		} else {
			stopPolling();
		}
	}

	onMount(async () => {
		await refresh();
		if (polling) startPolling();
	});

	onDestroy(() => {
		stopPolling();
	});

	function formatUptime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) {
			return `${hours}h ${minutes}m`;
		}
		return `${minutes}m`;
	}

	function formatTime(date: Date): string {
		return date.toLocaleTimeString();
	}

	function getProgressPercent(run: RunSummary): number {
		if (run.total_requests === 0) return 0;
		return (run.requests_completed / run.total_requests) * 100;
	}

	function formatNextRun(dateStr: string | null): string {
		if (!dateStr) return '-';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = date.getTime() - now.getTime();
		if (diffMs < 0) return 'Now';
		const diffMins = Math.floor(diffMs / 60000);
		if (diffMins < 60) return `In ${diffMins}m`;
		const diffHours = Math.floor(diffMins / 60);
		return `In ${diffHours}h ${diffMins % 60}m`;
	}
</script>

<svelte:head>
	<title>System Monitor | API Test Machine</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold">System Monitor</h1>
		<div class="flex items-center gap-4">
			<span class="text-sm text-slate-400">
				{#if lastRefresh}
					Last: {formatTime(lastRefresh)}
				{/if}
			</span>
			<button
				class="px-3 py-1 rounded text-sm {polling ? 'bg-green-600' : 'bg-slate-600'} hover:opacity-80"
				on:click={togglePolling}
			>
				{polling ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
			</button>
			<button
				class="px-3 py-1 rounded text-sm bg-blue-600 hover:bg-blue-700"
				on:click={refresh}
			>
				Refresh
			</button>
			<a href="/" class="text-blue-400 hover:underline">&larr; Dashboard</a>
		</div>
	</div>

	{#if loading}
		<div class="card text-center py-8 text-slate-400">Loading system status...</div>
	{:else if error}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300">
			{error}
		</div>
	{:else if status}
		<!-- Server Status & Process Grid -->
		<div class="grid md:grid-cols-2 gap-6">
			<!-- Server Status -->
			<div class="card">
				<h2 class="text-lg font-bold mb-4 flex items-center gap-2">
					<div class="w-3 h-3 rounded-full {status.server.online ? 'bg-green-500' : 'bg-red-500'}"></div>
					Server Status
				</h2>
				<div class="grid grid-cols-3 gap-4">
					<div>
						<div class="text-slate-400 text-sm">Status</div>
						<div class="text-xl font-bold {status.server.online ? 'text-green-400' : 'text-red-400'}">
							{status.server.online ? 'ONLINE' : 'OFFLINE'}
						</div>
					</div>
					<div>
						<div class="text-slate-400 text-sm">Version</div>
						<div class="text-xl font-bold text-cyan-400">{status.server.version}</div>
					</div>
					<div>
						<div class="text-slate-400 text-sm">Uptime</div>
						<div class="text-xl font-bold text-white">{formatUptime(status.server.uptime)}</div>
					</div>
				</div>
			</div>

			<!-- Process Status -->
			<div class="card">
				<h2 class="text-lg font-bold mb-4">Processes</h2>
				<div class="grid grid-cols-2 gap-3">
					{#each status.processes as process}
						<div class="bg-slate-700/50 rounded-lg p-3 flex items-center gap-3">
							<div class="w-3 h-3 rounded-full {process.running ? 'bg-green-500' : 'bg-red-500'}"></div>
							<div class="flex-1">
								<div class="text-white font-medium">{process.name}</div>
								<div class="text-sm text-slate-400">Port {process.port}</div>
							</div>
							<div class="text-sm {process.running ? 'text-green-400' : 'text-red-400'}">
								{process.running ? 'Running' : 'Stopped'}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<!-- Stats Summary -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-4">
			<div class="card">
				<div class="text-slate-400 text-sm">Total Runs</div>
				<div class="text-3xl font-bold text-cyan-400">{status.stats.total_runs}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Active</div>
				<div class="text-3xl font-bold text-yellow-400">{status.stats.active_runs}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Passed</div>
				<div class="text-3xl font-bold text-green-400">{status.stats.passed_runs}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Failed</div>
				<div class="text-3xl font-bold text-red-400">{status.stats.failed_runs}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Pass Rate</div>
				<div class="text-3xl font-bold text-white">{status.stats.pass_rate}%</div>
			</div>
		</div>

		<!-- Active Runs & Schedules -->
		<div class="grid md:grid-cols-2 gap-6">
			<!-- Active Runs -->
			<div class="card">
				<h2 class="text-lg font-bold mb-4">
					Active Runs ({status.active_runs.length})
				</h2>
				{#if status.active_runs.length === 0}
					<div class="text-slate-400 text-center py-4">No active runs</div>
				{:else}
					<div class="space-y-3">
						{#each status.active_runs as run}
							<a href="/runs/{run.id}" class="block bg-slate-700/50 rounded-lg p-3 hover:bg-slate-700">
								<div class="flex items-center justify-between mb-2">
									<span class="text-white font-medium truncate">{run.name}</span>
									<span class="text-xs px-2 py-1 rounded bg-yellow-500/20 text-yellow-400 uppercase">
										{run.status}
									</span>
								</div>
								<div class="flex items-center gap-2">
									<div class="flex-1 bg-slate-600 rounded-full h-2 overflow-hidden">
										<div
											class="h-full bg-blue-500 transition-all"
											style="width: {getProgressPercent(run)}%"
										></div>
									</div>
									<span class="text-sm text-slate-400">
										{run.requests_completed}/{run.total_requests}
									</span>
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Active Schedules -->
			<div class="card">
				<h2 class="text-lg font-bold mb-4">
					Active Schedules ({status.active_schedules.length})
				</h2>
				{#if status.active_schedules.length === 0}
					<div class="text-slate-400 text-center py-4">No active schedules</div>
				{:else}
					<div class="space-y-3">
						{#each status.active_schedules as schedule}
							<div class="bg-slate-700/50 rounded-lg p-3">
								<div class="flex items-center justify-between mb-1">
									<span class="text-white font-medium truncate">{schedule.name}</span>
									<span class="text-xs px-2 py-1 rounded bg-green-500/20 text-green-400">
										{schedule.trigger_type}
									</span>
								</div>
								<div class="flex items-center justify-between text-sm">
									<span class="text-slate-400">Test: {schedule.test_name}</span>
									<span class="text-slate-400">
										Runs: {schedule.run_count}{schedule.max_runs ? `/${schedule.max_runs}` : ''}
									</span>
								</div>
								<div class="text-sm text-blue-400 mt-1">
									Next: {formatNextRun(schedule.next_run_time)}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Quick Links -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4">Quick Actions</h2>
			<div class="flex flex-wrap gap-3">
				<a href="/" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white">
					Dashboard
				</a>
				<a href="/new" class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white">
					New Test
				</a>
				<a href="/schedules" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded text-white">
					Schedules
				</a>
				<a href="/storage" class="px-4 py-2 bg-slate-600 hover:bg-slate-700 rounded text-white">
					Storage Status
				</a>
			</div>
		</div>
	{/if}
</div>
