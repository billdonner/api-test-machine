<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, colors } from '$lib/chartConfig';
	import type { RunSummary } from '$lib/types';

	export let runs: RunSummary[] = [];

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function getLast30Days(): string[] {
		const days: string[] = [];
		const today = new Date();
		for (let i = 29; i >= 0; i--) {
			const date = new Date(today);
			date.setDate(date.getDate() - i);
			days.push(date.toISOString().split('T')[0]);
		}
		return days;
	}

	function countRunsByDay(runs: RunSummary[]): Map<string, { passed: number; failed: number; other: number }> {
		const counts = new Map<string, { passed: number; failed: number; other: number }>();

		for (const run of runs) {
			if (!run.started_at) continue;
			const day = run.started_at.split('T')[0];
			const existing = counts.get(day) || { passed: 0, failed: 0, other: 0 };

			if (run.passed === true) {
				existing.passed++;
			} else if (run.passed === false) {
				existing.failed++;
			} else {
				existing.other++;
			}
			counts.set(day, existing);
		}
		return counts;
	}

	function buildConfig(runs: RunSummary[]) {
		const days = getLast30Days();
		const counts = countRunsByDay(runs);

		const passedData = days.map(day => counts.get(day)?.passed || 0);
		const failedData = days.map(day => counts.get(day)?.failed || 0);
		const otherData = days.map(day => counts.get(day)?.other || 0);

		// Format labels to show just month/day
		const labels = days.map(day => {
			const date = new Date(day);
			return `${date.getMonth() + 1}/${date.getDate()}`;
		});

		return {
			type: 'bar' as const,
			data: {
				labels,
				datasets: [
					{
						label: 'Passed',
						data: passedData,
						backgroundColor: colors.green[500],
						borderRadius: 2
					},
					{
						label: 'Failed',
						data: failedData,
						backgroundColor: colors.red[500],
						borderRadius: 2
					},
					{
						label: 'Other',
						data: otherData,
						backgroundColor: colors.slate[500],
						borderRadius: 2
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						position: 'top' as const,
						labels: {
							color: colors.slate[300],
							usePointStyle: true,
							pointStyle: 'rect'
						}
					},
					tooltip: {
						backgroundColor: colors.slate[800],
						titleColor: colors.slate[100],
						bodyColor: colors.slate[300],
						borderColor: colors.slate[600],
						borderWidth: 1
					}
				},
				scales: {
					x: {
						stacked: true,
						ticks: {
							color: colors.slate[400],
							maxRotation: 45,
							minRotation: 45
						},
						grid: {
							display: false
						}
					},
					y: {
						stacked: true,
						beginAtZero: true,
						ticks: {
							color: colors.slate[400],
							stepSize: 1
						},
						grid: {
							color: colors.slate[700]
						}
					}
				}
			}
		};
	}

	onMount(() => {
		if (runs.length > 0) {
			chart = new Chart(canvas, buildConfig(runs));
		}
	});

	// Reactive update when runs change
	$: if (chart && runs) {
		const config = buildConfig(runs);
		chart.data = config.data;
		chart.update('none');
	} else if (!chart && canvas && runs.length > 0) {
		chart = new Chart(canvas, buildConfig(runs));
	}

	onDestroy(() => {
		chart?.destroy();
	});
</script>

<div class="h-48">
	{#if runs.length > 0}
		<canvas bind:this={canvas}></canvas>
	{:else}
		<div class="h-full flex items-center justify-center text-slate-500">No run data available</div>
	{/if}
</div>
