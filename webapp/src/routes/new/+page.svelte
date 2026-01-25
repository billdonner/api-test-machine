<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { HttpMethod, TestSpec } from '$lib/types';

	let name = '';
	let url = '';
	let method: HttpMethod = 'GET';
	let totalRequests = 100;
	let concurrency = 10;
	let requestsPerSecond: number | null = null;
	let timeoutSeconds = 30;
	let headersText = '';
	let bodyText = '';

	// Thresholds
	let maxLatencyP95: number | null = null;
	let maxErrorRate: number | null = null;

	let submitting = false;
	let error: string | null = null;
	let isEditing = false;

	const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

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
		if (!url.trim()) {
			error = 'URL is required';
			return;
		}

		submitting = true;

		try {
			// Parse headers
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

			// Parse body
			let body: string | Record<string, unknown> | undefined;
			if (bodyText.trim()) {
				try {
					body = JSON.parse(bodyText);
				} catch {
					body = bodyText;
				}
			}

			// Build thresholds
			const thresholds: Record<string, number> = {};
			if (maxLatencyP95) thresholds.max_latency_p95_ms = maxLatencyP95;
			if (maxErrorRate) thresholds.max_error_rate = maxErrorRate / 100;

			const response = await api.createRun({
				spec: {
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
				}
			});

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

		<!-- Headers & Body -->
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
