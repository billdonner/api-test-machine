/**
 * Chart.js configuration and registration for the webapp
 */

import {
	Chart,
	CategoryScale,
	LinearScale,
	BarController,
	BarElement,
	DoughnutController,
	ArcElement,
	ScatterController,
	PointElement,
	Tooltip,
	Legend,
	type ChartOptions
} from 'chart.js';

// Only register Chart.js components in browser (not during SSR)
if (typeof window !== 'undefined') {
	Chart.register(
		CategoryScale,
		LinearScale,
		BarController,
		BarElement,
		DoughnutController,
		ArcElement,
		ScatterController,
		PointElement,
		Tooltip,
		Legend
	);
}

// Re-export Chart for convenience
export { Chart };

// Color palette matching slate theme
export const colors = {
	blue: {
		500: '#3b82f6',
		400: '#60a5fa',
		300: '#93c5fd'
	},
	green: {
		500: '#22c55e',
		400: '#4ade80',
		300: '#86efac'
	},
	red: {
		500: '#ef4444',
		400: '#f87171',
		300: '#fca5a5'
	},
	orange: {
		500: '#f97316',
		400: '#fb923c',
		300: '#fdba74'
	},
	yellow: {
		500: '#eab308',
		400: '#facc15'
	},
	slate: {
		900: '#0f172a',
		800: '#1e293b',
		700: '#334155',
		600: '#475569',
		500: '#64748b',
		400: '#94a3b8',
		300: '#cbd5e1',
		200: '#e2e8f0',
		100: '#f1f5f9'
	}
};

// Latency gradient colors (green=fast to red=slow)
export const latencyColors = [
	colors.green[500], // Min
	colors.green[400], // P50
	colors.yellow[500], // P90
	colors.orange[400], // P95
	colors.orange[500], // P99
	colors.red[500] // Max
];

/**
 * Get color for HTTP status code
 */
export function getStatusCodeColor(code: number): string {
	if (code >= 200 && code < 300) return colors.green[500];
	if (code >= 300 && code < 400) return colors.blue[400];
	if (code >= 400 && code < 500) return colors.orange[500];
	if (code >= 500) return colors.red[500];
	return colors.slate[500];
}

// Default dark theme options for all charts
export const darkThemeDefaults: Partial<ChartOptions> = {
	responsive: true,
	maintainAspectRatio: false,
	plugins: {
		legend: {
			labels: {
				color: colors.slate[300]
			}
		},
		tooltip: {
			backgroundColor: colors.slate[800],
			titleColor: colors.slate[100],
			bodyColor: colors.slate[300],
			borderColor: colors.slate[600],
			borderWidth: 1
		}
	},
	scales: {
		x: {
			ticks: {
				color: colors.slate[400]
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
				color: colors.slate[700]
			}
		}
	}
};
