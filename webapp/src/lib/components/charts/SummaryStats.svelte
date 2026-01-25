<script lang="ts">
	import type { RunStatus } from '$lib/types';

	export let statusCounts: Record<RunStatus, number>;
	export let passed: number;
	export let failed: number;

	$: totalRuns = Object.values(statusCounts).reduce((sum, count) => sum + count, 0);
	$: activeRuns = statusCounts['running'] || 0;
	$: completedRuns = statusCounts['completed'] || 0;
	$: totalWithResult = passed + failed;
	$: successRate = totalWithResult > 0 ? Math.round((passed / totalWithResult) * 100) : 0;
</script>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
	<div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
		<div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
			<svg
				class="w-4 h-4"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
				></path>
			</svg>
			Test Runs
		</div>
		<div class="text-2xl font-bold text-white">{totalRuns}</div>
	</div>

	<div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
		<div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
			<svg
				class="w-4 h-4 text-blue-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M13 10V3L4 14h7v7l9-11h-7z"
				></path>
			</svg>
			Active
		</div>
		<div class="text-2xl font-bold text-blue-400">{activeRuns}</div>
	</div>

	<div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
		<div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
			<svg
				class="w-4 h-4 text-green-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
				></path>
			</svg>
			Completed
		</div>
		<div class="text-2xl font-bold text-green-400">{completedRuns}</div>
	</div>

	<div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
		<div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
			<svg
				class="w-4 h-4"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
				></path>
			</svg>
			Success Rate
		</div>
		<div class="text-2xl font-bold {successRate >= 50 ? 'text-green-400' : 'text-red-400'}">
			{successRate}%
		</div>
	</div>
</div>
