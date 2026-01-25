<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { RequestSummary } from '$lib/types';

	export let requests: RequestSummary[];

	let canvas: HTMLCanvasElement;
	let chart: any = null;

	// Create histogram buckets
	function createHistogram(data: number[], bucketCount = 10) {
		if (data.length === 0) return { labels: [], counts: [] };

		const min = Math.min(...data);
		const max = Math.max(...data);
		const range = max - min || 1;
		const bucketSize = range / bucketCount;

		const buckets = new Array(bucketCount).fill(0);
		const labels: string[] = [];

		for (let i = 0; i < bucketCount; i++) {
			const start = min + i * bucketSize;
			const end = min + (i + 1) * bucketSize;
			labels.push(`${start.toFixed(0)}-${end.toFixed(0)}`);
		}

		for (const value of data) {
			let bucketIndex = Math.floor((value - min) / bucketSize);
			if (bucketIndex >= bucketCount) bucketIndex = bucketCount - 1;
			buckets[bucketIndex]++;
		}

		return { labels, counts: buckets };
	}

	$: latencies = requests.map((r) => r.latency_ms);
	$: histogram = createHistogram(latencies, 8);

	$: chartData = {
		labels: histogram.labels,
		datasets: [
			{
				label: 'Requests',
				data: histogram.counts,
				backgroundColor: '#60a5fa80',
				borderColor: '#60a5fa',
				borderWidth: 1
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
			type: 'bar',
			data: chartData,
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						display: false
					},
					tooltip: {
						callbacks: {
							title: function (context) {
								return `${context[0].label}ms`;
							},
							label: function (context) {
								return `${context.raw} requests`;
							}
						}
					}
				},
				scales: {
					x: {
						display: true,
						title: {
							display: true,
							text: 'Latency (ms)',
							color: '#94a3b8'
						},
						ticks: {
							color: '#94a3b8',
							maxRotation: 45
						},
						grid: {
							display: false
						}
					},
					y: {
						display: true,
						title: {
							display: true,
							text: 'Count',
							color: '#94a3b8'
						},
						ticks: {
							color: '#94a3b8',
							stepSize: 1
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

<div class="w-full h-48">
	<canvas bind:this={canvas}></canvas>
</div>
