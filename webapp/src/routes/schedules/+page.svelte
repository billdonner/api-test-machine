<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { api } from '$lib/api';
	import type { Schedule, TestConfig, ScheduleTrigger } from '$lib/types';

	let schedules: Schedule[] = [];
	let testConfigs: TestConfig[] = [];
	let loading = true;
	let error: string | null = null;
	let showCreateForm = false;

	// Create form state
	let formName = '';
	let formDescription = '';
	let formTestName = '';
	let formTriggerType: 'interval' | 'cron' | 'date' = 'interval';
	let formMaxRuns: number | null = null;
	let formEnabled = true;

	// Interval trigger fields
	let intervalMinutes = 5;
	let intervalHours = 0;
	let intervalDays = 0;

	// Cron trigger fields
	let cronMinute = '0';
	let cronHour = '*';
	let cronDay = '*';
	let cronMonth = '*';
	let cronDayOfWeek = '*';

	// Date trigger fields
	let dateRunDate = '';

	let creating = false;
	let pollInterval: ReturnType<typeof setInterval> | null = null;

	async function loadSchedules() {
		try {
			const response = await api.listSchedules();
			schedules = response.schedules;
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load schedules';
		} finally {
			loading = false;
		}
	}

	async function loadTestConfigs() {
		try {
			const response = await api.listTestConfigs();
			testConfigs = response.configs;
			if (testConfigs.length > 0 && !formTestName) {
				formTestName = testConfigs[0].name;
			}
		} catch (e) {
			console.error('Failed to load test configs:', e);
		}
	}

	async function createSchedule() {
		if (!formName || !formTestName) {
			alert('Please fill in required fields');
			return;
		}

		creating = true;
		try {
			let trigger: ScheduleTrigger;
			if (formTriggerType === 'interval') {
				trigger = {
					type: 'interval',
					minutes: intervalMinutes || undefined,
					hours: intervalHours || undefined,
					days: intervalDays || undefined
				};
			} else if (formTriggerType === 'cron') {
				trigger = {
					type: 'cron',
					minute: cronMinute,
					hour: cronHour,
					day: cronDay,
					month: cronMonth,
					day_of_week: cronDayOfWeek,
					timezone: 'UTC'
				};
			} else {
				trigger = {
					type: 'date',
					run_date: new Date(dateRunDate).toISOString()
				};
			}

			await api.createSchedule({
				name: formName,
				description: formDescription || undefined,
				test_name: formTestName,
				trigger,
				max_runs: formMaxRuns,
				enabled: formEnabled
			});

			// Reset form
			formName = '';
			formDescription = '';
			formMaxRuns = null;
			showCreateForm = false;

			await loadSchedules();
		} catch (e) {
			alert('Failed to create schedule: ' + (e instanceof Error ? e.message : 'Unknown error'));
		} finally {
			creating = false;
		}
	}

	async function deleteSchedule(id: string, name: string) {
		if (!confirm(`Delete schedule "${name}"? This cannot be undone.`)) return;

		try {
			await api.deleteSchedule(id);
			await loadSchedules();
		} catch (e) {
			alert('Failed to delete schedule: ' + (e instanceof Error ? e.message : 'Unknown error'));
		}
	}

	async function pauseSchedule(id: string) {
		try {
			await api.pauseSchedule(id);
			await loadSchedules();
		} catch (e) {
			alert('Failed to pause schedule: ' + (e instanceof Error ? e.message : 'Unknown error'));
		}
	}

	async function resumeSchedule(id: string) {
		try {
			await api.resumeSchedule(id);
			await loadSchedules();
		} catch (e) {
			alert('Failed to resume schedule: ' + (e instanceof Error ? e.message : 'Unknown error'));
		}
	}

	function formatNextRun(dateStr: string | null): string {
		if (!dateStr) return 'Not scheduled';
		const date = new Date(dateStr);
		const now = new Date();
		const diff = date.getTime() - now.getTime();

		if (diff < 0) return 'Overdue';
		if (diff < 60000) return 'In less than a minute';
		if (diff < 3600000) return `In ${Math.round(diff / 60000)} min`;
		if (diff < 86400000) return `In ${Math.round(diff / 3600000)} hours`;
		return date.toLocaleString();
	}

	function formatTrigger(schedule: Schedule): string {
		const t = schedule.trigger;
		if (t.type === 'interval') {
			const parts = [];
			if (t.days) parts.push(`${t.days}d`);
			if (t.hours) parts.push(`${t.hours}h`);
			if (t.minutes) parts.push(`${t.minutes}m`);
			if (t.seconds) parts.push(`${t.seconds}s`);
			return `Every ${parts.join(' ')}`;
		} else if (t.type === 'cron') {
			return `Cron: ${t.minute} ${t.hour} ${t.day} ${t.month} ${t.day_of_week}`;
		} else {
			return `Once: ${new Date(t.run_date).toLocaleString()}`;
		}
	}

	function getScheduleStatus(schedule: Schedule): 'active' | 'paused' | 'completed' | 'disabled' {
		if (!schedule.enabled) return 'disabled';
		if (schedule.paused) return 'paused';
		if (schedule.max_runs !== null && schedule.run_count >= schedule.max_runs) return 'completed';
		return 'active';
	}

	function getStatusBadgeClass(status: string): string {
		switch (status) {
			case 'active':
				return 'bg-green-600 text-white';
			case 'paused':
				return 'bg-yellow-600 text-white';
			case 'completed':
				return 'bg-blue-600 text-white';
			case 'disabled':
				return 'bg-slate-600 text-slate-300';
			default:
				return 'bg-slate-600 text-slate-300';
		}
	}

	onMount(() => {
		loadSchedules();
		loadTestConfigs();
		pollInterval = setInterval(loadSchedules, 5000);
	});

	onDestroy(() => {
		if (pollInterval) {
			clearInterval(pollInterval);
		}
	});
