<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, colors } from '$lib/chartConfig';
	import type { RequestSummary } from '$lib/types';

	export let requests: RequestSummary[] = [];

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function hasData(reqs: RequestSummary[]): boolean {
		return reqs.length > 0;
	}

	function buildConfig(reqs: RequestSummary[]) {
		// Sort by request number
		const sorted = [...reqs].sort((a, b) => a.request_number - b.request_number);

		// Create data points with color based on success/error
		const dataPoints = sorted.map(r => ({
			x: r.request_number,
			y: r.latency_ms,
			status: r.status_code,
			error: r.error
		}));

		// Separate successful and failed requests
		const successPoints = dataPoints.filter(p => p.status && p.status >= 200 && p.status < 400 && !p.error);
		const errorPoints = dataPoints.filter(p => !p.status || p.status >= 400 || p.error);

		return {
			type: 'scatter' as const,
			data: {
				datasets: [
					{
						label: 'Successful',
						data: successPoints.map(p => ({ x: p.x, y: p.y })),
						backgroundColor: colors.green[500] + '80',
						borderColor: colors.green[500],
						pointRadius: 4,
						pointHoverRadius: 6
					},
					{
						label: 'Failed',
						data: errorPoints.map(p => ({ x: p.x, y: p.y })),
						backgroundColor: colors.red[500] + '80',
						borderColor: colors.red[500],
						pointRadius: 4,
						pointHoverRadius: 6
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						display: true,
						position: 'top' as const,
						labels: {
							color: colors.slate[300],
							usePointStyle: true,
							pointStyle: 'circle'
						}
					},
					tooltip: {
						backgroundColor: colors.slate[800],
						titleColor: colors.slate[100],
						bodyColor: colors.slate[300],
						borderColor: colors.slate[600],
						borderWidth: 1,
						callbacks: {
							title: function(context: { raw: { x: number } }[]) {
								return `Request #${context[0].raw.x}`;
							},
							label: function(context: { raw: { y: number }, dataset: { label: string } }) {
								return `${context.dataset.label}: ${context.raw.y.toFixed(1)} ms`;
							}
						}
					}
				},
				scales: {
					x: {
						title: {
							display: true,
							text: 'Request #',
							color: colors.slate[400]
						},
						ticks: {
							color: colors.slate[400]
						},
						grid: {
							color: colors.slate[700]
						}
					},
					y: {
						title: {
							display: true,
							text: 'Latency (ms)',
							color: colors.slate[400]
						},
						beginAtZero: true,
						ticks: {
							color: colors.slate[400],
							callback: function(value: number | string) {
								return `${value} ms`;
							}
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
		if (hasData(requests)) {
			chart = new Chart(canvas, buildConfig(requests));
		}
	});

	// Reactive update
	$: if (chart && hasData(requests)) {
		const config = buildConfig(requests);
		chart.data = config.data;
		chart.update('none');
	} else if (!chart && canvas && hasData(requests)) {
		chart = new Chart(canvas, buildConfig(requests));
	}

	onDestroy(() => {
		chart?.destroy();
	});
</script>

<div class="h-64">
	{#if hasData(requests)}
		<canvas bind:this={canvas}></canvas>
	{:else}
		<div class="h-full flex items-center justify-center text-slate-500">
			No request data
		</div>
	{/if}
</div>
