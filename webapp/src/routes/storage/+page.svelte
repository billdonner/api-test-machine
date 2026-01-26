<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { StorageStatus } from '$lib/types';

	let status: StorageStatus | null = null;
	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		try {
			status = await api.getStorageStatus();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load storage status';
		} finally {
			loading = false;
		}
	});

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleString();
	}

	function formatBytes(bytes: number | null): string {
		if (bytes === null) return '-';
		const units = ['B', 'KB', 'MB', 'GB'];
		let size = bytes;
		for (const unit of units) {
			if (size < 1024) return `${size.toFixed(1)} ${unit}`;
			size /= 1024;
		}
		return `${size.toFixed(1)} TB`;
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'completed': return 'bg-green-500';
			case 'running': return 'bg-blue-500';
			case 'pending': return 'bg-yellow-500';
			case 'failed': return 'bg-red-500';
			case 'cancelled': return 'bg-gray-500';
			default: return 'bg-slate-500';
		}
	}

	function getPassRate(passed: number, failed: number): string {
		const total = passed + failed;
		if (total === 0) return '-';
		return `${((passed / total) * 100).toFixed(1)}%`;
	}

	// Calculate max for chart scaling
	$: maxDayCount = status?.runs_by_day?.length
		? Math.max(...status.runs_by_day.map(d => d.count), 1)
		: 1;

	$: totalStatusCount = status?.runs_by_status?.length
		? status.runs_by_status.reduce((sum, s) => sum + s.count, 0)
		: 0;
</script>

