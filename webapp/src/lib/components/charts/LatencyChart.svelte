<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, colors, latencyColors } from '$lib/chartConfig';
	import type { Metrics } from '$lib/types';

	export let metrics: Metrics | null = null;

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;

	function hasData(m: Metrics | null): boolean {
		if (!m) return false;
		return (
			m.latency_min_ms !== undefined ||
			m.latency_p50_ms !== undefined ||
			m.latency_p90_ms !== undefined ||
			m.latency_p95_ms !== undefined ||
			m.latency_p99_ms !== undefined ||
			m.latency_max_ms !== undefined
		);
	}

	function buildConfig(m: Metrics) {
		const labels: string[] = [];
		const data: number[] = [];
		const bgColors: string[] = [];

		// Build data arrays in order
		const entries: [string, number | undefined, string][] = [
			['Min', m.latency_min_ms, latencyColors[0]],
			['P50', m.latency_p50_ms, latencyColors[1]],
			['P90', m.latency_p90_ms, latencyColors[2]],
			['P95', m.latency_p95_ms, latencyColors[3]],
			['P99', m.latency_p99_ms, latencyColors[4]],
			['Max', m.latency_max_ms, latencyColors[5]]
		];

		for (const [label, value, color] of entries) {
			if (value !== undefined && value !== null) {
				labels.push(label);
				data.push(value);
				bgColors.push(color);
			}
		}

		return {
			type: 'bar' as const,
			data: {
				labels,
				datasets: [
					{
						label: 'Latency (ms)',
						data,
						backgroundColor: bgColors,
						borderColor: bgColors.map((c) => c),
						borderWidth: 1,
						borderRadius: 4
					}
				]
			},
			options: {
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
							label: function (context: { raw: unknown }) {
								const value = context.raw as number;
								return `${value.toFixed(1)} ms`;
							}
						}
					}
				},
				scales: {
					x: {
						ticks: {
							color: colors.slate[400]
						},
						grid: {
							display: false
						}
					},
					y: {
						beginAtZero: true,
						ticks: {
							color: colors.slate[400],
							callback: function (value: number | string) {
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

<div class="h-64">
	{#if hasData(metrics)}
		<canvas bind:this={canvas}></canvas>
	{:else}
		<div class="h-full flex items-center justify-center text-slate-500">No latency data</div>
	{/if}
</div>
