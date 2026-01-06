<script lang="ts">
	import type {
		Checklist,
		Collection,
		Lodging,
		Note,
		Transportation,
		Visit,
		Activity,
		User
	} from '$lib/types';
	// @ts-ignore
	import { DateTime } from 'luxon';
	// lodging icons and helpers
	import { LODGING_TYPES_ICONS } from '$lib';

	export let collection: Collection;
	export let user: User | null = null;

	function getLodgingIcon(type: string): string {
		return (LODGING_TYPES_ICONS as Record<string, string>)[type] || '🏨';
	}

	function convertDistance(km: number): number {
		if (user?.measurement_system === 'imperial') {
			return km * 0.621371; // Convert km to miles
		}
		return km;
	}

	function convertElevation(meters: number): number {
		if (user?.measurement_system === 'imperial') {
			return meters * 3.28084; // Convert meters to feet
		}
		return meters;
	}

	function getDistanceUnit(): string {
		return user?.measurement_system === 'imperial' ? 'mi' : 'km';
	}

	function getDistanceUnitLong(): string {
		return user?.measurement_system === 'imperial' ? 'miles' : 'kilometers';
	}

	function getElevationUnit(): string {
		return user?.measurement_system === 'imperial' ? 'ft' : 'm';
	}

	function getElevationUnitLong(): string {
		return user?.measurement_system === 'imperial' ? 'feet' : 'meters';
	}

	const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
	const distanceFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
	const compactFormatter = new Intl.NumberFormat(undefined, {
		notation: 'compact',
		maximumFractionDigits: 1
	});

	const tripStart = collection.start_date ? DateTime.fromISO(collection.start_date) : null;
	const tripEnd = collection.end_date ? DateTime.fromISO(collection.end_date) : null;

	function overlapsCollectionRange(
		startStr: string | null | undefined,
		endStr: string | null | undefined
	): boolean {
		if (!tripStart || !tripEnd) return true; // If no collection window, include everything
		if (!startStr) return false;

		const start = DateTime.fromISO(startStr);
		if (!start.isValid) return false;

		const end = endStr ? DateTime.fromISO(endStr) : start;
		if (!end.isValid) return false;

		return end >= tripStart && start <= tripEnd;
	}

	function addRangeDays(
		startStr: string | null | undefined,
		endStr: string | null | undefined,
		target: Set<string>
	) {
		if (!startStr) return;
		const start = DateTime.fromISO(startStr);
		const end = endStr ? DateTime.fromISO(endStr) : start;
		if (!start.isValid || !end.isValid) return;

		let cursor = start.startOf('day');
		const finalDay = end.startOf('day');
		while (cursor <= finalDay) {
			target.add(cursor.toISODate());
			cursor = cursor.plus({ days: 1 });
		}
	}

	$: tripDurationDays =
		tripStart && tripEnd ? Math.max(1, Math.floor(tripEnd.diff(tripStart, 'days').days) + 1) : null;

	$: visitedLocations = (collection.locations || []).filter((loc) =>
		loc.visits?.some((visit) => overlapsCollectionRange(visit.start_date, visit.end_date))
	);

	$: visitsInRange = visitedLocations.flatMap((loc) =>
		(loc.visits || []).filter((visit) => overlapsCollectionRange(visit.start_date, visit.end_date))
	);

	$: countriesVisited = (() => {
		const map = new Map<string, { name: string; code: string; flag?: string }>();
		visitedLocations.forEach((loc) => {
			const country = loc.country;
			if (!country) return;
			const key = country.country_code || String(country.id) || country.name;
			if (!key) return;
			if (!map.has(key))
				map.set(key, {
					name: country.name,
					code: country.country_code || '',
					flag: country.flag_url || ''
				});
		});
		return Array.from(map.values());
	})();

	$: transportSegments = (collection.transportations || []).filter((segment) =>
		overlapsCollectionRange(segment.date, segment.end_date)
	);

	$: totalDistance = convertDistance(
		transportSegments.reduce((sum, segment) => sum + (segment.distance || 0), 0)
	);

	$: lodgingStays = (collection.lodging || []).filter((stay) =>
		overlapsCollectionRange(stay.check_in, stay.check_out)
	);

	$: lodgingNights = lodgingStays.reduce((sum, stay) => {
		if (!stay.check_in || !stay.check_out) return sum;
		const start = DateTime.fromISO(stay.check_in);
		const end = DateTime.fromISO(stay.check_out);
		if (!start.isValid || !end.isValid) return sum;
		const diff = Math.max(1, Math.floor(end.diff(start, 'days').days));
		return sum + diff;
	}, 0);

	$: notesInRange = (collection.notes || []).filter((note: Note) =>
		overlapsCollectionRange(note.date, note.date)
	);

	$: checklistsInRange = (collection.checklists || []).filter((list: Checklist) =>
		overlapsCollectionRange(list.date, list.date)
	);

	$: imagesInRange = (() => {
		let total = 0;
		visitedLocations.forEach((loc) => (total += loc.images?.length || 0));
		transportSegments.forEach((segment) => (total += segment.images?.length || 0));
		lodgingStays.forEach((stay) => (total += stay.images?.length || 0));
		return total;
	})();

	$: regionsVisited = (() => {
		const map = new Map<string, { name: string; country: string }>();
		visitedLocations.forEach((loc) => {
			const region = loc.region;
			if (!region) return;
			const key = String(region.id || region.name);
			if (!key) return;
			if (!map.has(key)) map.set(key, { name: region.name, country: region.country_name || '' });
		});
		return Array.from(map.values());
	})();

	$: citiesVisited = (() => {
		const map = new Map<string, { name: string; region: string }>();
		visitedLocations.forEach((loc) => {
			const city = loc.city;
			if (!city) return;
			const key = String(city.id || city.name);
			if (!key) return;
			if (!map.has(key)) map.set(key, { name: city.name, region: city.region_name || '' });
		});
		return Array.from(map.values());
	})();

	$: categoriesWithIcons = (() => {
		const map = new Map<string, { name: string; icon: string; count: number }>();
		visitedLocations.forEach((loc) => {
			if (!loc.category) return;
			const name = loc.category.display_name || loc.category.name;
			const icon = loc.category.icon || '📍';
			if (!name) return;
			if (!map.has(name)) {
				map.set(name, { name, icon, count: 0 });
			}
			const existing = map.get(name)!;
			existing.count++;
		});
		return Array.from(map.values()).sort((a, b) => b.count - a.count);
	})();

	$: activitiesInRange = (() => {
		const activities: Activity[] = [];
		visitsInRange.forEach((visit: Visit) => {
			if (visit.activities && visit.activities.length > 0) {
				activities.push(...visit.activities);
			}
		});
		return activities;
	})();

	$: totalActivityDistance = convertDistance(
		activitiesInRange.reduce((sum, act) => sum + (act.distance || 0), 0) / 1000
	);
	$: totalActivityElevation = convertElevation(
		activitiesInRange.reduce((sum, act) => sum + (act.elevation_gain || 0), 0)
	);
	$: totalActivityCalories = activitiesInRange.reduce((sum, act) => sum + (act.calories || 0), 0);

	$: sportTypes = (() => {
		const types = new Map<string, number>();
		activitiesInRange.forEach((act) => {
			const sport = act.sport_type || 'Other';
			types.set(sport, (types.get(sport) || 0) + 1);
		});
		return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
	})();

	$: activeDayCount = (() => {
		const days = new Set<string>();
		visitsInRange.forEach((visit: Visit) => addRangeDays(visit.start_date, visit.end_date, days));
		transportSegments.forEach((segment: Transportation) =>
			addRangeDays(segment.date, segment.end_date, days)
		);
		lodgingStays.forEach((stay: Lodging) => addRangeDays(stay.check_in, stay.check_out, days));
		return days.size;
	})();

	$: scopeLabel = (() => {
		const dayPart = tripDurationDays
			? `${tripDurationDays} ${tripDurationDays === 1 ? 'day' : 'days'}`
			: '';
		const countryPart = countriesVisited.length
			? `${countriesVisited.length} ${countriesVisited.length === 1 ? 'country' : 'countries'}`
			: '';
		return [dayPart, countryPart].filter(Boolean).join(' in ');
	})();

	$: windowLabel =
		tripStart && tripEnd
			? `${tripStart.toLocaleString(DateTime.DATE_MED)} - ${tripEnd.toLocaleString(DateTime.DATE_MED)}`
			: null;

	function getTransportIcon(type?: string | null) {
		const normalized = (type || '').toLowerCase();
		if (normalized.includes('flight') || normalized.includes('plane') || normalized.includes('air'))
			return '✈️';
		if (normalized.includes('train') || normalized.includes('rail')) return '🚆';
		if (normalized.includes('bus')) return '🚌';
		if (normalized.includes('car') || normalized.includes('drive')) return '🚗';
		if (normalized.includes('boat') || normalized.includes('ferry') || normalized.includes('ship'))
			return '🚢';
		return '🚗';
	}

	function capitalize(text?: string | null) {
		if (!text) return '';
		const s = String(text);
		return s.charAt(0).toUpperCase() + s.slice(1);
	}

	$: distanceByTransportType = (() => {
		const types = new Map<string, number>();
		transportSegments.forEach((segment) => {
			const icon = getTransportIcon(segment.type);
			const distance = convertDistance(segment.distance || 0);
			types.set(icon, (types.get(icon) || 0) + distance);
		});
		return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
	})();

	$: averageLocationRating = (() => {
		const rated = visitedLocations.filter((loc) => loc.rating !== null && loc.rating !== undefined);
		if (rated.length === 0) return 0;
		return rated.reduce((sum, loc) => sum + (loc.rating || 0), 0) / rated.length;
	})();

	$: checklistStats = (() => {
		let totalItems = 0;
		let checkedItems = 0;
		checklistsInRange.forEach((list) => {
			if (list.items) {
				totalItems += list.items.length;
				checkedItems += list.items.filter((item) => item.is_checked).length;
			}
		});
		return {
			total: totalItems,
			checked: checkedItems,
			percentage: totalItems > 0 ? Math.round((checkedItems / totalItems) * 100) : 0
		};
	})();

	$: lodgingTypeBreakdown = (() => {
		const types = new Map<string, number>();
		lodgingStays.forEach((stay) => {
			const type = stay.type || 'Other';
			types.set(type, (types.get(type) || 0) + 1);
		});
		return Array.from(types.entries()).sort((a, b) => b[1] - a[1]);
	})();

	$: totalAttachments = (() => {
		let total = 0;
		visitedLocations.forEach((loc) => (total += loc.attachments?.length || 0));
		transportSegments.forEach((segment) => (total += segment.attachments?.length || 0));
		lodgingStays.forEach((stay) => (total += stay.attachments?.length || 0));
		return total;
	})();