</script>

<svelte:head>
	<title>Schedules | API Test Machine</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold">Scheduled Tests</h1>
		<button
			on:click={() => (showCreateForm = !showCreateForm)}
			class="btn btn-primary"
		>
			{showCreateForm ? 'Cancel' : '+ New Schedule'}
		</button>
	</div>

	{#if error}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-300">
			{error}
		</div>
	{/if}

	<!-- Create Form -->
	{#if showCreateForm}
		<div class="card space-y-4">
			<h2 class="text-lg font-bold">Create New Schedule</h2>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label for="schedule-name" class="label">Schedule Name *</label>
					<input
						id="schedule-name"
						type="text"
						bind:value={formName}
						placeholder="e.g., Hourly Health Check"
						class="input w-full"
					/>
				</div>

				<div>
					<label for="test-select" class="label">Test to Run *</label>
					<select id="test-select" bind:value={formTestName} class="input w-full">
						{#each testConfigs as config}
							<option value={config.name}>{config.name}</option>
						{/each}
					</select>
				</div>
			</div>

			<div>
				<label for="description" class="label">Description</label>
				<input
					id="description"
					type="text"
					bind:value={formDescription}
					placeholder="Optional description"
					class="input w-full"
				/>
			</div>

			<!-- Trigger Type Selection -->
			<div>
				<label class="label">Trigger Type</label>
				<div class="flex gap-4">
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="radio" bind:group={formTriggerType} value="interval" class="text-blue-500" />
						<span>Interval</span>
					</label>
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="radio" bind:group={formTriggerType} value="cron" class="text-blue-500" />
						<span>Cron</span>
					</label>
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="radio" bind:group={formTriggerType} value="date" class="text-blue-500" />
						<span>One-time</span>
					</label>
				</div>
			</div>

			<!-- Interval Trigger Fields -->
			{#if formTriggerType === 'interval'}
				<div class="grid grid-cols-3 gap-4">
					<div>
						<label for="interval-days" class="label">Days</label>
						<input
							id="interval-days"
							type="number"
							min="0"
							bind:value={intervalDays}
							class="input w-full"
						/>
					</div>
					<div>
						<label for="interval-hours" class="label">Hours</label>
						<input
							id="interval-hours"
							type="number"
							min="0"
							max="23"
							bind:value={intervalHours}
							class="input w-full"
						/>
					</div>
					<div>
						<label for="interval-minutes" class="label">Minutes</label>
						<input
							id="interval-minutes"
							type="number"
							min="0"
							max="59"
							bind:value={intervalMinutes}
							class="input w-full"
						/>
					</div>
				</div>
			{/if}

			<!-- Cron Trigger Fields -->
			{#if formTriggerType === 'cron'}
				<div class="grid grid-cols-5 gap-2">
					<div>
						<label for="cron-minute" class="label text-xs">Minute</label>
						<input id="cron-minute" type="text" bind:value={cronMinute} class="input w-full" placeholder="*" />
					</div>
					<div>
						<label for="cron-hour" class="label text-xs">Hour</label>
						<input id="cron-hour" type="text" bind:value={cronHour} class="input w-full" placeholder="*" />
					</div>
					<div>
						<label for="cron-day" class="label text-xs">Day</label>
						<input id="cron-day" type="text" bind:value={cronDay} class="input w-full" placeholder="*" />
					</div>
					<div>
						<label for="cron-month" class="label text-xs">Month</label>
						<input id="cron-month" type="text" bind:value={cronMonth} class="input w-full" placeholder="*" />
					</div>
					<div>
						<label for="cron-dow" class="label text-xs">Day of Week</label>
						<input id="cron-dow" type="text" bind:value={cronDayOfWeek} class="input w-full" placeholder="*" />
					</div>
				</div>
				<p class="text-xs text-slate-400">Cron format: minute hour day month day_of_week (e.g., "0 2 * * *" for daily at 2 AM)</p>
			{/if}

			<!-- Date Trigger Fields -->
			{#if formTriggerType === 'date'}
				<div>
					<label for="run-date" class="label">Run Date & Time</label>
					<input
						id="run-date"
						type="datetime-local"
						bind:value={dateRunDate}
						class="input w-full"
					/>
				</div>
			{/if}

			<!-- Max Runs -->
			<div class="grid grid-cols-2 gap-4">
				<div>
					<label for="max-runs" class="label">Max Runs (leave empty for indefinite)</label>
					<input
						id="max-runs"
						type="number"
						min="1"
						bind:value={formMaxRuns}
						placeholder="Indefinite"
						class="input w-full"
					/>
				</div>
				<div class="flex items-end">
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="checkbox" bind:checked={formEnabled} class="w-4 h-4 text-green-500" />
						<span>Enabled</span>
					</label>
				</div>
			</div>

			<div class="flex justify-end gap-3">
				<button
					on:click={() => (showCreateForm = false)}
					class="btn bg-slate-700 hover:bg-slate-600"
				>
					Cancel
				</button>
				<button
					on:click={createSchedule}
					disabled={creating || !formName || !formTestName}
					class="btn btn-primary disabled:opacity-50"
				>
					{creating ? 'Creating...' : 'Create Schedule'}
				</button>
			</div>
		</div>
	{/if}

	<!-- Schedules List -->
	<div class="card">
		{#if loading && schedules.length === 0}
			<div class="text-center py-8 text-slate-400">Loading schedules...</div>
		{:else if schedules.length === 0}
			<div class="text-center py-8 text-slate-400">
				No scheduled tests.
				<button on:click={() => (showCreateForm = true)} class="text-blue-400 hover:underline">
					Create one?
				</button>
			</div>
		{:else}
			<div class="space-y-3">
				{#each schedules as schedule (schedule.id)}
					{@const status = getScheduleStatus(schedule)}
					<div class="border border-slate-700 rounded-lg p-4 hover:bg-slate-800/50 transition-colors">
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3">
									<!-- Status indicator -->
									{#if status === 'active'}
										<span class="w-3 h-3 bg-green-500 rounded-full animate-pulse" title="Active"></span>
									{:else if status === 'paused'}
										<span class="w-3 h-3 bg-yellow-500 rounded-full" title="Paused"></span>
									{:else if status === 'completed'}
										<span class="w-3 h-3 bg-blue-500 rounded-full" title="Completed"></span>
									{:else}
										<span class="w-3 h-3 bg-slate-500 rounded-full" title="Disabled"></span>
									{/if}

									<h3 class="font-bold text-lg truncate">{schedule.name}</h3>
									<span class="px-2 py-0.5 rounded text-xs font-medium {getStatusBadgeClass(status)}">
										{status}
									</span>
								</div>

								<div class="mt-2 text-sm text-slate-400 space-y-1">
									<div class="flex items-center gap-4">
										<span>Test: <span class="text-slate-300">{schedule.test_name}</span></span>
										<span>{formatTrigger(schedule)}</span>
									</div>
									<div class="flex items-center gap-4">
										<span>
											Runs: <span class="text-slate-300">{schedule.run_count}</span>/{schedule.max_runs ?? '∞'}
										</span>
										{#if status === 'active' || status === 'paused'}
											<span>
												Next: <span class="text-slate-300">{formatNextRun(schedule.next_run_time)}</span>
											</span>
										{/if}
									</div>
								</div>
							</div>

							<!-- Action Buttons - Prominent -->
							<div class="flex items-center gap-2 flex-shrink-0">
								{#if status === 'active'}
									<button
										on:click={() => pauseSchedule(schedule.id)}
										class="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded font-medium transition-colors"
									>
										Pause
									</button>
								{:else if status === 'paused'}
									<button
										on:click={() => resumeSchedule(schedule.id)}
										class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded font-medium transition-colors"
									>
										Resume
									</button>
								{/if}
								<button
									on:click={() => deleteSchedule(schedule.id, schedule.name)}
									class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded font-medium transition-colors"
								>
									Delete
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>

			<div class="mt-4 pt-4 border-t border-slate-700 text-sm text-slate-400">
				{schedules.length} schedule{schedules.length !== 1 ? 's' : ''} total
				| {schedules.filter(s => getScheduleStatus(s) === 'active').length} active
			</div>
		{/if}
	</div>
</div>
