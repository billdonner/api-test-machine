<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { RunStatus } from '$lib/types';

	export let statusCounts: Record<RunStatus, number>;

	let canvas: HTMLCanvasElement;
	let chart: any = null;

	const statusColors: Record<RunStatus, string> = {
		pending: '#facc15',
		running: '#60a5fa',
		completed: '#4ade80',
		cancelled: '#facc15',
		failed: '#f87171'
	};

	const statusOrder: RunStatus[] = ['pending', 'running', 'completed', 'cancelled', 'failed'];

	$: total = Object.values(statusCounts).reduce((sum, count) => sum + count, 0);

	$: chartData = {
		labels: statusOrder.map((s) => s.charAt(0).toUpperCase() + s.slice(1)),
		datasets: [
			{
				data: statusOrder.map((s) => statusCounts[s] || 0),
				backgroundColor: statusOrder.map((s) => statusColors[s]),
				borderColor: '#1e293b',
				borderWidth: 2
			}
		]
	};

	async function initChart() {
		if (!browser || !canvas) return;

		const module = await import('chart.js/auto');
		const Chart = module.default;

		if (chart) {
			chart.destroy();
		}

		chart = new Chart(canvas, {
			type: 'doughnut',
			data: chartData,
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '65%',
				plugins: {
					legend: {
						display: false
					},
					tooltip: {
						callbacks: {
							label: function (context) {
								const value = context.raw as number;
								const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
								return `${context.label}: ${value} (${percentage}%)`;
							}
						}
					}
				}
			}
		});
	}

	$: if (browser && canvas && statusCounts) {
		if (chart) {
			chart.data = chartData;
			chart.update('none');
		}
	}

	onMount(() => {
		initChart();
	});

	onDestroy(() => {
		if (chart) {
			chart.destroy();
		}
	});
</script>

<div class="flex flex-col items-center">
	<div class="relative w-40 h-40">
		<canvas bind:this={canvas}></canvas>
		<div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
			<span class="text-2xl font-bold text-white">{total}</span>
			<span class="text-xs text-slate-400">total</span>
		</div>
	</div>
	<div class="mt-3 flex flex-wrap justify-center gap-2">
		{#each statusOrder as status}
			{#if statusCounts[status] > 0}
				<div class="flex items-center gap-1 text-xs">
					<div class="w-2 h-2 rounded-full" style="background-color: {statusColors[status]}"></div>
					<span class="text-slate-300 capitalize">{status}</span>
				</div>
			{/if}
		{/each}
	</div>
</div>
