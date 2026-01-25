<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, colors } from '$lib/chartConfig';
	import type { Metrics } from '$lib/types';

	export let metrics: Metrics | null = null;

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function hasData(m: Metrics | null): boolean {
		return m !== null && m.total_requests > 0;
	}

	function getSuccessRate(m: Metrics): number {
		if (m.total_requests === 0) return 0;
		return (m.successful_requests / m.total_requests) * 100;
	}

	function buildConfig(m: Metrics) {
		return {
			type: 'doughnut' as const,
			data: {
				labels: ['Success', 'Failed'],
				datasets: [
					{
						data: [m.successful_requests, m.failed_requests],
						backgroundColor: [colors.green[500], colors.red[500]],
						borderColor: [colors.green[400], colors.red[400]],
						borderWidth: 1,
						hoverOffset: 4
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '65%',
				plugins: {
					legend: {
						position: 'bottom' as const,
						labels: {
							color: colors.slate[300],
							padding: 16,
							usePointStyle: true
						}
					},
					tooltip: {
						backgroundColor: colors.slate[800],
						titleColor: colors.slate[100],
						bodyColor: colors.slate[300],
						borderColor: colors.slate[600],
						borderWidth: 1,
						callbacks: {
							label: function (context: { label?: string; raw: unknown }) {
								const total = m.total_requests;
								const value = context.raw as number;
								const percentage = ((value / total) * 100).toFixed(1);
								return `${context.label || ''}: ${value} (${percentage}%)`;
							}
						}
					}
				}
			}
		};
	}

	onMount(() => {
		if (metrics && hasData(metrics)) {
			chart = new Chart(canvas, buildConfig(metrics));
		}
	});

	// Reactive update for polling
	$: if (chart && metrics && hasData(metrics)) {
		const config = buildConfig(metrics);
		chart.data = config.data;
		chart.update('none');
	}

	onDestroy(() => {
		chart?.destroy();
	});
</script>

<div class="h-64 relative">
	{#if hasData(metrics)}
		<canvas bind:this={canvas}></canvas>
		<!-- Center overlay showing percentage -->
		{#if metrics}
			<div
				class="absolute inset-0 flex items-center justify-center pointer-events-none"
				style="margin-bottom: 32px;"
			>
				<div class="text-center">
					<div
						class="text-3xl font-bold {getSuccessRate(metrics) >= 95
							? 'text-green-400'
							: getSuccessRate(metrics) >= 80
								? 'text-yellow-400'
								: 'text-red-400'}"
					>
						{getSuccessRate(metrics).toFixed(1)}%
					</div>
					<div class="text-xs text-slate-400">Success</div>
				</div>
			</div>
		{/if}
	{:else}
		<div class="h-full flex items-center justify-center text-slate-500">No data available</div>
	{/if}
</div>
