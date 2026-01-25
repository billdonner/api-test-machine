<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { HttpMethod, TestSpec, DistributionStrategy, EndpointSpec } from '$lib/types';

	let name = '';
	let url = '';
	let method: HttpMethod = 'GET';
	let totalRequests = 100;
	let concurrency = 10;
	let requestsPerSecond: number | null = null;
	let timeoutSeconds = 30;
	let headersText = '';
	let bodyText = '';

	// Multi-endpoint mode
	let multiEndpointMode = false;
	let distributionStrategy: DistributionStrategy = 'round_robin';
	let endpoints: Array<{
		name: string;
		url: string;
		method: HttpMethod;
		weight: number;
		headersText: string;
		bodyText: string;
	}> = [];

	// Thresholds
	let maxLatencyP95: number | null = null;
	let maxErrorRate: number | null = null;

	let submitting = false;
	let error: string | null = null;
	let isEditing = false;

	const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
	const distributionStrategies: { value: DistributionStrategy; label: string; description: string }[] = [
		{ value: 'round_robin', label: 'Round Robin', description: 'Cycle through endpoints A, B, C, A, B, C...' },
		{ value: 'weighted', label: 'Weighted', description: 'Distribute based on weights' },
		{ value: 'sequential', label: 'Sequential', description: 'All requests to A, then B, then C' }
	];

	function addEndpoint() {
		endpoints = [...endpoints, {
			name: `Endpoint ${endpoints.length + 1}`,
			url: '',
			method: 'GET',
			weight: 1,
			headersText: '',
			bodyText: ''
		}];
	}

	function removeEndpoint(index: number) {
		endpoints = endpoints.filter((_, i) => i !== index);
	}

	function toggleMultiEndpointMode() {
		multiEndpointMode = !multiEndpointMode;
		if (multiEndpointMode && endpoints.length === 0) {
			// Initialize with one endpoint using current single URL values
			endpoints = [{
				name: 'Endpoint 1',
				url: url || '',
				method: method,
				weight: 1,
				headersText: headersText,
				bodyText: bodyText
			}];
		}
	}

	onMount(() => {
		// Check for spec in URL params (for editing)
		const specParam = $page.url.searchParams.get('spec');
		if (specParam) {
			try {
				const spec: TestSpec = JSON.parse(decodeURIComponent(specParam));
				isEditing = true;

				// Pre-fill form fields
				name = spec.name || '';
				url = spec.url || '';
				method = spec.method || 'GET';
				totalRequests = spec.total_requests || 100;
				concurrency = spec.concurrency || 10;
				requestsPerSecond = spec.requests_per_second || null;
				timeoutSeconds = spec.timeout_seconds || 30;

				if (spec.headers && Object.keys(spec.headers).length > 0) {
					headersText = JSON.stringify(spec.headers, null, 2);
				}
				if (spec.body) {
					if (typeof spec.body === 'string') {
						bodyText = spec.body;
					} else {
						bodyText = JSON.stringify(spec.body, null, 2);
					}
				}
				if (spec.thresholds) {
					maxLatencyP95 = spec.thresholds.max_latency_p95_ms || null;
					maxErrorRate = spec.thresholds.max_error_rate ? spec.thresholds.max_error_rate * 100 : null;
				}

				// Load multi-endpoint configuration
				if (spec.endpoints && spec.endpoints.length > 0) {
					multiEndpointMode = true;
					distributionStrategy = spec.distribution_strategy || 'round_robin';
					endpoints = spec.endpoints.map(ep => ({
						name: ep.name,
						url: ep.url,
						method: ep.method || 'GET',
						weight: ep.weight || 1,
						headersText: ep.headers && Object.keys(ep.headers).length > 0
							? JSON.stringify(ep.headers, null, 2)
							: '',
						bodyText: ep.body
							? (typeof ep.body === 'string' ? ep.body : JSON.stringify(ep.body, null, 2))
							: ''
					}));
				}
			} catch (e) {
				console.error('Failed to parse spec from URL:', e);
			}
		}
	});

	async function submit() {
		error = null;

		if (!name.trim()) {
			error = 'Name is required';
			return;
		}

		// Validation for single vs multi-endpoint mode
		if (multiEndpointMode) {
			if (endpoints.length === 0) {
				error = 'At least one endpoint is required';
				return;
			}
			for (let i = 0; i < endpoints.length; i++) {
				if (!endpoints[i].url.trim()) {
					error = `Endpoint ${i + 1}: URL is required`;
					return;
				}
				if (!endpoints[i].name.trim()) {
					error = `Endpoint ${i + 1}: Name is required`;
					return;
				}
			}
		} else {
			if (!url.trim()) {
				error = 'URL is required';
				return;
			}
		}

		submitting = true;

		try {
			// Build thresholds
			const thresholds: Record<string, number> = {};
			if (maxLatencyP95) thresholds.max_latency_p95_ms = maxLatencyP95;
			if (maxErrorRate) thresholds.max_error_rate = maxErrorRate / 100;

			let spec: Parameters<typeof api.createRun>[0]['spec'];

			if (multiEndpointMode) {
				// Build endpoint specs
				const endpointSpecs: EndpointSpec[] = [];
				for (const ep of endpoints) {
					// Parse endpoint headers
					let epHeaders: Record<string, string> = {};
					if (ep.headersText.trim()) {
						try {
							epHeaders = JSON.parse(ep.headersText);
						} catch {
							error = `Endpoint "${ep.name}": Invalid headers JSON`;
							submitting = false;
							return;
						}
					}

					// Parse endpoint body
					let epBody: string | Record<string, unknown> | undefined;
					if (ep.bodyText.trim()) {
						try {
							epBody = JSON.parse(ep.bodyText);
						} catch {
							epBody = ep.bodyText;
						}
					}

					endpointSpecs.push({
						name: ep.name.trim(),
						url: ep.url.trim(),
						method: ep.method,
						headers: epHeaders,
						body: epBody,
						weight: ep.weight,
						expected_status_codes: [200, 201, 204]
					});
				}

				spec = {
					name: name.trim(),
					url: endpoints[0]?.url || '',  // Use first endpoint URL for backward compat
					method: endpoints[0]?.method || 'GET',
					endpoints: endpointSpecs,
					distribution_strategy: distributionStrategy,
					total_requests: totalRequests,
					concurrency,
					requests_per_second: requestsPerSecond || undefined,
					timeout_seconds: timeoutSeconds,
					thresholds
				};
			} else {
				// Single endpoint mode (legacy)
				let headers: Record<string, string> = {};
				if (headersText.trim()) {
					try {
						headers = JSON.parse(headersText);
					} catch {
						error = 'Invalid headers JSON';
						submitting = false;
						return;
					}
				}

				let body: string | Record<string, unknown> | undefined;
				if (bodyText.trim()) {
					try {
						body = JSON.parse(bodyText);
					} catch {
						body = bodyText;
					}
				}

				spec = {
					name: name.trim(),
					url: url.trim(),
					method,
					total_requests: totalRequests,
					concurrency,
					requests_per_second: requestsPerSecond || undefined,
					timeout_seconds: timeoutSeconds,
					headers,
					body,
					thresholds
				};
			}

			const response = await api.createRun({ spec });

			goto(`/runs/${response.id}`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create test';
		}

		submitting = false;
	}
</script>

<svelte:head>
	<title>{isEditing ? 'Edit Test' : 'New Test'} | API Test Machine</title>
</svelte:head>

<div class="max-w-2xl mx-auto space-y-6">
	<div class="flex items-center gap-4">
		<a href="/" class="text-slate-400 hover:text-white">&larr; Back</a>
		<h1 class="text-2xl font-bold">{isEditing ? 'Edit Test' : 'New Test'}</h1>
	</div>

	{#if isEditing}
		<div class="bg-blue-900/30 border border-blue-700/50 rounded-lg p-4 text-blue-300 text-sm">
			Editing a test will create a new test run with the modified settings. The original run will not be changed.
		</div>
	{/if}

	{#if error}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300">
			{error}
		</div>
	{/if}

	<form on:submit|preventDefault={submit} class="space-y-6">
		<!-- Basic Info -->
		<div class="card space-y-4">
			<h2 class="text-lg font-bold">Basic Info</h2>

			<div>
				<label for="name" class="label">Test Name *</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					placeholder="e.g., API Health Check"
					class="input w-full"
					required
				/>
			</div>

			<!-- Multi-endpoint toggle -->
			<div class="flex items-center gap-3">
				<button
					type="button"
					on:click={toggleMultiEndpointMode}
					class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {multiEndpointMode ? 'bg-blue-600' : 'bg-slate-600'}"
				>
					<span
						class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {multiEndpointMode ? 'translate-x-6' : 'translate-x-1'}"
					></span>
				</button>
				<span class="text-sm">Multi-endpoint mode</span>
				{#if multiEndpointMode}
					<span class="text-xs text-slate-400">Test multiple URLs in a single run</span>
				{/if}
			</div>

			{#if !multiEndpointMode}
				<!-- Single URL mode -->
				<div class="grid md:grid-cols-4 gap-4">
					<div class="md:col-span-3">
						<label for="url" class="label">URL *</label>
						<input
							id="url"
							type="text"
							bind:value={url}
							placeholder="https://api.example.com/endpoint"
							class="input w-full"
							required
						/>
					</div>
					<div>
						<label for="method" class="label">Method</label>
						<select id="method" bind:value={method} class="input w-full">
							{#each methods as m}
								<option value={m}>{m}</option>
							{/each}
						</select>
					</div>
				</div>
			{:else}
				<!-- Multi-endpoint mode -->
				<div class="space-y-4">
					<div>
						<label for="distribution" class="label">Distribution Strategy</label>
						<select id="distribution" bind:value={distributionStrategy} class="input w-full md:w-auto">
							{#each distributionStrategies as strat}
								<option value={strat.value}>{strat.label}</option>
							{/each}
						</select>
						<p class="text-xs text-slate-400 mt-1">
							{distributionStrategies.find(s => s.value === distributionStrategy)?.description}
						</p>
					</div>

					<!-- Endpoint list -->
					<div class="space-y-3">
						{#each endpoints as endpoint, index}
							<div class="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
								<div class="flex items-center justify-between mb-3">
									<span class="text-sm font-medium text-slate-300">Endpoint {index + 1}</span>
									{#if endpoints.length > 1}
										<button
											type="button"
											on:click={() => removeEndpoint(index)}
											class="text-red-400 hover:text-red-300 text-sm"
										>
											Remove
										</button>
									{/if}
								</div>

								<div class="grid gap-3">
									<div class="grid md:grid-cols-2 gap-3">
										<div>
											<label class="label text-xs">Name *</label>
											<input
												type="text"
												bind:value={endpoint.name}
												placeholder="e.g., Get Users"
												class="input w-full text-sm"
											/>
										</div>
										<div class="grid grid-cols-2 gap-2">
											<div>
												<label class="label text-xs">Method</label>
												<select bind:value={endpoint.method} class="input w-full text-sm">
													{#each methods as m}
														<option value={m}>{m}</option>
													{/each}
												</select>
											</div>
											<div>
												<label class="label text-xs">Weight</label>
												<input
													type="number"
													bind:value={endpoint.weight}
													min="1"
													max="100"
													class="input w-full text-sm"
												/>
											</div>
										</div>
									</div>

									<div>
										<label class="label text-xs">URL *</label>
										<input
											type="text"
											bind:value={endpoint.url}
											placeholder="https://api.example.com/endpoint"
											class="input w-full text-sm"
										/>
									</div>

									<details class="text-sm">
										<summary class="cursor-pointer text-slate-400 hover:text-slate-300">
											Advanced options (headers, body)
										</summary>
										<div class="mt-2 space-y-2">
											<div>
												<label class="label text-xs">Headers (JSON)</label>
												<textarea
													bind:value={endpoint.headersText}
													placeholder={'{"Authorization": "Bearer token"}'}
													class="input w-full h-16 font-mono text-xs"
												></textarea>
											</div>
											<div>
												<label class="label text-xs">Body</label>
												<textarea
													bind:value={endpoint.bodyText}
													placeholder={'{"key": "value"}'}
													class="input w-full h-16 font-mono text-xs"
												></textarea>
											</div>
										</div>
									</details>
								</div>
							</div>
						{/each}

						<button
							type="button"
							on:click={addEndpoint}
							class="w-full py-2 border-2 border-dashed border-slate-600 rounded-lg text-slate-400 hover:border-slate-500 hover:text-slate-300 text-sm"
						>
							+ Add Endpoint
						</button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Load Configuration -->
		<div class="card space-y-4">
			<h2 class="text-lg font-bold">Load Configuration</h2>

			<div class="grid md:grid-cols-3 gap-4">
				<div>
					<label for="totalRequests" class="label">Total Requests</label>
					<input
						id="totalRequests"
						type="number"
						bind:value={totalRequests}
						min="1"
						max="1000000"
						class="input w-full"
					/>
				</div>
				<div>
					<label for="concurrency" class="label">Concurrency</label>
					<input
						id="concurrency"
						type="number"
						bind:value={concurrency}
						min="1"
						max="1000"
						class="input w-full"
					/>
				</div>
				<div>
					<label for="rps" class="label">Rate Limit (req/s)</label>
					<input
						id="rps"
						type="number"
						bind:value={requestsPerSecond}
						min="0.1"
						max="10000"
						step="0.1"
						placeholder="Unlimited"
						class="input w-full"
					/>
				</div>
			</div>

			<div>
				<label for="timeout" class="label">Timeout (seconds)</label>
				<input
					id="timeout"
					type="number"
					bind:value={timeoutSeconds}
					min="1"
					max="300"
					class="input w-32"
				/>
			</div>
		</div>

		<!-- Headers & Body (only in single-endpoint mode) -->
		{#if !multiEndpointMode}
			<div class="card space-y-4">
				<h2 class="text-lg font-bold">Request Details</h2>

				<div>
					<label for="headers" class="label">Headers (JSON)</label>
					<textarea
						id="headers"
						bind:value={headersText}
						placeholder={'{"Authorization": "Bearer token"}'}
						class="input w-full h-24 font-mono text-sm"
					></textarea>
				</div>

				<div>
					<label for="body" class="label">Body (JSON or text)</label>
					<textarea
						id="body"
						bind:value={bodyText}
						placeholder={'{"key": "value"}'}
						class="input w-full h-32 font-mono text-sm"
					></textarea>
				</div>
			</div>
		{/if}

		<!-- Thresholds -->
		<div class="card space-y-4">
			<h2 class="text-lg font-bold">Pass/Fail Thresholds</h2>
			<p class="text-sm text-slate-400">Set thresholds to determine if the test passes or fails.</p>

			<div class="grid md:grid-cols-2 gap-4">
				<div>
					<label for="maxLatency" class="label">Max P95 Latency (ms)</label>
					<input
						id="maxLatency"
						type="number"
						bind:value={maxLatencyP95}
						min="1"
						placeholder="No limit"
						class="input w-full"
					/>
				</div>
				<div>
					<label for="maxError" class="label">Max Error Rate (%)</label>
					<input
						id="maxError"
						type="number"
						bind:value={maxErrorRate}
						min="0"
						max="100"
						step="0.1"
						placeholder="No limit"
						class="input w-full"
					/>
				</div>
			</div>
		</div>

		<!-- Submit -->
		<div class="flex justify-end gap-4">
			<a href="/" class="btn btn-secondary">Cancel</a>
			<button type="submit" disabled={submitting} class="btn btn-primary">
				{submitting ? 'Starting...' : isEditing ? 'Run Modified Test' : 'Start Test'}
			</button>
		</div>
	</form>
</div>
