<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, colors, getStatusCodeColor } from '$lib/chartConfig';
	import type { Metrics } from '$lib/types';

	export let metrics: Metrics | null = null;

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function hasData(m: Metrics | null): boolean {
		if (!m) return false;
		return Object.keys(m.status_code_counts).length > 0;
	}

	function getStatusText(code: number): string {
		const statusTexts: Record<number, string> = {
			200: 'OK',
			201: 'Created',
			204: 'No Content',
			301: 'Moved Permanently',
			302: 'Found',
			304: 'Not Modified',
			400: 'Bad Request',
			401: 'Unauthorized',
			403: 'Forbidden',
			404: 'Not Found',
			405: 'Method Not Allowed',
			408: 'Request Timeout',
			429: 'Too Many Requests',
			500: 'Internal Server Error',
			502: 'Bad Gateway',
			503: 'Service Unavailable',
			504: 'Gateway Timeout'
		};
		return statusTexts[code] || '';
	}

	function buildConfig(m: Metrics) {
		// Sort status codes numerically
		const sortedCodes = Object.entries(m.status_code_counts)
			.map(([code, count]) => ({ code: parseInt(code), count }))
			.sort((a, b) => a.code - b.code);

		const labels = sortedCodes.map((e) => e.code.toString());
		const data = sortedCodes.map((e) => e.count);
		const bgColors = sortedCodes.map((e) => getStatusCodeColor(e.code));

		return {
			type: 'bar' as const,
			data: {
				labels,
				datasets: [
					{
						label: 'Count',
						data,
						backgroundColor: bgColors,
						borderColor: bgColors,
						borderWidth: 1,
						borderRadius: 4
					}
				]
			},
			options: {
				indexAxis: 'y' as const,
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						display: false
					},
					tooltip: {
						backgroundColor: colors.slate[800],
						titleColor: colors.slate[100],
						bodyColor: colors.slate[300],
						borderColor: colors.slate[600],
						borderWidth: 1,
						callbacks: {
							title: function (context: { label: string }[]) {
								const code = parseInt(context[0].label);
								const statusText = getStatusText(code);
								return `HTTP ${context[0].label} ${statusText}`;
							},
							label: function (context: { raw: unknown }) {
								const value = context.raw as number;
								return `${value} requests`;
							}
						}
					}
				},
				scales: {
					x: {
						beginAtZero: true,
						ticks: {
							color: colors.slate[400],
							stepSize: 1
						},
						grid: {
							color: colors.slate[700]
						}
					},
					y: {
						ticks: {
							color: colors.slate[400]
						},
						grid: {
							display: false
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

<div class="h-48">
	{#if hasData(metrics)}
		<canvas bind:this={canvas}></canvas>
	{:else}
		<div class="h-full flex items-center justify-center text-slate-500">
			No status code data
		</div>
	{/if}
</div>
