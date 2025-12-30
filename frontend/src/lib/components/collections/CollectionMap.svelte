<script lang="ts">
	import FullMap, { type FullMapFeatureCollection } from '$lib/components/map/FullMap.svelte';
	import { GeoJSON, LineLayer, Marker } from 'svelte-maplibre';
	import { goto } from '$app/navigation';
	import { getActivityColor } from '$lib';
	import type { Collection } from '$lib/types';
	import { onMount } from 'svelte';

	export let collection: Collection;
	// Allow disabling/enabling clustering for markers
	export let clusterEnabled: boolean = false;
	export let clusterOptions: any = { radius: 300, maxZoom: 8, minPoints: 2 };

	// Build marker features from collection.locations
	function locationToFeature(loc: any) {
		const lat = loc?.latitude !== undefined && loc?.latitude !== null ? Number(loc.latitude) : null;
		const lon =
			loc?.longitude !== undefined && loc?.longitude !== null ? Number(loc.longitude) : null;
		if (lat === null || lon === null) return null;
		return {
			type: 'Feature' as const,
			geometry: { type: 'Point' as const, coordinates: [lon, lat] as [number, number] },
			properties: {
				id: loc.id,
				name: loc.name,
				visitStatus: loc.is_visited ? 'visited' : 'planned',
				categoryIcon: loc.category?.icon || '📍'
			}
		};
	}

	// Merge attachments/activity geojson into a single feature collection
	function collectLinesGeojson(coll: Collection) {
		if (!coll) return null;
		const features: any[] = [];

		// Locations: attachments and visits -> activities
		for (const loc of coll.locations || []) {
			if (Array.isArray(loc.attachments)) {
				for (const a of loc.attachments) {
					if (!a || !a.geojson) continue;
					if (a.geojson.type === 'FeatureCollection' && Array.isArray(a.geojson.features)) {
						features.push(...a.geojson.features);
					} else if (a.geojson.type === 'Feature') {
						features.push(a.geojson);
					}
				}
			}

			if (Array.isArray(loc.visits)) {
				for (const visit of loc.visits) {
					if (!visit.activities) continue;
					for (const activity of visit.activities) {
						if (activity && activity.geojson) {
							// normalize features and inject activity-type color
							const color = getActivityColor(activity.sport_type || (activity as any).type || '');
							if (
								activity.geojson.type === 'FeatureCollection' &&
								Array.isArray(activity.geojson.features)
							) {
								for (const f of activity.geojson.features) {
									if (f && typeof f === 'object') {
										f.properties = f.properties || {};
										f.properties._color = color;
										f.properties.activity_type =
											activity.sport_type || (activity as any).type || null;
										features.push(f);
									}
								}
							} else if (activity.geojson.type === 'Feature') {
								const f = activity.geojson as any;
								f.properties = f.properties || {};
								f.properties._color = color;
								f.properties.activity_type = activity.sport_type || (activity as any).type || null;
								features.push(f);
							}
						}
					}
				}
			}
		}

		// Transportations: attachments
		for (const t of coll.transportations || []) {
			if (!t || !Array.isArray(t.attachments)) continue;
			for (const a of t.attachments) {
				if (!a || !a.geojson) continue;
				if (a.geojson.type === 'FeatureCollection' && Array.isArray(a.geojson.features)) {
					for (const f of a.geojson.features) {
						if (f && typeof f === 'object') {
							f.properties = f.properties || {};
							// default transport attachments to a neutral blue color
							f.properties._color = f.properties._color || '#60a5fa';
							features.push(f);
						}
					}
				} else if (a.geojson.type === 'Feature') {
					const f = a.geojson as any;
					f.properties = f.properties || {};
					f.properties._color = f.properties._color || '#60a5fa';
					features.push(f);
				}
			}
		}

		if (features.length === 0) return null;
		return { type: 'FeatureCollection', features };
	}

	// Marker GeoJSON for FullMap
	$: markerGeoJson = {
		type: 'FeatureCollection' as const,
		features: (collection?.locations || []).map(locationToFeature).filter((f) => f !== null)
	} as FullMapFeatureCollection;

	$: linesGeoJson = collectLinesGeojson(collection) as {
		type: 'FeatureCollection';
		features: any[];
	} | null;

	// Return gradient classes matching map page markers for visit status
	function getVisitStatusClass(status: string | null | undefined) {
		if (!status) return 'bg-gray-200';
		if (status === 'visited') return 'bg-gradient-to-br from-emerald-400 to-emerald-600';
		if (status === 'planned') return 'bg-gradient-to-br from-blue-400 to-blue-600';
		return 'bg-gray-200';
	}

	// Compute bounds from geojson features
	function computeBoundsFromGeoJSON(geo: any) {
		if (!geo || !geo.features || !geo.features.length) return null;
		let minLon = Infinity,
			minLat = Infinity,
			maxLon = -Infinity,
			maxLat = -Infinity;
		const pushPoint = (c: number[]) => {
			if (!Array.isArray(c) || c.length < 2) return;
			const lon = Number(c[0]);
			const lat = Number(c[1]);
			if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
			if (lon < minLon) minLon = lon;
			if (lon > maxLon) maxLon = lon;
			if (lat < minLat) minLat = lat;
			if (lat > maxLat) maxLat = lat;
		};

		for (const feat of geo.features) {
			const geom = feat.geometry;
			if (!geom) continue;
			const type = geom.type;
			const coords = geom.coordinates;
			if (!coords) continue;
			if (type === 'Point') pushPoint(coords as number[]);
			else if (type === 'LineString' || type === 'MultiPoint') {
				for (const c of coords as any[]) pushPoint(c);
			} else if (type === 'MultiLineString' || type === 'Polygon') {
				for (const part of coords as any[]) {
					for (const c of part) pushPoint(c);
				}
			} else if (type === 'MultiPolygon') {
				for (const poly of coords as any[])
					for (const ring of poly) for (const c of ring) pushPoint(c);
			}
		}

		if (minLon === Infinity) return null;
		return [
			[minLon, minLat],
			[maxLon, maxLat]
		];
	}

	// Fit bounds when map and lines are available
	let mapRef: any = null;
	$: if (mapRef && linesGeoJson) {
		const b = computeBoundsFromGeoJSON(linesGeoJson);
		if (b) {
			try {
				mapRef.fitBounds(b, { padding: 40 });
			} catch (e) {
				// ignore
			}
		}
	}
