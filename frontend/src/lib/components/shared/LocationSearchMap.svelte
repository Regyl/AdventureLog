<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { MapLibre, Marker, MapEvents } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { getBasemapUrl } from '$lib';

	import SearchIcon from '~icons/mdi/magnify';
	import LocationIcon from '~icons/mdi/crosshairs-gps';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';
	import ClearIcon from '~icons/mdi/close';
	import PinIcon from '~icons/mdi/map-marker';

	type GeoSelection = {
		name: string;
		lat: number;
		lng: number;
		location: string;
		type?: string;
		category?: string;
	};

	type LocationMeta = {
		city?: { name: string; id: string; visited: boolean };
		region?: { name: string; id: string; visited: boolean };
		country?: { name: string; country_code: string; visited: boolean };
		display_name?: string;
		location_name?: string;
	};

	const dispatch = createEventDispatcher();

	export let initialSelection: GeoSelection | null = null;
	export let searchQuery = '';
	export let displayName = '';
	export let showDisplayNameInput = true;
	export let displayNamePosition: 'before' | 'after' = 'before';
	export let displayNameLabel = '';
	export let displayNamePlaceholder = '';
	export let isReverseGeocoding = false;

	let isSearching = false;
	let searchResults: GeoSelection[] = [];
	let selectedLocation: GeoSelection | null = null;
	let selectedMarker: { lng: number; lat: number } | null = null;
	let locationData: LocationMeta | null = null;
	let mapCenter: [number, number] = [-74.5, 40];
	let mapZoom = 2;
	let mapComponent: any;
	let searchTimeout: ReturnType<typeof setTimeout>;
	let initialApplied = false;

	async function applyInitialSelection(selection: GeoSelection) {
		selectedLocation = selection;
		selectedMarker = { lng: selection.lng, lat: selection.lat };
		mapCenter = [selection.lng, selection.lat];
		mapZoom = 14;
		searchQuery = selection.name || '';
		displayName = selection.location || selection.name;
		await performDetailedReverseGeocode(selection.lat, selection.lng);
	}

	async function searchLocations(query: string) {
		if (!query.trim() || query.length < 3) {
			searchResults = [];
			return;
		}

		isSearching = true;
		try {
			const response = await fetch(
				`/api/reverse-geocode/search/?query=${encodeURIComponent(query)}`
			);
			const results = await response.json();

			searchResults = results.map((result: any) => ({
				id: result.name + result.lat + result.lon,
				name: result.name,
				lat: parseFloat(result.lat),
				lng: parseFloat(result.lon),
				type: result.type,
				category: result.category,
				location: result.display_name,
				importance: result.importance,
				powered_by: result.powered_by
			}));
		} catch (error) {
			console.error('Search error:', error);
			searchResults = [];
		} finally {
			isSearching = false;
		}
	}

	function handleSearchInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchLocations(searchQuery);
		}, 300);
	}

	function emitUpdate(selection: GeoSelection) {
		dispatch('update', {
			name: selection.name,
			lat: selection.lat,
			lng: selection.lng,
			location: selection.location
		});
	}

	async function selectSearchResult(searchResult: GeoSelection) {
		selectedLocation = searchResult;
		selectedMarker = { lng: searchResult.lng, lat: searchResult.lat };
		mapCenter = [searchResult.lng, searchResult.lat];
		mapZoom = 14;
		searchResults = [];
		searchQuery = searchResult.name;

		displayName = searchResult.location || searchResult.name;

		emitUpdate(searchResult);
		await performDetailedReverseGeocode(searchResult.lat, searchResult.lng);
	}

	async function handleMapClick(e: { detail: { lngLat: { lng: number; lat: number } } }) {
		selectedMarker = {
			lng: e.detail.lngLat.lng,
			lat: e.detail.lngLat.lat
		};

		await reverseGeocode(e.detail.lngLat.lng, e.detail.lngLat.lat);
	}

	async function reverseGeocode(lng: number, lat: number) {
		isReverseGeocoding = true;

		try {
			const response = await fetch(`/api/reverse-geocode/search/?query=${lat},${lng}`);
			const results = await response.json();

			if (results && results.length > 0) {
				const result = results[0];
				selectedLocation = {
					name: result.name,
					lat: lat,
					lng: lng,
					location: result.display_name,
					type: result.type,
					category: result.category
				};
				searchQuery = result.name;
				displayName = result.display_name || result.name;
			} else {
				selectedLocation = {
					name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
					lat: lat,
					lng: lng,
					location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
				};
				searchQuery = selectedLocation.name;
				displayName = selectedLocation.location;
			}

			if (selectedLocation) {
				emitUpdate(selectedLocation);
			}

			await performDetailedReverseGeocode(lat, lng);
		} catch (error) {
			console.error('Reverse geocoding error:', error);
			selectedLocation = {
				name: `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
				lat: lat,
				lng: lng,
				location: `${lat.toFixed(4)}, ${lng.toFixed(4)}`
			};
			searchQuery = selectedLocation.name;
			if (!displayName) displayName = selectedLocation.location;
			locationData = null;
			if (selectedLocation) emitUpdate(selectedLocation);
		} finally {
			isReverseGeocoding = false;
		}
	}

	async function performDetailedReverseGeocode(lat: number, lng: number) {
		try {
			const response = await fetch(
				`/api/reverse-geocode/reverse_geocode/?lat=${lat}&lon=${lng}&format=json`
			);

			if (response.ok) {
				const data = await response.json();
				locationData = {
					city: data.city
						? {
								name: data.city,
								id: data.city_id,
								visited: data.city_visited || false
							}
						: undefined,
					region: data.region
						? {
								name: data.region,
								id: data.region_id,
								visited: data.region_visited || false
							}
						: undefined,
					country: data.country
						? {
								name: data.country,
								country_code: data.country_id,
								visited: false
							}
						: undefined,
					display_name: data.display_name,
					location_name: data.location_name
				};
				displayName = data.display_name;
			} else {
				locationData = null;
			}
		} catch (error) {
			console.error('Detailed reverse geocoding error:', error);
			locationData = null;
		}
	}

	function useCurrentLocation() {
		if ('geolocation' in navigator) {
			navigator.geolocation.getCurrentPosition(
				async (position) => {
					const lat = position.coords.latitude;
					const lng = position.coords.longitude;
					selectedMarker = { lng, lat };
					mapCenter = [lng, lat];
					mapZoom = 14;
					await reverseGeocode(lng, lat);
				},
				(error) => {
					console.error('Geolocation error:', error);
				}
			);
		}
	}

	function clearLocationSelection() {
		selectedLocation = null;
		selectedMarker = null;
		locationData = null;
		searchQuery = '';
		searchResults = [];
		displayName = '';
		mapCenter = [-74.5, 40];
		mapZoom = 2;
		dispatch('clear');
	}

	$: if (!initialApplied && initialSelection) {
		initialApplied = true;
		applyInitialSelection(initialSelection);
	}
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
	<div class="space-y-4">
		{#if showDisplayNameInput && displayNamePosition === 'before'}
			<div class="form-control">
				<label class="label" for="location-display">
					<span class="label-text font-medium">
						{displayNameLabel || $t('adventures.location_display_name')}
					</span>
				</label>
				<input
					type="text"
					id="location-display"
					bind:value={displayName}
					class="input input-bordered bg-base-100/80 focus:bg-base-100"
					placeholder={displayNamePlaceholder || 'Enter location display name'}
				/>
			</div>
		{/if}

		<div class="form-control">
			<label class="label" for="search-location">
				<span class="label-text font-medium">{$t('adventures.search_location')}</span>
			</label>
			<div class="relative">
				<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
					<SearchIcon class="w-4 h-4 text-base-content/40" />
				</div>
				<input
					type="text"
					id="search-location"
					bind:value={searchQuery}
					on:input={handleSearchInput}
					placeholder="Enter city, location, or landmark..."
					class="input input-bordered w-full pl-10 pr-4 bg-base-100/80 focus:bg-base-100"
					class:input-primary={selectedLocation}
				/>
				{#if searchQuery && !selectedLocation}
					<button
						class="absolute inset-y-0 right-0 pr-3 flex items-center"
						on:click={clearLocationSelection}
					>
						<ClearIcon class="w-4 h-4 text-base-content/40 hover:text-base-content" />
					</button>
				{/if}
			</div>
		</div>

		{#if isSearching}
			<div class="flex items-center justify-center py-4">
				<span class="loading loading-spinner loading-sm"></span>
				<span class="ml-2 text-sm text-base-content/60">{$t('adventures.searching')}...</span>
			</div>
		{:else if searchResults.length > 0}
			<div class="space-y-2">
				<div class="label">
					<span class="label-text text-sm font-medium">{$t('adventures.search_results')}</span>
				</div>
				<div class="max-h-48 overflow-y-auto space-y-1">
					{#each searchResults as result}
						<button
							class="w-full text-left p-3 rounded-lg border border-base-300 hover:bg-base-100 hover:border-primary/50 transition-colors"
							on:click={() => selectSearchResult(result)}
						>
							<div class="flex items-start gap-3">
								<PinIcon class="w-4 h-4 text-primary mt-1 flex-shrink-0" />
								<div class="min-w-0 flex-1">
									<div class="font-medium text-sm truncate">{result.name}</div>
									<div class="text-xs text-base-content/60 truncate">{result.location}</div>
									{#if result.category}
										<div class="text-xs text-primary/70 capitalize">{result.category}</div>
									{/if}
								</div>
							</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<div class="flex items-center gap-2">
			<div class="divider divider-horizontal text-xs">{$t('adventures.or')}</div>
		</div>

		<button class="btn btn-outline gap-2 w-full" on:click={useCurrentLocation}>
			<LocationIcon class="w-4 h-4" />
			{$t('adventures.use_current_location')}
		</button>

		{#if showDisplayNameInput && displayNamePosition === 'after'}
			<div class="form-control">
				<label class="label" for="location-display-after">
					<span class="label-text font-medium">
						{displayNameLabel || $t('adventures.location_display_name')}
					</span>
				</label>
				<input
					type="text"
					id="location-display-after"
					bind:value={displayName}
					class="input input-bordered bg-base-100/80 focus:bg-base-100"
					placeholder={displayNamePlaceholder || 'Enter location display name'}
				/>
			</div>
		{/if}

		{#if selectedLocation && selectedMarker}
			<div class="card bg-success/10 border border-success/30">
				<div class="card-body p-4">
					<div class="flex items-start gap-3">
						<div class="p-2 bg-success/20 rounded-lg">
							<CheckIcon class="w-4 h-4 text-success" />
						</div>
						<div class="flex-1 min-w-0">
							<h4 class="font-semibold text-success mb-1">{$t('adventures.location_selected')}</h4>
							<p class="text-sm text-base-content/80 truncate">{selectedLocation.name}</p>
							<p class="text-xs text-base-content/60 mt-1">
								{selectedMarker.lat.toFixed(6)}, {selectedMarker.lng.toFixed(6)}
							</p>

							{#if locationData?.city || locationData?.region || locationData?.country}
								<div class="flex flex-wrap gap-2 mt-3">
									{#if locationData.city}
										<div class="badge badge-info badge-sm gap-1">
											🏙️ {locationData.city.name}
										</div>
									{/if}
									{#if locationData.region}
										<div class="badge badge-warning badge-sm gap-1">
											🗺️ {locationData.region.name}
										</div>
									{/if}
									{#if locationData.country}
										<div class="badge badge-success badge-sm gap-1">
											🌎 {locationData.country.name}
										</div>
									{/if}
								</div>
							{/if}
						</div>
						<button class="btn btn-ghost btn-sm" on:click={clearLocationSelection}>
							<ClearIcon class="w-4 h-4" />
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<div class="label">
				<span class="label-text font-medium">{$t('worldtravel.interactive_map')}</span>
			</div>
			{#if isReverseGeocoding}
				<div class="flex items-center gap-2">
					<span class="loading loading-spinner loading-sm"></span>
					<span class="text-sm text-base-content/60"
						>{$t('worldtravel.getting_location_details')}...</span
					>
				</div>
			{/if}
		</div>

		<div class="relative">
			<MapLibre
				bind:this={mapComponent}
				style={getBasemapUrl()}
				class="w-full h-80 rounded-lg border border-base-300"
				center={mapCenter}
				zoom={mapZoom}
				standardControls
			>
				<MapEvents on:click={handleMapClick} />

				{#if selectedMarker}
					<Marker
						lngLat={[selectedMarker.lng, selectedMarker.lat]}
						class="grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-primary shadow-lg cursor-pointer"
					>
						<PinIcon class="w-5 h-5 text-primary-content" />
					</Marker>
				{/if}
			</MapLibre>
		</div>

		{#if !selectedMarker}
			<p class="text-sm text-base-content/60 text-center">{$t('adventures.click_on_map')}</p>
		{/if}
	</div>
</div>
