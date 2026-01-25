<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { RequestSummary } from '$lib/types';

	export let requests: RequestSummary[];
	export let p50: number | undefined = undefined;
	export let p95: number | undefined = undefined;
	export let p99: number | undefined = undefined;

	let canvas: HTMLCanvasElement;
	let chart: any = null;

	$: sortedRequests = [...requests].sort((a, b) => a.request_number - b.request_number);

	$: chartData = {
		labels: sortedRequests.map((r) => `#${r.request_number}`),
		datasets: [
			{
				label: 'Latency (ms)',
				data: sortedRequests.map((r) => r.latency_ms),
				borderColor: sortedRequests.map((r) => (r.error ? '#ef4444' : '#60a5fa')),
				backgroundColor: sortedRequests.map((r) => (r.error ? '#ef444480' : '#60a5fa80')),
				pointRadius: 5,
				pointHoverRadius: 7,
				showLine: true,
				tension: 0.1,
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

		// Build annotation lines for percentiles
		const annotations: any = {};
		if (p50) {
			annotations.p50Line = {
				type: 'line',
				yMin: p50,
				yMax: p50,
				borderColor: '#22c55e',
				borderWidth: 2,
				borderDash: [5, 5],
				label: {
					display: true,
					content: `P50: ${p50.toFixed(0)}ms`,
					position: 'start',
					backgroundColor: '#22c55e',
					color: '#fff',
					font: { size: 10 }
				}
			};
		}
		if (p95) {
			annotations.p95Line = {
				type: 'line',
				yMin: p95,
				yMax: p95,
				borderColor: '#f59e0b',
				borderWidth: 2,
				borderDash: [5, 5],
				label: {
					display: true,
					content: `P95: ${p95.toFixed(0)}ms`,
					position: 'start',
					backgroundColor: '#f59e0b',
					color: '#fff',
					font: { size: 10 }
				}
			};
		}
		if (p99) {
			annotations.p99Line = {
				type: 'line',
				yMin: p99,
				yMax: p99,
				borderColor: '#ef4444',
				borderWidth: 2,
				borderDash: [5, 5],
				label: {
					display: true,
					content: `P99: ${p99.toFixed(0)}ms`,
					position: 'start',
					backgroundColor: '#ef4444',
					color: '#fff',
					font: { size: 10 }
				}
			};
		}

		chart = new Chart(canvas, {
			type: 'line',
			data: chartData,
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: {
					intersect: false,
					mode: 'index'
				},
				plugins: {
					legend: {
						display: false
					},
					tooltip: {
						callbacks: {
							title: function (context) {
								const idx = context[0].dataIndex;
								const req = sortedRequests[idx];
								return `Request #${req.request_number}`;
							},
							label: function (context) {
								const idx = context.dataIndex;
								const req = sortedRequests[idx];
								const lines = [`Latency: ${req.latency_ms.toFixed(2)}ms`];
								if (req.status_code) lines.push(`Status: ${req.status_code}`);
								if (req.error) lines.push(`Error: ${req.error}`);
								if (req.response_size_bytes)
									lines.push(`Size: ${(req.response_size_bytes / 1024).toFixed(1)}KB`);
								return lines;
							}
						}
					}
				},
				scales: {
					x: {
						display: true,
						title: {
							display: true,
							text: 'Request',
							color: '#94a3b8'
						},
						ticks: {
							color: '#94a3b8',
							maxTicksLimit: 10
						},
						grid: {
							color: '#334155'
						}
					},
					y: {
						display: true,
						title: {
							display: true,
							text: 'Latency (ms)',
							color: '#94a3b8'
						},
						ticks: {
							color: '#94a3b8'
						},
						grid: {
							color: '#334155'
						},
						beginAtZero: true
					}
				}
			}
		});
	}

	$: if (browser && canvas && requests) {
		if (chart) {
			chart.data = chartData;
			chart.update('none');
		} else {
			initChart();
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

<div class="w-full h-64">
	<canvas bind:this={canvas}></canvas>
</div>

<!-- Legend -->
<div class="mt-3 flex flex-wrap gap-4 text-xs justify-center">
	<div class="flex items-center gap-1">
		<div class="w-3 h-3 rounded-full bg-blue-400"></div>
		<span class="text-slate-400">Success</span>
	</div>
	<div class="flex items-center gap-1">
		<div class="w-3 h-3 rounded-full bg-red-400"></div>
		<span class="text-slate-400">Error</span>
	</div>
	{#if p50}
		<div class="flex items-center gap-1">
			<div class="w-4 h-0.5 bg-green-500"></div>
			<span class="text-slate-400">P50</span>
		</div>
	{/if}
	{#if p95}
		<div class="flex items-center gap-1">
			<div class="w-4 h-0.5 bg-amber-500"></div>
			<span class="text-slate-400">P95</span>
		</div>
	{/if}
	{#if p99}
		<div class="flex items-center gap-1">
			<div class="w-4 h-0.5 bg-red-500"></div>
			<span class="text-slate-400">P99</span>
		</div>
	{/if}
</div>
