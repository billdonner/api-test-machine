<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';

	export let passed: number;
	export let failed: number;

	let canvas: HTMLCanvasElement;
	let chart: any = null;

	$: total = passed + failed;
	$: passPercentage = total > 0 ? Math.round((passed / total) * 100) : 0;

	$: chartData = {
		labels: ['Pass', 'Fail'],
		datasets: [
			{
				data: [passed, failed],
				backgroundColor: ['#22c55e', '#ef4444'],
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
				rotation: -90,
				circumference: 180,
				cutout: '70%',
				plugins: {
					legend: {
						display: false
					},
					tooltip: {
						callbacks: {
							label: function (context) {
								const value = context.raw as number;
								const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
								return `${context.label}: ${value} (${pct}%)`;
							}
						}
					}
				},
				animation: {
					animateRotate: true,
					duration: 800
				}
			}
		});
	}

	$: if (browser && canvas && (passed !== undefined || failed !== undefined)) {
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
	<div class="relative w-40 h-24">
		<canvas bind:this={canvas}></canvas>
		<div class="absolute inset-x-0 bottom-0 flex flex-col items-center pointer-events-none">
			<span class="text-2xl font-bold {passPercentage >= 50 ? 'text-green-400' : 'text-red-400'}">
				{passPercentage}%
			</span>
			<span class="text-xs text-slate-400">pass rate</span>
		</div>
	</div>
	<div class="mt-3 flex gap-4 text-xs">
		<div class="flex items-center gap-1">
			<div class="w-2 h-2 rounded-full bg-green-500"></div>
			<span class="text-slate-300">Pass: {passed}</span>
		</div>
		<div class="flex items-center gap-1">
			<div class="w-2 h-2 rounded-full bg-red-500"></div>
			<span class="text-slate-300">Fail: {failed}</span>
		</div>
	</div>
</div>
