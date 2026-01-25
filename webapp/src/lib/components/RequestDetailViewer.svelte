<script lang="ts">
	import { api } from '$lib/api';
	import type { RequestSummary, RequestDetail } from '$lib/types';

	export let runId: string;
	export let requests: RequestSummary[] = [];

	let expandedRequest: number | null = null;
	let requestDetails: Map<number, RequestDetail> = new Map();
	let loadingDetail: number | null = null;

	// Extract image URLs from response body
	function extractImageUrls(body: string | null): string[] {
		if (!body) return [];

		const urls: string[] = [];

		// Check if response is an image content-type (binary would show as placeholder)
		if (body.startsWith('<binary:') || body.startsWith('data:image')) {
			return [];
		}

		// Try to parse as JSON and find image URLs
		try {
			const json = JSON.parse(body);
			findImageUrlsInObject(json, urls);
		} catch {
			// Not JSON, try to find URLs with regex
			const urlRegex = /(https?:\/\/[^\s"'<>]+\.(?:png|jpg|jpeg|gif|webp|svg|bmp))/gi;
			const matches = body.match(urlRegex);
			if (matches) {
				urls.push(...matches);
			}
		}

		return [...new Set(urls)]; // Remove duplicates
	}

	function findImageUrlsInObject(obj: unknown, urls: string[], depth = 0): void {
		if (depth > 10) return; // Prevent infinite recursion

		if (typeof obj === 'string') {
			// Check if it's an image URL with extension
			if (/^https?:\/\/.+\.(png|jpg|jpeg|gif|webp|svg|bmp)(\?.*)?$/i.test(obj)) {
				urls.push(obj);
			}
			// Check for data URLs
			if (obj.startsWith('data:image/')) {
				urls.push(obj);
			}
			// Check common image URL patterns
			if (/^https?:\/\/.*(image|img|photo|picture|pic|thumbnail|thumb|picsum|unsplash)/i.test(obj)) {
				urls.push(obj);
			}
		} else if (Array.isArray(obj)) {
			for (const item of obj) {
				findImageUrlsInObject(item, urls, depth + 1);
			}
		} else if (obj && typeof obj === 'object') {
			for (const [key, value] of Object.entries(obj)) {
				// Check if key suggests an image
				if (/image|img|photo|picture|pic|thumbnail|thumb|icon|avatar|logo|download_url|src|url/i.test(key)) {
					if (typeof value === 'string' && value.startsWith('http')) {
						// Additional check for image-like URLs
						if (/\.(png|jpg|jpeg|gif|webp|svg|bmp)|picsum|unsplash|image|photo|img/i.test(value)) {
							urls.push(value);
						}
					}
				}
				findImageUrlsInObject(value, urls, depth + 1);
			}
		}
	}

	async function toggleRequest(requestNum: number) {
		if (expandedRequest === requestNum) {
			expandedRequest = null;
			return;
		}

		expandedRequest = requestNum;

		// Load details if not cached
		if (!requestDetails.has(requestNum)) {
			loadingDetail = requestNum;
			try {
				const detail = await api.getRequestDetail(runId, requestNum);
				requestDetails.set(requestNum, detail);
				requestDetails = requestDetails; // Trigger reactivity
			} catch (e) {
				console.error('Failed to load request detail:', e);
			}
			loadingDetail = null;
		}
	}

	function formatJson(str: string | null): string {
		if (!str) return '';
		try {
			const parsed = JSON.parse(str);
			return JSON.stringify(parsed, null, 2);
		} catch {
			return str;
		}
	}

	function formatHeaders(headers: Record<string, string> | null): string {
		if (!headers) return '';
		return Object.entries(headers)
			.map(([k, v]) => `${k}: ${v}`)
			.join('\n');
	}

	function getStatusColor(code: number | null): string {
		if (!code) return 'text-slate-400';
		if (code >= 200 && code < 300) return 'text-green-400';
		if (code >= 300 && code < 400) return 'text-blue-400';
		if (code >= 400 && code < 500) return 'text-orange-400';
		return 'text-red-400';
	}

	// Collect all images from all loaded request details
	$: allImageUrls = Array.from(requestDetails.values())
		.flatMap(detail => extractImageUrls(detail.response_body))
		.filter((url, i, arr) => arr.indexOf(url) === i); // Unique
</script>

<div class="space-y-4">
	<h3 class="text-lg font-bold">Request Details ({requests.length} sampled)</h3>

	<!-- Request list -->
	<div class="space-y-2">
		{#each requests as req}
			{@const detail = requestDetails.get(req.request_number)}
			<div class="border border-slate-700 rounded-lg overflow-hidden">
				<!-- Header row -->
				<button
					class="w-full px-4 py-3 flex items-center justify-between bg-slate-800 hover:bg-slate-750 transition-colors text-left"
					on:click={() => toggleRequest(req.request_number)}
				>
					<div class="flex items-center gap-4">
						<span class="text-slate-400">#{req.request_number}</span>
						<span class="{getStatusColor(req.status_code)} font-mono font-bold">
							{req.status_code || 'ERR'}
						</span>
						<span class="text-slate-300">{req.latency_ms.toFixed(0)}ms</span>
						{#if req.error}
							<span class="text-red-400 text-sm">{req.error}</span>
						{/if}
					</div>
					<span class="text-slate-400">
						{expandedRequest === req.request_number ? '▼' : '▶'}
					</span>
				</button>

				<!-- Expanded detail -->
				{#if expandedRequest === req.request_number}
					<div class="p-4 bg-slate-900 border-t border-slate-700">
						{#if loadingDetail === req.request_number}
							<div class="text-slate-400">Loading...</div>
						{:else if detail}
							<div class="grid md:grid-cols-2 gap-4">
								<!-- Request -->
								<div>
									<h4 class="text-sm font-bold text-slate-300 mb-2">Request</h4>
									<div class="bg-slate-800 rounded p-3 text-sm font-mono overflow-x-auto">
										<div class="text-blue-400 mb-2">
											{detail.request_method} {detail.request_url}
										</div>
										{#if detail.request_headers && Object.keys(detail.request_headers).length > 0}
											<div class="text-slate-400 text-xs mb-2">
												<pre class="whitespace-pre-wrap">{formatHeaders(detail.request_headers)}</pre>
											</div>
										{/if}
										{#if detail.request_body}
											<div class="mt-2 pt-2 border-t border-slate-700">
												<pre class="text-green-300 whitespace-pre-wrap text-xs max-h-48 overflow-auto">{formatJson(detail.request_body)}</pre>
											</div>
										{/if}
									</div>
								</div>

								<!-- Response -->
								<div>
									<h4 class="text-sm font-bold text-slate-300 mb-2">Response</h4>
									<div class="bg-slate-800 rounded p-3 text-sm font-mono overflow-x-auto">
										<div class="{getStatusColor(detail.status_code)} mb-2">
											{detail.status_code} {detail.status_code && detail.status_code >= 200 && detail.status_code < 300 ? 'OK' : ''}
										</div>
										{#if detail.response_headers && Object.keys(detail.response_headers).length > 0}
											<div class="text-slate-400 text-xs mb-2">
												<pre class="whitespace-pre-wrap">{formatHeaders(detail.response_headers)}</pre>
											</div>
										{/if}
										{#if detail.response_body}
											<div class="mt-2 pt-2 border-t border-slate-700">
												<pre class="text-yellow-300 whitespace-pre-wrap text-xs max-h-64 overflow-auto">{formatJson(detail.response_body)}</pre>
											</div>
										{/if}
									</div>
								</div>
							</div>

							<!-- Images found in this response -->
							{@const imageUrls = extractImageUrls(detail.response_body)}
							{#if imageUrls.length > 0}
								<div class="mt-4">
									<h4 class="text-sm font-bold text-slate-300 mb-2">Images Found ({imageUrls.length})</h4>
									<div class="flex flex-wrap gap-2">
										{#each imageUrls as url}
											<a href={url} target="_blank" rel="noopener noreferrer">
												<img
													src={url}
													alt="Response image"
													class="h-20 w-20 object-cover rounded border border-slate-600 hover:border-blue-400 transition-colors"
													on:error={(e) => e.currentTarget.style.display = 'none'}
												/>
											</a>
										{/each}
									</div>
								</div>
							{/if}
						{:else}
							<div class="text-slate-500">No details available</div>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<!-- Image Gallery (all images from all requests) -->
	{#if allImageUrls.length > 0}
		<div class="mt-6 pt-6 border-t border-slate-700">
			<h3 class="text-lg font-bold mb-4">Image Gallery ({allImageUrls.length} images)</h3>
			<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
				{#each allImageUrls as url}
					<a
						href={url}
						target="_blank"
						rel="noopener noreferrer"
						class="group relative aspect-square bg-slate-800 rounded-lg overflow-hidden border border-slate-700 hover:border-blue-400 transition-colors"
					>
						<img
							src={url}
							alt="API response image"
							class="w-full h-full object-cover"
							on:error={(e) => {
								e.currentTarget.parentElement.style.display = 'none';
							}}
						/>
						<div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
							<span class="text-white text-sm">Open</span>
						</div>
					</a>
				{/each}
			</div>
		</div>
	{/if}
</div>
