<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { apiKey, apiHealthy, checkHealth, testRepetitions, maxConcurrency } from '$lib/stores';

	let showSettings = false;

	onMount(() => {
		checkHealth();
	});

	// Auto-save API key with debounce
	let keyTimeout: ReturnType<typeof setTimeout>;
	function onKeyChange(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		clearTimeout(keyTimeout);
		keyTimeout = setTimeout(() => {
			apiKey.set(value || null);
			checkHealth();
		}, 500);
	}
</script>

<div class="min-h-screen flex flex-col">
	<header class="bg-slate-800 border-b border-slate-700">
		<div class="container mx-auto px-4 py-3 flex items-center justify-between">
			<a href="/" class="text-xl font-bold text-white flex items-center gap-2">
				<span class="text-2xl">&#9889;</span>
				API Test Machine
			</a>

			<nav class="flex items-center gap-4">
				<a href="/schedules" class="text-slate-300 hover:text-white transition-colors">Schedules</a>
				<a href="/new" class="btn btn-primary">New Test</a>

				<button
					on:click={() => (showSettings = !showSettings)}
					class="text-slate-400 hover:text-white"
					title="Settings"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
						/>
					</svg>
				</button>

				<div class="flex items-center gap-2">
					{#if $apiHealthy === true}
						<span class="w-2 h-2 bg-green-500 rounded-full" title="API Connected"></span>
					{:else if $apiHealthy === false}
						<span class="w-2 h-2 bg-red-500 rounded-full" title="API Disconnected"></span>
					{:else}
						<span class="w-2 h-2 bg-yellow-500 rounded-full" title="Checking..."></span>
					{/if}
				</div>
			</nav>
		</div>

		{#if showSettings}
			<div class="container mx-auto px-4 py-4 border-t border-slate-700">
				<div class="flex flex-wrap gap-6 items-end">
					<div class="flex-1 min-w-[200px]">
						<label for="api-key-input" class="label">API Key</label>
						<input
							id="api-key-input"
							type="password"
							value={$apiKey || ''}
							on:input={onKeyChange}
							placeholder="Enter API key..."
							class="input w-full"
						/>
						<p class="text-xs text-slate-400 mt-1">Leave empty for dev mode</p>
					</div>
					<div class="w-28">
						<label for="reps-input" class="label">Repetitions</label>
						<input
							id="reps-input"
							type="number"
							min="0"
							max="100"
							value={$testRepetitions}
							on:input={(e) => testRepetitions.set(Math.max(0, Math.min(100, parseInt(e.currentTarget.value) || 0)))}
							class="input w-full"
						/>
						<p class="text-xs text-slate-400 mt-1">0 = as specified</p>
					</div>
					<div class="w-28">
						<label for="conc-input" class="label">Max Concurrency</label>
						<input
							id="conc-input"
							type="number"
							min="0"
							max="100"
							value={$maxConcurrency}
							on:input={(e) => maxConcurrency.set(Math.max(0, Math.min(100, parseInt(e.currentTarget.value) || 0)))}
							class="input w-full"
						/>
						<p class="text-xs text-slate-400 mt-1">0 = as specified</p>
					</div>
				</div>
			</div>
		{/if}
	</header>

	<main class="flex-1 container mx-auto px-4 py-6">
		<slot />
	</main>

	<footer class="bg-slate-800 border-t border-slate-700 py-4">
		<div class="container mx-auto px-4 text-center text-slate-400 text-sm">
			API Test Machine v0.1.0
		</div>
	</footer>
</div>