</script>

<div class="w-full" style="min-height:600px; height:600px;">
	<FullMap
		geoJson={markerGeoJson}
		center={markerGeoJson.features.length ? markerGeoJson.features[0].geometry.coordinates : [0, 0]}
		zoom={8}
		mapClass="w-full h-[600px]"
		{clusterEnabled}
		{clusterOptions}
	>
		<svelte:fragment slot="overlays" let:map>
			{#if linesGeoJson}
				{@const _ = mapRef = map}
				<GeoJSON data={linesGeoJson}>
					<LineLayer
						id="collection-lines"
						paint={{
							// read per-feature baked color `_color`, fallback to blue
							'line-color': ['coalesce', ['get', '_color'], '#60a5fa'],
							'line-width': 3,
							'line-opacity': 0.9
						}}
					/>
				</GeoJSON>
			{/if}
		</svelte:fragment>

		<svelte:fragment slot="marker" let:markerProps let:markerLngLat let:isActive let:setActive>
			{#if markerProps && markerLngLat}
				<Marker lngLat={markerLngLat} class={isActive ? 'map-pin-active' : 'map-pin'}>
					<div class="relative group z-[1000] group-hover:z-[10000] focus-within:z-[10000]">
						<div
							class="map-pin-hit grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-lg text-base cursor-pointer group-hover:scale-110 transition-all duration-200 {getVisitStatusClass(
								markerProps.visitStatus
							)}"
							class:scale-110={isActive}
							role="button"
							tabindex="0"
							on:mouseenter={() => setActive(true)}
							on:mouseleave={() => setActive(false)}
							on:focus={() => setActive(true)}
							on:blur={() => setActive(false)}
							on:click={(e) => {
								e.stopPropagation();
								goto(`/locations/${markerProps.id}`);
							}}
							on:keydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									e.stopPropagation();
									goto(`/locations/${markerProps.id}`);
								}
							}}
						>
							{markerProps.categoryIcon || '📍'}
						</div>

						<div
							class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-all duration-200 z-[9999]"
							class:opacity-100={isActive}
							class:pointer-events-auto={isActive}
						>
							<div
								class="card card-compact bg-base-100 shadow-xl border border-base-300 min-w-56 max-w-80"
							>
								<div class="card-body gap-3">
									<div class="space-y-2">
										<div class="min-w-0">
											<h3 class="card-title text-sm leading-tight truncate">{markerProps.name}</h3>
											<div class="mt-1 flex items-center gap-2">
												<div
													class="badge badge-sm {markerProps.visitStatus === 'visited'
														? 'badge-success'
														: 'badge-info'}"
												>
													{markerProps.visitStatus === 'visited' ? 'Visited' : 'Planned'}
												</div>
												{#if markerProps.categoryIcon}
													<div class="badge badge-ghost badge-sm">{markerProps.categoryIcon}</div>
												{/if}
											</div>
										</div>
									</div>
									<div class="card-actions">
										<button
											class="btn btn-xs"
											on:click|stopPropagation={() => goto(`/locations/${markerProps.id}`)}
											>Open</button
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				</Marker>
			{/if}
		</svelte:fragment>
	</FullMap>
</div>

<style>
	:global(.min-h-\[600px\]) {
		min-height: 600px;
	}
</style>