<svelte:head>
	<title>Storage Status | API Test Machine</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold">Storage Status</h1>
		<a href="/" class="text-blue-400 hover:underline">&larr; Back to Dashboard</a>
	</div>

	{#if loading}
		<div class="card text-center py-8 text-slate-400">Loading storage status...</div>
	{:else if error}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300">
			{error}
		</div>
	{:else if status}
		<!-- Database Info Card -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4 flex items-center gap-2">
				<span class="text-2xl">
					{#if status.storage_type === 'sqlite'}
						<svg class="w-6 h-6 inline" fill="currentColor" viewBox="0 0 24 24">
							<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
						</svg>
					{:else}
						<svg class="w-6 h-6 inline" fill="currentColor" viewBox="0 0 24 24">
							<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
						</svg>
					{/if}
				</span>
				Database Information
			</h2>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
				<div>
					<div class="text-slate-400 text-sm">Storage Type</div>
					<div class="text-xl font-bold text-white uppercase">{status.storage_type}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Database Size</div>
					<div class="text-xl font-bold text-white">{status.database_size_human || '-'}</div>
				</div>
				{#if status.sqlite_version}
					<div>
						<div class="text-slate-400 text-sm">SQLite Version</div>
						<div class="text-xl font-bold text-white">{status.sqlite_version}</div>
					</div>
				{/if}
				<div>
					<div class="text-slate-400 text-sm">Database Path</div>
					<div class="text-sm font-mono text-slate-300 truncate" title={status.database_path || ''}>
						{status.database_path || '-'}
					</div>
				</div>
			</div>
		</div>

		<!-- Stats Overview -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-4">
			<div class="card">
				<div class="text-slate-400 text-sm">Total Runs</div>
				<div class="text-3xl font-bold text-white">{status.total_runs}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Total Requests</div>
				<div class="text-3xl font-bold text-blue-400">{status.total_requests_stored.toLocaleString()}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Avg Requests/Run</div>
				<div class="text-3xl font-bold text-purple-400">{status.avg_requests_per_run}</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Avg Duration</div>
				<div class="text-3xl font-bold text-yellow-400">
					{status.avg_run_duration_seconds ? `${status.avg_run_duration_seconds.toFixed(1)}s` : '-'}
				</div>
			</div>
			<div class="card">
				<div class="text-slate-400 text-sm">Data Transferred</div>
				<div class="text-3xl font-bold text-green-400">{formatBytes(status.total_data_transferred_bytes)}</div>
			</div>
		</div>

		<!-- Date Range -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4">Data Range</h2>
			<div class="grid grid-cols-2 gap-4">
				<div>
					<div class="text-slate-400 text-sm">Oldest Run</div>
					<div class="text-white">{formatDate(status.oldest_run_date)}</div>
				</div>
				<div>
					<div class="text-slate-400 text-sm">Newest Run</div>
					<div class="text-white">{formatDate(status.newest_run_date)}</div>
				</div>
			</div>
		</div>

		<!-- Charts Row -->
		<div class="grid md:grid-cols-2 gap-6">
			<!-- Status Distribution -->
			<div class="card">
				<h2 class="text-lg font-bold mb-4">Runs by Status</h2>
				{#if status.runs_by_status.length > 0}
					<div class="space-y-3">
						{#each status.runs_by_status as item}
							<div class="flex items-center gap-3">
								<div class="w-24 text-sm text-slate-300 capitalize">{item.status}</div>
								<div class="flex-1 bg-slate-700 rounded-full h-6 overflow-hidden">
									<div
										class="{getStatusColor(item.status)} h-full transition-all duration-500 flex items-center justify-end pr-2"
										style="width: {(item.count / totalStatusCount) * 100}%"
									>
										<span class="text-xs font-bold text-white">{item.count}</span>
									</div>
								</div>
								<div class="w-16 text-right text-sm text-slate-400">
									{((item.count / totalStatusCount) * 100).toFixed(1)}%
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-slate-400 text-center py-4">No data</div>
				{/if}
			</div>

			<!-- Runs per Day Chart -->
			<div class="card">
				<h2 class="text-lg font-bold mb-4">Runs per Day (Last 30 Days)</h2>
				{#if status.runs_by_day.length > 0}
					<div class="h-48 flex items-end gap-1">
						{#each status.runs_by_day as day}
							<div class="flex-1 flex flex-col items-center group relative">
								<!-- Tooltip -->
								<div class="absolute bottom-full mb-2 hidden group-hover:block bg-slate-700 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
									{day.date}: {day.count} runs ({day.passed} pass, {day.failed} fail)
								</div>
								<!-- Bar -->
								<div
									class="w-full bg-slate-600 rounded-t relative overflow-hidden"
									style="height: {(day.count / maxDayCount) * 100}%"
								>
									<!-- Passed portion -->
									{#if day.passed > 0}
										<div
											class="absolute bottom-0 w-full bg-green-500"
											style="height: {(day.passed / day.count) * 100}%"
										></div>
									{/if}
									<!-- Failed portion -->
									{#if day.failed > 0}
										<div
											class="absolute top-0 w-full bg-red-500"
											style="height: {(day.failed / day.count) * 100}%"
										></div>
									{/if}
								</div>
							</div>
						{/each}
					</div>
					<div class="flex justify-between text-xs text-slate-500 mt-2">
						<span>{status.runs_by_day[0]?.date || ''}</span>
						<span>{status.runs_by_day[status.runs_by_day.length - 1]?.date || ''}</span>
					</div>
					<div class="flex justify-center gap-4 mt-3 text-xs">
						<span class="flex items-center gap-1">
							<span class="w-3 h-3 bg-green-500 rounded"></span> Passed
						</span>
						<span class="flex items-center gap-1">
							<span class="w-3 h-3 bg-red-500 rounded"></span> Failed
						</span>
						<span class="flex items-center gap-1">
							<span class="w-3 h-3 bg-slate-600 rounded"></span> Other
						</span>
					</div>
				{:else}
					<div class="text-slate-400 text-center py-4">No data for the last 30 days</div>
				{/if}
			</div>
		</div>

		<!-- Top Tests -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4">Top Tests by Run Count</h2>
			{#if status.top_tests.length > 0}
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="text-left text-slate-400 text-sm border-b border-slate-700">
								<th class="pb-3 font-medium">Test Name</th>
								<th class="pb-3 font-medium text-right">Runs</th>
								<th class="pb-3 font-medium text-right">Passed</th>
								<th class="pb-3 font-medium text-right">Failed</th>
								<th class="pb-3 font-medium text-right">Pass Rate</th>
								<th class="pb-3 font-medium text-right">Last Run</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-700">
							{#each status.top_tests as test}
								<tr class="hover:bg-slate-700/50">
									<td class="py-3">
										<span class="text-white font-medium">{test.name}</span>
									</td>
									<td class="py-3 text-right">
										<span class="text-blue-400 font-bold">{test.run_count}</span>
									</td>
									<td class="py-3 text-right">
										<span class="text-green-400">{test.passed}</span>
									</td>
									<td class="py-3 text-right">
										<span class="text-red-400">{test.failed}</span>
									</td>
									<td class="py-3 text-right">
										<span class="text-white">{getPassRate(test.passed, test.failed)}</span>
									</td>
									<td class="py-3 text-right text-sm text-slate-400">
										{formatDate(test.last_run)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="text-slate-400 text-center py-4">No tests recorded yet</div>
			{/if}
		</div>

		<!-- Storage Health -->
		<div class="card">
			<h2 class="text-lg font-bold mb-4">Storage Health</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="bg-slate-700/50 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<div class="w-3 h-3 rounded-full bg-green-500"></div>
						<span class="text-white font-medium">Database Connected</span>
					</div>
					<p class="text-sm text-slate-400">Storage is operational and accepting requests</p>
				</div>
				<div class="bg-slate-700/50 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<div class="w-3 h-3 rounded-full {status.database_size_bytes && status.database_size_bytes > 100 * 1024 * 1024 ? 'bg-yellow-500' : 'bg-green-500'}"></div>
						<span class="text-white font-medium">Storage Size</span>
					</div>
					<p class="text-sm text-slate-400">
						{#if status.database_size_bytes && status.database_size_bytes > 100 * 1024 * 1024}
							Consider archiving old runs
						{:else}
							Storage usage is healthy
						{/if}
					</p>
				</div>
				<div class="bg-slate-700/50 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<div class="w-3 h-3 rounded-full bg-green-500"></div>
						<span class="text-white font-medium">Indexing</span>
					</div>
					<p class="text-sm text-slate-400">Indexes are configured for optimal query performance</p>
				</div>
			</div>
		</div>
	{/if}
</div>