</script>

<div class="space-y-6">
	<!-- Hero Overview Card -->
	<div
		class="card bg-gradient-to-br from-primary/10 to-secondary/10 shadow-xl border border-primary/20"
	>
		<div class="card-body space-y-4">
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-center gap-2">
					{#if countriesVisited.length}
						{#each countriesVisited.slice(0, 3) as country}
							{#if country.flag}
								<img src={country.flag} alt={country.name} class="w-8 h-6 rounded shadow-sm" />
							{/if}
						{/each}
					{/if}
					<h2 class="text-3xl font-bold">{collection.name}</h2>
				</div>

				{#if windowLabel}
					<div class="flex flex-wrap items-center gap-2 text-sm">
						<span class="badge badge-lg badge-ghost">📅 {windowLabel}</span>
						{#if scopeLabel}
							<span class="badge badge-lg badge-primary">{scopeLabel}</span>
						{/if}
					</div>
				{:else}
					<p class="text-sm opacity-70">📁 Folder view - showing all data</p>
				{/if}
			</div>

			<!-- Key Stats Row -->
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-info/20">
					<div class="stat-figure text-info text-3xl">📍</div>
					<div class="stat-title text-xs">Footprints</div>
					<div class="stat-value text-info text-2xl">{visitedLocations.length}</div>
					<div class="stat-desc">Locations visited</div>
				</div>

				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-success/20">
					<div class="stat-figure text-success text-3xl">📸</div>
					<div class="stat-title text-xs">Photos</div>
					<div class="stat-value text-success text-2xl">
						{compactFormatter.format(imagesInRange)}
					</div>
					<div class="stat-desc">Images captured</div>
				</div>

				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-warning/20">
					<div class="stat-figure text-warning text-3xl">🗺️</div>
					<div class="stat-title text-xs">Places</div>
					<div class="stat-value text-warning text-2xl">{countriesVisited.length}</div>
					<div class="stat-desc">
						{regionsVisited.length} regions, {citiesVisited.length} cities
					</div>
				</div>

				<div class="stat bg-base-100 rounded-lg shadow p-4 border border-accent/20">
					<div class="stat-figure text-accent text-3xl">👥</div>
					<div class="stat-title text-xs">Travelers</div>
					<div class="stat-value text-accent text-2xl">
						{collection.collaborators?.length || 0}
					</div>
					<div class="stat-desc">On this trip</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Geographic Breakdown -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body space-y-4">
			<h3 class="card-title text-xl flex items-center gap-2">
				<span class="text-2xl">🌎</span>
				Geographic Breakdown
			</h3>

			{#if countriesVisited.length}
				<div>
					<h4 class="font-semibold mb-2 flex items-center gap-2">
						<span>🏳️</span> Countries ({countriesVisited.length})
					</h4>
					<div class="flex flex-wrap gap-2">
						{#each countriesVisited as country}
							<div class="flex items-center gap-2 badge badge-lg badge-primary badge-outline p-3">
								{#if country.flag}
									<img src={country.flag} alt={country.name} class="w-6 h-4 rounded" />
								{/if}
								<span class="font-medium">{country.name}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if regionsVisited.length}
				<div>
					<h4 class="font-semibold mb-2 flex items-center gap-2">
						<span>🗺️</span> Regions ({regionsVisited.length})
					</h4>
					<div class="flex flex-wrap gap-2">
						{#each regionsVisited.slice(0, 15) as region}
							<span class="badge badge-lg badge-secondary badge-outline">
								{region.name}{#if region.country}, {region.country}{/if}
							</span>
						{/each}
						{#if regionsVisited.length > 15}
							<span class="badge badge-lg badge-ghost">+{regionsVisited.length - 15} more</span>
						{/if}
					</div>
				</div>
			{/if}

			{#if citiesVisited.length}
				<div>
					<h4 class="font-semibold mb-2 flex items-center gap-2">
						<span>🏙️</span> Cities ({citiesVisited.length})
					</h4>
					<div class="flex flex-wrap gap-2">
						{#each citiesVisited.slice(0, 20) as city}
							<span class="badge badge-accent badge-outline">
								{city.name}
							</span>
						{/each}
						{#if citiesVisited.length > 20}
							<span class="badge badge-ghost">+{citiesVisited.length - 20} more</span>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Trip Timeline & Duration -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h3 class="card-title text-xl flex items-center gap-2">
				<span class="text-2xl">📆</span>
				Trip Timeline
			</h3>
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
				<div class="stat bg-primary/10 rounded-lg p-4">
					<div class="stat-title text-xs">Total Days</div>
					<div class="stat-value text-primary text-2xl">{tripDurationDays ?? 'N/A'}</div>
					<div class="stat-desc">Trip window</div>
				</div>
				<div class="stat bg-success/10 rounded-lg p-4">
					<div class="stat-title text-xs">Active Days</div>
					<div class="stat-value text-success text-2xl">{activeDayCount}</div>
					<div class="stat-desc">With activities</div>
				</div>
				<div class="stat bg-info/10 rounded-lg p-4">
					<div class="stat-title text-xs">Visits</div>
					<div class="stat-value text-info text-2xl">{visitsInRange.length}</div>
					<div class="stat-desc">Total visits</div>
				</div>
				<div class="stat bg-warning/10 rounded-lg p-4">
					<div class="stat-title text-xs">Nights</div>
					<div class="stat-value text-warning text-2xl">{lodgingNights}</div>
					<div class="stat-desc">{lodgingStays.length} stays</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Distance Breakdown -->
	{#if totalDistance > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2 mb-2">
					<span class="text-2xl">🛣️</span>
					Distance Traveled
				</h3>

				<div
					class="flex items-center justify-center p-6 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-lg mb-4"
				>
					<div class="text-center">
						<div class="text-5xl font-bold text-primary">
							{numberFormatter.format(totalDistance)}
						</div>
						<div class="text-sm opacity-70 mt-1">{getDistanceUnitLong()} traveled</div>
					</div>
				</div>

				{#if distanceByTransportType.length > 0}
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
						{#each distanceByTransportType as [icon, distance]}
							<div class="stat bg-base-300 rounded-lg p-3">
								<div class="stat-figure text-3xl">{icon}</div>
								<div class="stat-value text-lg">{numberFormatter.format(distance)}</div>
								<div class="stat-desc text-xs">{getDistanceUnitLong()}</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}
	<!-- Activities Stats -->
	{#if activitiesInRange.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2 mb-2">
					<span class="text-2xl">🏃</span>
					Physical Activities
				</h3>

				<div class="stats stats-vertical sm:stats-horizontal shadow mb-4">
					<div class="stat bg-accent/10">
						<div class="stat-figure text-accent text-3xl">🎯</div>
						<div class="stat-title">Activities</div>
						<div class="stat-value text-accent">{activitiesInRange.length}</div>
						<div class="stat-desc">Total recorded</div>
					</div>
					<div class="stat bg-info/10">
						<div class="stat-figure text-info text-3xl">📏</div>
						<div class="stat-title">Distance</div>
						<div class="stat-value text-info">
							{distanceFormatter.format(totalActivityDistance)}
						</div>
						<div class="stat-desc">{getDistanceUnitLong()}</div>
					</div>
					<div class="stat bg-success/10">
						<div class="stat-figure text-success text-3xl">⛰️</div>
						<div class="stat-title">Elevation</div>
						<div class="stat-value text-success">
							{numberFormatter.format(totalActivityElevation)}
						</div>
						<div class="stat-desc">{getElevationUnitLong()} gained</div>
					</div>
					<div class="stat bg-warning/10">
						<div class="stat-figure text-warning text-3xl">🔥</div>
						<div class="stat-title">Calories</div>
						<div class="stat-value text-warning">
							{compactFormatter.format(totalActivityCalories)}
						</div>
						<div class="stat-desc">burned</div>
					</div>
				</div>

				{#if sportTypes.length > 0}
					<div>
						<h4 class="font-semibold mb-2">Sport Types</h4>
						<div class="flex flex-wrap gap-2">
							{#each sportTypes as [sport, count]}
								<span class="badge badge-lg badge-primary badge-outline">
									{sport} ({count})
								</span>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Content & Media -->
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h3 class="card-title text-xl flex items-center gap-2 mb-2">
				<span class="text-2xl">📱</span>
				Content & Media
			</h3>

			<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
				<div
					class="stat bg-gradient-to-br from-primary/20 to-primary/5 rounded-lg p-4 border border-primary/30"
				>
					<div class="stat-figure text-primary text-3xl">📸</div>
					<div class="stat-title text-xs">Photos</div>
					<div class="stat-value text-primary text-2xl">
						{numberFormatter.format(imagesInRange)}
					</div>
					<div class="stat-desc">Images</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-secondary/20 to-secondary/5 rounded-lg p-4 border border-secondary/30"
				>
					<div class="stat-figure text-secondary text-3xl">📝</div>
					<div class="stat-title text-xs">Notes</div>
					<div class="stat-value text-secondary text-2xl">{notesInRange.length}</div>
					<div class="stat-desc">Written</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-accent/20 to-accent/5 rounded-lg p-4 border border-accent/30"
				>
					<div class="stat-figure text-accent text-3xl">✅</div>
					<div class="stat-title text-xs">Checklists</div>
					<div class="stat-value text-accent text-2xl">{checklistsInRange.length}</div>
					<div class="stat-desc">Lists</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-info/20 to-info/5 rounded-lg p-4 border border-info/30"
				>
					<div class="stat-figure text-info text-3xl">🚆</div>
					<div class="stat-title text-xs">Transport</div>
					<div class="stat-value text-info text-2xl">{transportSegments.length}</div>
					<div class="stat-desc">Segments</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-success/20 to-success/5 rounded-lg p-4 border border-success/30"
				>
					<div class="stat-figure text-success text-3xl">🏨</div>
					<div class="stat-title text-xs">Lodging</div>
					<div class="stat-value text-success text-2xl">{lodgingStays.length}</div>
					<div class="stat-desc">Places</div>
				</div>

				<div
					class="stat bg-gradient-to-br from-warning/20 to-warning/5 rounded-lg p-4 border border-warning/30"
				>
					<div class="stat-figure text-warning text-3xl">📍</div>
					<div class="stat-title text-xs">Locations</div>
					<div class="stat-value text-warning text-2xl">{visitedLocations.length}</div>
					<div class="stat-desc">Visited</div>
				</div>

				{#if totalAttachments > 0}
					<div
						class="stat bg-gradient-to-br from-error/20 to-error/5 rounded-lg p-4 border border-error/30"
					>
						<div class="stat-figure text-error text-3xl">📎</div>
						<div class="stat-title text-xs">Attachments</div>
						<div class="stat-value text-error text-2xl">{totalAttachments}</div>
						<div class="stat-desc">Files</div>
					</div>
				{/if}
			</div>

			<!-- Additional Stats Row -->
			{#if averageLocationRating > 0 || checklistStats.total > 0 || lodgingTypeBreakdown.length > 0}
				<div class="divider">More Details</div>
				<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
					{#if averageLocationRating > 0}
						<div class="stat bg-base-300 rounded-lg p-4">
							<div class="stat-figure text-2xl">⭐</div>
							<div class="stat-title text-xs">Avg Rating</div>
							<div class="stat-value text-lg">{averageLocationRating.toFixed(1)}</div>
							<div class="stat-desc text-xs">of locations</div>
						</div>
					{/if}

					{#if checklistStats.total > 0}
						<div class="stat bg-base-300 rounded-lg p-4">
							<div class="stat-figure text-2xl">✓</div>
							<div class="stat-title text-xs">Tasks Done</div>
							<div class="stat-value text-lg">{checklistStats.percentage}%</div>
							<div class="stat-desc text-xs">
								{checklistStats.checked}/{checklistStats.total} items
							</div>
						</div>
					{/if}

					{#if lodgingTypeBreakdown.length > 0}
						<div class="stat bg-base-300 rounded-lg p-4">
							<div class="stat-figure text-2xl">🛏️</div>
							<div class="stat-title text-xs">Lodging Types</div>
							<div class="stat-value text-lg">{lodgingTypeBreakdown.length}</div>
							<div class="stat-desc text-xs truncate">
								{getLodgingIcon(lodgingTypeBreakdown[0][0])}
								{capitalize(lodgingTypeBreakdown[0][0])}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Categories -->
	{#if categoriesWithIcons.length > 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2">
					<span class="text-2xl">🏷️</span>
					Categories
				</h3>
				<div class="flex flex-wrap gap-2">
					{#each categoriesWithIcons as category}
						<div class="badge badge-lg badge-primary badge-outline p-3 flex items-center gap-2">
							<span class="text-lg">{category.icon}</span>
							<span class="font-medium">{category.name}</span>
							<span class="badge badge-xs badge-primary">{category.count}</span>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Lodging Types Breakdown -->
	{#if lodgingTypeBreakdown.length > 1}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body">
				<h3 class="card-title text-xl flex items-center gap-2">
					<span class="text-2xl">🏨</span>
					Lodging Types
				</h3>
				<div class="flex flex-wrap gap-2">
					{#each lodgingTypeBreakdown as [type, count]}
						<div class="badge badge-lg badge-success badge-outline p-3 flex items-center gap-2">
							<span class="text-lg">{getLodgingIcon(type)}</span>
							<span class="font-medium">{capitalize(type)}</span>
							<span class="badge badge-xs badge-success ml-2">{count}</span>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
